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


import logging, argparse
from nrf24 import *
import curses
from devices.device import Device, match_device
from devices import amazonbasics, logitech_mouse
from array import array

channels = []
args = None
parser = None
radio = None

# task = 'scan'         # Task
command = ''         # Stored commands
commands = ['A', 'B', 'C']
commands.append('')
commandsID = len(commands)
scanner = None
sniffer = None
matcher = None
attacker = None
devices = []          # Device list
deviceID = None       # Selected deviceID
# selection = None      # Selection
selection_limit = 0   # Selection limit
stdscr = None
stdscrID = 0



def init_commands():
  global command, commands, commandsID
  command = ''
  commands = []
  file = open('history', 'r') 
  for line in file:
    commands.append(line.replace('\n', ''))
  commands.append(command)
  commandsID = len(commands)-1
  file.close()
  
def save_commonds():
  global commands
  file = open('history', 'w')
  for command in commands[:-1]:
    file.write(command+'\n')
  # file.writelines(commands)
  file.close()

# Initialize the argument parser
def init_args(description):

  global parser
  parser = argparse.ArgumentParser(description,
    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=50,width=120))
  parser.add_argument('-c', '--channels', type=int, nargs='+', help='RF channels', default=range(2, 84), metavar='N')
  parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output', default=False)
  parser.add_argument('-l', '--lna', action='store_true', help='Enable the LNA (for CrazyRadio PA dongles)', default=False)
  parser.add_argument('-i', '--index', type=int, help='Dongle index', default=0)

