#!/usr/bin/env python2
'''

'''

import sys
sys.path.append("..")


import time, threading
from lib import common
import config
import curses

stdscr = None
stdscrID = 0

# Standard startup. Probably don't need to change this
def init():
  global stdscr
  stdscr = curses.initscr()
  curses.cbreak()
  curses.noecho()
  stdscr.keypad(1)

# Standard shutdown. Probably don't need to change this.
def end():
  global stdscr
  curses.nocbreak()
  stdscr.keypad(0)
  curses.echo()
  curses.endwin()

msg_old = ''
_lock = threading.RLock()
def refresh(msg=None):
  global msg_old, _lock
  global stdscr, stdscrID
  with _lock:
    if msg == None:
      msg = msg_old
    else:
      msg_old = msg
    notice = 'Command (<m: main>, <b: back>, <q: quit>): '
    try:
      stdscr.clear()
      for i in range(len(msg)):
        # stdscr.addstr(i, 0, str(msg[i]))
        stdscr.addstr(i, 0, msg[i])
        # stdscr.move(0, 0)
      stdscr.addstr(i+1, 0, '')
      stdscr.addstr(i+2, 0, notice+config.command)
      x = len(msg)+1
      y = 0
      for i in range(len(notice)+stdscrID):
        try:
          y += 1
          stdscr.move(x,y)
        except:
          x += 1
          y = 0
      stdscr.move(x,y)
    except Exception as e:
      stdscr.clear()
      stdscr.addstr(0, 0, 'There is no enough space to display , please change the size of your console.')
    
    stdscr.refresh()
