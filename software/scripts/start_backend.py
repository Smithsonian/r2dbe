import logging
import os.path
import sys

from mandc import Station

_default_log_basename = os.path.extsep.join([os.path.basename(os.path.splitext(__file__)[0]), "log"])
_default_log = os.path.sep.join([os.path.expanduser("~"), "log",_default_log_basename])

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

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Configure R2DBE backends")
	parser.add_argument("-l", "--log-file", dest="log", metavar="FILE", type=str, default=_default_log,
	  help="write log messages to FILE in addition to stdout (default is $HOME/log/")
	parser.add_argument("-v", "--verbose", action="store_true", default=False,
	  help="set logging to level DEBUG")
	parser.add_argument("conf", metavar="CONFIG", type=str,
	  help="backend configuration file")
	args = parser.parse_args()

	# Configure logging
	_configure_logging(logfilename=args.log, verbose=args.verbose)

	# Parse configuration file
	station_backend = Station.from_file(args.conf)

	# Set up
	station_backend.setup()
