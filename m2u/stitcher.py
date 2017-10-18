from channels import *
from rtpext import RTPMABRSTITCHER

import threading
import Queue


class Stitcher(threading.Thread):

    _stitcherqueue = Queue.Queue(30)
    _timeout = 0.1

    @classmethod
    def stitch(cls, ssrc, burstseqfirst, burstseqlast, chunknumber, checksum, logger):
        logger.debug('Initiate stitching for: ssrc=%s, rtpseq=%d-%d, chunknumber=%d, checksum=%s' % (ssrc, burstseqfirst, burstseqlast, chunknumber, RTPMABRSTITCHER.checksum2str(checksum)))
        cls._stitcherqueue.put_nowait((ssrc, burstseqfirst, burstseqlast, chunknumber, checksum))

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._memdb = args[1]

        self._run = True

    def run(self):
        while self._run:
            try:
                # get stitching job
                ssrc, burstseqfirst, burstseqlast, chunknumber, checksum = Stitcher._stitcherqueue.get(True, Stitcher._timeout)

                memdbkeys = []
                if burstseqlast >= burstseqfirst:
                    for seq in range(burstseqfirst, burstseqlast + 1):
                        memdbkeys.append(Slice.getmemcachedkey(ssrc, seq))

                # handle RTP seq overflow
                else:
                    for seq in range(burstseqfirst, 2 ** 16):
                        memdbkeys.append(Slice.getmemcachedkey(ssrc, seq))
                    for seq in range(0, burstseqlast + 1):
                        memdbkeys.append(Slice.getmemcachedkey(ssrc, seq))

                # get all slices from memcached
                ret = self._memdb.get_multi(memdbkeys)


                chunk = ''
                for key in memdbkeys:
                    try:
                        chunk += ret[key]
                    except KeyError:
                        self._logger.error("Packet %s has been lost --> retransmission (not yet implemented)!" % key)
                        continue

                # check fragment integrity
                if len(memdbkeys) != len(ret.keys()):           # or not RTPMABRSTITCHER.validateChecksum(chunk, checksum) :
                    self._logger.warning("ssrc: %d chunknumber: %d stitching failed, len: %dB, checksum: '%s' is invalid, expected: '%s' (plr: %d/%d)!" % (ssrc, chunknumber, len(chunk), RTPMABRSTITCHER.checksum2str(RTPMABRSTITCHER.checksum(chunk)), RTPMABRSTITCHER.checksum2str(checksum), len(memdbkeys)-len(ret.keys()), len(memdbkeys)))
                    continue

                self._logger.debug("ssrc: %d chunknumber: %d has been stitched, packet loss rate: %d/%d" % (ssrc, chunknumber, len(memdbkeys)-len(ret.keys()), len(memdbkeys)))


                # store in memcached
                if not self._memdb.set(Chunk.getmemcachedkey(ssrc, chunknumber), chunk):
                    self._logger.warning("Cannot store stitched object in memcached!")


            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self._run = False

    def stop(self):
        self._run = False
