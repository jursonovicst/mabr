import imp
try:
  imp.find_module('dpkt')
except ImportError:
    raise Exception("This scrypt requires dpkt.rtp python library, please install python-dpkt!")
from dpkt.rtp import RTP

import socket, struct


class RTPEXT(RTP):
    __hdr__ = RTP.__hdr__ + (
        ('id', 'H', 0x0000),    # RTP extension header identifier
        ('length', 'H', 0),     # RTP extension header length, fix value, to be updated, if header changes!
    )

    def unpack(self, buf):
        super(RTPEXT, self).unpack(buf)



# RTP packet to hold slices of fragments. Not the last fragment
class RTPMABRDATA(RTPEXT):
    ID = 0xabba

    __hdr__ = RTPEXT.__hdr__ + (
        ('bytemin', 'I', 0),    # slice's starting byte offset in the fragment
        ('bytemax', 'I', 0),    # slice's ending byte offset in the fragment
    )

    def __init__(self, rtpmabrdata=None):
        super(RTPMABRDATA, self).__init__()
        self.id = self.ID
        self.length = 2

    def unpack(self, buf):
        super(RTPMABRDATA, self).unpack(buf)
        if self.id !=  RTPMABRDATA.ID:
            raise Exception("Invalid RTPMABRDATA packet format")


# RTP packet to hold the last slices of fragments
class RTPMABRSTITCHER(RTPMABRDATA):
    ID = 0xbaab                         # RTPMABRSTITCHER extension header identifier

    __hdr__ = RTPMABRDATA.__hdr__ + (   # same as above
        ('burstseqfirst', 'H', 0),        # ???
        ('burstseqlast', 'H', 0),        # ???
        ('chunknumber', 'I', 0),        # ???
    )

    def __init__(self, rtpmabrdata=None):
        super(RTPMABRSTITCHER, self).__init__()
        if rtpmabrdata is not None:
            self._type = rtpmabrdata._type
            self.seq = rtpmabrdata.seq
            self.ts = rtpmabrdata.ts
            self.ssrc = rtpmabrdata.ssrc
            self.id = self.ID
            self.length = super(RTPMABRSTITCHER, self).length + 2
            self.bytemin = rtpmabrdata.bytemin
            self.bytemax = rtpmabrdata.bytemax
            self.csrc = rtpmabrdata.csrc

            self.data = rtpmabrdata.data

    def unpack(self, buf):
        super(RTPMABRDATA, self).unpack(buf)
        if self.id !=  RTPMABRSTITCHER.ID:
            raise Exception("Invalid RTPMABRSTITCHER packet format")
