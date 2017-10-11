import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import urllib2
import dash
import Queue
import traceback
import sys
import re


import imp
try:
    imp.find_module('memcache')
except ImportError:
    raise Exception("This script requires memcache python library, please install python-memcache!")
import memcache


from receiver import Receiver
from stitcher import Stitcher
from channels import *
import time

def MakeHandlerClass(logger, ingestproxy, mcip, memcachedaddress):
    class CustomHandler(BaseHTTPRequestHandler, object):

        _urltemplates = []
        _jobs = {}

        @staticmethod
        def stop():
            for key in CustomHandler._jobs:
                p = CustomHandler._jobs.pop(key)
                p.stop()

        def __init__(self, *args, **kwargs):
            self._logger = logger
            self._ingestproxy = None if ingestproxy == None or ingestproxy =="" else {'http': ingestproxy}
            self._mcip = mcip
            self._memcachedaddress = memcachedaddress
            self._memcached = memcache.Client([memcachedaddress], debug=0)

            self._multicastdelivery = []

            super(CustomHandler, self).__init__(*args, **kwargs)

        def do_GET(self):


            # check Host header
            if 'Host' not in self.headers:
                self.send_response(400)
                self.wfile.write("No Host header specified.")
                self._logger.warning("No Host header specified.")
                return

            # remove port from url if any
            host = re.sub(':\d+$', '', self.headers['Host'])

            # check if FQDN matches with channel configured
            if not Channel.validateFQDN(host):
                self.send_response(401)
                self.wfile.write("FQDN '%s' not configured to proxy." % host)
                self._logger.warning("FQDN '%s' not configured to proxy." % host)
                return

            requesturl = 'http://' + host + self.path
            try:

                ######################
                # mpd                #
                ######################

                # find channel (if any)
                channel = Channel.getChannelByMPDURL(host, self.path)
                if channel is not None:
                    # match on one channel
                    self._logger.debug("parse mpd: '%s'" % requesturl)

                    # Parse mpd
                    mpd = self.passthrough(channel.getMPDIngestUrl())
                    mpdparser = dash.MPDParser(mpd)

                    # parse url templates for multicast
                    for template, representationid in mpdparser.getMediaPatterns():
                        mediapattern = os.path.dirname(self.path) + '/' + template

                        channel.findStream(representationid).setMediaPattern(mediapattern)
                        self._logger.debug("Add '%s' pattern for multicast delivery." % mediapattern)

                    # parse url templates for multicast
                    for template, representationid in mpdparser.getInitializationPatterns():
                        initializationpattern = os.path.dirname(self.path) + '/' + template

                        channel.findStream(representationid).setInitializationPattern(initializationpattern)
                        self._logger.debug("Add '%s' pattern for passthrough." % initializationpattern)


                    # Start multicast receivers, if not already running
                    for stream in channel.getStreams():
                        mcast_grp, mcast_port, ssrc = stream.getMCParam()
                        receiverid = mcast_grp + ':' + str(mcast_port)
                        if receiverid not in CustomHandler._jobs or not CustomHandler._jobs[receiverid].is_alive():
                            p = Receiver(name="receiver-%s" % receiverid, args=(self._logger.getChild("Receiver"), self._mcip, self._memcachedaddress, stream))
                            CustomHandler._jobs[receiverid] = p
                            p.start()

                    return

                ######################
                # media              #
                ######################
                channel, stream = Channel.getChannelByURL(host, self.path)
                if channel is not None and stream is not None:
                    #check, if the whole fragment is in memcached
                    chunk = self._memcached.get(Chunk.getmemcachedkey(stream.getSSRC(), stream.getChunknumberFromPath(self.path)))

                    if not chunk:
                        self._logger.warning("cache miss: '%s'" % requesturl)
                        self.passthrough(channel.getIngestUrl(self.path))
                    else:
                        self._logger.debug("cache hit: '%s' " % requesturl)
                        self.respond(chunk)

                    return

                ######################
                # initialization     #
                ######################
                channel = Channel.getChannelByInitSegmentURL(host, self.path)
                if channel is not None:
                    self._logger.debug("cache passthg: '%s'" % requesturl)
                    self.passthrough(channel.getIngestUrl(self.path))

                    return

                # Deny
                self.send_response(404)
                self.wfile.write("Request %s os not part of an MPEG-DASH stream." % requesturl)
                self._logger.warning("Request %s os not part of an MPEG-DASH stream." % requesturl)

            except urllib2.HTTPError as e:
                self.send_response(e.code)
                self.wfile.write(e.message)
                self._logger.debug(e.message)

            except urllib2.URLError as e:
                self.send_response(400)
                self.wfile.write("%s could not be reached: %s" % (e.url, e.reason))
                self._logger.debug("%s could not be reached: %s" % (e.url, e.reason))

            except Exception as e:
                self.send_response(500)
                self.wfile.write("Internal server error: %s." % e.message)
                self._logger.warning("Internal server error: %s." % e.message)
                self._logger.debug(traceback.format_exc())

            return

        def passthrough(self, url):
            proxy_handler = urllib2.ProxyHandler(self._ingestproxy)
            opener = urllib2.build_opener(proxy_handler)
            buff = None
            res = None

            try:
                res = opener.open(url)

                self.send_response(res.getcode())
                for key in res.info():
                    self.send_header(key, res.info()[key])
                self.end_headers()
                buff = res.read()
                self.wfile.write(buff)

                self._logger.debug("Passthrough url '%s'" % url)
            except urllib2.URLError as e:
                e.url = url
                raise e
            return buff

        def respond(self, buff):
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(buff)

            except Exception as e:
                print e.message
                self.send_response(500)
                self.wfile.write(e.message)


        #silence logging
        def log_message(self, format, *args):
            return

    return CustomHandler



class DASHProxy():

    def __init__(self, logger, ip, port, configfps, ingestproxy, mcip, memcachedaddress):

        self._logger = logger
        self._ip = ip
        self._port = int(port)

        # read all config files and add channels
        for configfp in configfps:
            Channel.append(configfp)

        # handler class for responding to http requests
        self._myhandler = MakeHandlerClass(self._logger.getChild("HTTPServer"), ingestproxy, mcip, memcachedaddress)
        self._server = None

        # used to trigger the stitching of RTP packets
        self._stitcher = Stitcher(name="stitcher", args=(self._logger.getChild("Stitcher"), memcachedaddress))

    def serve_requests(self):

        try:
            #start stitcher
            self._stitcher.start()

            #start HTTP server
            self._server = HTTPServer((self._ip, self._port), self._myhandler)

            self._logger.info("Handling requests on %s:%d" % (self._ip, self._port))

            # This will block and periodically check the shutdown signal
            self._server.serve_forever()
        except:
            self.stop()
            raise

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None

        if self._stitcher is not None:
            self._stitcher.stop()
            self._stitcher.join(1)
            self._stitcher = None


