#!/usr/bin/python

from signal import signal, SIGINT
from sys import exit
# handle SIGINT
def signal_handler(signal, frame):
        exit(0)
signal(SIGINT, signal_handler)

import logging

from argparse import ArgumentParser
from numpy import int32
from vdif import VDIFFrame

VDIF_PKT_SIZE = 8224
DEFAULT_LOG_FILE = '/var/log/r2dbe/pps-drift.log'
LOG_HEADER = 'ref_epoch,sec_since_epoch,data_frame,pps_offset\r\n'
# typical lines in log file are 22 characters wide, and one line per second means +/-2MB per day, so 100MB is roughly 50 days
MAX_LOG_FILE_SIZE = 100*2**20

# parse input arguments
parser = ArgumentParser(description='Get drift from VDIF packet')
parser.add_argument('-v', dest='verbose', help='display debugging logs')
parser.add_argument('-l', dest='logfile', type=str, default=DEFAULT_LOG_FILE, help='Specify the log file to use (default is {0})'.format(DEFAULT_LOG_FILE))
parser.add_argument('file', type=str, nargs=1, help='VDIF file containing data')
args = parser.parse_args()

# set up basic logger
logging.basicConfig(format='%(asctime)-15s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

if not args.file:
	err_msg = 'No input file specified'
	logging.error(err_msg)
	raise ValueError(err_msg)
try:
	with open(args.file[0],'r') as f_vdif:
		b = f_vdif.read(VDIF_PKT_SIZE)
		if (len(b) == VDIF_PKT_SIZE):
			v = VDIFFrame.from_bin(b)
			log_str = '{0},{1},{2},{3}\r\n'.format(v.ref_epoch,v.secs_since_epoch,v.data_frame,int32(v.eud[1]))
			try:
				with open(args.logfile,'a') as f_log:
					f_log_size = f_log.tell()
					if f_log_size == 0:
						f_log.write(LOG_HEADER)
					elif f_log_size < MAX_LOG_FILE_SIZE:
						f_log.write(log_str)
			except IOError as ioe:
				err_msg = 'Could not append log file {0} [{1}]'.format(args.logfile,ioe.message)
				logging.error(err_msg)
				raise ioe
except IOError as ioe:
	print 'Could not read from input file {0} [{1}]'.format(args.file[0],ioe.message)
	raise ioe

	
