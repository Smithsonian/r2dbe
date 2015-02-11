import corr
import struct
from numpy import int32, uint32, array, zeros, arange, linspace, split, conjugate, log10
from numpy.fft import rfft
from datetime import datetime, timedelta, tzinfo
import r2dbe_snaps
import socket

import matplotlib.pyplot as plt
import matplotlib.mlab as mlab


class UTC(tzinfo):
    """ UTC tzinfo """

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

def r2dbe_datetime(name):

    # now how many usecs per frame
    usecs_per_frame = 8
    
    # get ref epoch and data_frame
    secs_since_ep = roach2.read_int('r2dbe_vdif_'+name+'_hdr_w0_sec_ref_ep')    
    ref_epoch     = roach2.read_int('r2dbe_vdif_'+name+'_hdr_w1_ref_ep')    

    # get the date
    date = datetime(year = 2000 + ref_epoch/2,
                    month = 1 + (ref_epoch & 1) * 6,
                    day = 1, tzinfo=UTC())

    # get the seconds from the start of the day
    secs = timedelta(seconds = secs_since_ep)

    return date + secs

def get_data():
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
    #unpack the 8 bit data
    x0_8 = r2dbe_snaps.data_from_snap_8bit(x['data'][0],L) 
    x1_8 = r2dbe_snaps.data_from_snap_8bit(x['data'][1],L)
    
    x0_2 = r2dbe_snaps.data_from_snap_2bit(x['data'][2],L) 
    x1_2 = r2dbe_snaps.data_from_snap_2bit(x['data'][3],L)

    clk = roach2.est_brd_clk()            
    gps_cnt = roach2.read_int('r2dbe_onepps_gps_pps_cnt')            
    msr_cnt = roach2.read_int('r2dbe_onepps_msr_pps_cnt')            
    offset_samp = roach2.read_int('r2dbe_onepps_offset')            
    offset_ns   = float(offset_samp)/clk*1e3
    

    pol_chr = ['L (or X)', 'R (or Y)']
    pol0num = roach2.read_uint('r2dbe_vdif_0_hdr_w4') & 0x1           
    pol1num = roach2.read_uint('r2dbe_vdif_1_hdr_w4') & 0x1           
    pol0    = pol_chr[pol0num]
    pol1    = pol_chr[pol1num]
    

    st0num  = roach2.read_uint('r2dbe_vdif_0_hdr_w3_station_id')            
    st1num  = roach2.read_uint('r2dbe_vdif_1_hdr_w3_station_id')            
    st0     = ''.join([chr((st0num>>8) & 0xff), chr(st0num & 0xff)])
    st1     = ''.join([chr((st1num>>8) & 0xff), chr(st1num & 0xff)])

    return x0_8, x1_8, x0_2, x1_2, th0, th1, clk, gps_cnt, msr_cnt, offset_samp,offset_ns, pol0, pol1, st0, st1

