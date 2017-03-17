import os, signal
import threading
import time
import string
import urllib2
import socket
import random
import rtpext
import struct

class MCSender(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)
        self._periodid = args[0]
        self._mcast_grp = args[1]
        self._mcast_port = int(args[2])
        self._ssrc = int(args[3])
        self._urltemplate = args[4]
        self._number = int(args[5])
        self._period = int(args[6])
        proxy_handler = urllib2.ProxyHandler({'http': args[7]} if args[7] != "" else {})
        self._opener = urllib2.build_opener(proxy_handler)
        self._logger = args[8]

        self._timer = None
        self._run = False
        self._timeoffset_ut = time.time()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        random.seed(os.urandom(1))
        self._rtp_pkt = rtpext.RTPExt()
        self._rtp_pkt.version = 2
        self._rtp_pkt.p=0
        self._rtp_pkt.x=0
        self._rtp_pkt.cc=0x0
        self._rtp_pkt.m=0
        self._rtp_pkt.x=1
        self._rtp_pkt.pt=96
        self._rtp_pkt.seq = random.randint(0,65535)
        self._rtp_pkt.ts=0x00
        self._rtp_pkt.ssrc=self._ssrc
        self._rtp_pkt.ehid=12

        test= str(self._rtp_pkt)

    def _calctimestamp(self,resolution):
        return int((time.time()-self._timeoffset_ut) * resolution)

    def _mytimer(self, fireat_wc):
        # set next timer and compensate drift from wc(wallclock)
        drift = time.time() - fireat_wc
        self._timer = threading.Timer(self._period - drift, MCSender._mytimer, [self, fireat_wc + self._period])
        self._timer.start()

        # 1. Load segment
        url = string.replace(self._urltemplate, "$Number$", str(self._number))
        message = "Accessing segment '%s':" % url
        ret = None
        try:
            ret = self._opener.open(url)
            message += " HTTP %s" % ret.getcode()

            #send it out
                        #ADSL   IP  UDP RTP
            mtu=1500    -4      -20 -8  -100
            readpos = 0
            numberofsentpackets = 0
            buff=ret.read(mtu)
            self._rtp_pkt.m = 1
            self._rtp_pkt.ts = self._calctimestamp(90000)
            while buff != "":
                # update sequence number
                self._rtp_pkt.seq = (self._rtp_pkt.seq + 1) % 65536

                #add retransmission information
                self._rtp_pkt.eh = struct.pack('!I', readpos) + struct.pack('!I', readpos+len(buff)-1) + url + ("." * (len(url) % 4))   #TODO: add '\0' instead of '.'
                self._rtp_pkt.ehlen = len(self._rtp_pkt.eh) / 4

                #copy data
                self._rtp_pkt.data = buff

                #send it out
                sent = self._sock.sendto(str(self._rtp_pkt), (self._mcast_grp, self._mcast_port))

                #next packet
                readpos += len(buff)
                numberofsentpackets += 1
                buff = ret.read(mtu)
                self._rtp_pkt.m = 0

            message += " (%d packets)" % numberofsentpackets

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