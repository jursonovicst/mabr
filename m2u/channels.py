import ConfigParser
import re

# represents a channel
class Channel:

    # indexed by (servicefqdn, mpdpath)
    _channels = {}

    # just create an instance of Channel, and append it to the static dictionary indexed by (servicefqdn, mpdpath)
    @classmethod
    def append(cls, configfp):
        config = ConfigParser.ConfigParser()
        config.readfp(configfp)

        servicefqdn = config.get('general', 'servicefqdn').lower()
        mpdpath = config.get('general', 'mpdpath')

        if (servicefqdn,mpdpath) in cls._channels:
            raise Exception('Channel (%s, %s) already defined by %s' % (servicefqdn, mpdpath, configfp.name))

        cls._channels[(servicefqdn, mpdpath)] = Channel(config)

    # find and return a Channel instance
    @classmethod
    def getChannelByURL(cls, servicefqdn, mpdpath):
        try:
            return cls._channels[(servicefqdn,mpdpath)]
        except KeyError:
            return None

    # check if an fqdn is configured to any channel
    @classmethod
    def validateFQDN(cls, fqdn):
        for key in cls._channels:
            if key[0] == fqdn.lower():
                return True

        return False


    @classmethod
    def getChannelByMPDURL(cls, fqdn, path):
        if cls._channels.has_key((fqdn, path)):
            return cls._channels[(fqdn, path)]

        return None


    @classmethod
    def getChannelByInitSegmentURL(cls, fqdn, path):
        for ckey in cls._channels:
            for skey in cls._channels[ckey]._streams:
                if cls._channels[ckey]._servicefqdn == fqdn and re.match(cls._channels[ckey]._streams[skey].getInitializationPattern(), path):
                    return cls._channels[ckey]

        return None


    @classmethod
    def getChannelByURL(cls, fqdn, path):
        for channel in cls._channels.itervalues():
            for stream in channel.getStreams():
                if channel.getServiceFQDN() == fqdn and re.match(stream.getMediaPattern(), path):
                    return channel, stream

        return None




    def __init__(self, config):
        self._servicefqdn = config.get('general', 'servicefqdn')
        self._mpdpath = config.get('general', 'mpdpath')
        self._ingestfqdn = config.get('general', 'ingestfqdn')

        self._streams = {}      # indexed by (representationid)

        for section in config.sections():       # section represents the representationid
            if section == 'general':
                continue

            self._streams[section] = Stream(config, section)

    def getMPDRequestUrl(self):
        return "http://%s%s" % (self._servicefqdn, self._mpdpath)

    def getMPDIngestUrl(self):
        return "http://%s%s" % (self._ingestfqdn, self._mpdpath)

    def getStreams(self):
        for stream in self._streams.itervalues():
            yield stream

    def findStream(self, representationid):
        try:
            return self._streams[representationid]
        except KeyError:
            raise Exception("representation %s has not been found in config" % representationid)


    def getIngestUrl(self, path):
        return "http://%s%s" % (self._ingestfqdn, path)

    def getMPDPath(self):
        return self._mpdpath

    def getRepresentationIDs(self):
        for representationid in self._streams:
            yield representationid

    def getServiceFQDN(self):
        return self._servicefqdn

#    def getMCParams(self):
#        for representationid in self._streams:
#            yield self._streams[representationid].getMCParam()

#    ####check###
#    def getMPDUrl(self):
#        return self._mpdurl.scheme + "://" + self._mpdurl.netloc + self._mpdurl.path + self._mpdurl.query       #TODO: check if query is right here...




class Stream: #=representation or an RTP stream

    def __init__(self, config, representationid):
        self._representationid = representationid
        self._mcast_grp = config.get(representationid, 'mcast_grp')         # representationid represents the section in the config
        self._mcast_port = config.getint(representationid, 'mcast_port')
        self._ssrc = config.getint(representationid, 'ssrc')
        self._mediapattern = None                # store the mpd media path pattern
        self._initializationpattern = None       # store the mpd initialization path pattern

        self._rtplog = {}

    def getMCParam(self):
        return (self._mcast_grp, self._mcast_port, self._ssrc)

    def getSSRC(self):
        return self._ssrc

    def getChunknumberFromPath(self, path):
        m=re.match(self._mediapattern, path)
        return m.group(1)

    def getMediaPattern(self):
        return self._mediapattern

    def setMediaPattern(self, pattern):
        self._mediapattern = pattern

    def getInitializationPattern(self):
        return self._initializationpattern

    def setInitializationPattern(self, pattern):
        self._initializationpattern = pattern


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
