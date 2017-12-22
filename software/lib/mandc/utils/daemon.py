import logging

import atexit
import os
import os.path
import sys

from signal import SIGTERM
from time import sleep

class Daemon(object):

	def __init__(self, pidfile, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null"):
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		self.pidfile = pidfile

	def _get_pid_from_file(self):
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None

		return pid

	def _kill(self, pid, sig):
		# Try killing the daemon process
		try:
			while True:
				os.kill(pid, sig)
				sleep(0.1)
		except OSError, err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				print str(err)
				sys.exit(1)

	def _message(self, msg, lvl=logging.INFO):
		# Try logging first
		if hasattr(self, "logger"):
			self.logger.log(lvl, msg)
			return

		# Otherwise write to stdout / stderr
		if lvl >= logging.ERROR:
			sys.stderr.write(msg)
		else:
			sys.stdout.write(msg)

	def daemonize(self):
		try:
			pid = os.fork()
			if pid > 0:
				# exit first parent
				sys.exit(0)
		except OSError, e:
			self._message("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror), lvl=logging.ERROR)
			sys.exit(1)

		# decouple from parent environment
		os.chdir("/")
		os.setsid()
		os.umask(0)

		# do second fork
		try:
			pid = os.fork()
			if pid > 0:
				# exit from second parent
				sys.exit(0)
		except OSError, e:
			self._message("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror), lvl=logging.ERROR)
			sys.exit(1)

		# Redirect standard file descriptors
		sys.stdout.flush()
		sys.stderr.flush()
		si = file(self.stdin, "r")
		so = file(self.stdout, "a+")
		se = file(self.stderr, "a+", 0)
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())

		# Write pidfile
		atexit.register(self.delpid)
		pid = str(os.getpid())
		file(self.pidfile,"w+").write("%s\n" % pid)
   
	def delpid(self):
		self._message("Deleting PID file '{0}'".format(self.pidfile))
		# Remove PID file
		os.remove(self.pidfile)

	def start(self):
		# Check for a pidfile to see if the daemon already runs
		pid = self._get_pid_from_file()

		if pid:
			message = "pidfile %s already exist. Daemon already running?\n"
			self.logger.warn(message % self.pidfile)
			sys.exit(1)
	   
		# Start the daemon
		self.daemonize()
		self.run()

	def stop(self):
		# Get the pid from the pidfile
		pid = self._get_pid_from_file()

		if not pid:
			message = "pidfile %s does not exist. Daemon not running?\n"
			self.logger.warn(message % self.pidfile)
			return # not an error in a restart

		self._kill(pid, SIGTERM)

	def restart(self):
		self.stop()
		self.start()

	def run(self):
		pass
