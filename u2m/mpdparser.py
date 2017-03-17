import urllib2
import xml.etree.ElementTree as ET
import string
import os
import time
import xml.dom.minidom

from mcsender import *

class MPDParser:
    mpdurl=""
    mpdroot=None

    def __init__(self, mpdurl, proxy, logger, config):
        self.mpdurl = mpdurl
        self._proxy = proxy
        self._logger = logger
        self._config = config
        self._jobs = []

    def _calculateNumberNow(self, startNumber, availabilityStartTime, timeShiftBufferDepth):
        try:
            availabilityStartTime_utc = time.mktime(time.strptime(availabilityStartTime, "%Y-%m-%dT%H:%M:%S.%fZ"))
        except ValueError:
            try:
                availabilityStartTime_utc = time.mktime(time.strptime(availabilityStartTime, "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError:
                raise Exception("No matching timeformat for %s" % availabilityStartTime)

        #print time.strptime(timeShiftBufferDepth, "PT%HH%MM%SS")
        #timeShiftBufferDepth_utc = time.mktime(time.strptime(timeShiftBufferDepth, "PT%HH%MM%SS"))
        return time.time()-availabilityStartTime_utc+time.timezone+int(startNumber)-10  #TODO: fix above

    def cancel(self):
        for p in self._jobs:
            p.terminate()

    def run(self):
        #get mpd

        proxy_handler = urllib2.ProxyHandler({'http': self._proxy} if self._proxy != "" else {})

        self._logger.debug("Open manifest file '%s'" % self.mpdurl)
        opener = urllib2.build_opener(proxy_handler)
        ret = opener.open(self.mpdurl)
        mpd = ret.read()

        #parse mpd
        self.mpdroot = ET.fromstring(mpd)
        #print xml.dom.minidom.parseString(ET.tostring(self.mpdroot, 'utf-8')).toprettyxml(indent="  ")

        #check xml #TODO: use xslt...
        if 'profiles' not in self.mpdroot.attrib:
            raise Exception("invalid mpd, no profile")
        self._logger.debug("MPD %s found" % self.mpdroot.attrib['profiles'])

        if 'type' not in self.mpdroot.attrib or self.mpdroot.attrib['type']!="dynamic":
            raise Exception("Non dynamic MPD")
        self._logger.debug("Dynamic mpd found")

        #find repres
        ns = {'ns': 'urn:mpeg:dash:schema:mpd:2011'}
        for period in self.mpdroot.findall('.//ns:Period', ns):
            self._logger.debug("Period '%s' found" % (period.attrib['id'] if 'id' in period.attrib else "--"))

            for adaptationset in period.findall('.//ns:AdaptationSet', ns):
                self._logger.debug("AdaptationSet '%s' found" % (adaptationset.attrib['id'] if 'id' in adaptationset.attrib else '--'))

                segmenttemplate = adaptationset.find('.//ns:SegmentTemplate', ns)
                self._logger.debug("SegmentTemplate (media=%s) found" % (segmenttemplate.attrib['media'] if 'media' in segmenttemplate.attrib else "--"))
                for representation in adaptationset.findall('.//ns:Representation', ns):
                    self._logger.debug("Representation '%s' found (bitrate: %s)" % (representation.attrib['id'],representation.attrib['bandwidth']))

                    mcast_grp = self._config.get(representation.attrib['id'], 'mcast_grp')
                    mcast_port = self._config.get(representation.attrib['id'], 'mcast_port')
                    ssrc = self._config.get(representation.attrib['id'], 'ssrc')
                    url = os.path.dirname(self.mpdurl) + "/" + string.replace(segmenttemplate.attrib['media'],"$RepresentationID$",representation.attrib['id'])
                    p = MCSender(name="u2m-%s" % representation.attrib['id'], args=(period.attrib['id'], mcast_grp, int(mcast_port), int(ssrc), url, self._calculateNumberNow(segmenttemplate.attrib['startNumber'], self.mpdroot.attrib['availabilityStartTime'], None), 1, self._proxy, self._logger))
                    self._jobs.append(p)
                    p.start()

        for p in self._jobs:
            p.join()

        self._logger.debug("Exit")






