#!/usr/bin/env python2
'''
  Reference: http://www.ipsum-generator.com
'''

from tools import Scanner, Sniffer, Attacker
from lib import common
from lib.common import *
common.init_args('./app.py')
common.parse_and_init()
common.init_screen()
common.init_commands()

def scan():
  global selection, task
  # Update scanner's status
  if not common.scanner.isAlive():
    common.scanner = Scanner()
    common.scanner.start()
  else:
    common.scanner.resume()
  # Refresh devices
  if common.scanner.records != []:
    # Acquire the address, channel, and payload from the first record
    address = common.scanner.records[0][0]
    channel = common.scanner.records[0][1]
    payload = common.scanner.records[0][2]
    # Remove the first record
    del common.scanner.records[0]
    # Add a new device or update the device
    common.add_device(address, channel, payload)
  else:
    common.update_scanner_msg()
  # Update selection and task
  if selection != None:
    if selection > 0:
      # scanner.join()
      common.scanner.pause()
      common.deviceID = selection-1
      task = 'tasks'
    selection = None

def tasks():
  global selection, task
  device = common.devices[common.deviceID]
  # Enable a sniffer to capture packets to varify the device
  if device.model == None:
    # Enable matcher
    if not common.matcher.isAlive():
      common.matcher = Sniffer(device.address)
      common.matcher.start()
    else:
      common.matcher.resume(device.address)
    # Refresh devices
    if common.matcher.records != []:
      # Acquire the address, channel, and payload from the first record
      address = device.address
      channel = common.matcher.records[0][0]
      payload = common.matcher.records[0][1]
      # Remove the first record
      del common.matcher.records[0]
      # Add a new device or update the device
      common.update_device(address, channel, payload)
    else:
      common.update_matcher_msg()
  # Enable tasks
  # There is a bug that this following code will be executed everytime and require to be fixed later
  else:
    common.update_tasks_msg()
  # Update selection
  if selection != None:
    if selection == 1:
      task = 'sniff'
    elif selection == 2:
      task = 'attack'
    else:
      task = 'scan'
    selection = None

def sniff():
  global selection, task
  device = common.devices[common.deviceID]
  if not common.sniffer.isAlive():
    common.sniffer = Sniffer(device.address)
    common.sniffer.start()
  else:
    common.sniffer.resume(device.address)
  # Update sniffing results and Display
  common.update_sniffer_msg()
  # Update selection
  if selection != None:
    common.sniffer.pause()
    if selection == 0:
      task = 'scan'
    else:
      task = 'tasks'
    selection = None

def attack():
  global selection, task
  device = common.devices[common.deviceID]
  if not common.attacker.isAlive():
    common.attacker = Attacker(device.address)
    common.attacker.start()
  else:
    common.attacker.resume(device.address)
  # Update attacking results and Display
  common.update_attacker_msg()
  if selection != None:
    common.attacker.pause()
    if selection == 0:
      task = 'scan'
    else:
      task = 'tasks'
    selection = None

import threading
class myThread(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    self._flag = threading.Event()
    self._flag.set()
  def run(self):
    while not self._stopevent.isSet():
      global task
      if task == 'scan':
        scan()
      elif task == 'tasks':
        tasks()
      elif task == 'sniff':
        sniff()
      elif task == 'attack':
        attack()
      # self._stopevent.wait(0.02)
  def join(self, timeout = None):
    while self.isAlive():
      self._stopevent.set()
      threading.Thread.join(self, timeout)



def check_selection(c):
  global selection
  result = None
  if c == ord('q'):
    common.save_commonds()
    global mainThread
    # Stop main thread
    mainThread.join()
    common.attacker.join()
    common.sniffer.join()
    common.matcher.join()
    common.scanner.join()
    common.exit_screen()
    exit(0)
  if c == ord('b'):
    result = -1
  elif c == ord('m'):
    result = 0
  elif c >= 49 and c <= 57:
    result = c-48
  elif c >= 97 and c <= 122:
    result = c-87
  if result > common.selection_limit:
    result = None
  selection = result
  return selection

import curses
if __name__ == "__main__":
  task = 'scan'         # Task
  selection = None      # Selection
  common.scanner = Scanner()
  common.sniffer = Sniffer()
  common.matcher = Sniffer()
  common.attacker = Attacker()
  mainThread = myThread()
  mainThread.start()
  while True:
    c = common.stdscr.getch()
    commandsID = commandsID
    command = common.command
    commands = common.commands
    stdscrID = common.stdscrID
    try:
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
        command = command[:stdscrID-1]+command[stdscrID:]
        commands[-1] = common.command
        if stdscrID > 0: stdscrID -= 1
      # Pressed ENTER
      elif (c == curses.KEY_ENTER  or c == 10 or c == 13) and len(command) > 0:
        c = ord(command[-1])
        if check_selection(c) == None:
          if common.attacker.isAlive() and common.attacker._flag.isSet():
            common.attacker.set_command(command)
            # Update commands if it is new
            if len(commands) < 2 or command != commands[-2]:
              # Update the last command in commands
              commands[-1] = common.command
              # Add an empty command to the commands list
              commands.append('')
        # Update commandsID
        commandsID = len(commands)-1
        # Renew command
        command = ''
        stdscrID = 0
      else:
        command = command[:stdscrID]+chr(c)+command[stdscrID:]
        commands[-1] = common.command
        stdscrID += 1
    except Exception as e:
      pass
    commandsID = commandsID
    common.command = command
    common.commands = commands
    common.stdscrID = stdscrID
