import os
import threading
import time
import string
import urllib2
import socket
import random
import rtpext


class MCSender(threading.Thread):

    timeout = 1

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)
        self._mcast_grp = args[0]
        self._mcast_port = int(args[1])
        self._ssrc = int(args[2])
        self._urltemplate = string.replace(args[3], "$RepresentationID$", args[4])
        self._representationid = args[4]
        self._number = int(args[5])
        self._period = float(args[6])
        proxy_handler = urllib2.ProxyHandler({'http': args[7]} if args[7] != "" else {})
        self._opener = urllib2.build_opener(proxy_handler)
        self._logger = args[8]
        self._bandwidthcap = float(args[9])
        self._mtu = int(args[10])
        self._mcast_ttl = int(args[11])

        # Fetch
        self._fetchtimer = None
        self._fetchperiod = self._period
        self._fetchstatus = 0

        # Tokenbank
        self._tokentimer = None
        self._tokensem = threading.BoundedSemaphore(10)

        # Packet buffer
        self._jobsem = threading.Semaphore(0)
        self._jobbuffer = []


        self._run = False
        self._timeoffset_ut = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self._mcast_ttl)   # by default, TTL for multicast is 1, increase this value to send to other networks.
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)


        # RTP frame (custom dpkt.rtp.RTP)
        random.seed(os.urandom(1))
        self._rtp_pkt = rtpext.RTPMABRDATA()
        self._rtp_pkt.version = 2
        self._rtp_pkt.p = 0
        self._rtp_pkt.cc = 0x0
        self._rtp_pkt.pt = 96
        self._rtp_pkt.seq = random.randint(0, 65535)     # start with random RTP sequence number
        self._rtp_pkt.ts = 0x00
        self._rtp_pkt.ssrc = self._ssrc


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


    def _calctimestamp(self, resolution):
        return int((time.time()-self._timeoffset_ut) * resolution)


    def _fetchcallback(self, fireat_wc):

        try:
            # we are BEHIND: we are too late (or exactly on time), the fragment present on the origin. Probably we can acquire them faster.
            # we are AHEAD: we are too early, the fragment have not published yet on the origin (hopefully, and we do not encounter a server error)

            # 0. Set next timer
            # compensate drift from wc (wallclock)
            drift = fireat_wc - time.time()

            # converge to origin's publication time (_fetchstatus > 0 --> we are behind, _fetchstatus < 0 --> we are ahead)
            self._fetchperiod -= (self._fetchstatus * 0.001)

            # set timer
            self._fetchtimer = threading.Timer(self._fetchperiod + drift, MCSender._fetchcallback, [self, fireat_wc + self._fetchperiod])
            self._fetchtimer.start()


            # 1. Load segment
            url = string.replace(self._urltemplate, "$Number$", str(self._number))     # keep in mind, that ffmpeg default setting is not compatible: %05d stuff...
            message = "Accessing segment '%s': " % url

            # repeate until fragment does present on origin or origin error (!=404), limit by two fragment time
            ret = ''
            retcode = 404
            WAITAFTER404 = 0.100
            MAXATTEMPT = int(self._period / WAITAFTER404 * 2)
            attempt = 0
            while retcode == 404:
                try:
                    attempt += 1
                    ret = self._opener.open(url)
                    retcode = ret.getcode()
                except urllib2.HTTPError as e:
                    # exit criteria
                    if attempt == MAXATTEMPT:
                        message += "HTTP %s (reason: %s, attempts: %d, giving up!)" % (e.code, e.reason, attempt)
                        self._logger.warning(message)
                        return

                    # we are ahead (hopefully), wait a bit...
                    if e.code == 404:
                        time.sleep(WAITAFTER404)

                    retcode = e.code


            if attempt == 1:
                if self._fetchstatus < 0:
                    # we are exactly on time, first 200 after a series of 404, reset _fetchperiod, and start slowly decreasing it
                    self._fetchstatus = 1
                    self._fetchperiod = self._period
                else:
                    # we were behind, let's hurry up a bit
                    self._fetchstatus += 1
            else:

                if self._fetchstatus > 0:
                    # we are exactly on time, first 404 after a series of 200, reset _fetchperiod, and start slowly increasing it
                    self._fetchstatus = -1
                    self._fetchperiod = self._period
                else:
                    # we were ahead, let's slow down a bit:
                    self._fetchstatus -= 1

            message += "HTTP %s (length: %8dB, attempts: %2d" % (ret.getcode(), int(ret.headers['content-length']), attempt)


            # 2. send it out in parts
                                # IP  UDP RTP+RTPe+RTPeh
            readsize = self._mtu -20 -8  -rtpext.RTPMABRDATA.__hdr_len__
            readpos = 0
            numberofsentpackets = 0

            buff = ret.read(readsize)     # slice of a fragment
            chunk = buff                  # the whole fragment (for checksum calculation)
            self._rtp_pkt.m = 0
            self._rtp_pkt.ts = self._calctimestamp(90000)

            burstseqfirst = self._rtp_pkt.seq

            while buff != "":
                # Add retransmission information
                self._rtp_pkt.bytemin = readpos
                self._rtp_pkt.bytemax = readpos + len(buff) - 1

                # Copy data
                self._rtp_pkt.data = buff

                # Next packet
                readpos += len(buff)
                buff = ret.read(readsize)
                chunk += buff
                if buff != "":
                    # put it into the jobbuffer for timed sendout (avoid RTP bursts)
                    self._jobbuffer.append(str(self._rtp_pkt))
                else:
                    # Last packet, set marker
                    rtp_pkt_stitcher = rtpext.RTPMABRSTITCHER(self._rtp_pkt)
                    rtp_pkt_stitcher.m = 1                                          # TODO: use RTP extension header ids to identify packet types, marker should be just informationan only
                    rtp_pkt_stitcher.burstseqfirst = burstseqfirst
                    rtp_pkt_stitcher.burstseqlast = rtp_pkt_stitcher.seq
                    rtp_pkt_stitcher.chunknumber = self._number
                    rtp_pkt_stitcher.updatechecksum(chunk)
                    message += ", checksum: %s" % rtpext.RTPMABRSTITCHER.checksum2str(rtp_pkt_stitcher.checksum)

                    # put it into the jobbuffer
                    self._jobbuffer.append(str(rtp_pkt_stitcher))

                # Send them out
                self._jobsem.release()

                # Update sequence number
                numberofsentpackets += 1
                self._rtp_pkt.seq = (self._rtp_pkt.seq + 1) % 65536

            message += ", packets: %4d, period: %.03f)" % (numberofsentpackets, self._fetchperiod)
            self._logger.debug(message)

        except Exception as e:
            self._logger.warning(e.message)

        self._number += 1


    def run(self):
        self._run = True
        self._timeoffset_ut = time.time()

        # Start fetching segments
        self._fetchcallback(time.time()+self._period)

        # Start adding tokens, set the bitrate limit here by calculating how frequently a packet can leave
        self._tokencallback(self._mtu * 8.0 / self._bandwidthcap / 1.1, time.time())

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
            pass

        self._tokentimer.cancel()
        self._fetchtimer.cancel()
        self._opener.close()
        self._logger.debug("Exiting...")

    def stop(self):
        self._run = False
