import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import urllib2
import dash
#from receiver import Receiver


def MakeHandlerClass(logger, allowedfqdns):
    class CustomHandler(BaseHTTPRequestHandler, object):

        _initsegmentpaths = []

        def __init__(self, *args, **kwargs):
            self._logger = logger
            self._allowedfqdns = allowedfqdns

            super(CustomHandler, self).__init__(*args, **kwargs)

        def do_GET(self):

            #Check if Host is in allowed FQDNs
            if 'Host' not in self.headers:
                self.send_response(400)
                self.wfile.write("Ho Host header specified.")
                self._logger.warning("Ho Host header specified.")
                return
            if self.headers['Host'] not in self._allowedfqdns:
                self.send_response(400)
                self.wfile.write("Host '%s' is not configured for transport." % self.headers['Host'])
                self._logger.warning("Host '%s' is not configured for transport." % self.headers['Host'])
                return

            url = "http://%s%s" % (self.headers['Host'], self.path)
            fqdn = self.headers['Host']
            query = ""
            path = self.path
            if path.find('?') != -1:
                (path,query) = path.split("?", 2)
            dirname = os.path.dirname(path)
            (filename,ext)=os.path.splitext(os.path.basename(path))

            # url:      http://examlpe.com/mabr/file.txt?tom=tom
            # fqdn:     example.com
            # path:     /mabr/file.txt
            # dirname:  /mabr
            # filename: file
            # ext:      .txt
            # query:    tom=tom

            if ext == ".mpd":
                mpd = self.passthrough(url)

                # Parse mpd and figure out init segment urls for passthrough
                mpdparser = dash.MPDParser(mpd)
                for initsegmentpath in mpdparser.getinitsegmentpaths():
                    CustomHandler._initsegmentpaths.add(fqdn + dirname + initsegmentpath)
                    self._logger.debug("Initsegment %s marked for passthrough" % (fqdn + dirname + initsegmentpath))

            elif ext == ".m4s" or ext == ".mp4":
                #check for passthrough init segments
                if (fqdn + path) in CustomHandler._initsegmentpaths:
                    self.passthrough(url)

            else:
                self._logger.debug("Unknown extension: '%s" % ext)



            return

        def passthrough(self, url):
            proxy_handler = urllib2.ProxyHandler({'http': 'http://10.35.3.35:3128'})
            opener = urllib2.build_opener(proxy_handler)
            buff = None
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
                self.send_response(res.getcode())
                self.wfile.write(e.message)
            finally:
                return buff

    return CustomHandler



class Server(threading.Thread):


    def __init__(self, group=None, target=None, name="HTTPServer", args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._ip = args[1]
        self._port = int(args[2])
        fqdns = args[3]

        self._run = False
        self._logger.debug("HTTPServer thread started")
        myhandler = MakeHandlerClass(self._logger,fqdns)
        self._server = HTTPServer((self._ip, self._port), myhandler)

    def run(self):
        self._run = True

        self._logger.debug("Start handling requests")
        while self._run:
            try:
                # This will block abd periodically check the shutdown signal
                self._server.serve_forever()
            except KeyboardInterrupt:
                self._logger.debug("KeyboardInterrupt")
                self.stop()
            except Exception as e:
                self._server.shutdown()

    def stop(self):
        self._run = False
        self._server.shutdown()


