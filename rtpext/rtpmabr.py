import binascii
import sys

import imp
try:
  imp.find_module('dpkt')
except ImportError:
    raise Exception("This scrypt requires dpkt.rtp python library, please install python-dpkt!")
from dpkt.rtp import RTP


# RTP with general header estension
class RTPEXT(RTP):
    __hdr__ = RTP.__hdr__ + (
        ('id', 'H', 0x0000),    # RTP extension header identifier
        ('length', 'H', 0),     # RTP extension header length, fix value, to be updated, if header changes!
    )
    def __init__(self):
        super(RTPEXT, self).__init__()
        self.x=1

    def unpack(self, buf):
        super(RTPEXT, self).unpack(buf)
        if self.x != 1:
            raise Exception("Invalid RTPEXT packet format: extension header is missing.")


# RTP packet to hold slices of a fragment, but not the last slice
class RTPMABRDATA(RTPEXT):
    ID = 0xabba                         # RTPMABRDATA extension header identifier

    __hdr__ = RTPEXT.__hdr__ + (
        ('bytemin', 'I', 0),    # slice's starting byte offset in the fragment
        ('bytemax', 'I', 0),    # slice's ending byte offset in the fragment
    )

    def __init__(self, rtpmabrdata=None):
        super(RTPMABRDATA, self).__init__()
        self.id = self.ID
        self.length = 2         # in 4 bytes

    def unpack(self, buf):
        super(RTPMABRDATA, self).unpack(buf)
        if self.id !=  RTPMABRDATA.ID:
            raise Exception("Invalid RTPMABRDATA header format, ID: %04x is unknown" % self.id)


# RTP packet to hold the last slice of a fragment
class RTPMABRSTITCHER(RTPMABRDATA):

    @staticmethod
    def checksum(buff):
        return binascii.crc32(buff) & 0xffffffff

    @staticmethod
    def validateChecksum(buff, checksum):
        return (RTPMABRSTITCHER.checksum(buff) == checksum)

    @staticmethod
    def checksum2str(checksum):
        return "0x%08x" % checksum

    @staticmethod
    def hexdump(filename, buff):
        if filename is None:
            f = sys.stdout
        else:
            f = open(filename, 'w')

        for i in range(0,len(buff),16):
            f.write("%04x" % i)
            for j in range(i, i+(16 if len(buff)-i >= 16 else len(buff)-i) ):
                f.write(" %s%02x" % (" " if j%16==8 else "", ord(buff[j])))
            f.write("  ")
            for j in range(i, i+(16 if len(buff)-i >= 16 else len(buff)-i) ):
                f.write("%c" % buff[j] if ord(buff[j]) >=32 and ord(buff[j]) <127 else '.')
            f.write("\n")

        if filename is not None:
            f.close()


    ID = 0xbaab                         # RTPMABRSTITCHER extension header identifier

    __hdr__ = RTPMABRDATA.__hdr__ + (   # same as above
        ('burstseqfirst', 'H', 0),      # reserved for later use
        ('burstseqlast', 'H', 0),       # reserved for later use
        ('chunknumber', 'I', 0),        # the DASH number of a fragment
        ('checksum', 'I', 0),           # checksum on 4 bytes
    )

    def __init__(self, rtpmabrdata=None):
        super(RTPMABRSTITCHER, self).__init__()
        self.id = self.ID
        self.length += 3                # in 4 bytes
        if rtpmabrdata is not None:
            self._type = rtpmabrdata._type
            self.seq = rtpmabrdata.seq
            self.ts = rtpmabrdata.ts
            self.ssrc = rtpmabrdata.ssrc
            self.bytemin = rtpmabrdata.bytemin
            self.bytemax = rtpmabrdata.bytemax
            self.csrc = rtpmabrdata.csrc

            self.data = rtpmabrdata.data

    def updateChecksum(self, buff):
        self.checksum = RTPMABRSTITCHER.checksum(buff)

    def unpack(self, buf):
        super(RTPMABRDATA, self).unpack(buf)
        if self.id !=  RTPMABRSTITCHER.ID:
            raise Exception("Invalid RTPMABRSTITCHER packet format, ID: %04x is unknown" % self.id)
