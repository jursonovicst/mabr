import os
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
        self._mcast_grp = args[0]
        self._mcast_port = int(args[1])
        self._ssrc = int(args[2])
        self._urltemplate = string.replace(args[3],"$RepresentationID$",args[4])
        self._representationid = args[4]
        self._number = int(args[5])
        self._period = float(args[6])
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

    def _calctimestamp(self,resolution):
        return int((time.time()-self._timeoffset_ut) * resolution)

    def _mytimer(self, fireat_wc):
        message = ""
        try:
            # 0. set next timer and compensate drift from wc(wallclock)
            drift = time.time() - fireat_wc
            self._timer = threading.Timer(self._period - drift, MCSender._mytimer, [self, fireat_wc + self._period])
            self._timer.start()

            # 1. Load segment
            url = string.replace(self._urltemplate, "$Number$", str(self._number))
            message = "Accessing segment '%s':" % url

            ret = self._opener.open(url)
            message += " HTTP %s" % ret.getcode()

            # 2. send it out
            representationid_padded = self._representationid + ("\0" * ((4 - len(self._representationid) % 4) % 4))
                        #ADSL   IP  UDP RTP RTPe    RTPeh
            mtu = 1500  -4      -20 -8  -12 -4      -12-len(representationid_padded)
            readpos = 0
            numberofsentpackets = 0

            buff=ret.read(mtu)
            self._rtp_pkt.m = 0
            self._rtp_pkt.ts = self._calctimestamp(90000)
            while buff != "":
                #add retransmission information
                self._rtp_pkt.eh = struct.pack('!I', readpos) + struct.pack('!I', readpos+len(buff)-1) + struct.pack('!I', self._number) + representationid_padded
                self._rtp_pkt.ehlen = len(self._rtp_pkt.eh) / 4

                #copy data
                self._rtp_pkt.data = buff

                #next packet
                readpos += len(buff)
                buff = ret.read(mtu)
                if buff == "":
                    self._rtp_pkt.m = 1 # Last packet, set marker

                #send it out
                sent = self._sock.sendto(str(self._rtp_pkt), (self._mcast_grp, self._mcast_port))

                # update sequence number
                numberofsentpackets += 1
                self._rtp_pkt.seq = (self._rtp_pkt.seq + 1) % 65536


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
            self._logger.info("Sending representation '%s' to %s:%d (ssrc: %d)" % (self._representationid, self._mcast_grp, self._mcast_port, self._ssrc))
            while self._run:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._run = False
            self._timer.stop()
            self._opener.close()

    def stop(self):
        self._run = False
        self._timer.stop()
        self._opener.close()
