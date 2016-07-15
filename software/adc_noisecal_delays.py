import corr
import struct
import numpy

import matplotlib
matplotlib.use('Agg')

import pylab

import argparse
parser = argparse.ArgumentParser(description='Set 2-bit quantization threshold')
parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
    help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
parser.add_argument('-v','--verbose',action='count',
    help="control verbosity, use multiple times for more detailed output")
parser.add_argument('host',metavar='R2DBE',type=str,nargs='?',default='r2dbe-1',
    help="hostname or ip address of r2dbe (default is 'r2dbe-1')")
args = parser.parse_args()

# connect to roach2
roach2 = corr.katcp_wrapper.FpgaClient(args.host)
if not roach2.wait_connected(timeout=args.timeout):
    msg = "Could not establish connection to '{0}' within {1} seconds, aborting".format(
        args.host,args.timeout)
    raise RuntimeError(msg)

# connect to digital noise
execfile('switch_set_noise.py')

# start with no delay settings
roach2.write_int('r2dbe_delay_0_samples',0)
roach2.write_int('r2dbe_delay_1_samples',0)


# grab 8bit snapshot data from both if0 and if1
x=corr.snap.snapshots_get([roach2,roach2],['r2dbe_snap_8bit_0_data','r2dbe_snap_8bit_1_data'])

# note, this snapshots_get function grabs data from BRAMs that fill up with a bit of 8 bit data on each PPS tick

# unpack the x data
y0 = struct.unpack('>{0}b'.format(x['lengths'][0]),x['data'][0])
y1 = struct.unpack('>{0}b'.format(x['lengths'][1]),x['data'][1])

# shorten the arrays
y0 = y0[:1000]
y1 = y1[:1000]

# correlate data and look for lag
z = numpy.correlate(y0,y1,"full")

L = len(y0)
lags = numpy.arange(-L+1,L,1)

# find maximum value of cross-corr
ind = z.argmax()
dly = lags[ind]



# plot and save lag data
pylab.figure()
pylab.plot(lags,z)
pylab.xlim(-100,100)
pylab.title('Cross Corr Lags, w/o correction')
pylab.annotate('Delay (lags): {0}'.format(dly), 
                   xy=(dly, z[ind]), xytext=(0.8, 0.8), textcoords='axes fraction', backgroundcolor='white',
                   arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
pylab.xlabel('Delay (lags)')
pylab.savefig('/home/oper/cross_lags.pdf')


# apply delay in the roach2 board
if dly<0: #if dly is negative, then if0 needs to be delayed by dly
   roach2.write_int('r2dbe_delay_0_samples',abs(dly))
else:
   roach2.write_int('r2dbe_delay_1_samples',abs(dly))


# plot and save fixed lag data
x=corr.snap.snapshots_get([roach2,roach2],['r2dbe_snap_8bit_0_data','r2dbe_snap_8bit_1_data'])
y0 = struct.unpack('>{0}b'.format(x['lengths'][0]),x['data'][0])
y1 = struct.unpack('>{0}b'.format(x['lengths'][1]),x['data'][1])
y0 = y0[:1000]
y1 = y1[:1000]
z = numpy.correlate(y0,y1,"full")
L = len(y0)
lags = numpy.arange(-L+1,L,1)
ind = z.argmax()
dly = lags[ind]

pylab.figure()
pylab.plot(lags,z)
pylab.xlim(-100,100)
pylab.title('Cross Corr Lags, after fix')
pylab.annotate('Delay (lags): {0}'.format(dly), 
                   xy=(dly, z[ind]), xytext=(0.8, 0.8), textcoords='axes fraction', backgroundcolor='white',
                   arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
pylab.xlabel('Delay (lags)')
pylab.savefig('/home/oper/cross_lags_fixed.pdf')

   
# set noise switch back to IF
execfile('switch_set_IF.py')




