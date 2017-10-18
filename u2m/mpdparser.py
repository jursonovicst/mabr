import xml.etree.ElementTree as ET
import ConfigParser
import re
from mcsender import *


class MPDParser:

    @staticmethod
    def _str2unixtime(self, timestr):
        if timestr is None or timestr == "":
            return 0

        # time is stored always in localtime
        try:
            return time.mktime(time.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%fZ"))
        except ValueError:
            try:
                return time.mktime(time.strptime(timestr, "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError:
                try:
                    return time.mktime(time.strptime(timestr, "%Y-%m-%dT%H:%M:%S")) - time.altzone      # This is in UTC, convert to localtime + do not forget DST!!!
                except ValueError:
                    try:
                        match = re.search("PT(\d+(\.\d+)*)S", timestr)
                        return float(match.group(1))
                    except:
                        raise Exception("No matching timeformat for %s" % timestr)


    def __init__(self, proxy, logger, configfp):
        self._proxy = proxy
        proxy_handler = urllib2.ProxyHandler({'http': self._proxy} if self._proxy != "" else {})
        self._opener = urllib2.build_opener(proxy_handler)
        self._logger = logger
        self._config = ConfigParser.ConfigParser()
        self._config.readfp(configfp)
        self._jobs = []

    def _calculateLastNumber(self, timescale, duration, startNumber, availabilityStartTime, presentationTimeOffset=0, suggestedPresentationDelay=0):
        return self._calculateNumber(time.time(), timescale, duration, startNumber, availabilityStartTime, presentationTimeOffset, suggestedPresentationDelay)

    def _calculateNumber(self, at, timescale, duration, startNumber, availabilityStartTime, presentationTimeOffset=0, suggestedPresentationDelay=0):

        self._logger.debug("at %d" % at)
        self._logger.debug("timescale %d" % int(timescale))
        self._logger.debug("duration %d" % int(duration))
        self._logger.debug("startNumber %d" % int(startNumber))
        self._logger.debug("availabilityStartTime %d" % self._str2unixtime(availabilityStartTime))
        self._logger.debug("presentationTimeOffset %s" % presentationTimeOffset)
        self._logger.debug("suggestedPresentationDelay %d" % self._str2unixtime(suggestedPresentationDelay))
        return (time.time() - self._str2unixtime(availabilityStartTime) - int(duration) / int(timescale)) / (int(duration)/int(timescale)) + int(startNumber)

    def fetch(self):
        # get mpd
        mpdurl = 'http://' + self._config.get('general', 'ingestfqdn') + self._config.get('general', 'mpdpath')
        self._logger.debug("Open manifest file '%s'" % mpdurl)
        ret = self._opener.open(mpdurl)
        mpd = ret.read()
        self._opener.close()

        # parse mpd
        mpdroot = ET.fromstring(mpd)

        #check xml      # TODO: use xslt...
        if 'profiles' not in mpdroot.attrib:
            raise Exception("invalid mpd, no profile")
        self._logger.debug("MPD %s found" % mpdroot.attrib['profiles'])

        if 'type' not in mpdroot.attrib or mpdroot.attrib['type'] != "dynamic":
            raise Exception("Non dynamic MPD")
        self._logger.debug("Dynamic mpd found")

        # find repres
        ns = {'ns': 'urn:mpeg:dash:schema:mpd:2011'}
        for period in mpdroot.findall('.//ns:Period', ns):
            self._logger.debug("Period '%s' found" % (period.attrib['id'] if 'id' in period.attrib else "--"))

            for adaptationset in period.findall('.//ns:AdaptationSet', ns):
                self._logger.debug("AdaptationSet '%s' found" % (adaptationset.attrib['id'] if 'id' in adaptationset.attrib else '--'))

                segmenttemplate = adaptationset.find('.//ns:SegmentTemplate', ns)
                self._logger.debug("SegmentTemplate (media=%s) found" % (segmenttemplate.attrib['media'] if 'media' in segmenttemplate.attrib else "--"))
                for representation in adaptationset.findall('.//ns:Representation', ns):
                    self._logger.debug("Representation '%s' found (bitrate: %.2fMbps)" % (representation.attrib['id'], float(representation.attrib['bandwidth'])/1000/1000))

                    try:
                        mcast_grp = self._config.get(representation.attrib['id'], 'mcast_grp')
                        mcast_port = self._config.get(representation.attrib['id'], 'mcast_port')
                        ssrc = self._config.getint(representation.attrib['id'], 'ssrc')
                        urltemplate = os.path.dirname(mpdurl) + "/" + segmenttemplate.attrib['media']
                        p = MCSender(name="u2m-%d" % ssrc, args=(mcast_grp,          # 0
                                                                 int(mcast_port),    # 1
                                                                 int(ssrc),          # 2
                                                                 urltemplate,        # 3
                                                                 representation.attrib['id'],    # 4
                                                                 self._calculateLastNumber(segmenttemplate.attrib['timescale'], segmenttemplate.attrib['duration'], segmenttemplate.attrib['startNumber'], mpdroot.attrib['availabilityStartTime'], mpdroot.attrib['presentationTimeOffset'] if 'presentationTimeOffset' in mpdroot.attrib else 0, mpdroot.attrib['suggestedPresentationDelay'] if 'suggestedPresentationDelay' in mpdroot.attrib else 0),
                                                                 int(segmenttemplate.attrib['duration'])/int(segmenttemplate.attrib['timescale']),
                                                                 self._proxy,        # 7
                                                                 self._logger.getChild('MCSender-%d' % ssrc),       # 8
                                                                 int(representation.attrib['bandwidth'])*float(self._config.get('general', 'bwfactor')),  # 9
                                                                 self._config.getint('general', 'mtu'),  # 10
                                                                 self._config.getint('general', 'mcast_ttl')    # 11
                                                                 ))
                        p.start()
                        self._jobs.append(p)
                    except ConfigParser.NoSectionError:
                        pass    # if representationid is not in config, do not send representation


    def join(self):
        while any(p.join(MCSender.timeout) is None and p.isAlive for p in self._jobs):
            pass


    def stop(self):
        for p in self._jobs:
            if p.isAlive():
                p.stop()
                p.join(MCSender.timeout)





