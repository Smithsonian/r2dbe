#!/usr/bin/env python
import logging
import os
import signal
import socket
import sys

from argparse import ArgumentParser
from ConfigParser import NoOptionError, NoSectionError, RawConfigParser
from datetime import datetime, timedelta
from functools import partial
from logging.handlers import RotatingFileHandler
from netifaces import ifaddresses
from Queue import Empty, Queue
from select import select
from subprocess import Popen
from time import sleep
from threading import Lock, Thread

from corr.katcp_wrapper import FpgaClient

from paccap_defines import *

default_logger = logging.getLogger(__file__.split(os.sep)[-1][:-3])

RTF_MAX_BYTES=16*1024*1024
RTF_BACKUP_COUNT=5

def ref_epoch():
	utcnow = datetime.utcnow()
	utcref = datetime(utcnow.year,1+6*int(utcnow.month/6),1,0,0,0)
	return utcref

def seconds_since_ref_epoch(date=None):
	if date is None:
		date = datetime.utcnow()
	return int((date-ref_epoch()).total_seconds())

class ConnectionError(RuntimeError):
	pass

class DataTerminal(object):

	def __init__(self,iface,port,ip=None):
		self._iface = iface
		if ip is None:
			ip = ifaddresses(iface)[2][0]["addr"]
		self._ip = ip
		self._port = port

	@property
	def iface(self):
		return self._iface

	@property
	def ip(self):
		return self._ip

	@property
	def port(self):
		return self._port

class R2Connect(object):

	def __init__(self,r2dbe_host,parent_logger=default_logger):
		self.r2dbe_host = r2dbe_host
		self.r2dbe = FpgaClient(r2dbe_host)
		if not self.r2dbe.wait_connected(timeout=10):
			raise ConnectionError("Could not connect to R2DBE host '{host}'".format(host=r2dbe_host))
		self._channels = {}

		# set logger
		self.logger = parent_logger.getChild("{name}[{host}]".format(name=self.__class__.__name__,host=self.r2dbe_host))

	def __len__(self):
		return len(self._channels)

	def all_channels(self):
		return self._channels.keys()

	def rec_channel(self,ch_n,sec,npak):
		mask_eq = 0x40000000
		mask_lt = 0x80000000
		self.r2dbe.write_int("r2dbe_pcap_{n}_sec".format(n=ch_n), mask_eq | sec)
		self.r2dbe.write_int("r2dbe_pcap_{n}_df".format(n=ch_n), mask_lt | npak)
		self.logger.debug("Channel #{n} to pass through packets that match (sec=={sec} && df<{npak})".format(
		  n=ch_n,sec=sec,npak=npak))

	def get_channel(self,ch_n):
		return self._channels[ch_n]

	def set_channel(self,ch_n,iface,port,ip=None):
		self._channels[ch_n] = DataTerminal(iface,port,ip=ip)
		self.logger.debug("Channel #{n} terminates at {ip}:{port} ({iface})".format(
		  n=ch_n,ip=self.get_channel(ch_n).ip,port=self.get_channel(ch_n).port,iface=self.get_channel(ch_n).iface))

class LoggingThread(Thread):

	def __init__(self,parent_logger=default_logger,*args,**kwargs):
		super(LoggingThread,self).__init__(*args,**kwargs)

		# set logger
		self.logger = parent_logger.getChild("{name}".format(name=self.__class__.__name__))

class StoppableThread(LoggingThread):

	def __init__(self,*args,**kwargs):
		super(StoppableThread,self).__init__(*args,**kwargs)

		# create lock and default stop condition to False
		self.lock = Lock()
		self.stopped = False

	def is_stopped(self):
		self.lock.acquire()
		stopped = self.stopped
		self.lock.release()
		return stopped

	def set_stop(self):
		self.lock.acquire()
		self.stopped = True
		self.lock.release()

