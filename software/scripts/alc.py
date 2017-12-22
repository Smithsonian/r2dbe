#!/usr/bin/env python2.7

import logging

import os.path
import sys

from mandc import Station

from mandc.r2dbe import R2dbe, R2DBE_INPUTS

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

	parser = argparse.ArgumentParser(description="Set 2-bit quantization threshold")
	parser.add_argument("-l", "--log-file", dest="log", metavar="FILE", type=str, default=None,
	  help="write log messages to FILE in addition to stdout (default is $HOME/log/alc_HOST.log")
	parser.add_argument("-v", "--verbose", action="store_true", default=False,
	  help="set logging to level DEBUG")
	parser.add_argument("r2dbe_host", metavar="HOST", type=str,
	  help="set thresholds for HOST")
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

	# Configure logger
	logger = _configure_logging(logfilename=args.log, verbose=args.verbose)

	# Instantiate R2dbe instance
	r2dbe = R2dbe(args.r2dbe_host)

	# Set thresholds
	for inp in R2DBE_INPUTS:
		r2dbe.set_2bit_threshold(inp)

	# Get thresholds and log
	th = r2dbe.get_2bit_threshold(list(R2DBE_INPUTS))
	logger.info("Thresholds for {host!r} set to if0={th[0]}, if1={th[1]}".format(host=r2dbe, th=th))
