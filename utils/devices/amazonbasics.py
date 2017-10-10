#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Github: xswxm
Blog: xswxm.com

The following packets are captured from AmazonBasics MG-0975
  Buttons
  [X]release:       31:00:00:30:3C:2A 
  [L]left:          01:01:00:30:3C:2A
  [R]right:         01:02:00:30:3C:2A
  [M]mid:           31:04:00:30:3C:2A
  [U]scroll up:     01:00:01:30:3C:2A
  [D]scroll down:   31:00:FF:30:3C:2A
  [ ]sync:          03:3C:2A
  Movement
  left:             02:FF:0F:00:3C:2A
  right:            32:01:00:00:3C:2A
  up:               32:00:F0:FF:3C:2A
  down:             32:00:10:00:3C:2A

Channels(Gengral):  3, 8, 20, 62, 74, 79
Other channels:     21, 48, 52

Packet explaination
  Packet: AB:CD:EF:GH:IJ:KL
  A:      No meaning, usually is 0, 1, 2, 3
  B:      1 stands for buttons, 2 stands for mouse movement
  CD:     when B=1, they stand for different buttons
  GH:     when B=1, they stand for srollings
  CDEFGH: when B=2, they stand for relative mouse movement
  IJKL:   suffix numbers
'''

result_old = [None]*7

def decode(payload):
  global result_old
  msg = []
  msg.append('{0:<16}{1:<8}{2:<8}{3:<8}{4:<8}{5:<8}{6:<8}'.
    format('Move', 'LEFT', 'RIGHT', 'MIDDLE', 'SCL_UP', 'SCL_DN', 'SYNC'))
  result = [None]*7
  if len(payload) == 0:
    import copy
    result = result_old
    result = [None]*7
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
  result_old = result
  return msg

from array import array
def encode(cmd, device):
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
  # Sleep commond (in milliseconds, range[0, 65535])
  if 'SLP' in cmd:
    t = int(cmd[4:-1])
    payload = array('B', [0, 0])
    payload[1] = t/0x100
    payload[0] = t%0x100
    payloads.append(array('B', payload))
  elif 'PING' in cmd:
    t = int(cmd[5:-1])
    payload = array('B', [t%0x100])
    payloads.append(array('B', payload))
  elif 'RLS' in cmd:
    payloads.append(array('B', [0x0F]*19+[0]*5))
    payloads.append(array('B', [0x0F]*24))
  # Mouse movements and clicks
  elif 'MOV' in cmd:
    cs = cmd[4:-1].split(',')
    # payload = array('B', [])
    if len(cs) == 1:
      payloads.append(buttons(cs[0]))
    elif len(cs) == 2:
      payloads.append(move(cs))
    elif len(cs) == 3:
      payloads.append(move(cs[:2]))
      payloads.append(buttons(cs[2]))
  # Key combination
  else:
    global key
    cmds = len(cmd) == 1 and [cmd] or cmd.split('+')
    payload_prefix = array('B', [0x0F]*19)
    payload = array('B', [0]*5)
    for cmd in cmds:
      p = key[cmd]
      if p[1] != 0: payload[1] += p[1]
      # Can accept two original keys at most
      if p[3] != 0:
        if payload[3] == 0:
          payload[3] = p[3]
        elif payload[4] == 0:
          payload[4] = p[3]
    payloads.append(payload_prefix+payload)
    payloads.append(payload_prefix+array('B', [0]*5))
  return payloads

  # cmd = cmd.replace(' ', '').replace('(', '').replace(')', '').split('+')
  # for command in cmd:
  #   c = command.split(',')
  #   # payload = array('B', [])
  #   if len(c) == 1:
  #       payloads.append(buttons(c[0]))
  #   elif len(c) == 2:
  #       payloads.append(move(c))
  #   elif len(c) == 3:
  #     payloads.append(move(c[:2]))
  #     payloads.append(buttons(c[2]))
  # return payloads



key = {}
key['CTRL']     = array('B', [0, 0x01, 0, 0, 0])
key['SHIFT']    = array('B', [0, 0x02, 0, 0, 0])
key['ALT']      = array('B', [0, 0x04, 0, 0, 0])
key['SUPER']    = array('B', [0, 0x08, 0, 0, 0])
key['WIN']      = array('B', [0, 0x08, 0, 0, 0])
key['CTRL_L']   = array('B', [0, 0x01, 0, 0, 0])
key['SHIFT_L']  = array('B', [0, 0x02, 0, 0, 0])
key['ALT_L']    = array('B', [0, 0x04, 0, 0, 0])
key['SUPER_L']  = array('B', [0, 0x08, 0, 0, 0])
key['WIN_L']    = array('B', [0, 0x08, 0, 0, 0])
key['CTRL_R']   = array('B', [0, 0x10, 0, 0, 0])
key['SHIFT_R']  = array('B', [0, 0x20, 0, 0, 0])
key['ALT_R']    = array('B', [0, 0x40, 0, 0, 0])
key['SUPER_R']  = array('B', [0, 0x80, 0, 0, 0])
key['WIN_R']    = array('B', [0, 0x80, 0, 0, 0])

# key['CTRL_L']   = array('B', [0, 0, 0, 0xE0, 0])
# key['SHIFT_L']  = array('B', [0, 0, 0, 0xE1, 0])
# key['ALT_L']    = array('B', [0, 0, 0, 0xE2, 0])
# key['WIN_L']    = array('B', [0, 0, 0, 0xE3, 0])
# key['CTRL_R']   = array('B', [0, 0, 0, 0xE4, 0])
# key['SHIFT_R']  = array('B', [0, 0, 0, 0xE5, 0])
# key['ALT_R']    = array('B', [0, 0, 0, 0xE6, 0])
# key['WIN_R']    = array('B', [0, 0, 0, 0xE7, 0])

key['a'] = array('B', [0, 0, 0, 0x04, 0])
key['b'] = array('B', [0, 0, 0, 0x05, 0])
key['c'] = array('B', [0, 0, 0, 0x06, 0])
key['d'] = array('B', [0, 0, 0, 0x07, 0])
key['e'] = array('B', [0, 0, 0, 0x08, 0])
key['f'] = array('B', [0, 0, 0, 0x09, 0])
key['g'] = array('B', [0, 0, 0, 0x0A, 0])
key['h'] = array('B', [0, 0, 0, 0x0B, 0])
key['i'] = array('B', [0, 0, 0, 0x0C, 0])
key['j'] = array('B', [0, 0, 0, 0x0D, 0])
key['k'] = array('B', [0, 0, 0, 0x0E, 0])
key['l'] = array('B', [0, 0, 0, 0x0F, 0])
key['m'] = array('B', [0, 0, 0, 0x10, 0])
key['n'] = array('B', [0, 0, 0, 0x11, 0])
key['o'] = array('B', [0, 0, 0, 0x12, 0])
key['p'] = array('B', [0, 0, 0, 0x13, 0])
key['q'] = array('B', [0, 0, 0, 0x14, 0])
key['r'] = array('B', [0, 0, 0, 0x15, 0])
key['s'] = array('B', [0, 0, 0, 0x16, 0])
key['t'] = array('B', [0, 0, 0, 0x17, 0])
key['u'] = array('B', [0, 0, 0, 0x18, 0])
key['v'] = array('B', [0, 0, 0, 0x19, 0])
key['w'] = array('B', [0, 0, 0, 0x1A, 0])
key['x'] = array('B', [0, 0, 0, 0x1B, 0])
key['y'] = array('B', [0, 0, 0, 0x1C, 0])
key['z'] = array('B', [0, 0, 0, 0x1D, 0])
key['1'] = array('B', [0, 0, 0, 0x1E, 0])
key['2'] = array('B', [0, 0, 0, 0x1F, 0])
key['3'] = array('B', [0, 0, 0, 0x20, 0])
key['4'] = array('B', [0, 0, 0, 0x21, 0])
key['5'] = array('B', [0, 0, 0, 0x22, 0])
key['6'] = array('B', [0, 0, 0, 0x23, 0])
key['7'] = array('B', [0, 0, 0, 0x24, 0])
key['8'] = array('B', [0, 0, 0, 0x25, 0])
key['9'] = array('B', [0, 0, 0, 0x26, 0])
key['0'] = array('B', [0, 0, 0, 0x27, 0])
key['LF'] = array('B', [0, 0, 0, 0x28, 0])
key['ESC'] = array('B', [0, 0, 0, 0x29, 0])
key['BS'] = array('B', [0, 0, 0, 0x2A, 0])
key['TAB'] = array('B', [0, 0, 0, 0x2B, 0])
key[' '] = array('B', [0, 0, 0, 0x2C, 0])
key['-'] = array('B', [0, 0, 0, 0x2D, 0])
key['='] = array('B', [0, 0, 0, 0x2E, 0])
key['['] = array('B', [0, 0, 0, 0x2F, 0])
key[']'] = array('B', [0, 0, 0, 0x30, 0])
key['\\'] = array('B', [0, 0, 0, 0x31, 0])
# key['\\'] = array('B', [0, 0, 0, 0x32, 0])
key[';'] = array('B', [0, 0, 0, 0x33, 0])
key['\''] = array('B', [0, 0, 0, 0x34, 0])
key['`'] = array('B', [0, 0, 0, 0x35, 0])
key[','] = array('B', [0, 0, 0, 0x36, 0])
key['.'] = array('B', [0, 0, 0, 0x37, 0])
key['/'] = array('B', [0, 0, 0, 0x38, 0])
key['CAPS'] = array('B', [0, 0, 0, 0x39, 0])
key['F1'] = array('B', [0, 0, 0, 0x3A, 0])
key['F2'] = array('B', [0, 0, 0, 0x3B, 0])
key['F3'] = array('B', [0, 0, 0, 0x3C, 0])
key['F4'] = array('B', [0, 0, 0, 0x3D, 0])
key['F5'] = array('B', [0, 0, 0, 0x3E, 0])
key['F6'] = array('B', [0, 0, 0, 0x3F, 0])
key['F7'] = array('B', [0, 0, 0, 0x40, 0])
key['F8'] = array('B', [0, 0, 0, 0x41, 0])
key['F9'] = array('B', [0, 0, 0, 0x42, 0])
key['F10'] = array('B', [0, 0, 0, 0x43, 0])
key['F11'] = array('B', [0, 0, 0, 0x44, 0])
key['F12'] = array('B', [0, 0, 0, 0x45, 0])
key['PRT'] = array('B', [0, 0, 0, 0x46, 0])
key['SCR'] = array('B', [0, 0, 0, 0x47, 0])
key['PAUSE'] = array('B', [0, 0, 0, 0x48, 0])
key['INS'] = array('B', [0, 0, 0, 0x49, 0])
key['HOME'] = array('B', [0, 0, 0, 0x4A, 0])
key['PGUP'] = array('B', [0, 0, 0, 0x4B, 0])
key['DEL'] = array('B', [0, 0, 0, 0x4C, 0])
key['END'] = array('B', [0, 0, 0, 0x4D, 0])
key['PGDN'] = array('B', [0, 0, 0, 0x4E, 0])
key['RIGHT'] = array('B', [0, 0, 0, 0x4F, 0])
key['LEFT'] = array('B', [0, 0, 0, 0x50, 0])
key['DOWN'] = array('B', [0, 0, 0, 0x51, 0])
key['UP'] = array('B', [0, 0, 0, 0x52, 0])
key['NUM'] = array('B', [0, 0, 0, 0x53, 0])
key['NUM_/'] = array('B', [0, 0, 0, 0x54, 0])
key['NUM_*'] = array('B', [0, 0, 0, 0x55, 0])
key['NUM_-'] = array('B', [0, 0, 0, 0x56, 0])
key['NUM_+'] = array('B', [0, 0, 0, 0x57, 0])
key['NUM_ENTER'] = array('B', [0, 0, 0, 0x58, 0])
key['NUM_1'] = array('B', [0, 0, 0, 0x59, 0])
key['NUM_2'] = array('B', [0, 0, 0, 0x5A, 0])
key['NUM_3'] = array('B', [0, 0, 0, 0x5B, 0])
key['NUM_4'] = array('B', [0, 0, 0, 0x5C, 0])
key['NUM_5'] = array('B', [0, 0, 0, 0x5D, 0])
key['NUM_6'] = array('B', [0, 0, 0, 0x5E, 0])
key['NUM_7'] = array('B', [0, 0, 0, 0x5F, 0])
key['NUM_8'] = array('B', [0, 0, 0, 0x60, 0])
key['NUM_9'] = array('B', [0, 0, 0, 0x61, 0])
key['NUM_0'] = array('B', [0, 0, 0, 0x62, 0])
key['NUM_.'] = array('B', [0, 0, 0, 0x63, 0])
# key['UNKNOWN'] = array('B', [0, 0, 0, 0x64, 0])
key['MENU'] = array('B', [0, 0, 0, 0x65, 0])
key['POWER'] = array('B', [0, 0, 0, 0x66, 0])
key['NUM_='] = array('B', [0, 0, 0, 0x67, 0])
# key['XF86Tools'] = array('B', [0, 0, 0, 0x68, 0])
# key['NOT WOKING'] = array('B', [0, 0, 0, 0x69, 0])
# key['XF86Launch6'] = array('B', [0, 0, 0, 0x6A, 0])
# key['XF86Launch7'] = array('B', [0, 0, 0, 0x6B, 0])
# key['XF86Launch8'] = array('B', [0, 0, 0, 0x6C, 0])
# key['XF86Launch9'] = array('B', [0, 0, 0, 0x6D, 0])
# key['KEYCODE: 197'] = array('B', [0, 0, 0, 0x6E, 0])
key['MIC'] = array('B', [0, 0, 0, 0x6F, 0])
key['TOUCHPAD'] = array('B', [0, 0, 0, 0x70, 0])
key['TOUCHPADON'] = array('B', [0, 0, 0, 0x71, 0])
key['TOUCHPADOFF'] = array('B', [0, 0, 0, 0x72, 0])
# key['KEYCODE: 202'] = array('B', [0, 0, 0, 0x73, 0])
# key['XF86Open'] = array('B', [0, 0, 0, 0x74, 0])
key['HELP'] = array('B', [0, 0, 0, 0x75, 0])
# key['Sunpros'] = array('B', [0, 0, 0, 0x76, 0])
# key['SunFront'] = array('B', [0, 0, 0, 0x77, 0])
# key['CANCEL'] = array('B', [0, 0, 0, 0x78, 0])
# key['REDO'] = array('B', [0, 0, 0, 0x79, 0])
# key['UNDO'] = array('B', [0, 0, 0, 0x7A, 0])
# key['XF85Cut'] = array('B', [0, 0, 0, 0x7B, 0])
# key['XF86Copy'] = array('B', [0, 0, 0, 0x7C, 0])
# key['XF86Paste'] = array('B', [0, 0, 0, 0x7D, 0])
# key['Find'] = array('B', [0, 0, 0, 0x7E, 0])
key['EJECT'] = array('B', [0, 0, 0, 0xEC, 0])
key['MUTE'] = array('B', [0, 0, 0, 0x7F, 0])
key['VOLUP'] = array('B', [0, 0, 0, 0x80, 0])
key['VOLDN'] = array('B', [0, 0, 0, 0x81, 0])
# key['MUTE'] = array('B', [0, 0, 0, 0xF8, 0])
# key['VOLUP'] = array('B', [0, 0, 0, 0xED, 0])
# key['VOLDN'] = array('B', [0, 0, 0, 0xEE, 0])
# key['KEYCODE: 248'] = array('B', [0, 0, 0, 0x82, 0])
# key['KEYCODE: 130'] = array('B', [0, 0, 0, 0x90, 0])
# key['KEYCODE: 248'] = array('B', [0, 0, 0, 0xA0, 0])
# key['KEYCODE: 248'] = array('B', [0, 0, 0, 0xD0, 0])
# key['CTRL_L'] = array('B', [0, 0, 0, 0xE0, 0])
key['BROWSER'] = array('B', [0, 0, 0, 0xF0, 0])
key['SLEEP'] = array('B', [0, 0, 0, 0xF8, 0])
key['LOCK'] = array('B', [0, 0, 0, 0xF9, 0])
key['CALC'] = array('B', [0, 0, 0, 0xFB, 0])

key['A'] = array('B', [0, 0x02, 0, 0x04, 0])
key['B'] = array('B', [0, 0x02, 0, 0x05, 0])
key['C'] = array('B', [0, 0x02, 0, 0x06, 0])
key['D'] = array('B', [0, 0x02, 0, 0x07, 0])
key['E'] = array('B', [0, 0x02, 0, 0x08, 0])
key['F'] = array('B', [0, 0x02, 0, 0x09, 0])
key['G'] = array('B', [0, 0x02, 0, 0x0A, 0])
key['H'] = array('B', [0, 0x02, 0, 0x0B, 0])
key['I'] = array('B', [0, 0x02, 0, 0x0C, 0])
key['J'] = array('B', [0, 0x02, 0, 0x0D, 0])
key['K'] = array('B', [0, 0x02, 0, 0x0E, 0])
key['L'] = array('B', [0, 0x02, 0, 0x0F, 0])
key['M'] = array('B', [0, 0x02, 0, 0x10, 0])
key['N'] = array('B', [0, 0x02, 0, 0x11, 0])
key['O'] = array('B', [0, 0x02, 0, 0x12, 0])
key['P'] = array('B', [0, 0x02, 0, 0x13, 0])
key['Q'] = array('B', [0, 0x02, 0, 0x14, 0])
key['R'] = array('B', [0, 0x02, 0, 0x15, 0])
key['S'] = array('B', [0, 0x02, 0, 0x16, 0])
key['T'] = array('B', [0, 0x02, 0, 0x17, 0])
key['U'] = array('B', [0, 0x02, 0, 0x18, 0])
key['V'] = array('B', [0, 0x02, 0, 0x19, 0])
key['W'] = array('B', [0, 0x02, 0, 0x1A, 0])
key['X'] = array('B', [0, 0x02, 0, 0x1B, 0])
key['Y'] = array('B', [0, 0x02, 0, 0x1C, 0])
key['Z'] = array('B', [0, 0x02, 0, 0x1D, 0])
key['!'] = array('B', [0, 0x02, 0, 0x1E, 0])
key['@'] = array('B', [0, 0x02, 0, 0x1F, 0])
key['#'] = array('B', [0, 0x02, 0, 0x20, 0])
key['$'] = array('B', [0, 0x02, 0, 0x21, 0])
key['%'] = array('B', [0, 0x02, 0, 0x22, 0])
key['^'] = array('B', [0, 0x02, 0, 0x23, 0])
key['&'] = array('B', [0, 0x02, 0, 0x24, 0])
key['*'] = array('B', [0, 0x02, 0, 0x25, 0])
key['('] = array('B', [0, 0x02, 0, 0x26, 0])
key[')'] = array('B', [0, 0x02, 0, 0x27, 0])
key['_'] = array('B', [0, 0x02, 0, 0x2D, 0])
key['+'] = array('B', [0, 0x02, 0, 0x2E, 0])
key['{'] = array('B', [0, 0x02, 0, 0x2F, 0])
key['}'] = array('B', [0, 0x02, 0, 0x30, 0])
key['|'] = array('B', [0, 0x02, 0, 0x31, 0])
# key['|'] = array('B', [0, 0x02, 0, 0x32, 0])
key[':'] = array('B', [0, 0x02, 0, 0x33, 0])
key['"'] = array('B', [0, 0x02, 0, 0x34, 0])
key['~'] = array('B', [0, 0x02, 0, 0x35, 0])
key['<'] = array('B', [0, 0x02, 0, 0x36, 0])
key['>'] = array('B', [0, 0x02, 0, 0x37, 0])
key['?'] = array('B', [0, 0x02, 0, 0x38, 0])

# This ENTER is from the numpad
key['ENTER'] = array('B', [0, 0, 0, 0x58, 0])
