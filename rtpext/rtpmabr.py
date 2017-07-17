import imp
try:
  imp.find_module('dpkt')
except ImportError:
  print("This scrypt requires dpkt.rtp python library, please install python-dpkt!")
  exit(1)
from dpkt.rtp import RTP

import socket, struct


class RTPMABRDATA(RTP):
    ID = 0xabba

    __hdr__ = RTP.__hdr__ + (
        ('id', 'H', ID),
        ('length', 'H', 2),
        ('bytemin', 'I', 0),
        ('bytemax', 'I', 0),
    )

    def unpack(self, buf):
        super(RTPMABRDATA, self).unpack(buf)
        if self.id !=  RTPMABRDATA.ID:
            raise Exception("Invalid RTPMABRDATA packet format")



class RTPMABRSTITCHER(RTPMABRDATA):
    ID = 0xbaab

    __hdr__ = RTPMABRDATA.__hdr__ + (
        ('seqmin', 'I', 0),
        ('seqmax', 'I', 0),
        ('chunknumber', 'I', 0),
    )

    def __init__(self, rtpmabrdata=None):
        super(RTPMABRSTITCHER, self).__init__()
        if rtpmabrdata is not None:
            self._length=5

            self._type = rtpmabrdata._type
            self.seq = rtpmabrdata.seq
            self.ts = rtpmabrdata.ts
            self.ssrc = rtpmabrdata.ssrc
            self.id = RTPMABRSTITCHER.ID
            self.length = 5
            self.bytemin = rtpmabrdata.bytemin
            self.bytemax = rtpmabrdata.bytemax
            self.csrc = rtpmabrdata.csrc

            self.data = rtpmabrdata.data

    def unpack(self, buf):
        super(RTPMABRDATA, self).unpack(buf)
        if self.id !=  RTPMABRSTITCHER.ID:
            raise Exception("Invalid RTPMABRDATA packet format")
