#!/usr/bin/python
# -*- coding: UTF-8 -*-
# 
'''
Github: xswxm
Blog: xswxm.com

The following packets are captured from Logitech m215 & m545
  Buttons
  [ ]release:         00:C2:00:00:00:00:00:00:00:3E + 00:4F:00:00:6E:00:00:00:00:43
  [L]left:            00:C2:01:00:00:00:00:00:00:3D + 00:4F:00:00:6E:00:00:00:00:43
  [R]right:           00:C2:02:00:00:00:00:00:00:3C + 00:4F:00:00:6E:00:00:00:00:43
  [M]mid:             00:C2:04:00:00:00:00:00:00:3A + 00:4F:00:00:6E:00:00:00:00:43
  [P]prev(ctrl+pgup): 00:C2:08:00:00:00:00:00:00:36 + 00:4F:00:00:6E:00:00:00:00:43
  [N]next(ctrl+pgdn): 00:C2:10:00:00:00:00:00:00:2E + 00:4F:00:00:6E:00:00:00:00:43
  [U]scroll up:       00:C2:00:00:00:00:00:01:00:3D + 00:4F:00:00:6E:00:00:00:00:43
  [D]scroll down:     00:C2:00:00:00:00:00:FF:00:3F + 00:4F:00:00:6E:00:00:00:00:43
  Other
  [ ]sleep:           00:4F:00:04:B0:00:00:00:00:FD
  [ ]weak up:         00:4F:00:00:6E:00:00:00:00:43
  [ ]sync(sleep):     00:40:04:B0:0C
  [ ]sync(wake):      00:40:00:6E:52
  [ ]firmware info:   00:51:09:00:0B:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:9B
  Movement
  left:   00:C2:00:00:FF:0F:00:00:00:30
  right:  00:C2:00:00:01:00:00:00:00:3D
  up:     00:C2:00:00:00:F0:FF:00:00:4F
  down:   00:C2:00:00:00:10:00:00:00:2E

Packet explaination
  Packet: AB:CD:EF:GH:IJ:KL:MO:PQ:RS:TU
  ABCD:   prefix numbers. Usually, they are 00:C2, whe the device is not un-pluged, AB could be larger then 0
  EF:     stand for different buttons
  PQ:     stand for srollings
  IJKLMO: stand for relative mouse movement
  TU:     checksum
  GH:     unknown, usually are 00
  RS:     unknown, usually are 00
'''

result_old = [None]*9

def decode(payload):
  global result_old
  # payload_def = [0, 0x4F, 0, 0, 0x6E, 0, 0, 0, 0, 0x43]
  # payload_slp = [0, 0x4F, 0, 0x04, 0xB0, 0, 0, 0, 0, 0xFD]
  msg = []
  msg.append('{0:<16}{1:<8}{2:<8}{3:<8}{4:<8}{5:<8}{6:<8}{7:<8}{8:<8}'.
    format('Move', 'LEFT', 'RIGHT', 'MIDDLE', 'SCL_UP', 'SCL_DN', 'PREV', 'NEXT', 'SYNC'))
  result = [None]*9
  if len(payload) == 0:
    result = result_old
  elif len(payload) != 10:
    if len(payload) == 22:
      result[0] = 'FW_INFO'
    elif len(payload) == 5:
      result = result_old
      result[0] = (0, 0)
      result[4] = None
      result[5] = None
      result[8] = 'Yes'
    else:
      result[0] = 'Payload cannot be decoded.'
      # result = result_old
  elif payload[1] == 0x4F:
    result = result_old
  else:
    # Buttons
    if payload[2]/0x10 >= 1:  # Next Click
      payload[2] = payload[2]%0x10
      result[7] = 'Yes'
    if payload[2]/0x8 >= 1:  # Previous Click
      payload[2] = payload[2]%8
      result[6] = 'Yes'
    if payload[2]/0x4 >= 1:  # Mid Click
      payload[2] = payload[2]%4
      result[3] = 'Yes'
    if payload[2]/0x02 == 1:  # Right Click
      payload[2] = payload[2]%2
      result[2] = 'Yes'
    if payload[2]/0x01 == 1:  # Left Click
      result[1] = 'Yes'
    if payload[7] > 0x00 and payload[7] < 0x80:
      result[4] = 'Yes'
    elif payload[7] > 0x80:
      result[5] = 'Yes'
    # Movement
    # Calculate relative movement
    def calc_move(num):
      if num >= 2048:
          num = num-4096
      return num
    x = calc_move((payload[5]%0x10)*0x100+payload[4])
    y = calc_move(payload[6]*0x10 + payload[5]/0x10)
    result[0] = (x, y)
  msg.append('{0:<16}{1:<8}{2:<8}{3:<8}{4:<8}{5:<8}{6:<8}{7:<8}{8:<8}'.
    format(result[0], 
      result[1], 
      result[2], 
      result[3], 
      result[4], 
      result[5], 
      result[6], 
      result[7], 
      result[8]))
  result_old = result
  return msg

from array import array
def encode(cmd, device):
  def checksum(payload):
    cks = 0
    for i in range(9): cks += payload[i]
    return ((cks%0x100^0xFF)+0x01)%0x100
  def move(c):
    def parse_xy(x, y):
      def fix_num(num):
        num %= 0x1000
        if num == 0x800: num = 0
        return num
      x = fix_num(x)
      y = fix_num(y)
      payload = array('B', [prefix[0], prefix[1], 0, 0, 0, 0, 0, 0, 0, 0])
      payload[4] = x%0x100
      payload[5] = (y%0x10)*0x10+x/0x100
      payload[6] = y/0x10
      return payload
    x = int(c[0])
    y = int(c[1])
    return parse_xy(x, y)
  def buttons(s):
    payload = array('B', [prefix[0], prefix[1], 0, 0, 0, 0, 0, 0, 0, 0])
    if 'L' in s:
      payload[2] += 0x01
    if 'R' in s:
      payload[2] += 0x02
    if 'M' in s:
      payload[2] += 0x04
    if 'P' in s:
      payload[2] += 0x08
    if 'N' in s:
      payload[2] += 0x10
    if 'U' in s:
      payload[7] = 0x01
    elif 'D' in s:
      payload[7] = 0xFF
    return payload

  prefix = device.prefix
  payload_tag = device.payload_tag
  payloads = []
  # Sleep commond (in milliseconds, range[0, 65535])
  if 'SLP' in cmd:
    t = int(cmd[4:-1])
    payload = array('B', [0, 0])
    payload[1] = t/0x100
    payload[0] = t%0x100
    payloads.append(array('B', payload))
  elif 'RLS' in cmd:
    pass
  # Mouse movements and clicks
  elif 'MOV' in cmd:
    cs = cmd[4:-1].split(',')
    payload = array('B', [])
    if len(cs) == 1:
      payload = buttons(cs[0])
    elif len(cs) == 2:
      payload = move(cs)
    elif len(cs) == 3:
      payload = buttons(cs[2])
      payload[4:7] = move(cs[:2])[4:7]
    if len(cs) <= 3:
      payload[-1] = checksum(payload)
      payloads.append(payload)
      payloads.append(payload_tag)
  return payloads