import threading
import Queue
import signal, os

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


                keys = []
                if burstseqlast >= burstseqfirst:
                    for seq in range(burstseqfirst, burstseqlast):
                        keys.append(str(ssrc) + ":" + str(seq))

                #handle RTP seq overflow
                else:
                    for seq in range(burstseqfirst, 2 ** 32-1):
                        keys.append(str(ssrc) + ":" + str(seq))
                    for seq in range(0, burstseqlast):
                        keys.append(str(ssrc) + ":" + str(seq))

                # get all slices from memcached
                ret = self._memcached.get_multi(keys)

                # calculate packet loss rate
                packetlossrate = 1-(float(len(ret.keys())) / (len(keys)+0.0000001))
                if packetlossrate < 0.01:
                    self._logger.debug("packet loss rate: %d%%" % (packetlossrate * 100))
                elif packetlossrate < 0.05:
                    self._logger.warning("packet loss rate: %d%%" % (packetlossrate * 100))
                else:
                    self._logger.error("packet loss rate: %d%%" % (packetlossrate * 100))

                chunk = ''
                for seq in keys:
                    try:
                        chunk += ret[str(ssrc) + ":" + str(seq)]
                    except KeyError:
                        self._logger.warning("Packet rtpseq=%d has been lost --> retransmission (not yet implemented)!" % seq)
                        continue

                #check fragment size
                self._logger.debug("Fragment chunknumber=%d has been stitched!" % chunknumber)
                #print "gjgjhgh" + str(len(chunk))


            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self._run = False

    def stop(self):
        self._run = False