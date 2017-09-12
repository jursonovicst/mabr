import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import urllib2
import dash
import Queue
import traceback

import imp
try:
  imp.find_module('memcache')
except ImportError:
  print("This scrypt requires memcache python library, please install python-memcache!")
  exit(1)
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
            self._ingestproxy = ingestproxy
            self._mcip = mcip
            self._memcachedaddress = memcachedaddress
            self._memcached = memcache.Client([memcachedaddress], debug=0)

            self._multicastdelivery = []

            super(CustomHandler, self).__init__(*args, **kwargs)

        def do_GET(self):


            #Check Host header
            if 'Host' not in self.headers:
                self.send_response(400)
                self.wfile.write("No Host header specified.")
                self._logger.warning("No Host header specified.")
                return

            if not Channel.validatefqdn(self.headers['Host']):
                self.send_response(401)
                self.wfile.write("FQDN '%s' not configured to proxy." % self.headers['Host'])
                self._logger.warning("FQDN '%s' not configured to proxy." % self.headers['Host'])
                return

            requesturl = 'http://' + self.headers['Host'] + self.path
            try:

                ######################
                # mpd                #
                ######################
                channel = Channel.getChannelByID(self.headers['Host'], self.path)
                if channel is not None:
                    # match on one channel
                    self._logger.debug("parse mpd: '%s'" % requesturl)

                    # Parse mpd
                    mpd = self.passthrough(channel.getMPDIngestUrl())
                    mpdparser = dash.MPDParser(mpd)

                    # parse url templates for multicast
                    for template, representationid in mpdparser.getMediaPatterns():
                        mediapattern = os.path.dirname(self.path) + '/' + template

                        channel.findStream(representationid).setMedia(mediapattern)
                        self._logger.debug("Add '%s' pattern for multicast delivery." % mediapattern)

                    # parse url templates for multicast
                    for template, representationid in mpdparser.getInitializationPatterns():
                        initializationpattern = os.path.dirname(self.path) + '/' + template

                        channel.findStream(representationid).setInitialization(initializationpattern)
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
                channel = Channel.getChannelByChunk(self.headers['Host'], self.path)
                if channel is not None:
                    #check, if the whole fragment is in memcached
                    chunk = self._memcached.get(channel.getIngestUrl(self.path))

                    if not chunk:
                        self._logger.debug("cache miss: '%s'" % requesturl)
                        self.passthrough(channel.getIngestUrl(self.path))
                    else:
                        self._logger.debug("cache hit: '%s' " % requesturl)
                        self.respond(chunk)

                    return

                ######################
                # initialization     #
                ######################
                channel = Channel.getChannelByInitSegment(self.headers['Host'], self.path)
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

            except Exception as e:
                self.send_response(501)
                self.wfile.write("Internal server error: %s." % e.message)
                self._logger.warning("Internal server error: %s." % e.message)
                self._logger.debug(traceback.format_exc())

                return

            return

        def passthrough(self, url):
            proxy_handler = urllib2.ProxyHandler({'http': self._ingestproxy})
            opener = urllib2.build_opener(proxy_handler)
            buff = None
            res = None

            res = opener.open(url)

            self.send_response(res.getcode())
            for key in res.info():
                self.send_header(key, res.info()[key])
            self.end_headers()
            buff = res.read()
            self.wfile.write(buff)

#                self._logger.info("Passthrough url '%s'" % url)

            return buff

        def respond(self, buff):
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(buff)

            except Exception as e:
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
        except KeyboardInterrupt:
            self._logger.debug("received interrupt signal...")
        except Exception as e:
            self._logger.warning("Oops: %s, ..." % str(e))
        finally:
            self.stop()

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None

        if self._stitcher is not None:
            self._stitcher.stop()
            self._stitcher.join(1)
            self._stitcher = None


