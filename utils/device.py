#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Github: xswxm
Blog: xswxm.com

'''

# The following modules will be referred by 'config.py' DO NOT REMOVE IT
from utils.devices import amazonbasics, logitech_mouse

class Device():
  def __init__(self, address, channels, payloads, vendor=None, status=None):
    self.address = address
    self.channels = channels
    self.payloads = payloads
    self.vendor = vendor
    self.model = None
    self.status = status


class AmazonBasics():
  def __init__(self, address=None, channels=None, suffix=None):
    self.address = address
    self.vendor = 'AmazonBasics'
    self.model = 'Mouse'
    self.channels = channels
    self.suffix = suffix
    self.status = 'Unencrypted'
    self.moduler = 'amazonbasics'

class LogitechMouse():
  def __init__(self, address=None, channels=None, prefix=None, payload_tag=None, status=None):
    self.address = address
    self.vendor = 'Logitech'
    self.model = 'Mouse'
    self.channels = channels
    self.prefix = prefix
    self.payload_tag = payload_tag
    self.status = status
    if status == 'Unencrypted':
      self.moduler = 'logitech_mouse'
    else:
      self.moduler = None

def match_amazonbasics(address, channels, payloads):
  suffix = None
  count = 0
  limit = 3  # To ensure at least 2 packets share the same suffix
  def check_suffix(p, s, c):
    if s == None or s == p:
      c += 1
      return p, c
    else:
      return s, 0
  # Loop the payloads list to varify the format
  for payload in payloads:
    l = len(payload)
    # Example packet: [03:3C:2A]
    if l == 3:
      if payload[0] == 3:
        suffix, count = check_suffix(payload[1:3], suffix, count)
        if not count: break
      else:
        break
    # Example packet: [02:FD:EF:FF:3C:2A:29:E9]
    # The last 2 bytes could be junk caused by the environment
    elif l == 6:
      if payload[0]/0x10 <= 3 and payload[4] > 0 and payload[5] > 0:
        # Payload form mouse clicks, e.g.: [31:04:00:30:3C:2A]
        if payload[0]%0x10 == 1 and payload[1] <= 7:
          suffix, count = check_suffix(payload[4:6], suffix, count)
          if not count: break
        # Payload form mouse movement, e.g.: [02:FF:0F:00:3C:2A]
        elif payload[1]%0x10 == 2:
          suffix, count = check_suffix(payload[4:6], suffix, count)
          if not count: break
      else:
        break
    if suffix != None and count >= limit:
      return AmazonBasics(address, channels, suffix)
  # else:
  #   # Not found
  #   return None
  # Mismatch
  return None

from array import array
def match_logitech_mouse(address, channels, payloads):
  def checksum(payload):
    cks = 0
    for p in payload[:-1]: cks += p
    return ((cks%0x100^0xFF)+0x01)%0x100
  def check_payload(p, s, c):
    if s == None or  s == p:
      c += 1
      return p, c
    else:
      return s, 0
  
  sync_flag = False
  prefix = None
  count_prefix = 0
  payload_tag = None
  count_tag = 0
  prefix_limit = 4   # To ensure at least 4 packets share the same prefix
  tag_limit  = 1     # To ensure at least 1 packets share the same payload_tag

  # Justify device's status by checking the last byte of the address
  status = address[4] == 0 and 'Unpluged' or 'Unencrypted'
  for payload in payloads:
    # Checksum to varify if it is a payload from logitech
    # Comment it if you are worried about the performance
    if payload[-1] != checksum(payload):
      break
    l = len(payload)
    # Sync payload, e.g.: [00:40:04:B0:0C] and [00:40:00:6E:52]
    if l == 5:
      if payload[:2] == array('B', [0x00, 0x40]):
        sync_flag = True
    # Payload from mouse clicks and movement
    elif 10 <= l < 22 and payload[8] == 0:
      # Payload starting a event
      if payload[1] == 0xC2 and payload[2] < 0x20 and payload[3] == 0:
        prefix, count_prefix = check_payload(payload[:2], prefix, count_prefix)
        if count_prefix == 0: break
      # Payload ending a event
      elif payload[1] == 0x4F and payload[2] == payload[3] == 0:
        payload_tag, count_tag = check_payload(payload[:10], payload_tag, count_tag)
        if count_tag == 0: break
      # Payload entering sleep mode
      # elif payload[1] == 0x4F and payload[2] == 0 and payload[3] != 0:
      #   pass
    # Firmware info packet
    # elif l == 22:
    #   pass
    # Ruturn None if the packet does mathch the length 3 or 6
    if prefix != None and payload_tag != None and count_prefix >= prefix_limit and count_tag >= tag_limit and sync_flag:
      return LogitechMouse(address, channels, prefix, payload_tag, status)
  # else:
  #   # Not found
  #   return None
  # Mismatch
  return None

def prematch_device(address, channels, payloads):
  ls = []
  vendor = None
  status = None
  for payload in payloads:
    l = len(payload)
    if l in [3, 6, 24]: vendor = 'Chicony?'
    elif l in [5, 10, 22]: vendor = 'Logitech?'
    if l not in ls: ls.append(l)
  status = ','.join(str(l) for l in sorted(ls))
  return Device(address, channels, payloads, vendor, status)

def match_device(address, channels, payloads):
  device = None
  # Match devices if number of payloads is larger than three
  if len(payloads) > 3:
    device = match_amazonbasics(address, channels, payloads)
    if device != None: return device
    device = match_logitech_mouse(address, channels, payloads)
    if device != None: return device
  device = prematch_device(address, channels, payloads)
  return device