def plot_data():
    # get data
    x0_8, x1_8, x0_2, x1_2, th0, th1, clk, gps_cnt, msr_cnt, offset_samp, offset_ns, pol0, pol1, st0, st1 = get_data()
    
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

    plt.clf()
    plt.subplot(2,4,1)
    plt.plot((lim0_1, lim0_1),(0, 1),'k--')
    plt.plot((lim0_2, lim0_2),(0, 1),'k--')
    plt.plot((lim0_3, lim0_3),(0, 1),'k--')
    plt.plot(bins8,g,'gray', linewidth=1)
    plt.hist(  x0_8, 
                 bins8, 
                 normed=1, 
                 facecolor='blue', 
                 alpha=0.9, 
                 histtype='stepfilled')
    plt.xlim(-129,128)
    plt.xlabel('bin')
    plt.ylim(0,ylim_8)
    plt.ylabel('Frequency')
    plt.title('IF0: 8-bit Data Hist')
    plt.annotate('th={0}'.format(th0),xy=(th0+5,0.05))
    plt.annotate('ideal',xy=(bins8[175],g[175]),xytext=(75,0.01),arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
    if th0<th_id-3:
        plt.annotate('low pow', xy=(th0+5,0.045))
    elif th0>th_id+3:
        plt.annotate('high pow', xy=(th0+5,0.045))
    
    plt.grid()
    
    plt.subplot(2,4,2)
    plt.plot((lim1_1, lim0_1),(0, 1),'k--')
    plt.plot((lim1_2, lim0_2),(0, 1),'k--')
    plt.plot((lim1_3, lim0_3),(0, 1),'k--')
    plt.plot(bins8,g,'gray', linewidth=1)
    plt.hist(  x1_8, 
                 bins8, 
                 normed=1, 
                 facecolor='green', 
                 alpha=0.75, 
                 histtype='stepfilled')
    plt.xlim(-129,128)
    plt.xlabel('bin')
    plt.ylim(0,ylim_8)
    plt.ylabel('Frequency')
    plt.title('IF1: 8-bit Data Hist')
    plt.annotate('th={0}'.format(th1),xy=(th1+5,0.05))
    plt.annotate('ideal',xy=(bins8[175],g[175]),xytext=(75,0.01),arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
    if th1<th_id-3:
        plt.annotate('low pow', xy=(th1+5,0.045))
    elif th1>th_id+3:
        plt.annotate('high pow', xy=(th1+5,0.045))
    plt.grid()
    
    
    plt.subplot(2,4,5)
    n = plt.hist( x0_2, 
                    bins2, 
                    normed=1, 
                    facecolor='blue', 
                    alpha=0.75, 
                    histtype='stepfilled')
    for k in range(4):
        plt.annotate('{0:.1%}'.format(n[0][k]),xy=(n[1][k]+0.2,0.02))
    plt.xlim(-3,2)
    plt.xlabel('bin')
    plt.ylim(0,ylim_2)
    plt.ylabel('Frequency')
    plt.title('IF0: 2-bit Data Hist')
    plt.grid()
    
    plt.subplot(2,4,6)
    n = plt.hist( x1_2, 
                    bins2, 
                    normed=1, 
                    facecolor='green', 
                    alpha=0.75, 
                    histtype='stepfilled')
    for k in range(4):
        plt.annotate('{0:.1%}'.format(n[0][k]),xy=(n[1][k]+0.2,0.02))
    plt.xlim(-3,2)
    plt.xlabel('bin')
    plt.ylim(0,ylim_2)
    plt.ylabel('Frequency')
    plt.title('IF1: 2-bit Data Hist')
    plt.grid()

    
    # fft
    NFFT = 1024
    freqs = linspace(0.0, 4096/2, num=NFFT/2)
    y0_8 = rfft(split(x0_8, len(x0_8)/NFFT), axis=1)
    Y0_8 = (y0_8 * conjugate(y0_8)).sum(axis=0)

    y1_8 = rfft(split(x1_8, len(x1_8)/NFFT), axis=1)
    Y1_8 = (y1_8 * conjugate(y1_8)).sum(axis=0)

    y0_2 = rfft(split(x0_2, len(x0_2)/NFFT), axis=1)
    Y0_2 = (y0_2 * conjugate(y0_2)).sum(axis=0)

    y1_2 = rfft(split(x1_2, len(x1_2)/NFFT), axis=1)
    Y1_2 = (y1_2 * conjugate(y1_2)).sum(axis=0)
    
    # plot IFs for 8 bit
    plt.subplot(2,4,3)
    plt.step(freqs, 10*log10(abs(Y0_8[:-1])), 'b', label='IF 0')
    plt.step(freqs, 10*log10(abs(Y1_8[:-1])), 'g', label='IF 1')
   
    plt.xlim(0, 2048)
    plt.xlabel('Freq (MHz)')
    plt.ylabel('dB')
    plt.title('Autos 8-bit')
    plt.legend()
    plt.grid()

    plt.subplot(2,4,7)
    plt.step(freqs, 10*log10(abs(Y0_2[:-1])), 'b', label='IF 0')
    plt.step(freqs, 10*log10(abs(Y1_2[:-1])), 'g', label='IF 1')
   
    plt.xlim(0, 2048)
    plt.xlabel('Freq (MHz)')
    plt.ylabel('dB')
    plt.title('Autos 2-bit')
    plt.legend()
    plt.grid()

    # status
    left_lim = 0.02
    plt.subplot(1,4,4)
    plt.annotate('________________________________',
                 xy=(left_lim,0.99))
    plt.annotate('{0}'.format(socket.gethostname()),
                 xy=(left_lim,0.95))
    plt.annotate('________________________________',
                 xy=(left_lim,0.925))
    plt.annotate('IF0: {0}'.format(r2dbe_datetime('0')),
                 xy=(left_lim,0.90))
    plt.annotate('IF1: {0}'.format(r2dbe_datetime('1')),
                 xy=(left_lim,0.85))
    plt.annotate('________________________________',
                 xy=(left_lim,0.80))

    # station ids, polarizations, etc, IF noise box, etc
    plt.annotate('IF0: Pol {0}, station id {1}'.format(pol0,st0),
                 xy=(left_lim,0.75))
    plt.annotate('IF1: Pol {0}, station id {1}'.format(pol1,st1),
                 xy=(left_lim,0.7))
    plt.annotate('________________________________',
                 xy=(left_lim,0.65))

    # status
    plt.annotate('fpga clk rate (est):       {0:.2f} MHz'.format(clk),
                 xy=(left_lim,0.6))
    plt.annotate('gps pps ticks (secs past): {0}'.format(gps_cnt),
                 xy=(left_lim,0.55))
    plt.annotate('msr pps ticks:             {0}'.format(msr_cnt),
                 xy=(left_lim,0.50))
    plt.annotate('gps vs internal offset:    {0} samples'.format(offset_samp),
                 xy=(left_lim,0.45))
    plt.annotate('gps vs internal offset:    {0} ns'.format(offset_ns),
                 xy=(left_lim,0.4))

    plt.xlim(0,1)
    plt.ylim(0,1)
    f = plt.gca()
    f.axes.get_xaxis().set_visible(False)
    f.axes.get_yaxis().set_visible(False)

    #pylab.savefig('/home/oper/if0_8.pdf')
    fig.canvas.draw()
    fig.canvas.manager.window.after(100, plot_data)
    

if __name__ == '__main__':

    # connect to r2dbe running the bitcode already
    roach2 = corr.katcp_wrapper.FpgaClient('r2dbe-1')
    roach2.wait_connected()
   
    # set up plotting 
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    fig.canvas.manager.window.after(100,plot_data)
    plt.show()
    
