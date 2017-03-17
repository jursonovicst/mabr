from dpkt.rtp import RTP
import socket, struct


class RTPExt(RTP):
    ehid = 0
    ehlen = 0
    eh = ''

    def __len__(self):
        if self.x == 0:
            return super(RTPExt, self).__len__()
        else:
            return self.__hdr_len__ + len(self.csrc) + 2 + 2 + len(self.eh) + len(self.data)

    def __str__(self):
        if self.x == 0:
            return super(RTPExt, self).__str__()
        else:
            return self.pack_hdr() + self.csrc + struct.pack('!H',self.ehid) + struct.pack('!H',self.ehlen) + self.eh + str(self.data)

    def unpack(self, buf):
        if self.x == 0:
            super(RTPExt, self).unpack(buf)
        else:
            super(RTPExt, self).unpack(buf)
            self.csrc  =     buf[self.__hdr_len__:                                   self.__hdr_len__ + self.cc * 4    ]
            self.ehid  = struct.unpack('!H',buf[self.__hdr_len__ + self.cc * 4:                     self.__hdr_len__ + self.cc * 4 + 2])
            self.ehlen = struct.unpack('!H',buf[self.__hdr_len__ + self.cc * 4 + 2:                 self.__hdr_len__ + self.cc * 4 + 4])
            self.eh    =     buf[self.__hdr_len__ + self.cc * 4 + 4:                 self.__hdr_len__ + self.cc * 4 + 4 + self.ehlen * 4]
            self.data =      buf[self.__hdr_len__ + self.cc * 4 + 4 + self.ehlen * 4:]
