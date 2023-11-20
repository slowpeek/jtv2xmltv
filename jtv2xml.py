#!/usr/bin/python
#-*- coding: utf-8 -*-
# =======================================================================================================
# PDT file format:
# The file is always starts with "JTV 3.x TV Program Data" folowed by three characters with the code 0Ah.
# Starting from 01Ah offset there are the records with the variable length:
#  * 2 bytes - the number of characters in the TV-show title
#  * TV-show title
#
# NDX file format:
# The first two bytes is the number of records in .ndx file. Than there are 12 bytes records:
#   * First two bytes is always 0
#   * Eight bytes of FILETIME structure (Contains a 64-bit value representing the number of
#                                        100-nanosecond intervals since January 1, 1601 (UTC).)
#   * Two bytes - the offset pointer to TV-show characters number title in .pdt file.
# =======================================================================================================
import os
import sys
import struct
import datetime
from zipfile import ZipFile
from xml.etree import ElementTree as ET

jtvzip = 'jtv.zip'
xmltv = 'xmltv.xml'
pdt_encode = 'cp1251'

def ft_to_dt(ft):
    return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft/10)

def read_jtv_channels(jtvzip):
    jtv = ZipFile(jtvzip, 'r')
    channels = []
    memo = set()

    for item in jtv.namelist():
        (name, ext) = os.path.splitext(item)

        if ext == '.ndx' or ext == '.pdt':
            if name in memo:
                channels.append(name)
            else:
                memo.add(name)

    jtv.close()
    return channels

def write_xml_channels(doc, channels):
    chcount = 0
    for channel_name in channels:
        chcount += 1
        el = ET.SubElement(doc, 'channel', id=str(chcount))
        ET.SubElement(el, 'display-name').text = str(channel_name)

def write_xml_schedule(doc, chname, chid, title, str_time, end_time=None):
    attr = {
        'channel': str(chid),
        'start': str_time
    }

    if end_time is not None:
        attr['stop'] = end_time

    el = ET.SubElement(doc, 'programme', **attr)
    ET.SubElement(el, 'title').text = title

def read_jtv(doc, myzip, chname, chid):
    ndx_list = []
    with myzip.open(chname + '.ndx', 'r') as ndx:
        (ndx_num,) = struct.unpack('H', ndx.read(2))

        for i in range(ndx_num):
            (_, time, pdt_offset) = struct.unpack('<HQH', ndx.read(12))
            ndx_list.append((ft_to_dt(time).strftime('%Y%m%d%H%M%S'), pdt_offset))

    if ndx_num:
        pdt_dict = {}
        with myzip.open(chname + '.pdt', 'r') as pdt:
            for (time, pdt_offset) in ndx_list:
                if pdt_offset not in pdt_dict:
                    pdt.seek(pdt_offset)
                    (size,) = struct.unpack('H', pdt.read(2))
                    pdt_dict[pdt_offset] = pdt.read(size).decode(pdt_encode)

        # end_time for the last item
        ndx_list.append((None,))

        for i in range(ndx_num):
            write_xml_schedule(doc, chname, chid, pdt_dict[ndx_list[i][1]],
                               ndx_list[i][0], ndx_list[i+1][0])

def main():
    channels = read_jtv_channels(jtvzip)
    doc = ET.Element('tv')

    write_xml_channels(doc, channels)

    with ZipFile(jtvzip) as myzip:
        for i in range(len(channels)):
            read_jtv(doc, myzip, channels[i], i+1)

            sys.stdout.write('*')
            sys.stdout.flush()

        sys.stdout.write('\ndone\n')

    ET.indent(doc)
    ET.ElementTree(doc).write(xmltv, encoding='utf8')

if __name__ == '__main__':
    main()
