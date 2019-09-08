#!/usr/bin/env python2.7

import logging

import atexit
import os
import os.path
import sys

from functools import partial
from numpy import count_nonzero
from signal import signal, SIGINT, SIGTERM
from time import sleep

from mandc.monitor import *
from mandc.utils import Daemon
 
def sigint_handler(mongrpd, signum, frame):

	# Log signal
	mongrpd.logger.info("Received SIGINT, stopping monitor threads")

	# Set the stop condition for all monitors
	[m.set_stop() for m in mongrpd.monitors]

	while any([m.is_alive() for m in mongrpd.monitors]):
		sleep(1)

	# Log done
	mongrpd.logger.info("All monitor threads stopped")

class MonitorGroupDaemon(Daemon):

	def __init__(self, r2dbe_host, mon_def_list, logpath=None, loglevel=logging.INFO):
		# Set the R2DBE host
		self._r2dbe_host = r2dbe_host

		# Set the log path
		self._logpath = logpath
		if self._logpath is None:
			self._logpath = os.path.sep.join([os.path.expanduser("~"), "log"])

		# Set the PID filename
		self._pidfile = os.path.extsep.join([os.path.sep.join([self._logpath, self.name]), "pid"])

		# Set the logfile
		self._logfile = os.path.extsep.join([os.path.sep.join([self._logpath, self.name]), "log"])

		# Set the log level
		self._loglevel = loglevel

		# Keep the monitor definition list for later
		self._mon_def_list = mon_def_list

		# Then do parent class initializiation
		super(MonitorGroupDaemon, self).__init__(self._pidfile)

	def _configure_logging(self):
		# Start a root logger
		self.logger = logging.getLogger()
		file_handler = logging.FileHandler(self._logfile, "a")
		formatter = logging.Formatter('%(name)-30s: %(asctime)s : %(levelname)-8s %(message)s')
		file_handler.setFormatter(formatter)
		self.logger.addHandler(file_handler)
		self.logger.setLevel(self._loglevel)

		# Set katcp loglevel to CRITICAL only
		self._katcp_logger = logging.getLogger("katcp")
		self._katcp_logger.setLevel(logging.CRITICAL)

		# Write initial log entry
		self.logger.info("Started logging in {filename}".format(filename=__file__))

	def _instantiate_monitors(self):
		self._monitors = []
		for mdl in self._mon_def_list:
			monitor = mdl.cls(self._r2dbe_host, **mdl.kwargs)
			# Add the groups for this monitor
			for grp in mdl.grps:
				monitor.add_group(grp)
			self._monitors.append(monitor)

	@property
	def monitors(self):
		return self._monitors

	@property
	def name(self):
		return "_".join(["r2daemon", self._r2dbe_host])

	def run(self):
		# First configure logging
		self._configure_logging()

		# Then instantiate monitors
		self._instantiate_monitors()

		# Start the monitor threads
		[m.start() for m in self._monitors]

		# Register SIGINT handler to stop threads, passing self as first argument
		signal(SIGINT, partial(sigint_handler, self))

		# While any of the threads is still alive, sleep
		while any([m.is_alive() for m in self._monitors]):
			sleep(1)

		# Then wait for them to be done
		[m.join() for m in self._monitors]

	def stop(self):
		# First get PID
		pid = self._get_pid_from_file()

		if not pid:
			message = "pidfile %s does not exist. Daemon not running?\n"
			sys.stderr.write(message % self.pidfile)
			return # not an error in a restart

		# Send SIGINT to stop monitor threads. Note that this will cause the run()
		# method to return, and the process to terminate on its own volition, so
		# there is no need to also call super's method.
		self._kill(pid, SIGINT)

class MonitorDefinition(object):

	def __init__(self, cls, grps, **kwargs):
		self._cls = cls
		self._grps = grps
		self._kwargs = kwargs

	@property
	def cls(self):
		return self._cls

	@property
	def grps(self):
		return self._grps

	@property
	def kwargs(self):
		return self._kwargs

_default_mon_list = [
  MonitorDefinition(R2dbeMonitor, [R2DBE_GROUP_SNAP], period=2.0),
  MonitorDefinition(R2dbeMonitor, [R2DBE_GROUP_VDIF], period=60.0),
  MonitorDefinition(R2dbeSyncMonitor, [R2DBE_GROUP_TIME], period=0.9,
    usec_into=150000, usec_tol=50000, ignore_late=True)
]

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Control an R2DBE monitor daemon", epilog="" \
	  "The script must be called with exactly one of the control arguments --start, --stop, or --restart" \
	  "")
	parser.add_argument("--start", action="store_true", default=False,
	  help="start a monitor deamon")
	parser.add_argument("--restart", action="store_true", default=False,
	  help="restart a monitor daemon")
	parser.add_argument("--stop", action="store_true", default=False,
	  help="stop a monitor daemon")
	parser.add_argument("-v", "--verbose", action="store_true", default=False,
	  help="set logging to level DEBUG (in daemon process)")
	parser.add_argument("r2dbe_host", metavar="HOST", type=str,
	  help="control the daemon associated with HOST")
	args = parser.parse_args()

	# Check if valid call
	flags = [args.start, args.stop, args.restart]
	if count_nonzero(flags) != 1 or not any(flags):
		print "Call the script with exactly one control argument."
		sys.exit(1)

	# Set log level
	loglvl = logging.INFO
	if args.verbose:
		loglvl = logging.DEBUG

	# Create a daemon instance
	daemon = MonitorGroupDaemon(args.r2dbe_host, _default_mon_list, loglevel=loglvl)

	# Perform the requested action
	if args.start:
		daemon.start()
	elif args.stop:
		daemon.stop()
	else:
		daemon.restart()

	sys.exit(0)
