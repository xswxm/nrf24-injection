#!/usr/bin/env python2
'''
Author: xswxm
Blog: xswxm.com

Analyze payloads 1,2,3,4,5,6,7,8,9,0 sent from Crazyradio PA

'''

import time
import sys, curses


# Parse command line arguments
import argparse
parser = argparse.ArgumentParser(description='I am an analyzer!')
parser.add_argument('-p', '--period', type=int, 
    help='Time for monitoring the injected keystrokes.', default=30)
args = parser.parse_args()

stdscr = None

def display(count, min_length, max_length):
  msg = 'Total received: {0:>4}  Min: {1:>4}  Max: {2:>4}'.format(count, min_length, max_length)
  sys.stdout.write('\r'+msg)
  sys.stdout.flush()

# Initialize
stdscr = curses.initscr()
curses.cbreak()
curses.noecho()
stdscr.keypad(1)

period = args.period

c_old = stdscr.getch()
count = 1
length = 1
min_length = 0
max_length = 0
# Once it received its first keystroke, start counting time
start_time = time.time()
display(count, min_length, max_length)

while time.time() - start_time < period:
  # Get a keystroke
  c_new = stdscr.getch()
  diff = c_new - c_old
  if diff == 1 or diff == -9:
    count += 1
    length += 1
  # Missing keystrokes
  elif diff != 0:
    # Update minimum length
    if min_length == 0 or min_length > length:
      min_length = length
    # Update maximum length
    if max_length == 0 or max_length < length:
      max_length = length
    count += 1
    length = 1
  # Update c_old
  c_old = c_new
  display(count, min_length, max_length)
# Update minimum length
if min_length == 0 or min_length > length:
  min_length = length
# Update maximum length
if max_length == 0 or max_length < length:
  max_length = length
display(count, min_length, max_length)

curses.nocbreak()
stdscr.keypad(0)
curses.echo()
curses.endwin()

print 'Totoal number of received payloads:   {0}'.format(count)
print 'Minimum continous length of payloads: {0}'.format(min_length)
print 'Maximum continous length of payloads: {0}'.format(max_length)