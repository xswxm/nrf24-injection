#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

This script will measure the successful pings per seconds.
e.g.: sudo python ping.py -l -a 61:8E:9C:CD:03 -f 74 -t 0 -r 0

'''
import sys, time, threading
from lib import common
common.init_args('./ping.py')
common.parser.add_argument('-a', '--address', type=str, help='Address to sniff, following as it changes channels', required=True)
common.parser.add_argument('-f', '--channel', type=int, help='RF channel', default=0)
common.parse_and_init()

channel = common.args.channel
# Total number of payloads sent
count = 0

# Parse the prefix address
address = common.args.address.replace(':', '').decode('hex')[::-1][:5]
# Put the radio in sniffer mode (ESB w/o auto ACKs)
common.radio.enter_sniffer_mode(address)
# Set channel
common.radio.set_channel(channel)

stop_event = threading.Event()
stop_event.set()

# Update per milliseconds
def display():
  global count, stop_event
  # To record the number of payloads sent for every 100 milliseconds
  pings = [0]*10
  # Highest rate
  max_rate = 0
  while stop_event.isSet():
    pings = pings[1:] + [count]
    rate = pings[-1] - pings[0]
    if max_rate < rate: max_rate = rate
    msg = 'Maximum Rate: {0:>4}pks/s    Current Rate: {1:>4}pks/s'.format(max_rate, rate)
    sys.stdout.write('\r'+msg)
    sys.stdout.flush()
    time.sleep(0.1)


if __name__ == "__main__":
  t = threading.Thread(target=display,args=())
  t.start()
  try:
    while True:
      if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
        count += 1
  except KeyboardInterrupt:
    stop_event.clear()