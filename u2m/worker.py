import os, signal
import threading
import time
import string
import urllib2
import dpkt
import socket
import random

class Worker(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)
        self._periodid = args[0]
        self._mcast_grp = args[1]
        self._mcast_port = int(args[2])
        self._urltemplate = args[3]
        self._number = int(args[4])
        self._period = int(args[5])
        proxy_handler = urllib2.ProxyHandler({'http': args[6]} if args[6] != "" else {})
        self._opener = urllib2.build_opener(proxy_handler)
        self._logger = args[7]

        self._timer = None
        self._run = False
        self._timeoffset_ut = time.time()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        random.seed(os.urandom(1))
        self._rtp_pkt = dpkt.rtp.RTP()
        self._rtp_pkt.version = 2
        self._rtp_pkt.p=0
        self._rtp_pkt.x=0
        self._rtp_pkt.cc=0x2
        self._rtp_pkt.m=0
        self._rtp_pkt.pt=96
        self._rtp_pkt.seq = random.randint(0,65535)
        self._rtp_pkt.ts=0x00
        self._rtp_pkt.ssrc=random.randint(0,1<<32-1)
        self._rtp_pkt.csrc="11"

    def _calctimestamp(self,resolution):
        return int((time.time()-self._timeoffset_ut) * resolution)

    def _mytimer(self, fireat_wc):
        # set next timer and compensate drift from wc(wallclock)
        drift = time.time() - fireat_wc
        self._timer = threading.Timer(self._period - drift, Worker._mytimer, [self, fireat_wc + self._period])
        self._timer.start()

        # 1. Load segment
        url = string.replace(self._urltemplate, "$Number$", str(self._number))
        message = "Accessing segment '%s':" % url
        ret = None
        try:
            ret = self._opener.open(url)
            message += " HTTP %s" % ret.getcode()

            #send it out
            buff=ret.read(800)
            self._rtp_pkt.m = 1
            self._rtp_pkt.ts = self._calctimestamp(90000)
            while buff != "":
                self._rtp_pkt.seq = (self._rtp_pkt.seq + 1) % 65536
                self._rtp_pkt.data = buff
                sent = self._sock.sendto(str(self._rtp_pkt), (self._mcast_grp, self._mcast_port))
                buff = ret.read(800)
                self._rtp_pkt.m = 0

        except urllib2.HTTPError as e:
            message += " HTTP %s (%s)" % (e.code, e.reason)
        finally:
            self._logger.info(message)

        self._number += 1

    def run(self):
        self._run = True
        self._mytimer(time.time())
        try:
            while self._run:
                time.sleep(1)
        except KeyboardInterrupt:
            self._timer.cancel()
            self._run = False
            self._opener.close()