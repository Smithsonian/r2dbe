#!/usr/bin/env python
import logging
import sys

from argparse import ArgumentParser
from datetime import datetime, timedelta
from subprocess import Popen, PIPE
from time import sleep
import xml.etree.ElementTree as ET

RECORD_COMMAND_TEMPLATE='record={0}:{1}:{2}:{3}:{4}:{5};'
SEND_TO_PACCAP_CMD_TEMPLATE = 'echo \'{0}\' | ./paccap_cmd.py'

SCAN_TIME_FMT = '%Yy%jd%Hh%Mm%Ss'
SCAN_NAME_FMT = '%j-%H%M%S'

def send_paccap_cmd(start,npkt,name,station,experiment,logger=None):
	# build record command
	rec_cmd = RECORD_COMMAND_TEMPLATE.format(
	  start.strftime(SCAN_TIME_FMT),
	  npkt,
	  "dummy",
	  name,
	  experiment,
	  station
	)

	if logger is not None:
		logger.debug("Capture command is '{cmd}'".format(cmd=rec_cmd))

	# build the command line call
	cmd = SEND_TO_PACCAP_CMD_TEMPLATE.format(rec_cmd)

	if logger is not None:
		logger.debug("Command-line call is '{cmd}'".format(cmd=cmd))

	#~ # do the call
	p = Popen(cmd,stdout=PIPE,stderr=PIPE,shell=True)
	rc = p.wait()
	stdout = p.stdout.read()
	stderr = p.stderr.read()
	#~ rc = 0
	#~ stdout = "success"
	#~ stderr = "failure"

	if logger is not None:
		logger.debug("Command-line call returned code {rc}".format(rc=rc))

	if len(stdout) > 0:
		print stdout
	if len(stderr) > 0:
		print stderr

if __name__ == "__main__":
	# get timestamp
	utcnow = datetime.utcnow()
	timestamp = utcnow.strftime("%Y%m%d_%H%M%S")
	
	parser = ArgumentParser(description='Do scheduled packet capturing')
	parser.add_argument('-n','--num-pkt',metavar='NPKT',default=1024,
	  help="capture NPKT packets for each scan")
	parser.add_argument('-t','--time-threshold',metavar='SAFE',type=int,default=3,
	  help="do not prime capture within SAFE seconds of a scheduled scan (default is 3)")
	parser.add_argument('-v','--verbose',action='store_true',default=False,
	  help="set logging level to DEBUG")
	parser.add_argument('sched',metavar='SCHED',type=str,
	  help="read the schedule from the given XML file")
	args = parser.parse_args()
	
	tree = ET.parse(args.sched)
	root = tree.getroot()

	# Setup root logger
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)
	# Set log level to DEBUG if requested
	if args.verbose:
		logger.setLevel(logging.DEBUG)

	# Set logger format and handler
	formatter = logging.Formatter('%(name)-30s: %(asctime)s : %(levelname)-8s %(message).140s')

	# Create and set up file handler
	log_hndl = logging.StreamHandler(sys.stdout)
	log_hndl.setFormatter(formatter)
	logger.addHandler(log_hndl)

	scans = root.findall("scan")
	for ii,scan in enumerate(scans):

		# get scan start time
		start = datetime.strptime(scan.get('start_time'), '%Y%j%H%M%S')
		# get scan stop time
		duration = int(scan.get('duration'))
		stop = start + timedelta(0,duration)
		# get scan name, station, experiment, source
		name = scan.get('scan_name')
		station = scan.get('station_code')
		experiment = scan.get('experiment')
		source = scan.get('source')

		logger.debug("Scan #{sn} for station {sta} in experiment {exp} on source {src} starts at {start} is {sec} seconds long.".format(
		  sn=ii+1,sta=station,exp=experiment,src=source,start=start.strftime('%Y-%m-%d %H:%M:%S'),sec=duration))

		# safety threshold
		threshold = timedelta(0,args.time_threshold)
		
		# get current time
		utcnow = datetime.utcnow()
		
		# skip scans that have completed
		if utcnow > stop + threshold:
			# scan is over, skip
			logger.warning("Scan #{sn} started at {start}, it is already {now} skipping...".format(
			  sn=ii+1,start=start.strftime('%Y-%m-%d %H:%M:%S'),now=utcnow.strftime('%Y-%m-%d %H:%M:%S')))
			continue
		
		# sleep while current scan in progress
		if utcnow > start - threshold and utcnow < stop + threshold:
			# in the middle of a scan, sleep
			dt = stop + threshold - utcnow 
			dt = dt.days*24*60*60 + dt.seconds
			logger.warning("Waiting for scan #{sn} already started at {start} to finish, sleeping for {sec} seconds...".format(
			  sn=ii+1,sec=dt,start=start.strftime('%Y-%m-%d %H:%M:%S')))
			sleep(dt)
			logger.info("Scan #{sn} should be done, continuing processing...".format(sn=ii+1))
			continue
		
		# calculate time before next scan
		dt = (start - threshold) - datetime.utcnow()
		dt = dt.days*24*60*60 + dt.seconds
		if dt > 0:
			# do the call
			send_paccap_cmd(start,args.num_pkt,name,station,experiment,logger=logger)
			
		# then go to sleep until scan finishes
		utcnow = datetime.utcnow()
		dt = stop + threshold - utcnow
		dt = dt.days*24*60*60 + dt.seconds
		logger.debug("Going to sleep for {sec} seconds until end of scan #{sn}...".format(
		  sec=dt,sn=ii+1))
		sleep(dt)

	logger.info("Finished processing of file '{fl}'".format(fl=args.sched))
