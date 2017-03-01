import urllib2
import xml.etree.ElementTree as ET
import string
import os
import time
import xml.dom.minidom

from worker import *

class U2M:
    mpdurl=""
    mpdroot=None
    _jobs = []

    def __init__(self, mpdurl, proxy):
        self.mpdurl = mpdurl
        self._proxy = proxy

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

        opener = urllib2.build_opener(proxy_handler)
        ret = opener.open(self.mpdurl)
        mpd = ret.read()

        #parse mpd
        self.mpdroot = ET.fromstring(mpd)
        print xml.dom.minidom.parseString(ET.tostring(self.mpdroot, 'utf-8')).toprettyxml(indent="  ")

        #check xml
        if 'profiles' not in self.mpdroot.attrib:
            raise Exception("aaaa")
        print "MPD %s found" % self.mpdroot.attrib['profiles']

        if 'type' not in self.mpdroot.attrib or self.mpdroot.attrib['type']!="dynamic":
            raise Exception("Non dynamic MPD")
        print "Dynamic mpd found"

        #find repres
        ns = {'ns': 'urn:mpeg:dash:schema:mpd:2011'}
        for period in self.mpdroot.findall('.//ns:Period', ns):
            print "Period '%s' found" % period.attrib['id'] #if 'id' in period.attrib else "Unknown"

            for adaptationset in period.findall('.//ns:AdaptationSet', ns):
                print "AdaptationSet found"

                segmenttemplate = adaptationset.find('.//ns:SegmentTemplate', ns)
                print "SegmentTemplate (media=%s) found" % segmenttemplate.attrib['media'] #if 'media' in segmenttemplate.attrib else "Unknown"
                for representation in adaptationset.findall('.//ns:Representation', ns):
                    print "Representation '%s' found (bitrate: %s)" % (representation.attrib['id'],representation.attrib['bandwidth']) #if 'id' in representation.attrib else "Unknown"

                    url = os.path.dirname(self.mpdurl) + "/" + string.replace(segmenttemplate.attrib['media'],"$RepresentationID$",representation.attrib['id'])
                    p = Worker(None,None,"test", (period.attrib['id'], representation.attrib['id'], url, self._calculateNumberNow(segmenttemplate.attrib['startNumber'], self.mpdroot.attrib['availabilityStartTime'], None), 1, self._proxy))
                    self._jobs.append(p)
                    p.start()

        for p in self._jobs:
            p.join()

        print "EEE"






