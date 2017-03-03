import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import os
import urllib2
from receiver import Receiver


def MakeHandlerClassFromArgv(logger, fqdn):
    class CustomHandler(BaseHTTPRequestHandler, object):
        def __init__(self, *args, **kwargs):
            self._logger = logger
            self._fqdn = fqdn

            super(CustomHandler, self).__init__(*args, **kwargs)

        def do_GET(self):
            query = ""
            path = self.path
            if path.find('?') != -1:
                (path,query) = path.split("?", 2)

            (filename,ext)=os.path.splitext(os.path.basename(path))
            if ext == ".mpd":
                url = "http://%s%s%s" % (self.headers['Host'], path, "" if query == "" else "?"+query )
                self._logger.debug("get this mpd from %s" % url)
                proxy_handler = urllib2.ProxyHandler({'http': 'http://10.35.3.35:3128' })
                opener = urllib2.build_opener(proxy_handler)
                try:
                    res = opener.open(url)

                    self.send_response(res.getcode())
                    for header in res.info():
                        self.send_header(header[0],header[1])
                    self.end_headers()
                    buff = res.read()
                    self.wfile.write(buff)
                except urllib2.HTTPError as e:
                    self.send_response(res.getcode())
                    self.wfile.write(e.message)


            elif ext == ".m4s":
                self._logger.debug("stich file from memcached")


    #        self.send_response(200)
            #        self.send_header('Content-type', 'text/html')
            #self.end_headers()
            ## Send the html message
            #self.wfile.write("Hello World !")
            #print self.path
            #print self.request
            #print self.client_address
            #print self.requestline
            #print
            return

    return CustomHandler



class Server(threading.Thread):


    def __init__(self, group=None, target=None, name="HTTPServer", args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._ip = args[1]
        self._port = int(args[2])
        fqdn = args[3]

        self._run = False
        self._logger.debug("HTTPServer thread started")
        myhandler = MakeHandlerClassFromArgv(self._logger,fqdn)
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