# Parse and process common comand line arguments
def parse_and_init():
  global parser, args, channels, radio
  # Parse the command line arguments
  args = parser.parse_args()
  # Setup logging
  level = logging.DEBUG if args.verbose else logging.INFO
  logging.basicConfig(level=level, format='[%(asctime)s.%(msecs)03d]  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
  # Set the channels
  # channels = args.channels
  channels = range(2, 84)
  logging.debug('Using channels {0}'.format(', '.join(str(c) for c in channels)))
  # Initialize the radio
  radio = nrf24(args.index)
  if args.lna: radio.enable_lna()


# Standard startup. Probably don't need to change this
def init_screen():
  global stdscr
  stdscr = curses.initscr()
  curses.cbreak()
  curses.noecho()
  stdscr.keypad(1)

# Standard shutdown. Probably don't need to change this.
def exit_screen():
  global stdscr
  curses.nocbreak()
  stdscr.keypad(0)
  curses.echo()
  curses.endwin()

def refresh_screen(msg):
  global command, stdscr, stdscrID
  notice = 'Commond (<m: main menu>, <b: back>, <q: quit>): '
  stdscr.clear()
  for i in range(len(msg)):
    # stdscr.addstr(i, 0, str(msg[i]))
    stdscr.addstr(i, 0, msg[i])
    # stdscr.move(0, 0)
  stdscr.addstr(i+1, 0, '')
  stdscr.addstr(i+2, 0, notice+command)
  x = len(msg)+1
  y = len(notice)
  for i in range(stdscrID):
    try:
      y += 1
      stdscr.move(x,y)
    except:
      x += 1
      y = 0
  stdscr.move(x,y)
  stdscr.refresh()

def update_device(address, channel, payload):
  global devices, deviceID
  # Search in devices list
  device = devices[deviceID]
  # Update device's channels
  if channel not in device.channels:
    device.channels.append(channel)
  # Update device's payloads if it satifies the following requirements
  if len(payload) > 0 and payload not in device.payloads:
    device.payloads.append(payload)
    # Update device
    from devices.device import match_device
    device = match_device(device.address, device.channels, device.payloads)
    # Renew device
    devices[deviceID] = device
    if device.model != None:
      # Pause matcher
      global matcher
      matcher.pause()
      # # Update channels
      # update_channels()
      update_tasks_msg()
    else:
      update_matcher_msg()

def update_channels():
  global channels, radio, devices, deviceID
  c = []
  # Parse the ping payload
  ping_payload = '0F:0F:0F:0F'.replace(':', '').decode('hex')
  # Format the ACK timeout and auto retry values
  ack_timeout = 0
  ack_timeout = max(0, min(ack_timeout, 15))
  retries = max(0, min(1, 15))
  # channels = range(2, 84)
  for channel in channels:
    radio.set_channel(channel)
    import time
    time.sleep(0.01)
    if radio.transmit_payload(ping_payload, ack_timeout, retries):
      # Add new channel to channels
      c.append(channel)
  devices[deviceID].channels = c

# Add a new device to the devices
def add_device(address, channel, payload):
  global devices, selection_limit
  # Search in devices list
  for device in devices:
    if address == device.address:
      # Update device's channels
      if channel not in device.channels:
        device.channels.append(channel)
      # Update device's payloads if it satifies the following requirements
      if device.model == None and len(payload) > 0 and payload not in device.payloads:
        device.payloads.append(payload)
        # Update device
        device = match_device(device.address, device.channels, device.payloads)
      break
  # Add a new device to the devices
  else:
    payloads = []
    if len(payload) > 0: payloads.append(payload)
    devices.append(Device(address, [channel], payloads))
  # Display the scanned the result
  update_scanner_msg()

def update_scanner_msg():
  global devices, selection_limit
  # Update selection limit
  selection_limit = len(devices)
  msg = []
  msg.append('----------------------------------SCAN DEVICES----------------------------------')
  msg.append('{0:<4}{1:<16}{2:<18}{3:<12}{4:<16}{5:<14}'.format(
    'No.', 'Address', 'Channels', 'Vender', 'Model', 'Status'))
  for i in range(len(devices)):
    msg.append('{0:<4}{1:<16}{2:<18}{3:<12}{4:<16}{5:<14}'.format(
      i+1, 
      ':'.join('{:02X}'.format(b) for b in devices[i].address),
      ','.join(str(c) for c in devices[i].channels), 
      devices[i].vender, 
      devices[i].model, 
      devices[i].status))
  # Refresh screen
  refresh_screen(msg)

def update_tasks_msg():
  global devices, deviceID, selection_limit
  device = devices[deviceID]
  msg = []
  msg.append('----------------------------------SELECT TASKS----------------------------------')
  msg.append('You selected: {0} ({1} {2})'.format(
    ':'.join('{:02X}'.format(b) for b in device.address), 
    device.vender, device.model))
  selection_limit = 2
  msg.append('{0:<6}{1}'.format('No.', 'Task'))
  msg.append('{0:<6}{1}'.format('1', 'Sniff and record packets.'))
  msg.append('{0:<6}{1}'.format('2', 'Launch attacks.'))
  # Refresh screen
  refresh_screen(msg)

def update_matcher_msg():
  global devices, deviceID, selection_limit
  device = devices[deviceID]
  msg = []
  msg.append('----------------------------------SELECT TASKS----------------------------------')
  msg.append('You selected: {0} ({1} {2})'.format(
    ':'.join('{:02X}'.format(b) for b in device.address), 
    device.vender, device.model))
  selection_limit = 0
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
  # Refresh screen
  refresh_screen(msg)

def update_sniffer_msg():
  global selection_limit, sniffer, devices, deviceID
  device = devices[deviceID]
  selection_limit = 0
  msg = []
  msg.append('----------------------------------SNIFF PACKETS---------------------------------')
  msg.append('{0:<10}{1} {2}'.format('Device: ', device.vender, device.model))
  msg.append('{0:<10}{1}'.format('Address: ', ':'.join('{:02X}'.format(b) for b in device.address)))
  msg.append('{0:<10}{1}'.format('Channels: ', ', '.join(str(c) for c in device.channels)))
  payload = array('B', [])
  # channel = None
  if len(sniffer.records) > 0:
    # channel = sniffer.records[0][0]
    payload = sniffer.records[0][1]
    del sniffer.records[0]
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

  # # Decode the payload
  # for m in eval(decoder)(payload):
  #   msg.append(m)
  # Refresh screen
  refresh_screen(msg)

# The following method also has to been optimised 
def update_attacker_msg():
  global selection_limit, attacker, devices, deviceID
  device = devices[deviceID]
  selection_limit = 0
  msg = []
  msg.append('----------------------------------LAUNCH ATTACK---------------------------------')
  msg.append('{0:<10}{1} {2}'.format('Device: ', device.vender, device.model))
  msg.append('{0:<10}{1}'.format('Address: ', ':'.join('{:02X}'.format(b) for b in device.address)))
  msg.append('{0:<10}{1}'.format('Channels: ', ', '.join(str(c) for c in device.channels)))
  msg.append('')
  msg.append('----------------------------------ATTACK HISTORY--------------------------------')
  msg.append('{0:<5}{1:<4}{2}'.format('No.', 'Ch.', 'Payload'))
  l = len(attacker.records)
  ls = l > 10 and l-10 or 0
  for i in range(ls, l):
    msg.append('{0:<5}{1:<4}{2}'.format(i+1, attacker.records[i][0], attacker.records[i][1]))
  # Refresh screen
  refresh_screen(msg)