class ReceiverThread(StoppableThread):

	def __init__(self,pqueue,host,port,*args,**kwargs):
		super(ReceiverThread,self).__init__(*args,**kwargs)

		# instantiate socket
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		self.sock.setblocking(0)
		self.sock.bind((host,port))

		self.logger.info("Bound to socket {host}:{port}".format(host=host,port=port))

		# set the queue for putting messages
		self.queue = pqueue

	def run(self):

		# initialize message buffer
		msg = ""

		self.logger.info("Started")

		while not self.is_stopped():

			try:

				# attempt to read data
				data, addr = self.sock.recvfrom(CMD_MAX_LEN+1)

				# data received
				if len(data) > 0:

					self.logger.debug("Received '{dat}'".format(dat=data))

					# append to message
					msg = "".join([msg,data])

					# check if length exceeds allowed
					if len(msg) > CMD_MAX_LEN:
						self.logger.warn("Message exceeds maximum length (set by CMD_MAX_LEN), discarding")
						msg = ""
						continue

					# check if trailing incomplete command
					if msg[-1] != CMD_TERMINATE:
						self.logger.warn("Message contains incomplete command")

				cmds = msg.split(CMD_TERMINATE)
				# process received message, last element in split will be null-string or incomplete command
				for cmd in cmds[:-1]:
					if len(cmd) > 0:
						self.logger.debug("Adding '{cmd}' to process queue".format(cmd=cmd))
						self.queue.put(cmd)

				# set message buffer to remainder (null-string or incomplete command)
				msg = cmds[-1]

			except socket.error as sock_err:
				# EAGAIN | EWOULDBLOCK just means no data available yet, do nothing
				if socket.errno.errorcode[sock_err.errno] not in ["EAGAIN","EWOULDBLOCK"]:
					self.logger.critical("Socket error encountered: [#{errno}] '{msg}'. Terminating thread.".format(
					  errno=sock_err.errno, msg=sock_err.message))
					break

			sleep(0.1)

		self.logger.info("Stopped")

