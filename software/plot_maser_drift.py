#!/usr/bin/python

from argparse import ArgumentParser
from datetime import datetime, time, timedelta
from numpy import loadtxt, int32, unique, array, polyfit

import matplotlib.pyplot as plt
plt.ion()

DEFAULT_LOG_FILE = '/var/log/r2dbe/pps-drift.log'
VDIF_PKTS_PER_SECOND = 125000
DELTA_T_PER_COUNT = 1/256e6 # drift counter runs on 256 MHz clock

parser = ArgumentParser(description='Plot PPS drift logfile')
parser.add_argument('-v', dest='verbose', help='display debugging logs')
parser.add_argument('-l', dest='label', default='data', help='data label in plot legend')
parser.add_argument('-H', dest='hour_offset', type=int, default=0, help='offset x-axis ticks by this many hours (default is 0)')
parser.add_argument('--no-X', dest='noX', action='store_true', help="run non-X version (no plotting)")
parser.add_argument('-a', dest='now_ref_from_file', action='store_true', help="set reference time to first entry in log file")
parser.add_argument('logfile', type=str, nargs='?', default=DEFAULT_LOG_FILE, help='The log file to use (default is {0})'.format(DEFAULT_LOG_FILE))
args = parser.parse_args()

# interactive plotting on
#~ plt.ion()

# read data from CSV format log file
with open(args.logfile,'r') as f_logfile:
	data = loadtxt(f_logfile,delimiter=',',skiprows=1,dtype=int32)
ref_epoch = data[:,0]
secs_since_epoch = data[:,1]
data_frame = data[:,2]
drift = data[:,3]

# calculate hours since reference date for plotting help
ref_ref_epoch_date = datetime(2000,1,1,0,0,0)
if args.now_ref_from_file:
	now_ref = datetime(2000+int(ref_epoch[0]/2),(ref_epoch[0] % 2)*6+1,1,0,0,0)
	now_ref = now_ref + timedelta(seconds=int(secs_since_epoch[0]))
else:
	now_ref = datetime.utcnow()
	now_ref = datetime(now_ref.year,now_ref.month,now_ref.day)
delta_date = (now_ref - ref_ref_epoch_date)
now_hours = int((delta_date.days*24*3600 + delta_date.seconds)/3600)

# convert time to hours since start of first epoch (1 Jan 2000)
offset_secs = dict()
for this_epoch in unique(ref_epoch):
  ref_epoch_date = datetime(2000+this_epoch/2,(this_epoch % 2)*6+1,1,0,0,0)
  delta_date = (ref_epoch_date - ref_ref_epoch_date)
  offset_secs[this_epoch] = (delta_date.days*24*3600 + delta_date.seconds)
secs_since_first_epoch = secs_since_epoch + array([offset_secs[re] for re in ref_epoch],dtype=int32)
hours_since_first_epoch = (secs_since_first_epoch + 1.0*data_frame/VDIF_PKTS_PER_SECOND)/3600.0
hours_rel = hours_since_first_epoch-now_hours-args.hour_offset
new_ref = now_ref + timedelta(seconds=3600*args.hour_offset)

# convert drift counter to nanoseconds
drift_ns = drift * DELTA_T_PER_COUNT * 1e9

# fit linear polynomial
sec_rel = hours_rel*3600
drift_sec = drift_ns*1e-9
m,k = polyfit(sec_rel,drift_sec,deg=1)
lin_fit = m*sec_rel + k

print "Relative frequency offset is: {0:+.7} [Hz/Hz] (internal PPS is early by {1:+.7} [ps/s])".format(m,m*1e12)

if not args.noX:
	# plot
	fig = plt.figure()
	ax = plt.axes()
	ax.plot(hours_rel,drift_ns,'o',mfc='b',mec='b',label=args.label)
	ax.plot(hours_rel,lin_fit*1e9,'r--',label='linear fit')
	ax.set_xlabel('Hours since {0}'.format(new_ref.strftime('%H:%M:%S %d %b %Y')))
	ax.set_ylabel('Time between internal and external PPS [ns]')
	ax.legend(loc='best')
	plt.show()
