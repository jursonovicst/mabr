import os
import threading
import time
import string
import urllib2
import socket
import random
import rtpext
import struct
import math
import re

class MCSender(threading.Thread):

    _timeout = 1

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
        self._bandwidthcap = float(args[9])

        # Fetch
        self._fetchtimer = None

        # Tokenbank
        self._tokentimer = None
        self._tokensem = threading.BoundedSemaphore(10)

        # Packet buffer
        self._jobsem = threading.Semaphore(0)
        self._jobbuffer = []


        self._run = False
        self._timeoffset_ut = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)   #by default, TTL for multicast is 1, increase this value to send to other networks.
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)


        # RTP frame (custom dpkt.rtp.RTP)
        random.seed(os.urandom(1))
        self._rtp_pkt = rtpext.RTPMABRDATA()
        self._rtp_pkt.version = 2
        self._rtp_pkt.p=0
        self._rtp_pkt.x=1
        self._rtp_pkt.cc=0x0
        self._rtp_pkt.m=0
        self._rtp_pkt.pt=96
        self._rtp_pkt.seq = random.randint(0,65535)
        self._rtp_pkt.ts=0x00
        self._rtp_pkt.ssrc=self._ssrc


    def _tokencallback(self, period, fireat_wc):
        # Set next timer and compensate drift from wc(wallclock)
        drift = time.time() - fireat_wc
        self._tokentimer = threading.Timer(period - drift if drift < period else 0, MCSender._tokencallback, [self, period, fireat_wc + period])
        self._tokentimer.start()

        # Add token to tokenbucket
        try:
            self._tokensem.release()
        except ValueError:
            pass    # Ignore tokens over bucketsize


    def _calctimestamp(self,resolution):
        return int((time.time()-self._timeoffset_ut) * resolution)


    def _fetchcallback(self, fireat_wc):
        message = ""
        try:
            # 0. Set next timer and compensate drift from wc(wallclock)
            drift = time.time() - fireat_wc
            self._fetchtimer = threading.Timer(self._period - drift, MCSender._fetchcallback, [self, fireat_wc + self._period])
            self._fetchtimer.start()

            # 1. Load segment
            url = string.replace(self._urltemplate, "$Number$", str(self._number))     #keep in mind, that ffmpeg default setting is not compatible: %05d stuff...
            message = "Accessing segment '%s':" % url

            ret = self._opener.open(url)                                                #TODO: timeout
            message += " HTTP %s (%s byte)" % (ret.getcode(),ret.headers['content-length'])

            # 2. send it out in parts
            representationid_padded = self._representationid + ("\0" * ((4 - len(self._representationid) % 4) % 4))
                        #ADSL   IP  UDP RTP RTPe    RTPeh
            mtu = 1500  -4      -20 -8  -12 -4      -6*4
            readpos = 0
            numberofsentpackets = 0

            buff=ret.read(mtu)
            self._rtp_pkt.m = 0
            self._rtp_pkt.ts = self._calctimestamp(90000)
            seqoffirstpacket = self._rtp_pkt.seq
            seqoflastpacket = self._rtp_pkt.seq + math.ceil(int(ret.headers['content-length']) / mtu)

            seqmin = self._rtp_pkt.seq

            while buff != "":
                # Add retransmission information
                self._rtp_pkt.bytemin = readpos
                self._rtp_pkt.bytemax = readpos + len(buff) - 1

                # Copy data
                self._rtp_pkt.data = buff

                # Next packet
                readpos += len(buff)
                buff = ret.read(mtu)
                if buff != "":
                    # Put it into the jonbuffer
                    self._jobbuffer.append(str(self._rtp_pkt))
                else:
                    # Last packet, set marker
                    rtp_pkt_stitcher = rtpext.RTPMABRSTITCHER(self._rtp_pkt)
                    rtp_pkt_stitcher.m = 1
                    rtp_pkt_stitcher.seqmin = seqmin
                    rtp_pkt_stitcher.seqmax = rtp_pkt_stitcher.seq
                    rtp_pkt_stitcher.chunknumber = self._number

                    self._jobbuffer.append(str(rtp_pkt_stitcher))

                self._jobsem.release()


                # Update sequence number
                numberofsentpackets += 1
                self._rtp_pkt.seq = (self._rtp_pkt.seq + 1) % 65536

            message += " (%d packets)" % numberofsentpackets

            self._logger.debug(message)

        except urllib2.HTTPError as e:
            message += " HTTP %s (%s)" % (e.code, e.reason)
            self._logger.warning(message)

        self._number += 1


    def run(self):
        self._run = True
        self._timeoffset_ut = time.time()

        # Start fetching segments
        self._fetchcallback(time.time())

        # Start adding tokens, set the bitrate limit here by calculating how frequently a packet can leave
        self._tokencallback(1500.0 * 8.0 / self._bandwidthcap / 1.1, time.time())

        self._logger.info("Sending representation '%s' to %s:%d (ssrc: %d, bwcap: %.2fMbps)" % (self._representationid, self._mcast_grp, self._mcast_port, self._ssrc, self._bandwidthcap / 1000 / 1000))
        try:
            while self._run:
                # Get a token
                self._tokensem.acquire()

                # Get a job
                self._jobsem.acquire()

                # Send out the job
                self._sock.sendto(self._jobbuffer.pop(0), (self._mcast_grp, self._mcast_port))

        except KeyboardInterrupt:
            print "zzz"
        finally:
            self._tokentimer.cancel()
            self._fetchtimer.cancel()
            self._opener.close()
            self._logger.debug("Exiting...")

    def stop(self):
        self._run = False
