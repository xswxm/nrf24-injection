#!/usr/bin/env python2
'''
  Reference: http://www.ipsum-generator.com
'''

import curses
from tools import Scanner, Sniffer, Attacker
from lib import common
common.init_args('./app.py')
common.parse_and_init()

# Standard startup. Probably don't need to change this
stdscr = curses.initscr()
curses.cbreak()
curses.noecho()
stdscr.keypad(1)

# Standard shutdown. Probably don't need to change this.
def exit_screen():
  curses.nocbreak()
  stdscr.keypad(0)
  curses.echo()
  curses.endwin()

def refresh_screen(msg):
  global commands
  notice = 'Commond (<m: main menu>, <b: back>, <q: quit>): '
  stdscr.clear()
  for i in range(len(msg)):
    # stdscr.addstr(i, 0, str(msg[i]))
    stdscr.addstr(i, 0, msg[i])
    # stdscr.move(0, 0)
  stdscr.addstr(i+1, 0, '')
  stdscr.addstr(i+2, 0, notice+commands)
  stdscr.refresh()

def scan():
  global scanner, selection, selection_limit, task
  if not scanner.isAlive():
    scanner = Scanner()
    scanner.start()
  else:
    scanner.resume()
  devices = scanner.get_devices()
  selection_limit = len(devices)
  msg = []
  msg.append('----------------------------------SCAN DEVICES----------------------------------')
  msg.append('{0:<6}{1:<18}{2:<10}{3:<16}{4:<16}{5:<14}'.format(
    'No.', 'Address', 'Channel', 'Vender', 'Model', 'Status'))
  for i in range(len(devices)):
    msg.append('{0:<6}{1:<18}{2:<10}{3:<16}{4:<16}{5:<14}'.format(
      i+1, ':'.join('{:02X}'.format(b) for b in devices[i].address),
      devices[i].channel, devices[i].vender, devices[i].model, devices[i].status))
    # msg.append('{0:<6}{1:<18}{2:<10}{3:<16}{4:<16}{5:<14}'.format(
    #   i+1, ':'.join('{:02X}'.format(b) for b in devices[i].address),
    #   devices[i].channel, devices[i].vender, devices[i].model, devices[i].status))
  if selection != None:
    if selection > 0:
      # scanner.join()
      scanner.pause()
      global device, deviceID
      deviceID = selection-1
      device = devices[deviceID]
      task = 'tasks'
    selection = None
  return msg

def tasks():
  global selection, selection_limit, task, device
  msg = []
  msg.append('----------------------------------SELECT TASKS----------------------------------')
  msg.append('You selected: {0} ({1} {2})'.format(
    ':'.join('{:02X}'.format(b) for b in device.address), 
    device.vender, device.model))
  selection_limit = 0
  if device.model != None:
    # selection enabled
    selection_limit = 2
  else:
    msg.append('')
    msg.append('* Tasks is not avaliable right now because the device has not been located yet.')
    msg.append('* It may take minites to locate the device, please wait...')
    msg.append('')
    global matcher
    if not matcher.isAlive():
      matcher = Sniffer(device.address)
      matcher.start()
    else:
      matcher.resume(device.address)
    payload = matcher.payload
    if payload != None and len(payload) > 0:
      from devices.device import match_device
      payloads = []
      payloads = device.payloads
      l = len(payloads)
      #### Test Code For Monitoring payloads

      msg.append('Payload: {0}'.format(':'.join('{:02X}'.format(b) for b in payload)))
      flag = 0
      for p in payloads:
        msg.append('{0}'.format(':'.join('{:02X}'.format(b) for b in p)))
        flag += 1
        if flag > 10: break
      msg.append('Number of total payloads: '+ str(l))

      ####
      if l == 0 or (l > 0 and device.payloads[-1] != payload):
        payloads.append(payload)
        d = None
        d = match_device(device.address, device.channel, payloads)
        device = d
        if d.model != None:
          # Renew devices list
          global scanner, deviceID
          scanner.devices[deviceID] = d
          # Pause matcher
          matcher.pause()
  msg.append('{0:<6}{1}'.format('No.', 'Task'))
  msg.append('{0:<6}{1}'.format('1', 'Sniff and record packets.'))
  msg.append('{0:<6}{1}'.format('2', 'Launch attacks.'))
  if selection != None:
    if selection == 1:
      task = 'sniff'
    elif selection == 2:
      task = 'attack'
    else:
      task = 'scan'
    selection = None
  return msg

