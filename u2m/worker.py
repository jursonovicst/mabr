import os, signal
import multiprocessing
import pycurl
from threading import Timer
import time
import string

class Worker(multiprocessing.Process):

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs={}):
        multiprocessing.Process.__init__(self, group, target, name, args, kwarggs)
        self._periodid = args[0]
        self._representationid = args[1]
        self._urltemplate = args[2]
        self._number = int(args[3])
        self._period = int(args[4])

        self._timer = None
#        logging.debug("W-%s/%s: init" % (self._periodid,self._representationid))


        signal.signal(signal.SIGINT, signal.SIG_IGN)

        #self._m = pycurl.CurlMulti()

        self._run = False

        print "TTT"
#      self._m.setopt(pycurl.M_MAXCONNECTS, )       #shoud be 0 by default
#      self._m.setopt(pycurl.M_PIPELINING, pycurl.M)  #should be disabled

    def _mytimer(self, wallclock):
        # set next timer
        drift = time.time() - wallclock
        self._timer = Timer(self._period - drift, Worker._mytimer, [self, wallclock + self._period])
        self._timer.start()

        print string.replace(self._urltemplate, "$Number$", str(self._number))
        self._number += 1

    def run(self):
        self._run = True
        self._mytimer(time.time())

        while self._run:
            time.sleep(5)
