import xml.etree.ElementTree as ET
import string


class MPDParser:

    _ns = {'ns': 'urn:mpeg:dash:schema:mpd:2011'}

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
        for period in self._mpdroot.findall('.//ns:Period', MPDParser._ns):
            for adaptationset in period.findall('.//ns:AdaptationSet', MPDParser._ns):
                segmenttemplate = adaptationset.find('.//ns:SegmentTemplate', MPDParser._ns)
                for representation in adaptationset.findall('.//ns:Representation', MPDParser._ns):
                    initsegmentpaths.append("/" + string.replace(segmenttemplate.attrib['initialization'],"$RepresentationID$",representation.attrib['id']))

        return initsegmentpaths

    def getmulticasts(self):
        if self._mpdroot is None:
            self._loadmpd()

        #find multicast addresses
        multicasts = []
        for period in self._mpdroot.findall('.//ns:Period', MPDParser._ns):
            for adaptationset in period.findall('.//ns:AdaptationSet', MPDParser._ns):
                for representation in adaptationset.findall('.//ns:Representation', MPDParser._ns):
                    addr, port = representation.attrib['id'].split('-',2)
                    multicasts.append([addr,int(port)])

        return multicasts

    def getMediaPatterns(self):
        if self._mpdroot is None:
            self._loadmpd()

        for representation in self._mpdroot.findall('.//ns:Representation', MPDParser._ns):
            for segmenttemplate in representation.findall('.//ns:SegmentTemplate', MPDParser._ns):
                yield (segmenttemplate.attrib['media'].replace('$RepresentationID$',representation.attrib['id']).replace('.','\.').replace('$Number$', '(\d+)'), representation.attrib['id'])

    def getInitializationPatterns(self):
        if self._mpdroot is None:
            self._loadmpd()

        for representation in self._mpdroot.findall('.//ns:Representation', MPDParser._ns):
            for segmenttemplate in representation.findall('.//ns:SegmentTemplate', MPDParser._ns):
                yield (segmenttemplate.attrib['initialization'].replace('$RepresentationID$',representation.attrib['id']).replace('.','\.'), representation.attrib['id'])

    def geturltemplatefor(self, representationid):
        if self._mpdroot is None:
            self._loadmpd()

        #segmenttemplate = self._mpdroot.find(".//ns:AdaptationSet/ns:Representation[@id='%s']/../ns:SegmentTemplate" % representationid, MPDParser._ns)  #-->removed, because the current ffmpeg encoding puts the segmenttemplate unter the representation
        segmenttemplate = self._mpdroot.find(".//ns:AdaptationSet/ns:Representation[@id='%s']/ns:SegmentTemplate" % representationid, MPDParser._ns)
        return segmenttemplate.attrib['media']
