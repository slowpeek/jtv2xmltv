#!/usr/bin/env python3

# NDX format:
# - 16 bit uint = number or records
# - list:
#   - 2 x 0x00
#   - 64-bit uint = number of 100-ns intervals since Jan 1, 1601 UTC
#   - 16-bit uint = offset of the corresponding PDT record in the pdt file

# PDT format:
# - literal 'JTV 3.x TV Program Data'
# - 3 x 0xA0
# - list:
#   - 16-bit uint = title length
#   - title

import argparse
import datetime
import os
import shutil
import struct
import sys
import tempfile
from xml.etree import ElementTree as ET
import zipfile

def ft_to_dt(ft):
    return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft/10)

def get_channels(jtv):
    channels = []
    memo = set()

    for item in jtv.namelist():
        (name, ext) = os.path.splitext(item)

        if ext == '.ndx' or ext == '.pdt':
            if name in memo:
                channels.append(name)
            else:
                memo.add(name)

    return channels

def xml_channels(doc, channels, enc):
    if enc.lower() not in ('utf8', 'utf-8'):
        channels = [x.encode('cp437').decode(enc) for x in channels]

    chcount = 0
    for channel_name in channels:
        chcount += 1

        el = ET.SubElement(doc, 'channel', id=str(chcount))
        ET.SubElement(el, 'display-name').text = str(channel_name)

def xml_program_one(doc, chid, title, str_time, end_time=None):
    attr = {
        'channel': str(chid),
        'start': str_time
    }

    if end_time is not None:
        attr['stop'] = end_time

    el = ET.SubElement(doc, 'programme', **attr)
    ET.SubElement(el, 'title').text = title

def xml_program(doc, jtv, chname, chid, enc):
    ndx_list = []
    with jtv.open(chname + '.ndx', 'r') as ndx:
        (ndx_num,) = struct.unpack('<H', ndx.read(2))

        for i in range(ndx_num):
            (_, time, pdt_offset) = struct.unpack('<HQH', ndx.read(12))
            ndx_list.append((ft_to_dt(time).strftime('%Y%m%d%H%M%S'), pdt_offset))

    if ndx_num:
        pdt_dict = {}
        with jtv.open(chname + '.pdt', 'r') as pdt:
            for (time, pdt_offset) in ndx_list:
                if pdt_offset not in pdt_dict:
                    pdt.seek(pdt_offset)
                    (size,) = struct.unpack('<H', pdt.read(2))
                    pdt_dict[pdt_offset] = pdt.read(size).decode(enc)

        # end_time for the last item
        ndx_list.append((None,))

        for i in range(ndx_num):
            xml_program_one(doc, chid, pdt_dict[ndx_list[i][1]], ndx_list[i][0], ndx_list[i+1][0])

def main():
    parser = argparse.ArgumentParser(
        prog='jtv2xml.py',
        description='Convert jtv zip (stdin) to xmltv (stdout)',
    )

    parser.add_argument('--pdt-enc', required=True,
                        help='Encoding of program names in pdt')
    parser.add_argument('--zip-enc', required=True,
                        help='Encoding of filenames in zip')

    args = parser.parse_args()

    # --

    with tempfile.TemporaryFile() as tmp:
        shutil.copyfileobj(sys.stdin.buffer, tmp)

        with zipfile.ZipFile(tmp) as jtv:
            channels = get_channels(jtv)
            doc = ET.Element('tv')

            xml_channels(doc, channels, args.zip_enc)

            for i in range(len(channels)):
                xml_program(doc, jtv, channels[i], i+1, args.pdt_enc)

            ET.indent(doc)
            ET.ElementTree(doc).write(sys.stdout.buffer, 'utf-8', True)

if __name__ == '__main__':
    main()
