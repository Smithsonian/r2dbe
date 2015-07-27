#!/usr/bin/python

from argparse import ArgumentParser
from datetime import datetime, time, timedelta
from numpy import loadtxt, int32, unique, array, polyfit

import matplotlib.pyplot as plt
plt.ion()

DEFAULT_LOG_FILE = '/var/log/r2dbe/maser-drift.log'
VDIF_PKTS_PER_SECOND = 125000
DELTA_T_PER_COUNT = 1/256e6 # drift counter runs on 256 MHz clock

# calculate hours since reference date for plotting help
ref_ref_epoch_date = datetime(2000,1,1,0,0,0)
delta_date = (datetime.utcnow() - ref_ref_epoch_date)
now_hours = int((delta_date.days*24*3600 + delta_date.seconds)/3600)

parser = ArgumentParser(description='Plot drift from maser drift logfile')
parser.add_argument('-v', dest='verbose', help='display debugging logs')
parser.add_argument('-l', dest='label', default='data', help='data label in plot legend')
parser.add_argument('-H', dest='hour_offset', type=int, default=0, help='offset x-axis ticks by this many hours (default is 0, hours since reference is {0})'.format(now_hours))
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

# convert time to hours since start of first epoch (1 Jan 2000)
offset_secs = dict()
for this_epoch in unique(ref_epoch):
  ref_epoch_date = datetime(2000+this_epoch/2,(this_epoch % 2)*6+1,1,0,0,0)
  delta_date = (ref_epoch_date - ref_ref_epoch_date)
  offset_secs[this_epoch] = (delta_date.days*24*3600 + delta_date.seconds)
secs_since_first_epoch = secs_since_epoch + array([offset_secs[re] for re in ref_epoch],dtype=int32)
hours_since_first_epoch = (secs_since_first_epoch + 1.0*data_frame/VDIF_PKTS_PER_SECOND)/3600.0
hours_rel = hours_since_first_epoch-args.hour_offset

# convert drift counter to nanoseconds
drift_ns = drift * DELTA_T_PER_COUNT * 1e9

# fit quadratic polynomial
a,b,c = polyfit(hours_rel,drift_ns,deg=2)
y_fit = a*hours_rel**2 + b*hours_rel + c

print "Relative frequency offset is: {0:+.7} [Hz/Hz]".format(b*1e-9/3600)
print " Relative frequency slope is: {0:+.7} [Hz/Hz/s]".format(a*1e-9/3600)

# plot
fig = plt.figure()
ax = plt.axes()
ax.plot(hours_rel,drift_ns,'o',mfc='b',mec='b',label=args.label)
ax.plot(hours_rel,y_fit,'k-',label='quadratic fit')
ax.set_xlabel('Hours since 00:00:00 1 Jan 2000 - {0}'.format(args.hour_offset))
ax.set_ylabel('Maser second relative to GPS second [ns]')
ax.legend()
plt.show()
