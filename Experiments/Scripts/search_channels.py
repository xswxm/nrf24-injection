#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

This script is used to search device/dongle's channels.

HOW TO DETECT A DEVICE'S CHANNELS
1. Use general steps to discover the its mac address;
2. Keep the USB dongle pluged-in and turn the mouse/keyboard off;
3. Run this script to ping each channels for few seconds.

e.g.: sudo python search_channels.py -l -a 61:8E:9C:CD:03

'''
import sys
from lib import common
common.init_args('./search_channels.py')
common.parser.add_argument('-a', '--address', type=str, help='Address to sniff, following as it changes channels', required=True)
common.parse_and_init()

channels = []

# Parse the prefix address
address = common.args.address.replace(':', '').decode('hex')[::-1][:5]
# Put the radio in sniffer mode (ESB w/o auto ACKs)
common.radio.enter_sniffer_mode(address)

# Ping address in diff channels
while True:
  for channel in common.channels:
    common.radio.set_channel(channel)
    if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
      # Add new channel to channels
      if channel not in channels:
        channels.append(channel)
        channels.sort()
      msg = 'Channels: {0}'.format(', '.join(str(c) for c in channels))
      sys.stdout.write('\r'+msg)
      sys.stdout.flush()