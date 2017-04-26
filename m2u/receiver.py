import threading
import socket
import dpkt
import memcache



class Receiver(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwarggs=None):
        threading.Thread.__init__(self, group, target, name, args, kwarggs)

        self._logger = args[0]
        self._mcast_grp = args[1]
        self._mcast_port = int(args[2])
        self._memcachedaddress = args[3]
        self._memcached = memcache.Client([self._memcachedaddress], debug=0)

        self._run = False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        self._sock.settimeout(0.1)
        self._logger.debug("Receiver thread started for %s:%d" % (self._mcast_grp, self._mcast_port))

    def run(self):
        self._run = True

        # joining MC group
        self._sock.bind(('', self._mcast_port))
        host = socket.gethostbyname(socket.gethostname())
        self._sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
        self._sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._mcast_grp) + socket.inet_aton(host))

        while self._run:
            try:
                data, addr = self._sock.recvfrom(1024)
                rtp_pkt = dpkt.rtp.RTP()
                rtp_pkt.unpack(data)
                print rtp_pkt.version
                key = str(self._mcast_grp) + ":" + str(self._mcast_port) + ":" + str(rtp_pkt.seq)
                print key
                self._memcached.set(key,rtp_pkt.data)
            except socket.timeout:
                pass

    def stop(self):
        self._run = False

        # leaving MC group
        host = socket.gethostbyname(socket.gethostname())
        self._sock.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(self._mcast_grp) + socket.inet_aton(host))
