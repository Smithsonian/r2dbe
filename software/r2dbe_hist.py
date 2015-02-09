import corr
import struct
from numpy import int32, uint32, array, zeros, arange
import r2dbe_snaps

import matplotlib
import pylab
import matplotlib.mlab as mlab

# connect to r2dbe running the bitcode already
roach2 = corr.katcp_wrapper.FpgaClient('r2dbe-1')
roach2.wait_connected()

# read threshold values
th0 = roach2.read_int('r2dbe_quantize_0_thresh')
th1 = roach2.read_int('r2dbe_quantize_1_thresh')

# get data from all snapshots
x=corr.snap.snapshots_get([roach2,roach2,roach2,roach2],
                          ['r2dbe_snap_8bit_0_data',
                           'r2dbe_snap_8bit_1_data',
                           'r2dbe_snap_2bit_0_data',
                           'r2dbe_snap_2bit_1_data'])

L = x['lengths'][0]
print x['lengths']
#unpack the 8 bit data
x0_8 = r2dbe_snaps.data_from_snap_8bit(x['data'][0],L) 
x1_8 = r2dbe_snaps.data_from_snap_8bit(x['data'][1],L)

x0_2 = r2dbe_snaps.data_from_snap_2bit(x['data'][2],L) 
x1_2 = r2dbe_snaps.data_from_snap_2bit(x['data'][3],L)
        
print len(x0_8)
print len(x0_2)

# now have x0_8, x0_2, and the IF1s, now histograms

bins8 = arange(-128.5,128.5,1)
bins2 = arange(-2.5,2.5,1)

ylim_8 = 0.06
ylim_2 = 0.5

lim0_1 = -th0-0.5
lim0_2 = -0.5
lim0_3 = th0-0.5
lim1_1 = -th1-0.5
lim1_2 = -0.5
lim1_3 = th1-0.5

# create ideal gaussian shape for 8 bits
th_id = 32 # ideal thresh
g = mlab.normpdf(bins8, 0, th_id)


pylab.subplot(2,2,1)
pylab.plot((lim0_1, lim0_1),(0, 1),'k--')
pylab.plot((lim0_2, lim0_2),(0, 1),'k--')
pylab.plot((lim0_3, lim0_3),(0, 1),'k--')
pylab.plot(bins8,g,'gray', linewidth=1)
pylab.hist(  x0_8, 
             bins8, 
             normed=1, 
             facecolor='blue', 
             alpha=0.9, 
             histtype='stepfilled')
pylab.xlim(-129,128)
pylab.xlabel('bin')
pylab.ylim(0,ylim_8)
pylab.ylabel('Frequency')
pylab.title('IF0: 8-bit Data Hist')
pylab.annotate('th={0}'.format(th0),xy=(th0+5,0.05))
pylab.annotate('ideal',xy=(bins8[175],g[175]),xytext=(75,0.01),arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
if th0<th_id-3:
    pylab.annotate('low pow', xy=(th0+5,0.045))
elif th0>th_id+3:
    pylab.annotate('high pow', xy=(th0+5,0.045))

pylab.grid()

pylab.subplot(2,2,2)
pylab.plot((lim1_1, lim0_1),(0, 1),'k--')
pylab.plot((lim1_2, lim0_2),(0, 1),'k--')
pylab.plot((lim1_3, lim0_3),(0, 1),'k--')
pylab.plot(bins8,g,'gray', linewidth=1)
pylab.hist(  x1_8, 
             bins8, 
             normed=1, 
             facecolor='green', 
             alpha=0.75, 
             histtype='stepfilled')
pylab.xlim(-129,128)
pylab.xlabel('bin')
pylab.ylim(0,ylim_8)
pylab.ylabel('Frequency')
pylab.title('IF1: 8-bit Data Hist')
pylab.annotate('th={0}'.format(th1),xy=(th1+5,0.05))
pylab.annotate('ideal',xy=(bins8[175],g[175]),xytext=(75,0.01),arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
if th1<th_id-3:
    pylab.annotate('low pow', xy=(th1+5,0.045))
elif th1>th_id+3:
    pylab.annotate('high pow', xy=(th1+5,0.045))
pylab.grid()


pylab.subplot(2,2,3)
n = pylab.hist( x0_2, 
                bins2, 
                normed=1, 
                facecolor='blue', 
                alpha=0.75, 
                histtype='stepfilled')
for k in range(4):
    pylab.annotate('{0:.1%}'.format(n[0][k]),xy=(n[1][k]+0.2,0.02))
pylab.xlim(-3,2)
pylab.xlabel('bin')
pylab.ylim(0,ylim_2)
pylab.ylabel('Frequency')
pylab.title('IF0: 2-bit Data Hist')
pylab.grid()

pylab.subplot(2,2,4)
n = pylab.hist( x1_2, 
                bins2, 
                normed=1, 
                facecolor='green', 
                alpha=0.75, 
                histtype='stepfilled')
for k in range(4):
    pylab.annotate('{0:.1%}'.format(n[0][k]),xy=(n[1][k]+0.2,0.02))
pylab.xlim(-3,2)
pylab.xlabel('bin')
pylab.ylim(0,ylim_2)
pylab.ylabel('Frequency')
pylab.title('IF1: 2-bit Data Hist')
pylab.grid()

#pylab.savefig('/home/oper/if0_8.pdf')
pylab.show()
