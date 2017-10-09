import threading
import Queue
import signal, os
from channels import *

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
    def stitch(cls, ssrc, burstseqfirst, burstseqlast, chunknumber, logger):
        logger.debug('Initiate stitching for: ssrc=%s, rtpseq=%d-%d, chunknumber=%d' % (ssrc, burstseqfirst, burstseqlast, chunknumber))
        cls._stitcherqueue.put_nowait((ssrc, burstseqfirst, burstseqlast, chunknumber))

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._memcached = memcache.Client([args[1]])

        self._run = True

    def run(self):
        while self._run:
            try:
                #get stitching job
                ssrc, burstseqfirst, burstseqlast, chunknumber = Stitcher._stitcherqueue.get(True, Stitcher._timeout)

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

                #check fragment size

                # calculate packet loss rate
                packetlossrate = 1.0-(float(len(ret.keys())) / (len(memcachedkeys)+0.0000001))
                if packetlossrate < 0.01:
                    self._logger.debug("Fragment chunknumber=%d has been stitched, packet loss rate: %d%%" % (chunknumber, packetlossrate * 100))
                elif packetlossrate < 0.05:
                    self._logger.warning("Fragment chunknumber=%d has been stitched, packet loss rate: %d%%" % (chunknumber, packetlossrate * 100))
                else:
                    self._logger.error("Fragment chunknumber=%d has been stitched, packet loss rate: %d%%" % (chunknumber, packetlossrate * 100))

                #store in memcached
                self._memcached.set(Chunk.getmemcachedkey(ssrc,chunknumber), chunk)


            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self._run = False

    def stop(self):
        self._run = False