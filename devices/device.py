#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Github: xswxm
Blog: xswxm.com

'''

class Device():
  def __init__(self, address, channels, payloads, vender=None):
    self.address = address
    self.channels = channels
    self.payloads = payloads
    self.vender = vender
    self.model = None
    self.status = 'Matching'


class AmazonBasics():
  def __init__(self, address=None, channels=None, suffix=None):
    self.address = address
    self.vender = 'Amazon'
    self.model = 'AmazonBasics'
    self.channels = channels
    self.suffix = suffix
    self.status = 'Unencrypted'
    self.moduler = 'amazonbasics'

class LogitechMouse():
  def __init__(self, address=None, channels=None, prefix=None, payload_tag=None, status=None):
    self.address = address
    self.vender = 'Logitech'
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
  suffix_flag = False  # To ensure at least two packets share the same suffix
  # sync_flag = False
  for payload in payloads:
    l = len(payload)
    if l == 3:
      pass
      # sync_flag = True
    elif l == 6:
      if payload[0]%0x10 <=2 and payload[0]/0x10 <=3:
        if not suffix_flag:
          suffix_flag = True
        else:
          suffix = payload[4:6]
      # Ruturn None if the packet does not match the head
      else:
        break
    # Ruturn None if the packet does mathch the length 3 or 6
    else:
      break
    if suffix != None and suffix_flag:
      return AmazonBasics(address, channels, suffix)
  return None

from array import array
def match_logitech_mouse(address, channels, payloads):
  prefix = None
  payload_tag = None
  prefix_flag = False  # To ensure at least two packets share the same prefix
  sync_flag = False
  if address[4] == 0:
    status = 'Unpluged'
    sync_flag = True
    payload_tag = 0
    for payload in payloads:
      l = len(payload)
      if l == 10 and payload[0] > 0 and payload[8] == 0:
        if payload[1] == 0xC2:
          if not prefix_flag:
            prefix_flag = True
          else:
            prefix = payload[:2]
        elif payload[1] == 0x4F:
           payload_tag = payload
        # Ruturn None if the packet does not match the head
        else:
          break
      # Firmware info or sync packet
      elif l == 22 or l == 5:
        pass
      # Ruturn None if the packet does mathch the length 3 or 6
      else:
        break
  else:
    status = 'Unencrypted'
    for payload in payloads:
      l = len(payload)
      if l == 5:
        sync_flag = True
      elif l == 10 and payload[8] == 0:
        if payload[:2] == array('B', [0x00, 0xC2]):
          if not prefix_flag:
            prefix_flag = True
          else:
            prefix = payload[:2]
        elif payload[:2] == array('B', [0x00, 0x4F]):
          if payload[3] == 0:
            payload_tag = payload
          # # Sleep packet
          # else:
          #   pass
        # Ruturn None if the packet does not match the head
        else:
          # There are exceptions, require to be investigated into
          pass
          # break
      # Firmware info packet
      elif l == 22:
        pass
      # Ruturn None if the packet does mathch the length 3 or 6
      else:
        break
    if prefix != None and payload_tag != None and sync_flag and prefix_flag:
      return LogitechMouse(address, channels, prefix, payload_tag, status)
  return None

def prematch_device(payloads):
  for payload in payloads:
    l = len(payload)
    if l == 6:
      return 'AmazonBasics?'
    elif l == 10:
      return 'LogitechMouse?'
  return 'Checking'

def match_device(address, channels, payloads):
  device = None
  if len(payloads) > 3: 
    device = match_amazonbasics(address, channels, payloads)
    if device != None: return device
    device = match_logitech_mouse(address, channels, payloads)
    if device != None: return device
  device = Device(address, channels, payloads)
  device.status = prematch_device(payloads)
  return device
