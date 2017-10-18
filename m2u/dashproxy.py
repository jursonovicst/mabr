from memdb import MemDB
from receiver import Receiver
from stitcher import Stitcher
from channels import *

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os
import urllib2
import dash
import traceback
import sys
import re


def makehandlerclass(logger, ingestproxy, mcip, memdb):
    class CustomHandler(BaseHTTPRequestHandler, object):

        _urltemplates = []
        _receiverjobs = {}              # holds receiver threads listening to multicast streams

        @staticmethod
        def stop():
            # stop all receiver threads (and send multicast leave)
            for key in CustomHandler._receiverjobs:
                p = CustomHandler._receiverjobs.pop(key)
                p.stop()


        def __init__(self, *args, **kwargs):
            self._logger = logger
            self._ingestproxy = None if ingestproxy is None or ingestproxy == "" else {'http': ingestproxy}
            self._mcip = mcip
            self._memdb = memdb

            super(CustomHandler, self).__init__(*args, **kwargs)


        def do_GET(self):

            # check Host header
            if 'Host' not in self.headers:
                self.send_response(400)
                self.wfile.write("No Host header specified.")
                self._logger.warning("No Host header specified in request.")
                return

            # remove port from url if any
            host = re.sub(':\d+$', '', self.headers['Host'])

            # check if FQDN matches with channel configured
            if not Channel.validatefqdn(host):
                self.send_response(401)
                self.wfile.write("FQDN '%s' not configured to proxy." % host)
                self._logger.warning("FQDN '%s' not configured to proxy." % host)
                return

            requesturl = 'http://' + host + self.path
            try:
                # find channel (if any)
                channel = Channel.getchannelbympdurl(host, self.path)
                if channel is not None:
                    ######################
                    # mpd                #
                    ######################

                    # match on one channel
                    self._logger.info("parse mpd: '%s'" % requesturl)

                    # Parse mpd
                    mpd = self.passthrough(channel.getmpdingesturl())
                    mpdparser = dash.MPDParser(mpd)

                    # parse url templates for multicast
                    for template, representationid in mpdparser.getmediapatterns():
                        mediapattern = os.path.dirname(self.path) + '/' + template

                        channel.findstream(representationid).setmediapattern(mediapattern)
                        self._logger.debug("Set '%s' pattern for multicast delivery." % mediapattern)
                        self._logger.debug("Set '%s' pattern for multicast delivery." % mediapattern)

                    # parse url templates for initsegment
                    for template, representationid in mpdparser.getinitializationpatterns():
                        initializationpattern = os.path.dirname(self.path) + '/' + template

                        channel.findstream(representationid).setinitializationpattern(initializationpattern)
                        self._logger.debug("Set '%s' pattern for passthrough." % initializationpattern)

                    # parse mime-types
                    for mimetype, representationid in mpdparser.getmimetypes():
                        channel.findstream(representationid).setmimetype(mimetype)

                    # Start multicast receivers, if not already running
                    for stream in channel.getstreams():
                        mcast_grp, mcast_port, ssrc = stream.getmcparam()
                        receiverid = mcast_grp + ':' + str(mcast_port)
                        if receiverid not in CustomHandler._receiverjobs or not CustomHandler._receiverjobs[receiverid].is_alive():
                            p = Receiver(name="receiver-%s" % receiverid, args=(self._logger.getChild("Receiver"), self._mcip, self._memdb, stream))
                            CustomHandler._receiverjobs[receiverid] = p
                            p.start()
                    return

                channel, stream = Channel.getChannelByURL(host, self.path)
                if channel is not None and stream is not None:
                    ######################
                    # media              #
                    ######################

                    # check, if the whole fragment is in memdb (-->stitching was successful)
                    chunk = self._memdb.get(Chunk.getmemcachedkey(stream.getssrc(), stream.getchunknumberfrompath(self.path)))

                    if chunk is None:
                        self._logger.warning("cache miss: '%s'" % requesturl)
                        self.passthrough(channel.getingesturl(self.path))
                    else:
                        self._logger.debug("cache hit : '%s', len: %d " % (requesturl, len(chunk)))
                        self.send_response(200)
                        self.send_header('Content-Type', stream.getmimetype())
                        self.send_header('Content-Length', str(len(chunk)))

                        # fucking CORS
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET,HEAD,OPTIONS')
                        self.send_header('Access-Control-Expose-Headers', 'Server,range,Content-Length,Content-Range,Date')
                        self.send_header('Access-Control-Allow-Headers', 'origin,range,accept-encoding,referer')

                        self.end_headers()
                        self.wfile.write(chunk)
                    return

                channel = Channel.getchannelbyinitsegmenturl(host, self.path)
                if channel is not None:
                    ######################
                    # initialization     #
                    ######################

                    self._logger.debug("cache pass: '%s'" % requesturl)
                    self.passthrough(channel.getingesturl(self.path))
                    return

                ######################
                # deny               #
                ######################
                self._logger.warning("Request %s is not part of an MPEG-DASH stream." % requesturl)
                self.send_error(404, "Request %s is not part of an MPEG-DASH stream." % requesturl)

            except urllib2.HTTPError as e:
                self._logger.debug(e.message)
                self.send_error(e.code, e.message)

            except urllib2.URLError as e:
                self._logger.warning("URL could not be reached: %s" % e.reason)
                self.send_error(400, "URL could not be reached: %s" % e.reason)

            except Exception as e:
                self._logger.warning("Internal server error: %s" % e.message)
                self._logger.debug(traceback.format_exc())
                self.send_error(500, "Internal server error: %s" % e.message)

            except:
                self._logger.warning("Unexpected error: %s", sys.exc_info()[0])
                self._logger.debug(traceback.format_exc())
                self.send_error(500, "Unexpected error: %s" % sys.exc_info()[0])

            return


        def passthrough(self, url):
            proxy_handler = urllib2.ProxyHandler(self._ingestproxy)
            opener = urllib2.build_opener(proxy_handler)

            buff = None
            try:
                res = opener.open(url)
                buff = res.read()

                if res.getcode() >= 400:
                    self.send_error(res.getcode(), buff)
                else:
                    self.send_response(res.getcode())

                    # copy important headers
                    headers = res.info()
                    for headername in ['Content-Type', 'Cache-Control', 'Last-Modified']:
                        try:
                            self.send_header(headername, headers[headername])
                        except KeyError:
                            continue

                    # fucking CORS
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET,HEAD,OPTIONS')
                    self.send_header('Access-Control-Expose-Headers', 'Server,range,Content-Length,Content-Range,Date')
                    self.send_header('Access-Control-Allow-Headers', 'origin,range,accept-encoding,referer')

                    self.send_header('Content-Length', str(len(buff)))
                    self.end_headers()

                    self.wfile.write(buff)          # TODO: rewrite to use shutil.copyfileobj()

            except urllib2.URLError as e:
                e.url = url
                raise e
            return buff             # needed for MPD parse

        # silence logging
        def log_message(self, format, *args):
            return

    return CustomHandler


