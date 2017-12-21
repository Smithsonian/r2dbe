#!/usr/bin/python
#
# Usage: quickspecR2DBE.py [num of time integrations]
#
# Grabs ADC snapshots, time integrates them, and plots
# the spectrum of each input IF.
#

import adc5g, corr
from pylab import plot, show, title, xlabel, ylabel, subplot, gcf, xlim, semilogy
import pylab
import numpy
import sys

import argparse
parser = argparse.ArgumentParser(description='Set 2-bit quantization threshold')
parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
    help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
parser.add_argument('-v','--verbose',action='count',
    help="control verbosity, use multiple times for more detailed output")
parser.add_argument('host',metavar='R2DBE',type=str,nargs='?',default='r2dbe-1',
    help="hostname or ip address of r2dbe (default is 'r2dbe-1')")
args = parser.parse_args()

try:
    import matplotlib as mpl
    # Must disable path simplifcation to allow fringe peaks to be seen even in dense plots
    # http://stackoverflow.com/questions/15795720/matplotlib-major-display-issue-with-dense-data-sets
    mpl.rcParams['path.simplify'] = False
except:
    pass

def plotSpectrum(y,Fs,tstr):
	"""
	Plots a Single-Sided Amplitude Spectrum of y(t)
	"""
	n = len(y) # length of the signal
	k = numpy.arange(n)
	T = n/Fs
	frq = 1e-6 * k/T # two sides frequency range
	frq = frq[range(n/2)] # one side frequency range

	Y = numpy.fft.fft(y)/n # fft computing and normalization
	Y = Y[range(n/2)]
 
	#semilogy(frq,abs(Y),'k')
	plot(frq,abs(Y),'k')
	xlim([0,frq[-1]])	

	xlabel('Freq (MHz)')
	ylabel('log|Y(freq)|')
	title(tstr)

print 'Connecting...'
# connect to roach2
roach2 = corr.katcp_wrapper.FpgaClient(args.host)
if not roach2.wait_connected(timeout=args.timeout):
    msg = "Could not establish connection to '{0}' within {1} seconds, aborting".format(
        args.host,args.timeout)
    raise RuntimeError(msg)


Fs = 2*2048e6 # R2DBE sampling freq
Nif    = 2  # R2DBE typically 2 IFs
Ninteg = 1  # integrate this many ADC snapshots
if len(sys.argv)==2:
	Ninteg = int(sys.argv[1])

Nsamp = [0]*Nif
Lfft  = [0]*Nif
data  = [None]*Nif

for ii in range(Ninteg):
	for ifnr in range(Nif):
	        data8 = adc5g.get_snapshot(roach2, 'r2dbe_snap_8bit_%d_data' % (ifnr))
		Lfft[ifnr] = len(data8)
		Nsamp[ifnr] = Nsamp[ifnr] + Lfft[ifnr]
		if data[ifnr]==None:
			data[ifnr] = data8
		else:
			# data[ifnr] = data[ifnr] + data8
			data[ifnr] = [data[ifnr][n]+data8[n] for n in range(len(data8))]
	        print '   Int %d/%d : ADC %d snapshot of 8-bit data, got %d samples' % (ii+1,Ninteg,ifnr,len(data8))

for ifnr in range(Nif):
	subplot(Nif,1,(ifnr+1))
	plotSpectrum(data[ifnr], Fs, 'ADC %d' % (ifnr))
gcf().set_facecolor('white')
show()

