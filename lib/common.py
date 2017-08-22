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

channels = []
args = None
parser = None
radio = None
timeout = None
ack_timeout = None
retries = None
ping_payload = None

# Initialize the argument parser
def init_args(description):

  global parser
  parser = argparse.ArgumentParser(description,
    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=50,width=120))
  parser.add_argument('-c', '--channels', type=int, nargs='+', help='RF channels', default=range(2, 84), metavar='N')
  parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output', default=False)
  parser.add_argument('-l', '--lna', action='store_true', help='Enable the LNA (for CrazyRadio PA dongles)', default=False)
  parser.add_argument('-i', '--index', type=int, help='Dongle index', default=0)
  parser.add_argument('-t', '--timeout', type=int, help='Channel timeout, in milliseconds', default=100)
  parser.add_argument('-k', '--ack_timeout', type=int, help='ACK timeout in microseconds, accepts [250,4000], step 250', default=250)
  parser.add_argument('-r', '--retries', type=int, help='Auto retry limit, accepts [0,15]', default=1, choices=xrange(0, 16), metavar='RETRIES')
  parser.add_argument('-p', '--ping_payload', type=str, help='Ping payload, ex 0F:0F:0F:0F', default='0F:0F:0F:0F', metavar='PING_PAYLOAD')

# Parse and process common comand line arguments
def parse_and_init():

  global parser
  global args
  global channels
  global radio
  global timeout
  global ack_timeout
  global retries
  global ping_payload

  # Parse the command line arguments
  args = parser.parse_args()

  # Setup logging
  level = logging.DEBUG if args.verbose else logging.INFO
  logging.basicConfig(level=level, format='[%(asctime)s.%(msecs)03d]  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")

  # Update args
  channels = args.channels
  timeout = float(args.timeout) / 1000
  ack_timeout = int(args.ack_timeout / 250) - 1
  ack_timeout = max(0, min(ack_timeout, 15))
  retries = max(0, min(args.retries, 15))
  ping_payload = args.ping_payload.replace(':', '').decode('hex')

  logging.debug('Using channels {0}'.format(', '.join(str(c) for c in channels)))

  # Initialize the radio
  radio = nrf24(args.index)
  if args.lna: radio.enable_lna()

