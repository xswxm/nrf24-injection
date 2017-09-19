#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

This script will received the payloads from the player and pre-analyze them, 
then assigned new tasks to the config.py to further process them.
'''

import sys
sys.path.append("..")

import time, threading
from utils import config
from array import array

def scan():
  # Refresh devices
  from player import Player
  if Player.records != []:
    # Acquire the address, channel, and payload from the first record
    address = Player.records[0][0]
    channel = Player.records[0][1]
    payload = Player.records[0][2]
    # Remove the first record
    del Player.records[0]
    # Add a new device or update the device
    config.add_device(address, channel, payload)
  else:
    config.update_scanner_msg()

def tasks():
  from player import Player
  device = config.devices[config.deviceID]
  # Enable a sniffer to capture packets to varify the device
  if device.model == None:
    # Refresh devices
    if Player.records != []:
      # Acquire the address, channel, and payload from the first record
      address = device.address
      channel = Player.records[0][0]
      payload = Player.records[0][1]
      # Remove the first record
      del Player.records[0]
      # Add a new device or update the device
      config.update_device(address, channel, payload)
    else:
      config.update_matcher_msg()
  # Enable tasks
  # There is a bug that this following code will be executed everytime and require to be fixed later
  else:
    from player import Player
    Player._flag.clear()
    config.update_tasks_msg()


def sniff():
  # Update sniffing results and Display
  config.update_sniffer_msg()


def attack():
  # Update attacking results and Display
  from player import Player
  time_now = time.time()
  time_span = time_now-Messager.time_flag
  # Compute ping_rate
  if Player.payloads == [] and time_span>=1:
    Messager.ping_rate = Player.total_ping-Messager.total_ping
    Messager.total_ping = Player.total_ping
    Messager.ping_rate = Messager.ping_rate/time_span
    Messager.time_flag = time_now
    config.update_attacker_msg(Messager.ping_rate)
  elif Player.payloads != []:
    config.update_attacker_msg(Messager.ping_rate)


class Messager(threading.Thread):
  # Constructor
  _flag = threading.Event()
  total_ping = 0
  ping_rate = 0
  time_flag = time.time()

  def __init__(self, task='scan'):
    threading.Thread.__init__(self)
    self._stopevent = threading.Event()
    Messager._flag.set()
    self.task = task
    self._pause = True

  # Main thread
  def run(self):
    while not self._stopevent.isSet():
      # Running code here
      if self.task == 'scan':
        scan()
      elif self.task == 'tasks':
        tasks()
      elif self.task == 'sniff':
        sniff()
      elif self.task == 'attack':
        attack()
      # Pause messager
      self._pause = True
      Messager._flag.clear()
      Messager._flag.wait()
      self._pause = False

  # Exit thread
  def join(self, timeout=None):
    while self.isAlive():
      Messager._flag.set()
      self._stopevent.set()
      threading.Thread.join(self, timeout)

  # Stop thread
  def pause(self):
    while not self._pause:
      time.sleep(0.05)
