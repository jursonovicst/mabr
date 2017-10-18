import ConfigParser
import re


# represents a channel
class Channel:

    _channels = {}          # indexed by (servicefqdn, mpdpath)

    # just create an instance of Channel, and append it to the static dictionary indexed by (servicefqdn, mpdpath)
    @classmethod
    def append(cls, configfp):
        config = ConfigParser.ConfigParser()
        config.readfp(configfp)

        servicefqdn = config.get('general', 'servicefqdn').lower()
        mpdpath = config.get('general', 'mpdpath')

        if (servicefqdn, mpdpath) in cls._channels:
            raise Exception('Channel (%s, %s) already defined by %s' % (servicefqdn, mpdpath, configfp.name))

        cls._channels[(servicefqdn, mpdpath)] = Channel(config)


    # find and return a Channel instance
    @classmethod
    def getChannelByURL(cls, servicefqdn, mpdpath):
        try:
            return cls._channels[(servicefqdn, mpdpath)]
        except KeyError:
            return None


    # check if an fqdn is configured to any channel
    @classmethod
    def validatefqdn(cls, fqdn):
        for key in cls._channels:
            if key[0] == fqdn.lower():
                return True

        return False


    @classmethod
    def getchannelbympdurl(cls, fqdn, path):
        if (fqdn, path) in cls._channels:
            return cls._channels[(fqdn, path)]

        return None


    @classmethod
    def getchannelbyinitsegmenturl(cls, fqdn, path):
        for ckey in cls._channels:
            for skey in cls._channels[ckey]._streams:
                if cls._channels[ckey]._servicefqdn == fqdn and re.match(cls._channels[ckey]._streams[skey].getinitializationpattern(), path):
                    return cls._channels[ckey]

        return None


    @classmethod
    def getChannelByURL(cls, fqdn, path):
        for channel in cls._channels.itervalues():
            for stream in channel.getstreams():
                if channel.getservicefqdn() == fqdn and re.match(stream.getmediapattern(), path):
                    return channel, stream

        return None, None


    def __init__(self, config):
        self._servicefqdn = config.get('general', 'servicefqdn')
        self._mpdpath = config.get('general', 'mpdpath')
        self._ingestfqdn = config.get('general', 'ingestfqdn')

        self._streams = {}      # indexed by (representationid)

        for section in config.sections():       # section represents the representationid
            if section == 'general':
                continue

            self._streams[section] = Stream(config, section)

    def getmpdrequesturl(self):
        return "http://%s%s" % (self._servicefqdn, self._mpdpath)

    def getmpdingesturl(self):
        return "http://%s%s" % (self._ingestfqdn, self._mpdpath)

    def getstreams(self):
        for stream in self._streams.itervalues():
            yield stream

    def findstream(self, representationid):
        try:
            return self._streams[representationid]
        except KeyError:
            raise Exception("representation %s has not been found in config" % representationid)

    def getingesturl(self, path):
        return "http://%s%s" % (self._ingestfqdn, path)

    def getmpdpath(self):
        return self._mpdpath

    def getrepresentationids(self):
        for representationid in self._streams:
            yield representationid

    def getservicefqdn(self):
        return self._servicefqdn


class Stream:       # =representation or an RTP stream

    def __init__(self, config, representationid):
        self._representationid = representationid
        self._mcast_grp = config.get(representationid, 'mcast_grp')         # representationid represents the section in the config
        self._mcast_port = config.getint(representationid, 'mcast_port')
        self._ssrc = config.getint(representationid, 'ssrc')
        self._mediapattern = None                # store the mpd media path pattern
        self._initializationpattern = None       # store the mpd initialization path pattern
        self._mimetype = ''                      # store the mpd mimeType value

        self._rtplog = {}

    def getmcparam(self):
        return self._mcast_grp, self._mcast_port, self._ssrc

    def getssrc(self):
        return self._ssrc

    def getchunknumberfrompath(self, path):
        m = re.match(self._mediapattern, path)
        return m.group(1)

    def getmediapattern(self):
        return self._mediapattern

    def setmediapattern(self, pattern):
        self._mediapattern = pattern

    def getinitializationpattern(self):
        return self._initializationpattern

    def setinitializationpattern(self, pattern):
        self._initializationpattern = pattern

    def setmimetype(self, mimetype):
        self._mimetype = mimetype

    def getmimetype(self):
        return self._mimetype


class Chunk:

    @staticmethod
    def getmemcachedkey(ssrc, chunknumber):
        return "chunk:" + str(ssrc) + ":" + str(chunknumber)


    def __init__(self, chunknumber):
        self._chunknumber = chunknumber


class Slice:

    @staticmethod
    def getmemcachedkey(ssrc, seq):
        return "slice:" + str(ssrc) + ":" + str(seq)


    def __init__(self, seq):
        self._seq = seq         # RTP sequence number