class ProcessorThread(StoppableThread):

	def __init__(self,pqueue,r2connects,data_path,data_name_fmt,*args,**kwargs):
		super(ProcessorThread,self).__init__(*args,**kwargs)

		# set the queue for getting messages
		self.queue = pqueue

		# set process list
		self.processes = []

		# set R2SMAs in use, dictionary by hostname
		self.r2connects = {}
		for r2c in r2connects:
			self.r2connects[r2c.r2dbe_host] = r2c
			self.logger.debug("Added '{host}' = {r2c} to list of R2Connects".format(host=r2c.r2dbe_host,r2c=r2c))

		# set dataset format
		self.dataset_format = os.sep.join([data_path,data_name_fmt])

	def clean_zombies(self):
		for proc in self.processes:
			rc = proc.poll()
			if rc is not None:
				self.logger.info("Process {pid} done, calling wait() to remove from process table".format(pid=proc.pid))
				proc.wait()
				self.processes.remove(proc)
			else:
				#self.logger.debug("Process {pid} still running".format(pid=proc.pid))
				pass

	def do_noop(self,*args):
		return

	def do_record(self,*args):
		# parse argument list
		if len(args) != 6:
			self.logger.error("'record' expects 6 arguments, but found {narg}".format(narg=len(args)))
			return
		start,npak,dummy,name,exp,host = args

		# parse the start time
		MIN_FUTURE_SEC = 3
		try:
			start_date = datetime.strptime(start,"%Yy%jd%Hh%Mm%Ss")
		except:
			self.logger.error("Could not parse starting time, possibly improperly formatted.")
			return
		if start_date < (datetime.utcnow()+timedelta(seconds=MIN_FUTURE_SEC)):
			self.logger.error("Ignoring record set to less than MIN_FUTURE_SEC={mfs} into the future".format(
			  mfs=MIN_FUTURE_SEC))
			return
		start_sec = seconds_since_ref_epoch(date=start_date)
		now_sec = seconds_since_ref_epoch()
		ttl = start_sec - now_sec + 1

		# parse the number of packets
		MIN_NPAK = 1
		MAX_NPAK = 125000
		try:
			npak = int(npak)
		except:
			self.logger.error("Could not cast number of requested packets to int")
			return
		if npak < MIN_NPAK:
			self.logger.error("Less than MIN_NPAK={mnp} requested.".format(mnp=MIN_NPAK))
			return
		if npak > MAX_NPAK:
			self.logger.error("More than MAX_NPAK={mnp} requested.".format(mnp=MAX_NPAK))
			return

		# get the R2Connect instance and set packet filter
		cap_pids = []
		try:
			r2c = self.r2connects[host]
		except KeyError:
			self.logger.error("No R2Connect instance found for '{host}'".format(host=host))
			return

		for ch_n in r2c.all_channels():
			self.logger.info("Requesting channel #{n} on host '{host}' to record {npak} packets at {sec}".format(
			  n=ch_n,sec=start_sec,npak=npak,host=host))
			r2c.rec_channel(ch_n,start_sec,npak)

			# compile the dataset name
			outfile = self.dataset_format.format(exp=exp,daq=host,name=name,ch=ch_n)

			# start a capture process
			ch = r2c.get_channel(ch_n)
			hostname = str(ch.ip)
			portno = str(ch.port)
			npkt = str(npak)
			cmd_args = [PACCAP_EXEC,"-t",str(ttl),hostname,portno,npkt,outfile]
			this_proc = Popen(cmd_args)

			# add the process to the list
			if this_proc.pid > 0:
				self.logger.info("Launch '{cmdln}' returned PID={pid}".format(cmdln=" ".join(cmd_args),pid=this_proc.pid))
				self.processes.append(this_proc)
			else:
				self.logger.error("Launch '{cmdln}' returned {err}".format(err=this_proc.pid))

	def process(self,cmd):
		self.logger.info("Process command '{cmd}'".format(cmd=cmd))
		# check command format
		if CMD_ACTIONSEP not in cmd:
			self.logger.error("Invalid command format, no CMD_ACTIONSEP found")
			return
		action,params = cmd.split(CMD_ACTIONSEP)
		params = params.split(CMD_PARAMSSEP)
		fun = self.do_noop
		try:
			attr = "do_{act}".format(act=action)
			self.logger.debug("Looking for attribute {attr}".format(attr=attr))
			fun = getattr(self,attr)
		except AttributeError:
			self.logger.error("No definition for '{act}'".format(act=action))
		fun(*params)

	def run(self):

		self.logger.info("Started")

		while not self.is_stopped():

			# check the queue for new message
			try:
				cmd = self.queue.get_nowait()

				self.logger.debug("Popped command '{cmd}'".format(cmd=cmd))

				# process the message
				self.process(cmd)

			# if queue empty, do nothing and try again
			except Empty:
				pass

			# clean zombies if there are any
			self.clean_zombies()

			sleep(0.1)

		self.logger.info("Stopped")

def stop_all(threads_to_stop, signum, frame, logger=None):
	for th in threads_to_stop:
		if logger is not None:
			logger.info("Stopping {th}".format(th=th))
		th.set_stop()

