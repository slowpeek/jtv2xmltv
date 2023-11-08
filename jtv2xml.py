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
import re
import sys
import struct
import datetime
from zipfile import *

jtvzip = 'jtv.zip'
xmltv = 'xmltv.xml'
pdt_encode = 'cp1251'


def ft_to_dt(ft):
  microseconds = ft / 10
  seconds, microseconds = divmod(microseconds, 1000000)
  days, seconds = divmod(seconds, 86400)
  return datetime.datetime(1601, 1, 1) + datetime.timedelta(days, seconds, microseconds)


def read_jtv_channels(jtvzip):
  jtv = ZipFile(jtvzip, 'r')
  channels = []

  for item in jtv.namelist():
    if item[-4:] == '.ndx':
      channels.append(item[:-4])

  jtv.close()
  return channels


def write_xml_channels(channels, xmltv):
  chcount = 0
  with open(xmltv, 'w') as xmlfile:
    xmlfile.write('<?xml version="1.0" encoding="utf8"?>\n<tv>\n')
    for channel_name in channels:
      chcount += 1
      xmlfile.write('<channel id="%d">\n' % chcount)
      xmlfile.write('  <display-name>%s</display-name>\n' % channel_name)
      xmlfile.write('</channel>\n')
  xmlfile.close()


def write_xml_schedule(chname, chid, title, str_time, end_time):
  chcount = 0
  with open(xmltv, 'a') as xmlfile:
    if end_time is None:
      xmlfile.write('<programme channel="%d" start="%s">\n' % (chid, str_time))
    else:
      xmlfile.write('<programme channel="%d" start="%s" stop="%s">\n' % (chid, str_time, end_time))
    xmlfile.write('  <title>%s</title>\n</programme>\n' % title.replace('&', '&amp;'))
  xmlfile.close()


def read_jtv(chname, chid):
  ndx = chname + '.ndx'
  pdt = chname + '.pdt'

  with open('jtv/' + ndx, 'rb') as ndx:
    with open('jtv/' + pdt, 'rb') as pdt:
      number = struct.unpack('h', ndx.read(2))[0] # Number of records in .ndx file
      
      for i in range(number):
        str_time = 0 
        end_time = 0

        ndx.seek((i + 1) * 12 - 8)
        str_time = struct.unpack('Q', ndx.read(8))[0] # Get program start time in FILETIME format

        if i < (number - 1):
          ndx.seek((i + 2) * 12 - 8)
          end_time = struct.unpack('Q', ndx.read(8))[0]
        else:
          end_time = None # For the last TV-show we know only the start time.
        
        ndx.seek((i + 1) * 12)
        pdt_offset = struct.unpack('H', ndx.read(2))[0] # Offset pointer to .pdt file

        pdt.seek(pdt_offset)
        poffset = struct.unpack('H', pdt.read(2))[0] # Get TV-show's title characters number.

        try:
          title = struct.unpack('%ds' % poffset, pdt.read(poffset))[0]
          title = title.decode(pdt_encode).encode('utf-8')
        except Exception, e:
          print '\n\n\n\tSomething went wrong!\nFile "%s.pdt" is not fully decoded!\n' % chname
          print 'Error message:\n%s\n\nDebug information:' % e
          print 'chname - %s\nndx_offset  - %X\npdt_offset  - %X\npdt_namelen - %X\nfiletime   - %X\n'\
                 % (chname, 12*i+12, pdt_offset, poffset, str_time)
          ndx.close()
          pdt.close()
          break

        str_time = format(ft_to_dt(str_time), '%Y%m%d%H%M%S')
        if end_time is not None:
          end_time = format(ft_to_dt(end_time), '%Y%m%d%H%M%S')

        write_xml_schedule(chname, chid, title, str_time, end_time)
  ndx.close()
  pdt.close()

def main():
  ZipFile(jtvzip, 'r').extractall('jtv')
  channels = read_jtv_channels(jtvzip)
  write_xml_channels(channels, xmltv)

  for i in range(len(channels)):
    sys.stdout.write("*")
    sys.stdout.flush()
    read_jtv(channels[i], i+1)

  with open(xmltv, 'a') as xmlfile:
    xmlfile.write('</tv>\n')
  xmlfile.close()

  sys.stdout.write("\n")
  print "Done!"

if __name__ == '__main__':
  main()
