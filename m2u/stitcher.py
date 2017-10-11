import threading
import Queue
import signal, os
from channels import *
from rtpext import RTPMABRSTITCHER

import imp

import imp
try:
    imp.find_module('memcache')
except ImportError:
    raise Exception("This scrypt requires memcache python library, please install python-memcache!")
import memcache


class Stitcher(threading.Thread):
    _stitcherqueue = Queue.Queue(30)
    _timeout = 0.1


    @classmethod
    def stitch(cls, ssrc, burstseqfirst, burstseqlast, chunknumber, checksum, logger):
        logger.debug('Initiate stitching for: ssrc=%s, rtpseq=%d-%d, chunknumber=%d, checksum=%04x' % (ssrc, burstseqfirst, burstseqlast, chunknumber, checksum))
        cls._stitcherqueue.put_nowait((ssrc, burstseqfirst, burstseqlast, chunknumber, checksum))

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._memcached = memcache.Client([args[1]])

        self._run = True

    def run(self):
        while self._run:
            try:
                #get stitching job
                ssrc, burstseqfirst, burstseqlast, chunknumber, checksum = Stitcher._stitcherqueue.get(True, Stitcher._timeout)

                #find my channel
                #find my stream


                memcachedkeys = []
                if burstseqlast >= burstseqfirst:
                    for seq in range(burstseqfirst, burstseqlast):
                        memcachedkeys.append(Slice.getmemcachedkey(ssrc,seq))

                #handle RTP seq overflow
                else:
                    for seq in range(burstseqfirst, 2 ** 16-1):
                        memcachedkeys.append(Slice.getmemcachedkey(ssrc,seq))
                    for seq in range(0, burstseqlast):
                        memcachedkeys.append(Slice.getmemcachedkey(ssrc,seq))

                # get all slices from memcached
                ret = self._memcached.get_multi(memcachedkeys)


                chunk = ''
                for key in memcachedkeys:
                    try:
                        chunk += ret[key]
                    except KeyError:
                        #self._logger.warning("Packet rtpseq=%s has been lost --> retransmission (not yet implemented)!" % seq)
                        continue

                # calculate packet loss rate
                packetlossrate = 1.0-(float(len(ret.keys())) / (len(memcachedkeys)+0.0000001))

                # check fragment integrity
                if not RTPMABRSTITCHER.validateChecksum(chunk, checksum):
                    self._logger.warning("Fragment chunknumber=%d stitching failed, invalid checksum (packet loss rate: %d%%)!" % (chunknumber, packetlossrate * 100))
                    continue

                if packetlossrate < 0.01:
                    self._logger.debug("Fragment chunknumber=%d has been stitched, packet loss rate: %d%%" % (chunknumber, packetlossrate * 100))
                elif packetlossrate < 0.05:
                    self._logger.warning("Fragment chunknumber=%d has been stitched, packet loss rate: %d%%" % (chunknumber, packetlossrate * 100))
                else:
                    self._logger.error("Fragment chunknumber=%d has been stitched, packet loss rate: %d%%" % (chunknumber, packetlossrate * 100))


                # store in memcached
                self._memcached.set(Chunk.getmemcachedkey(ssrc,chunknumber), chunk)


            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self._run = False

    def stop(self):
        self._run = False