#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

This script will analyze the paylods/tasks assigned by the messager.py 
and output the result to display.py.
It also stores most parameters, which are shared between different classes and scripts.
'''

import sys
sys.path.append("..")

from array import array

from utils import display
from utils.device import *

from lib import common

command = ''
devices = []
deviceID = None
menu = []
channel_time = None
strict_match = None


# Add a new device to the devices
def add_device(address, channel, payload):
  from player import Player
  def redo_scan(channel):
    if Player.feature_ping < Player.last_ping:
      global channel_time
      # Pause Player correctly
      while not Player._pause:
        Player._flag.clear()
      # Set channel
      Player.channel = channel
      common.radio.set_channel(channel)
      # Set feature_ping to keep receiving payloads on this channel for few seconds
      Player.feature_ping = Player.last_ping + common.timeout + channel_time
      # Resume Player
      Player._flag.set()

  global devices
  # Search in devices list
  for i in range(len(devices)):
    if address == devices[i].address:
      # Update device's channels
      if channel not in devices[i].channels:
        devices[i].channels.append(channel)
        devices[i].channels.sort()
      # Update the device's payloads if it satifies the following requirements
      if devices[i].model == None and len(payload) > 0 and payload not in devices[i].payloads:
        devices[i].payloads.append(payload)
        # Update device
        devices[i] = match_device(address, devices[i].channels, devices[i].payloads)
        # Keep scanning on this channel to verify the device if the device was not recognized
        if devices[i].model == None:
          redo_scan(channel)
        else:
          Player.feature_ping = Player.last_ping
      break

  # Add a new device to the devices
  else:
    payloads = []
    if len(payload) > 0: payloads.append(payload)
    devices.append(match_device(address, [channel], payloads))
    # Found new device, keep scanning on this channel to verify the device
    redo_scan(channel)
  # Display the scanned the result
  update_scanner_msg()


def update_scanner_msg():
  global devices, menu
  # Update selection limit
  menu = range(len(devices))
  msg = []
  msg.append('----------------------------------SCAN DEVICES----------------------------------')
  msg.append('{0:<4}{1:<16}{2:<24}{3:<14}{4:<8}{5:<14}'.format(
    'No.', 'Address', 'Channels', 'Vendor', 'Model', 'Status'))
  for i in range(len(devices)):
    msg.append('{0:<4}{1:<16}{2:<24}{3:<14}{4:<8}{5:<14}'.format(
      i+1, 
      ':'.join('{:02X}'.format(b) for b in devices[i].address),
      ','.join(str(c) for c in devices[i].channels), 
      devices[i].vendor, 
      devices[i].model, 
      devices[i].status))
  # Refresh display
  display.refresh(msg)


def update_device(address, channel, payload):
  global devices, deviceID
  # Search in devices list
  device = devices[deviceID]
  # Update device's channels
  if channel not in device.channels:
    device.channels.append(channel)
    device.channels.sort()
  # Update device's payloads if it satifies the following requirements
  if len(payload) > 0 and payload not in device.payloads:
    device.payloads.append(payload)
    # Update device
    device = match_device(device.address, device.channels, device.payloads)
    # Renew device
    devices[deviceID] = device
    if device.model != None:
      # Pause player
      from player import Player
      Player._flag.set()
      # # Update channels
      # update_channels()
      update_tasks_msg()
    else:
      update_matcher_msg()

def update_tasks_msg():
  global devices, deviceID, menu
  device = devices[deviceID]
  msg = []
  msg.append('----------------------------------SELECT TASKS----------------------------------')
  msg.append('You selected: {0} ({1} {2})'.format(
    ':'.join('{:02X}'.format(b) for b in device.address), 
    device.vendor, device.model))
  menu = range(2)
  msg.append('{0:<6}{1}'.format('No.', 'Task'))
  msg.append('{0:<6}{1}'.format('1', 'Sniff and record packets.'))
  msg.append('{0:<6}{1}'.format('2', 'Launch attacks.'))
  # Refresh display
  display.refresh(msg)

def update_matcher_msg():
  global devices, deviceID, menu
  device = devices[deviceID]
  msg = []
  msg.append('----------------------------------SELECT TASKS----------------------------------')
  msg.append('You selected: {0} ({1} {2})'.format(
    ':'.join('{:02X}'.format(b) for b in device.address), 
    device.vendor, device.model))
  menu = []
  # msg.append('{0:<6}{1}'.format('No.', 'Task'))
  # msg.append('{0:<6}{1}'.format('1', 'Sniff and record packets.'))
  # msg.append('{0:<6}{1}'.format('2', 'Launch attacks.'))
  msg.append('')
  msg.append('* Tasks is not avaliable right now because the device has not been located yet.')
  msg.append('* It may take minites to locate the device, please wait...')
  msg.append('')
  #### Test Code For Monitoring payloads
  l = len(device.payloads)
  ls = l > 10 and l-10 or 0
  for i in range(ls, l):
    msg.append('{0:<10}{1}'.format(
      i+1, 
      ':'.join('{:02X}'.format(b) for b in device.payloads[i])))
  ####
  # Refresh display
  display.refresh(msg)


def update_sniffer_msg():
  global menu, devices, deviceID
  device = devices[deviceID]
  menu = []
  msg = []
  msg.append('----------------------------------SNIFF PACKETS---------------------------------')
  msg.append('{0:<10}{1} {2}'.format('Device: ', device.vendor, device.model))
  msg.append('{0:<10}{1}'.format('Address: ', ':'.join('{:02X}'.format(b) for b in device.address)))
  msg.append('{0:<10}{1}'.format('Channels: ', ', '.join(str(c) for c in device.channels)))
  payload = array('B', [])
  # channel = None
  from player import Player
  if len(Player.records) > 0:
    # channel = Player.records[0][0]
    payload = Player.records[0][1]
    del Player.records[0]
  # msg.append('{0:<10}{1}'.format('Channel: ', channel))
  msg.append('')
  # Acquire the decoder path
  decoder ='{0}.decode'.format(devices[deviceID].moduler)
  try:
    # Decode the payload
    for m in eval(decoder)(payload):
      msg.append(m)
  except Exception as e:
    msg.append(str(e))
  # Refresh display
  display.refresh(msg)

# The following method also has to been optimised 
def update_attacker_msg(ping_rate=0):
  global menu, devices, deviceID
  device = devices[deviceID]
  menu = []
  msg = []
  msg.append('----------------------------------LAUNCH ATTACK---------------------------------')
  msg.append('{0:<9}{1} {2} {3}'.format('Device', ':', device.vendor, device.model))
  msg.append('{0:<9}{1} {2}'.format('Address', ':', ':'.join('{:02X}'.format(b) for b in device.address)))
  msg.append('{0:<9}{1} {2}'.format('Channels', ':', ', '.join(str(c) for c in device.channels)))
  from player import Player
  status = len(Player.payloads) > 0 and 'Attacking...' or 'No attack request found.'
  msg.append('{0:<9}{1} {2}'.format('Status', ':', status))
  # Refresh ping rate
  msg.append('{0:<9}{1} {2:<4}{3}'.format('Ping rate', ':', int(ping_rate), 'pks/s'))
  msg.append('')
  msg.append('----------------------------------ATTACK HISTORY--------------------------------')
  msg.append('{0:<5}{1:<4}{2}'.format('No.', 'Ch.', 'Payload'))
  l = len(Player.records)
  ls = l > 10 and l-10 or 0
  for i in range(ls, l):
    msg.append('{0:<5}{1:<4}{2}'.format(i+1, Player.records[i][0], Player.records[i][1]))
  # Refresh display
  display.refresh(msg)


# Parse attack commands
def parse_attack_commands(cmds):
  # Parse commands
  global devices, deviceID
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
  # Convert command list into payload list
  # and append them into Player.payloads
  device = devices[deviceID]
  payloads = []
  # from utils.devices import amazonbasics, logitech_mouse
  encoder ='{0}.encode'.format(device.moduler)
  for cmd in split_command(cmds):
    # self.add_record(['CMD', cmd])
    for payload in eval(encoder)(cmd, device):
      payloads.append(payload)
  return payloads