#!/usr/bin/env python2.7

import logging

import os.path
import sys

from datetime import datetime
from signal import signal, SIGINT
from time import sleep

from mandc.data import VDIFTime
from mandc.r2dbe import R2dbe, R2DBE_INPUTS

def signal_handler(signal, frame):
	sys.exit(0)

def _configure_logging(logfilename=None, verbose=None):
	# Set up root logger
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)

	# Always add logging to stdout
	stdout_handler = logging.StreamHandler(sys.stdout)
	all_handlers = [stdout_handler]
	# And optionally to file
	if logfilename:
		file_handler = logging.FileHandler(logfilename, mode="a")
		all_handlers.append(file_handler)
	# Add handlers
	for handler in all_handlers:
		logger.addHandler(handler)

	# Silence all katcp messages, except CRITICAL
	katcp_logger = logging.getLogger('katcp')
	katcp_logger.setLevel(logging.CRITICAL)

	# If verbose, set level to DEBUG on file, or stdout if no logging to file
	if verbose:
		# First set DEBUG on root logger
		logger.setLevel(logging.DEBUG)
		# Then revert to INFO on 0th handler (i.e. stdout)
		all_handlers[0].setLevel(logging.INFO)
		# Finally DEBUG again on 1th handler (file if it exists, otherwise stdout again)
		all_handlers[-1].setLevel(logging.DEBUG)

	# Create and set formatters
	formatter = logging.Formatter('%(name)-30s: %(asctime)s : %(levelname)-8s %(message)s')
	for handler in all_handlers:
		handler.setFormatter(formatter)

	# Initial log messages
	logger.info("Started logging in {filename}".format(filename=__file__))
	if logfilename:
		logger.info("Log file is '{log}'".format(log=logfilename))

	# Return root logger
	return logger

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Log external vs internal PPS offset")
	parser.add_argument("-l", "--log-file", dest="log", metavar="FILE", type=str, default=None,
	  help="write log messages to FILE in addition to stdout (default is $HOME/log/pps_logger_HOST.log)")
	parser.add_argument("-o", "--output-file", dest="out", metavar="FILE", type=str, default=None,
	  help="write PPS data to FILE (default is $HOME/log/pps-drift_HOST.log)")
	parser.add_argument("-t", "--period", dest="period", metavar="SECONDS", type=int, default=60,
	  help="PPS log periodicity")
	parser.add_argument("-v", "--verbose", action="store_true", default=False,
	  help="set logging to level DEBUG")
	parser.add_argument("r2dbe_host", metavar="HOST", type=str,
	  help="log offset for HOST")
	args = parser.parse_args()

	# Set default log path if needed
	if not args.log:
		log_path = os.path.sep.join([os.path.expanduser("~"), "log"])
		log_basename = os.path.extsep.join([
		  "_".join([
		    os.path.basename(os.path.splitext(__file__)[0]),
		    args.r2dbe_host]),
		  "log"])
		args.log = os.path.sep.join([log_path, log_basename])

	# Set default output path if needed
	if not args.out:
		out_path = os.path.sep.join([os.path.expanduser("~"), "log"])
		out_basename = os.path.extsep.join([
		  "_".join([
		    "pps-drift",
		    args.r2dbe_host]),
		  "log"])
		args.out = os.path.sep.join([out_path, out_basename])

	# Configure logger
	logger = _configure_logging(logfilename=args.log, verbose=args.verbose)

	# handle SIGINT
	signal(SIGINT, signal_handler)

	# Instantiate R2dbe instance
	r2dbe = R2dbe(args.r2dbe_host)

	# Initialize output file, add header line if file not created yet
	if not os.path.isfile(args.out):
		with open(args.out, "w") as fh:
			fh.write("ref_epoch,sec_since_epoch,data_frame,pps_offset\r\n")

	# Main loop
	while True:
		# Get the current time
		datetime_now = datetime.utcnow()
		vdif_now = VDIFTime.from_datetime(datetime_now)

		# Get the current offset
		offset = r2dbe.get_gps_pps_clock_offset()

		# Log to output
		with open(args.out, "a") as fh:
			fh.write("{v.epoch},{v.sec},{v.frame},{offset}\r\n".format(v=vdif_now, offset=offset))

		# Go to sleep
		sleep(args.period)
