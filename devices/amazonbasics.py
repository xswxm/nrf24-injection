#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Github: xswxm
Blog: xswxm.com

The following packets are captured from AmazonBasics
  Buttons
  [X]release:       31:00:00:30:3C:2A 
  [L]left:          01:01:00:30:3C:2A
  [R]right:         01:02:00:30:3C:2A
  [M]mid:           31:04:00:30:3C:2A
  [U]scroll up:     01:00:01:30:3C:2A
  [D]scroll down:   31:00:FF:30:3C:2A
  [ ]sync:          03:3C:2A
  Movement
  left:   02:FF:0F:00:3C:2A
  right:  32:01:00:00:3C:2A
  up:     32:00:F0:FF:3C:2A
  down:   32:00:10:00:3C:2A

Packet explaination
  Packet: AB:CD:EF:GH:IJ:KL
  A:      No meaning, usually is 0, 1, 2, 3
  B:      1 stands for buttons, 2 stands for mouse movement
  CD:     when B=1, they stand for different buttons
  GH:     when B=1, they stand for srollings
  CDEFGH: when B=2, they stand for relative mouse movement
  IJKL:   suffix numbers

Example commonds
  L                     # Press left button
  L+                    # Press left button, then release the button
  LR                    # Press left and right buttons together
  LR+R                  # Press left and right buttons together,
                        #   then release left button and keep right button pressed
  -2047,-2047           # Move left by 2047 and move top by 2047
  2047,2047             # Move right by 2047 and move bottom by 2047
  1,1,LMR               # Move right by 1 and move bottom by 1, 
                        #   and press left, middle and right buttons
  1,1+LMR               # Move right by 1 and move bottom by 1, 
                        #   then press left, middle and right buttons

'''

result_old = [None]*7

def decode(payload):
  global result_old
  msg = []
  msg.append('{0:<16}{1:<8}{2:<8}{3:<8}{4:<8}{5:<8}{6:<8}'.
    format('Move', 'LEFT', 'RIGHT', 'MIDDLE', 'SCL_UP', 'SCL_DN', 'SYNC'))
  result = [None]*7
  if payload == None or len(payload) == 0:
    result = result_old
  elif len(payload) != 6:
    if len(payload) == 3:
      result = result_old
      result[0] = (0, 0)
      result[4] = None
      result[5] = None
      result[6] = 'Yes'
    else:
      result[0] = 'No Matching decoder found.'
  else:
    if payload[0]%0x10 == 1:  # Buttons
      if payload[1]/0x4 >= 1:  # Mid Click
        payload[1] = payload[1]%4
        result[3] = 'Yes'
      if payload[1]/0x02 == 1:  # Right Click
        payload[1] = payload[1]%2
        result[2] = 'Yes'
      if payload[1]/0x01 == 1:  # Left Click
        result[1] = 'Yes'
      if payload[2] > 0x00 and payload[2] < 0x80:
        result[4] = 'Yes'
      elif payload[2] > 0x80:
        result[5] = 'Yes'
    elif payload[0]%0x10 == 2: # Movement
      # Calculate relative movement
      def calc_move(num):
        if num >= 2048:
            num = num-4096
        return num
      x = calc_move((payload[2]%0x10)*0x100+payload[1])
      y = calc_move(payload[3]*0x10 + payload[2]/0x10)
      result[0] = (x, y)
  msg.append('{0:<16}{1:<8}{2:<8}{3:<8}{4:<8}{5:<8}{6:<8}'.
    format(result[0], 
      result[1], 
      result[2], 
      result[3], 
      result[4], 
      result[5], 
      result[6]))
  result_old = msg
  return msg

from array import array
def encode(commands, device):
  def move(c):
    x = int(c[0])
    y = int(c[1])
    def fix_num(num):
      num %= 4096
      if num == 2048: num = 0x00
      return num
    def parse_xy(x, y):
      x = fix_num(x)
      y = fix_num(y)
      payload = array('B', [0x02, 0, 0, 0, suffix[0], suffix[1]])
      payload[1] = x%0x100
      payload[2] = (y%0x10)*0x10+x/0x100
      payload[3] = y/0x10
      return payload
    return parse_xy(x, y)
  def buttons(s):
    payload = array('B', [0x01, 0x00, 0x00, 0x30, suffix[0], suffix[1]])
    if 'L' in s:
      payload[1] += 0x01
    if 'R' in s:
      payload[1] += 0x02
    if 'M' in s:
      payload[1] += 0x04
    if 'U' in s:
      payload[2] = 0x01
    elif 'D' in s:
      payload[2] = 0xFF
    return payload

  suffix = device.suffix
  payloads = []
  # if commond == None or commond == '':
  #   payloads.append([0x01, 0x00, 0x00, 0x30, suffix[0], suffix[1]])
  #   payloads.append([0x03, suffix[0], suffix[1]])
  #   return payloads
  # Parse commands
  commands = commands.replace(' ', '').replace('(', '').replace(')', '').split('+')
  for command in commands:
    c = command.split(',')
    # payload = array('B', [])
    if len(c) == 1:
        payloads.append(buttons(c[0]))
    elif len(c) == 2:
        payloads.append(move(c))
    elif len(c) == 3:
      payloads.append(move(c[:2]))
      payloads.append(buttons(c[2]))
  return payloads