def sniff():
  global sniffer, selection, selection_limit, task, device
  selection_limit = 0
  if not sniffer.isAlive():
    sniffer = Sniffer(device.address, device.moduler)
    sniffer.start()
  else:
    sniffer.resume(device.address, device.moduler)
  msg = []
  msg.append('----------------------------------SNIFF PACKETS---------------------------------')
  msg.append('{0:<10}{1} {2}'.format('Device: ', device.vender, device.model))
  msg.append('{0:<10}{1}'.format('Address: ', ':'.join('{:02X}'.format(b) for b in device.address)))
  for m in sniffer.get_msg():
    msg.append(m)
  if selection != None:
    sniffer.pause()
    if selection == 0:
      task = 'scan'
    else:
      task = 'tasks'
    selection = None
  return msg

def attack():
  global attacker, selection, selection_limit, task, device
  selection_limit = 0
  if not attacker.isAlive():
    attacker = Attacker(device)
    attacker.start()
  else:
    attacker.resume(device)
  msg = []
  msg.append('----------------------------------LAUNCH ATTACK---------------------------------')
  msg.append('{0:<10}{1} {2}'.format('Device: ', device.vender, device.model))
  msg.append('{0:<10}{1}'.format('Address: ', ':'.join('{:02X}'.format(b) for b in device.address)))
  msg.append('')
  for m in attacker.get_msg():
    msg.append(m)
  if selection != None:
    attacker.pause()
    if selection == 0:
      task = 'scan'
    else:
      task = 'tasks'
    selection = None
  return msg

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
        msg = scan()
      elif task == 'tasks':
        msg = tasks()
      elif task == 'sniff':
        msg = sniff()
      elif task == 'attack':
        msg = attack()
      refresh_screen(msg)
  def join(self, timeout = None):
    while self.isAlive():
      self._stopevent.set()
      threading.Thread.join(self, timeout)


# chars = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 
#               'H', 'I', 'J', 'K', 'L', 'M', 'N', 
#               'O', 'P', 'Q', 'R', 'S', 'T', 
#               'U', 'V', 'W', 'X', 'Y', 'Z',
#               'a', 'b', 'c', 'd', 'e', 'f', 'g', 
#               'h', 'i', 'j', 'k', 'l', 'm', 'n', 
#               'o', 'p', 'q', 'r', 's', 't', 
#               'u', 'v', 'w', 'x', 'y', 'z',
#               '+', '-', ',', ' ',
#               '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
# chars_spec = [curses.KEY_BACKSPACE, curses.KEY_ENTER, 10, 13]

def check_selection(c):
  global selection
  result = None
  if c == ord('q'):
    global mainThread, scanner, matcher, sniffer, attacker
    # Stop main thread
    mainThread.join()
    attacker.join()
    sniffer.join()
    matcher.join()
    scanner.join()
    exit_screen()
    exit(0)
  if c == ord('b'):
    result = -1
  elif c == ord('m'):
    result = 0
  elif c >= 49 and c <= 57:
    result = c-48
  elif c >= 97 and c <= 122:
    result = c-87
  if result > selection_limit:
    result = None
  selection = result

if __name__ == "__main__":
  task = 'scan'
  commands = ''
  scanner = Scanner()
  sniffer = Sniffer()
  matcher = Sniffer()
  attacker = Attacker()
  device = None
  deviceID = None
  selection = None
  selection_limit = 0
  mainThread = myThread()
  mainThread.start()
  while True:
    c = stdscr.getch()
    try:
      if c == curses.KEY_BACKSPACE:
        commands = commands[:-1]
      elif c == curses.KEY_ENTER  or c == 10 or c == 13:
        if len(commands) > 0:
          c = ord(commands[-1])
          check_selection(c)
          if attacker.isAlive() and attacker._flag.isSet():
            attacker.set_commands(commands)
        commands = ''
      else:
        commands += chr(c)
    except Exception as e:
      commands = str(e)
    # if chr(c) in chars or c in chars_spec:
    #   if c == curses.KEY_BACKSPACE:
    #     commands = commands[:-1]
    #   elif c == curses.KEY_ENTER  or c == 10 or c == 13:
    #     if len(commands) > 0:
    #       c = ord(commands[-1])
    #       check_selection(c)
    #       if attacker.isAlive() and attacker._flag.isSet():
    #         attacker.set_commands(commands)
    #     commands = ''
    #   else:
    #     commands += chr(c)


  