class DASHProxy:

    def __init__(self, logger, ip, port, configfps, ingestproxy, mcip):

        self._logger = logger
        self._ip = ip
        self._port = port

        # read all config files and add channels
        for configfp in configfps:
            Channel.append(configfp)

        # create shared memdb
        self._memdb = MemDB()

        # handler class for responding to http requests
        self._myhandler = makehandlerclass(self._logger.getChild("HTTPServer"), ingestproxy, mcip, self._memdb)
#        self._myhandler.protocol_version = "HTTP/1.1"  #-->Do not use HTTP1.1 because handler does not support 206 and byte requests easily.
        self._myhandler.server_version = "m2u"
        self._httpd = None

        # stitcher for concatenating RTP slices into fragments
        self._stitcher = Stitcher(name="stitcher", args=(self._logger.getChild("Stitcher"), self._memdb))


    def serve_requests(self):

        try:
            # start stitcher
            self._stitcher.start()

            # start HTTP server
            self._httpd = HTTPServer((self._ip, self._port), self._myhandler)
            self._logger.info("Handling requests on %s:%d" % (self._ip, self._port))

            # This will block and periodically check the shutdown signal
            self._httpd.serve_forever()
        except:
            self.stop()
            raise


    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd = None

        if self._stitcher is not None:
            self._stitcher.stop()
            self._stitcher.join(1)
            self._stitcher = None


