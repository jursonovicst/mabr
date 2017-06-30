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

        servicefqdn = config.get('general', 'servicefqdn')
        mpdpath = config.get('general', 'mpdpath')
        print servicefqdn
        print mpdpath

        if (servicefqdn,mpdpath) in cls._channels:
            raise Exception('Channel (%s, %s) already defined by %s' % (servicefqdn, mpdpath, configfp.name))

        cls._channels[(servicefqdn, mpdpath)] = Channel(config)

    # find and return a Channel instance
    @classmethod
    def getChannelByID(cls, servicefqdn, mpdpath):
        try:
            return cls._channels[(servicefqdn,mpdpath)]
        except KeyError:
            return None

    # check if an fqdn is configured to any channel
    @classmethod
    def validatefqdn(cls, fqdn):
        for key in cls._channels:
            print key
            if key[0] == fqdn:
                return True

        return False

    # check if an fqdn and path matches one chunkpattern
    @classmethod
    def getChannelByChunk(cls, fqdn, path):
        for ckey in cls._channels:
            for skey in cls._channels[ckey]._streams:
                if cls._channels[ckey]._servicefqdn == fqdn and re.match(cls._channels[ckey]._streams[skey]._media, path):
                    return cls._channels[ckey]

        return None

    # check if an fqdn and path matches one chunkpattern
    @classmethod
    def getChannelByInitSegment(cls, fqdn, path):
        for ckey in cls._channels:
            for skey in cls._channels[ckey]._streams:
                if cls._channels[ckey]._servicefqdn == fqdn and re.match(cls._channels[ckey]._streams[skey]._initialization, path):
                    return cls._channels[ckey]

        return None



    def __init__(self, config):
        self._servicefqdn = config.get('general', 'servicefqdn')
        self._mpdpath = config.get('general', 'mpdpath')
        self._ingestfqdn = config.get('general', 'ingestfqdn')

        self._streams = {}
        for section in config.sections():
            if section == 'general':
                continue

            self._streams[section] = Stream(config, section)    #section represents the representationid

        pass

    def getMPDRequestUrl(self):
        return "http://%s%s" % (self._servicefqdn, self._mpdpath)

    def getMPDIngestUrl(self):
        return "http://%s%s" % (self._ingestfqdn, self._mpdpath)

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

    def getStreams(self):
        for key in self._streams:
            yield self._streams[key]

#    def getMCParams(self):
#        for representationid in self._streams:
#            yield self._streams[representationid].getMCParam()

#    ####check###
#    def getMPDUrl(self):
#        return self._mpdurl.scheme + "://" + self._mpdurl.netloc + self._mpdurl.path + self._mpdurl.query       #TODO: check if query is right here...




class Stream: #=representation or an RTP stream

    def __init__(self, config, section):
        self._representationid = section
        self._mcast_grp = config.get(section, 'mcast_grp')
        self._mcast_port = config.getint(section, 'mcast_port')
        self._ssrc = config.getint(section, 'ssrc')
        self._media = None                # store the mpd media path pattern
        self._initialization = None       # store the mpd initialization path pattern

        self._rtplog = {}

    def getMCParam(self):
        return (self._mcast_grp, self._mcast_port, self._ssrc)

    def setMedia(self, pattern):
        self._media = pattern

    def setInitialization(self, pattern):
        self._initialization = pattern

class chunk:

    def __init__(self, chunknumber):
        self._chunknumber = chunknumber