if __name__ == "__main__":

	parser = ArgumentParser("Start paccap control process")
	parser.add_argument('-c','--config-file',metavar='FILE',type=str,default=DEFAULT_CFG_FILE,
	  help='read configuration from FILE')
	parser.add_argument('-l','--log-file',metavar='FILE',type=str,default=None,
	  help='write log messages to FILE')
	parser.add_argument('-v','--verbose',action='store_true',default=False,
	  help='set log level to DEBUG')
	args = parser.parse_args()

	# Read configuration
	rcp = RawConfigParser()
	rcp.read(args.config_file)

	################################################## Configure logging
	# Determine the log file
	log_file = DEFAULT_LOG_FILE
	try:
		log_file = rcp.get(CFG_SEC_SYSTEM,CFG_OPT_SYSTEM_LOG_FILE)
	except NoSectionError, NoOptionError:
		pass
	if args.log_file is not None:
		# Command-line option overrules all
		log_file = arsg.log_file

	# Setup root logger
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)

	# Silence all katcp messages
	katcp_logger = logging.getLogger('katcp')
	katcp_logger.setLevel(logging.CRITICAL)

	# Create and set formatting
	formatter = logging.Formatter('%(name)-30s: %(asctime)s : %(levelname)-8s %(message).140s')

	# Create and set up file handler
	log_hndl = RotatingFileHandler(log_file,maxBytes=RTF_MAX_BYTES,backupCount=RTF_BACKUP_COUNT)
	log_hndl.setFormatter(formatter)
	logger.addHandler(log_hndl)

	# Set log level to DEBUG if requested
	if args.verbose:
		logger.setLevel(logging.DEBUG)

	# Log startup
	logger.info("Started with configuration file '{conf}'".format(conf=args.config_file))

    ########################################## Initialize worker threads

	# Setup processing queue
	process_queue = Queue()

	# Set up the receiving thread
	host = DEFAULT_CTRL_HOST
	try:
		host = rcp.get(CFG_SEC_SYSTEM,CFG_OPT_SYSTEM_CTRL_HOST)
	except NoSectionError, NoOptionError:
		pass
	port = DEFAULT_CTRL_PORT
	try:
		port = int(rcp.get(CFG_SEC_SYSTEM,CFG_OPT_SYSTEM_CTRL_PORT))
	except NoSectionError, NoOptionError:
		pass
	mrt = ReceiverThread(process_queue,host,port)

	# Compile list of R2DBEs
	daq_list = []
	try:
		daq_list = rcp.get(CFG_SEC_DAQ,CFG_OPT_DAQ_LIST).split(",")
	except NoSectionError, NoOptionError:
		logger.critical("No data acquisition system list found in configuration file.")
		sys.exit(1)
	r2c_list = []
	for daq in daq_list:
		# do this check in case list starts / ends with separation character and there is a null-string entry
		if len(daq) > 0:
			# First try to establish connectoin to the given R2DBE
			try:
				r2c = R2Connect(daq)
			except ConnectionError:
				logger.error("Failed to initialize R2Connect for '{host}', skipping.".format(host=daq))
				continue

			# Add defined channels for given R2DBE
			for ch_n in R2DBE_CHANNELS:
				try:
					iface = rcp.get(daq,CFG_OPT_R2DBE_CHN_IFACE.format(n=ch_n))
					port = rcp.get(daq,CFG_OPT_R2DBE_CHN_PORT.format(n=ch_n))
					r2c.set_channel(ch_n,iface,port)
				except NoSectionError:
					logger.error("No section found for R2DBE '{host}', skipping.".format(host=daq))
					continue
				except NoOptionError:
					logger.warn("No or incomplete channel #{n} definition for R2DBE '{host}'".format(n=ch_n,host=daq))
					# if no definition for this channel, just continue
					pass

			# If no channels were defined, do not add R2DBE to list
			if len(r2c) < 1:
				logger.error("No channels defined for R2DBE '{host}', not adding to list.".format(host=daq))
				continue

			# Append the R2DBE to the list
			r2c_list.append(r2c)

	if len(r2c_list) < 1:
		logger.critical("Not one data acquisition system defined, exiting.")
		sys.exit(1)

	# Read data options
	data_path = DEFAULT_DATA_PATH
	try:
		data_path = rcp.get(CFG_SEC_DATA,CFG_OPT_DATA_PATH)
	except NoOptionError, NoSectionError:
		pass
	data_name_fmt = DEFAULT_DATA_NAME_FMT
	try:
		data_name_fmt = rcp.get(CFG_SEC_DATA,CFG_OPT_DATA_NAME_FMT)
	except NoOptionError, NoSectionError:
		pass

	# Set up the processing thread
	mpt = ProcessorThread(process_queue,r2c_list,data_path,data_name_fmt)

	# Convenient list of the worker threads
	worker_threads = [mrt, mpt]

	# Register signal handler for interrupt
	signal.signal(signal.SIGINT,partial(stop_all,worker_threads,logger=logger))
	logger.info("Set handler for SIGINT: stop_all")

	logger.info("Starting worker threads...")
	[wt.start() for wt in worker_threads]
	
	logger.info("Waiting until all threads have stopped...")
	while any([wt.is_alive() for wt in worker_threads]):
		sleep(2)

	logger.info("All threads have stopped, waiting for join...")
	[wt.join() for wt in worker_threads]

	logger.info("All threads have joined, exiting.")
	sys.exit(0)
