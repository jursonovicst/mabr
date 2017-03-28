import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import urllib2
import dash
import memcache
import re
import ConfigParser
from receiver import Receiver
from urlparse import urlparse
import time

def MakeHandlerClass(logger, channels, memcachedaddress, proxy):
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
            self._memcachedaddress = memcachedaddress
            self._memcached = memcache.Client([memcachedaddress], debug=0)
            self._proxy = proxy

            self._channels = channels

            self.__representationid = ''
            self._ssrc = None

            super(CustomHandler, self).__init__(*args, **kwargs)

        def do_GET(self):

            #Check if Host is in allowed FQDNs
            if 'Host' not in self.headers:
                self.send_response(400)
                self.wfile.write("Ho Host header specified.")
                self._logger.warning("Ho Host header specified.")
                return

            url = "http://%s%s" % (self.headers['Host'], self.path)

            if any(url == ch.getMPDUrl() for ch in self._channels):
                # mpd
                self._logger.debug("Parse MPD on '%s'" %url)


                # Parse mpd
                mpd = self.passthrough(url)
                mpdparser = dash.MPDParser(mpd)

                # Figure out url templates
                mpdparser.geturltemplatefor(5)
#                    if(fqdn + dirname + urltemplate) not in CustomHandler._urltemplates:
#                        CustomHandler._urltemplates.append(fqdn + dirname + urltemplate)
#                    self._logger.debug("URLtemplate %s added" % (fqdn + dirname + urltemplate))

                # Start multicast receivers, if not already running
                #for mcastaddr,mcastport in mpdparser.getmulticasts():
                #    key = mcastaddr + ':' + str(mcastport)
                #    if key not in CustomHandler._jobs or not CustomHandler._jobs[key].is_alive():
                #        p = Receiver(name="receiver-%s" % "id", args=(self._logger, mcastaddr, mcastport, self._memcachedaddress))
                #        CustomHandler._jobs[key] = p
                #        p.start()

            # Check for multicast
            elif url in self._urltemplates:
                self._logger.debug("URL '%s' matches urltemplate" % url)

            # Passthrough
            else:
                self.passthrough(url)


                #         elif ext == ".m4s" or ext == ".mp4":
                #                                if (fqdn + path) in CustomHandler._initsegmentpaths:
                #                   # Init segment -->passthrough
                #                   self.passthrough(url)
                #               else:
                #                   m4s = self._memcached.get(fqdn + path)
                #                   if m4s is None:
                #                       # MISS -->passthrough
                #                       self.passthrough(url)
                #                   else:
                #                       # HIT -->respond
                #                       self.respond(m4s)
                #
                #           else:
                #               self._logger.debug("Unknown extension: '%s" % ext)

            return

        def passthrough(self, url):
            proxy_handler = urllib2.ProxyHandler({'http': self._proxy})
            opener = urllib2.build_opener(proxy_handler)
            buff = None
            res = None
            try:
                res = opener.open(url)

                self.send_response(res.getcode())
                for header in res.info():
                    self.send_header(header[0], header[1])
                self.end_headers()
                buff = res.read()
                self.wfile.write(buff)

                self._logger.info("Passthrough url '%s'" % url)

            except urllib2.HTTPError as e:
                print res.getcode()
                self.send_response(res.getcode())

                self.wfile.write(e.message)
            finally:
                return buff

        def respond(self, buff):
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(buff)

                self._logger.info("Hit url '%s'" % '--')    #TODO: implement

            except Exception as e:
                self.send_response(500)
                self.wfile.write(e.message)

    return CustomHandler


class Channel:
    def __init__(self, fp):
        config = ConfigParser.ConfigParser()
        config.readfp(fp)
        self._mpdurl = config.get('general', 'mpd')

        self._data = {}

        for section in config.sections():
            if section == 'general':
                continue

            self._data[section] = (config.get(section, 'mcast_grp'), config.get(section, 'mcast_port'), config.get(section, 'ssrc'))

    def getFQDN(self):
        url = urlparse(self._mpdurl)
        return url.hostname

    def getMPDUrl(self):
        return self._mpdurl





class DASHProxy(threading.Thread):


    def __init__(self, group=None, target=None, name="HTTPServer", args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._ip = args[1]
        self._port = int(args[2])
        configfps = args[3]
        self._memcached = args[4]
        self._proxy = args[5]

        self._channels = []
        for configfp in configfps:
            self._channels.append(Channel(configfp))

        self._run = False
        self._server = None
        self._logger.debug("HTTPServer thread started")

    def run(self):
        self._run = True

        self._logger.info("Start handling requests on %s:%d" %(self._ip, self._port))
        while self._run:
            try:
                myhandler = MakeHandlerClass(self._logger, self._channels, self._memcached, self._proxy)
                self._server = HTTPServer((self._ip, self._port), myhandler)

                # This will block and periodically check the shutdown signal
                self._server.serve_forever()
            except KeyboardInterrupt:
                self._logger.debug("KeyboardInterrupt")
                self.stop()
            except Exception as e:
                self._logger.warning("Oops: " + e.message + ", respawn in 10 sec...")
                time.sleep(10)
                self._server.shutdown()

    def stop(self):
        self._run = False
        if self._server is not None:
            self._server.shutdown()


