import threading
import Queue
import signal, os

import imp

import imp
try:
  imp.find_module('memcache')
except ImportError:
  print("This scrypt requires memcache python library, please install python-memcache!")
  exit(1)
import memcache


class Stitcher(threading.Thread):
    _stitcherqueue = Queue.Queue(30)
    _timeout = 0.1


    @classmethod
    def stitch(cls, ssrc, seqmin, seqmax, chunknumber):
        cls._stitcherqueue.put_nowait((ssrc, seqmin, seqmax, chunknumber))

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._memcached = memcache.Client([args[1]], debug=0)

        self._run = True

    def run(self):
        laststitchedchunknumber = None
        laststitchedseq = None
        while self._run:
            try:
                ssrc, seqmin, seqmax, chunknumber = Stitcher._stitcherqueue.get(True, Stitcher._timeout)

                #find my channel
                #find my stream

                self._logger.debug('Stitching for ssrc=%d: %d-%d to chunknumber=%d' % (ssrc, seqmin, seqmax, chunknumber))

                keys = []
                for seq in range(seqmin,seqmax):
                    keys.append(str(ssrc) + ":" + str(seq))

                ret = self._memcached.get_multi(keys)

                self._logger.warning("packet loss rate: %d%%" % ( (1-(float(len(ret.keys())) / len(keys)) ) * 100 ) )

                chunk = ''
                for seq in range(seqmin,seqmax):
                    try:
                        chunk += ret[str(ssrc) + ":" + str(seq)]
                    except KeyError:
                        continue


                print "gjgjhgh" + str(len(chunk))


            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self._run = False

    def stop(self):
        self._run = False