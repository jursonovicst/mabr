import xml.etree.ElementTree as ET
import string


class MPDParser:

    def __init__(self, mpd):
        self._mpd = mpd
        self._mpdroot = None

    def _loadmpd(self):
        self._mpdroot = ET.fromstring(self._mpd)

        #check xml #TODO: use xslt...
        if 'profiles' not in self._mpdroot.attrib:
            raise Exception("invalid mpd, no profile")

        if 'type' not in self._mpdroot.attrib or self._mpdroot.attrib['type']!="dynamic":
            raise Exception("Non dynamic MPD")

    def getinitsegmentpaths(self):
        if self._mpdroot is None:
            self._loadmpd()

        #find repres
        initsegmentpaths = []
        ns = {'ns': 'urn:mpeg:dash:schema:mpd:2011'}
        for period in self._mpdroot.findall('.//ns:Period', ns):
            for adaptationset in period.findall('.//ns:AdaptationSet', ns):
                segmenttemplate = adaptationset.find('.//ns:SegmentTemplate', ns)
                for representation in adaptationset.findall('.//ns:Representation', ns):
                    initsegmentpaths.append("/" + string.replace(segmenttemplate.attrib['initialization'],"$RepresentationID$",representation.attrib['id']))

        return initsegmentpaths
