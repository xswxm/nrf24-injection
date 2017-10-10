#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

Main entrance for our nrf24-injection scripts.

This script can do the following tasks:
1. Search and analyze 2.4Ghz mice/keyboards;
2. Sniff payloads;
3. Launch attack, including keystroke injections.
'''

from lib import common
common.init_args('./app.py')
common.parser.add_argument('-e', '--channel_time', type=int, help='Time in milliseconds for keeping scanning on the channel where a new device was discovered', default=8)
common.parser.add_argument('-s', '--strict_match', action='store_true', help='Verify device with more strict rules', default=False)
common.parse_and_init()

import curses
from array import array
from utils.player import Player
from utils.messager import Messager
from utils import display
from utils import config

display.init()
task = 'scan'
selection = None      # Selection
config.channel_time = common.args.channel_time
config.strict_match = common.args.strict_match

commands = None
commandsID = None


def init_commands():
  global commands, commandsID
  config.command = ''
  commands = []
  file = open('history', 'r') 
  for line in file:
    commands.append(line.replace('\n', ''))
  commands.append(config.command)
  commandsID = len(commands)-1
  file.close()

  
def save_commonds():
  global commands
  file = open('history', 'w')
  for command in commands[:-1]:
    file.write(command+'\n')
  # file.writelines(commands)
  file.close()

def check_command(c):
  global commands, commandsID
  command = config.command
  stdscrID = display.stdscrID
  if c == curses.KEY_UP:
    if commandsID > 0:
      commandsID -= 1
      command = commands[commandsID]
      stdscrID = len(command)
    else:
      stdscrID = 0
  elif c == curses.KEY_DOWN:
    if commandsID < len(commands)-1:
      commandsID += 1
      command = commands[commandsID]
    stdscrID = len(command)
  elif c == curses.KEY_LEFT:
    if stdscrID > 0: stdscrID -= 1
  elif c == curses.KEY_RIGHT:
    if stdscrID < len(command): stdscrID += 1
  # Pressed BACKSPACE
  elif c == curses.KEY_BACKSPACE:
    if stdscrID > 0:
      command = command[:stdscrID-1]+command[stdscrID:]
      commands[-1] = command
      stdscrID -= 1
  # Pressed ENTER
  elif c == curses.KEY_ENTER or c == 10 or c == 13:
    if len(command) > 0:
      if update_selection(command) == None:
        if player.mode == 2:
          player.assign(command)
          # display.refresh()
          # Update commands if it is new
          if len(commands) < 2 or command != commands[-2]:
            # Update the last command in commands
            commands[-1] = command
            # Add an empty command to the commands list
            commands.append('')
      # Switch tasks
      else:
        update_tasks()
      # Update commandsID
      commandsID = len(commands)-1
      # Renew command
      command = ''
      # Update the last command in commands
      commands[-1] = ''
      # Reset cureses
      stdscrID = 0
  elif 0 <= c < 256:
    command = command[:stdscrID]+chr(c)+command[stdscrID:]
    commands[-1] = command
    stdscrID += 1
  config.command = command
  display.stdscrID = stdscrID

def quit_app():
  save_commonds()
  # Join all threads
  global player, messager
  # player.pause()
  # messager.pause()
  player.join()
  messager.join()
  # Clear display
  display.end()
  # Exit
  exit(0)

def update_selection(command):
  global selection
  selection = None
  # c = ord(command[-1])
  # Quit application
  if command[-1] == 'q':
    quit_app()
  # Back
  if command[-1] == 'b':
    selection = -1
  # Main menu
  elif command[-1] == 'm':
    selection = 0
  # Other selections
  else:
    try:
      # Parse the commond into type int
      selection = int(command)
      # Remove unvaild selections based on the menu
      if selection-1 not in config.menu:
        selection = None
    except:
      selection = None
  return selection


def update_tasks():
  global selection
  if selection == None:
    return
  global task, player, messager
  messager.pause()
  if task == 'scan':
    if selection > 0:
      # Update devices ang enter sniffing mode
      config.deviceID = selection-1
      player.setup(1, config.devices[config.deviceID].address)
      task = messager.task = 'tasks'

  elif task == 'tasks':
    if selection == 1:
      player.setup(1, config.devices[config.deviceID].address)
      task = messager.task = 'sniff'
    elif selection == 2:
      player.setup(2, config.devices[config.deviceID].address)
      task = messager.task = 'attack'
    else:
      player.setup(0, array('B', []))
      task = messager.task = 'scan'

  elif task == 'sniff' or task == 'attack':
    if selection == 0:
      player.setup(0, array('B', []))
      task = messager.task = 'scan'
    else:
      player.setup(1, config.devices[config.deviceID].address)
      task = messager.task = 'tasks'

  selection = None


def test_devices():
  pass
  from utils.device import Device, AmazonBasics, LogitechMouse
  from array import array
  device = Device(array('B', [0x29, 0xA7, 0x95, 0xCC, 0x09]), [5], [array('B',[0x01, 0x23, 0x45])], 'Test')
  device.status = 'Test'
  config.devices.append(device)
  device = AmazonBasics(array('B', [0x61, 0x8E, 0x9C, 0xCD, 0x03]), [3], array('B', [0x3C, 0x2A]))
  # device = Device(array('B', [0x61, 0x8E, 0x9C, 0xCD, 0x03]), [3], [], 'Test')
  device.status = 'Test'
  config.devices.append(device)
  device = Device(array('B', [0x98, 0xA3, 0x24, 0x69, 0x07]), [62], [], 'Test')
  device.status = 'Test'
  config.devices.append(device)
  device = LogitechMouse(array('B', [0x42, 0x66, 0x0A, 0xB1, 0x04]), [62], array('B', [0x00, 0xC2]), array('B', [0, 0x4F, 0, 0, 0x6E, 0, 0, 0, 0, 0x43]), 'Unencrypted')
  device.status = 'Test'
  config.devices.append(device)

  # for i in range(10):
  #   device = Device(array('B', [0x98, 0xA3, 0x24, 0x69, i]), [i], [], 'Test')
  #   device.status = 'Test'
  #   config.devices.append(device)


if __name__ == "__main__":
  # test_devices()
  init_commands()
  messager = Messager()
  messager.start()
  player = Player()
  player.start()
  try:
    while True:
      c = display.stdscr.getch()
      check_command(c)
      display.refresh()
  except KeyboardInterrupt:
    quit_app()