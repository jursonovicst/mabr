import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import urllib2
import dash

import imp
try:
  imp.find_module('memcache')
except ImportError:
  print("This scrypt requires memcache python library, please install python-memcache!")
  exit(1)
import memcache

import re
import ConfigParser
from receiver import Receiver
from urlparse import urlparse
import time

def MakeHandlerClass(logger, channels, memcachedaddress, proxy, fqdn, cdn):
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
            self._fqdn = fqdn
            self._cdn = cdn

            self._channels = channels

            self.__representationid = ''
            self._ssrc = None

            self._multicastdelivery = []

            super(CustomHandler, self).__init__(*args, **kwargs)

        def do_GET(self):

            #Check Host header
            if 'Host' not in self.headers:
                self.send_response(400)
                self.wfile.write("Ho Host header specified.")
                self._logger.warning("Ho Host header specified.")
                return

            if self.headers['Host'] != self._fqdn:
                self.send_response(401)
                self.wfile.write("FQDN '%s' not allowed to proxy." % self.headers['Host'])
                self._logger.warning("FQDN '%s' not allowed to proxy." % self.headers['Host'])
                return

            requesturl = 'http://' + self.headers['Host'] + self.path
            sourceurl =  'http://' + self._cdn + self.path

            channel = next((ch for ch in self._channels if ch.getMPDPath() == self.path), None)

            if channel is not None:
                # match on one channel
                self._logger.debug("parse: '%s'" % self.path)


                # Parse mpd
                mpd = self.passthrough(sourceurl)
                mpdparser = dash.MPDParser(mpd)

                # Figure out url templates for multicast
                for representationid in channel.getRepresentationIDs():
                    pathpattern = os.path.dirname(self.path) + '/' + mpdparser.geturltemplatefor(representationid).replace('$RepresentationID$', representationid).replace('.','\.').replace('$Number$', '\d+')
                    self._logger.debug("Add '%s' pattern for multicast delivery." % pathpattern)
                    self._multicastdelivery.append(pathpattern)
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
            elif (True if re.match(pattern, self.path) else False for pattern in self._multicastdelivery):
                self._logger.debug("multicast: '%s'" % self.path)
                self.passthrough(sourceurl)

            # Passthrough
            else:
                self._logger.debug("passthrough: '%s'" % self.path)
                self.passthrough(sourceurl)


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
                for key in res.info():
                    self.send_header(key, res.info()[key])
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
        self._url = urlparse(config.get('general', 'mpd'))
        self._data = {}

        for section in config.sections():
            if section == 'general':
                continue

            self._data[section] = (config.get(section, 'mcast_grp'), config.get(section, 'mcast_port'), config.get(section, 'ssrc'))

    def getMPDUrl(self):
        return self._url.scheme + "://" + self._url.netloc + self._url.path + self._url.query

    def getMPDPath(self):
        return self._url.path


    def getRepresentationIDs(self):
        return list(self._data)

class DASHProxy(threading.Thread):


    def __init__(self, group=None, target=None, name="HTTPServer", args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._ip = args[1]
        self._port = int(args[2])
        configfps = args[3]
        self._memcached = args[4]
        self._proxy = args[5]
        self._fqdn = args[6]
        self._cdn = args[7]

        self._channels = []
        for configfp in configfps:
            self._channels.append(Channel(configfp))

        self._server = None
        self._logger.debug("HTTPServer thread started")

    def run(self):

        self._logger.info("Start handling requests on %s:%d" %(self._ip, self._port))
        try:
            myhandler = MakeHandlerClass(self._logger, self._channels, self._memcached, self._proxy, self._fqdn, self._cdn)
            self._server = HTTPServer((self._ip, self._port), myhandler)

            # This will block and periodically check the shutdown signal
            self._server.serve_forever()
        except KeyboardInterrupt:
            self._logger.debug("KeyboardInterrupt")
        except Exception as e:
            self._logger.warning("Oops: %s, respawn in 10 sec..." % str(e))
            time.sleep(10)
        finally:
            self.stop()

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None


