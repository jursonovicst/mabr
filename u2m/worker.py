import os, signal
import multiprocessing
from threading import Timer
import time
import string
import urllib2

class Worker(multiprocessing.Process):

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs={}):
        multiprocessing.Process.__init__(self, group, target, name, args, kwarggs)
        self._periodid = args[0]
        self._representationid = args[1]
        self._urltemplate = args[2]
        self._number = int(args[3])
        self._period = int(args[4])
        proxy_handler = urllib2.ProxyHandler({'http': args[5]} if args[5] != "" else {})
        self._opener = urllib2.build_opener(proxy_handler)

        self._timer = None

#        signal.signal(signal.SIGINT, signal.SIG_IGN)
        self._run = False

    def _mytimer(self, fire_wc):
        # set next timer
        drift = time.time() - fire_wc
        self._timer = Timer(self._period - drift, Worker._mytimer, [self, fire_wc + self._period])
        self._timer.start()

        print string.replace(self._urltemplate, "$Number$", str(self._number))
        try:
            ret = self._opener.open(string.replace(self._urltemplate, "$Number$", str(self._number)))
        except urllib2.HTTPError as e:
            if e.code == 404:
                print e.code, e.reason
            else:
                raise e

        self._number += 1

    def run(self):
        self._run = True
        self._mytimer(time.time())
        try:
            while self._run:
                time.sleep(5)
        except KeyboardInterrupt:
            self._timer.cancel()
            self._run = False
            self._opener.close()