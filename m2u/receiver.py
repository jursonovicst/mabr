import threading
import socket
import struct
import Queue
import rtpext
from stitcher import *
from dpkt.rtp import RTP
from rtpext import *
import sys, traceback
from channels import *

import imp
try:
    imp.find_module('memcache')
except ImportError:
    raise Exception("This script requires memcache python library, please install python-memcache!")
import memcache


class Receiver(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._mcip = args[1]
        self._memcached = memcache.Client([args[2]])
        self._stream = args[3]
        self._mcast_grp, self._mcast_port, self._ssrc = self._stream.getMCParam()

        self._run = False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass
        self._sock.settimeout(0.1)

    def run(self):
        self._run = True

        # joining MC group
        self._sock.bind(('', self._mcast_port))   #may causes issues in windows
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._mcast_grp) + socket.inet_aton(self._mcip))

#        self._sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.INADDR_ANY if self._mcip == '0.0.0.0' else socket.inet_aton(self._mcip))
#        mreq = struct.pack('4sl', socket.inet_aton(self._mcast_grp), socket.INADDR_ANY if self._mcip == '0.0.0.0' else socket.inet_aton(self._mcip))

        self._logger.debug("Receiver thread started for %s:%d (ssrc: %d) on %s" % (self._mcast_grp, self._mcast_port, self._ssrc, self._mcip))

        laststitchedchunk=None
        while self._run:
            try:
                data, addr = self._sock.recvfrom(1500)
                rtp_pkt = RTP()
                rtp_pkt.unpack(data)

                # drop inproper packages
                if rtp_pkt.version != 2:
                    self._logger.warning('invalid RTP format' )
                    continue

                if int(rtp_pkt.ssrc) != self._ssrc:
                    self._logger.warning('Foregin RTP stream (ssrc=%d, but expecting %d)' % (int(rtp_pkt.ssrc),self._ssrc))     #TODO: implement received from...
                    continue

                if rtp_pkt.x == 1:
                    rtp_pkt=RTPEXT()
                    rtp_pkt.unpack(data)

                    if rtp_pkt.id == RTPMABRDATA.ID:
                        rtp_pkt = RTPMABRDATA()
                        rtp_pkt.unpack(data)
                    elif rtp_pkt.id == RTPMABRSTITCHER.ID:
                        rtp_pkt=RTPMABRSTITCHER()
                        rtp_pkt.unpack(data)
                    else:
                        self._logger.warning('Non MABR RTP packet (id=%02x)' % rtp_pkt.id)
                        continue
                else:
                    self._logger.warning('Non MABR RTP packet (RTP extension is missing)')
                    continue

                # store data
                if not self._memcached.set(Slice.getmemcachedkey(rtp_pkt.ssrc, rtp_pkt.seq), rtp_pkt.data):
                    self._logger.warning('Cannot store RTP packet: ssrc=%s, seq=%d' % (rtp_pkt.ssrc, rtp_pkt.seq))
#                else:
#                    self._logger.debug('RTP packet stored: ssrc=%s, seq=%d' % (rtp_pkt.ssrc, rtp_pkt.seq))




                # trigger stitcher
                if rtp_pkt.m == 1:
                    Stitcher.stitch(rtp_pkt.ssrc, rtp_pkt.burstseqfirst, rtp_pkt.burstseqlast, rtp_pkt.chunknumber, rtp_pkt.checksum, self._logger)


            except socket.timeout:
                pass
            except Exception as e:
                self._logger.warning("Oops: %s" % e.message)
                self._logger.debug(traceback.format_exc())


    def stop(self):
        self._run = False

        # leaving MC group
        host = socket.gethostbyname(socket.gethostname())
        self._sock.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(self._mcast_grp) + socket.inet_aton(host))

    def stitch(self,firstseq, lastseq):

        #delete_multi
        #get_multi
        pass