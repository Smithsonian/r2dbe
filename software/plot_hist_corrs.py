import swarm
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import argparse
import logging
import corr

def nanmean(x,axis=0):
    s    = np.nansum(x,axis=axis)
    nel  = np.sum(np.isfinite(x),axis=axis)
    x_nm = s/nel
    return x_nm

# parse the user's command line arguments
parser = argparse.ArgumentParser(description='sdbe histograms and autocorrs')
parser.add_argument('-v', dest='verbose', action='store_true', help='display debugging logs')
#parser.add_argument('-t', dest='thresh', action='store_true', help='get current threshold value')
parser.add_argument('-n', '--frames-to-check', dest='frames_to_check', default=-1, 
                    type=int, help='number of frames (from the beginning) to check (default: all)')
parser.add_argument('-s', '--sample-rate', dest='sample_rate', default=3328.0, 
                    type=float, help='rate at which the data was sampled in MHz (default: 3328.0)')
parser.add_argument('-gl', dest='gl', default=0, 
                    type=int, help='low limit frequency channel to include in range')
parser.add_argument('-gh', dest='gh', default=16384, 
                    type=int, help='high limit frequency channel to include in range')
parser.add_argument('files', type=str, nargs='+', help='VDIF files with data to correlate')
args = parser.parse_args()

# set up some basic logging
logging.basicConfig(format='%(asctime)-15s - %(message)s')
logger = logging.getLogger('vdif_corr')
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
 
# open all files into a list
logger.debug('opening files for reading')
files = list(open(filename, 'rb') for filename in args.files)

# set pkt_size 
pkt_size = 1056

# set error so no warnings on div by 0

# make array
nchunks = 2
nchan= 2**14
nsamp= 128

# start with 1 bcnt
nbcnt= 1


data = np.zeros((nbcnt,nchunks,nchan,nsamp),dtype=complex)*np.nan
bcnts = []

for file_ in files: 
    # keep track of frame counts
    frame_n = 0
    
    # logger states file
    logger.debug('Now reading file: {0}'.format(file_.name))
    
    # go through every frame
    end_of_frames = False
    while not end_of_frames:

        # read one packet
        pkt = file_.read(pkt_size)

        # check if we reached eof
        if not len(pkt) == pkt_size:
            logger.debug('    Reach eof, {0} frames'.format(frame_n))
            end_of_frames = True
            break

        frame = swarm.DBEFrame.from_bin(pkt)


        # set b index and add b to list if necessary
        try:
            b_ind = bcnts.index(frame.b)
        except:
            # if b count is new, add it to list and extend data array
            b_ind = len(bcnts)
            bcnts.append(frame.b)
            data=np.append(data,np.nan*np.zeros((nbcnt,nchunks,nchan,nsamp)),axis=0)

            logger.debug('    Adding new b count: {0}'.format(frame.b))
 

        # get running histogram values
        # data is broken into 3 layers
        for p in frame.bdata.keys():
            for ch in frame.bdata[p].keys():
                 # get frequency index
                 f_ind = frame.bdata[p][ch]['freq']
                 # check if guardband by frequency index
                 if p=='p0':
                      p_ind=0
                 else:
                      p_ind=1
                
                 data[b_ind,p_ind,f_ind,:]=frame.bdata[p][ch]['data']
 

        # exit if we've check all requested frames
        if frame_n == args.frames_to_check:
             end_of_frames = True
             logger.debug('    Finished {0} of {1} frames'.format(frame_n,frames_to_check))
        frame_n+=1


# at this point, array is finished.

# get statistics, per channel
nbins=4
vals = [-1.5,-0.5,0.5,1.5]
ch_occur = np.zeros((nbins,nchunks,nchan))

# find occurances, sum total of times -1.5 occurs in any bcount, at any time sample
# preserves separation by pol, by bins (states), and combines real and complex values as separate 2 bit samples
for (v,ind) in zip(vals,range(4)):
    ch_occur[ind]=(np.sum(np.sum(data.real==v,axis=0),axis=2)+np.sum(np.sum(data.imag==v,axis=0),axis=2))

# now turn occurances into percentages by sum over 0 axis (bins aka states)
s = np.sum(ch_occur,axis=0)

# add dimension
np.expand_dims(s,axis=0)

s = np.tile(s,(4,1,1))

# produces warning, s is sometimes 0, so get divide by 0.  However, ch_occur 
with np.errstate(invalid='ignore'):
    ch_hist = np.divide(ch_occur,s)*100



# now plot ch_hist as 2 (pol0,pol1) 2d (state counts v channels) 
plt.figure(figsize=(19,6))

p_h = 0.4
p_w = 0.62
p_l = 0.05
p_b = 0.1
p_buff = 0.05

ax_p = [[p_l,p_b+p_h+p_buff,p_w,p_h],[p_l,p_b,p_w,p_h]]

chunks = ['Phase Sum Chunk 0','Phase Sum Chunk 1']
#if args.thresh:
#    thresh = [' old thresh: ',' new thresh: Tn, T0, Tp: ']
#    sdbe = corr.katcp_wrapper.FpgaClient('roach2-09')
#    sdbe.wait_connected()
#
#    th = sdbe.read_int('quantize_0_thresh')
#    th_used = (th >> 12) & 0x1
#    if th_used:
#        tn = (th & 0xf) - 16    
#        t0 = (th >> 4) & 0xf    
#        tp = (th >> 8) & 0xf    
#        chunks[1]=chunks[1]+', Daves Thresh (tn,t0,tp): ({0},{1},{2})'.format(tn,t0,tp)
#    else:
#        t = (th >> 1) & 0x7f     
#        chunks[1]=chunks[1]+', Old Thresh T: {0}'.format(t)

for p in range(2):
    y = ch_hist[:,p,:]

    # create a masked array, so i can plot nans as masked
    xm = np.ma.array(y, mask=np.isnan(y))
     
    cmap=matplotlib.cm.jet
   
    #cmap.set_bad('w',1.) # set nans white
    cmap.set_bad('k',1.)  # set nans black
   
    ax = plt.axes(ax_p[p])
    ax.imshow(xm,extent=[0,16384,0,1], aspect='auto',cmap=cmap,interpolation='nearest',vmin=0,vmax=100)
    ax.set_yticks([0.125,0.375,0.625,0.875])
    ax.set_yticklabels(['+ +','+ -','- +','- -'])

    if p==0:
        ax.set_xticks([])
        ax.set_xticklabels([])
    else:
        plt.xlabel('channel number')

    plt.ylabel('state')
    plt.title('{0}'.format(chunks[p]))
    ax.annotate('',xy=(float(args.gl)/2**14,0.5),xytext=(float(args.gh)/2**14,0.5),xycoords='axes fraction',textcoords='axes fraction',arrowprops=dict(arrowstyle='<->',linewidth=2,color='white'))


p_wi = 0.7-p_buff-p_w
p_hbuff = 0.0
ax_ideal = [[p_l+p_w+p_hbuff,p_b+p_h+p_buff,p_wi,p_h],[p_l+p_w+p_hbuff,p_b,p_wi,p_h]]

xperfect = np.expand_dims(np.array([16,32,32,16]),axis=1)    
for p in range(2):
    ax = plt.axes(ax_ideal[p])
    ax.imshow(xperfect,extent=[0,1,0,4],aspect='auto',vmin=0,vmax=100,interpolation='nearest')
    ax.set_xticks([])
    ax.set_xticklabels([])
    ax.set_yticks([])
    ax.set_yticklabels([])
    ax.yaxis.set_label_position('right')
    ax.set_ylabel('ideal',rotation=270)



p_wh = 0.2
p_hbuff = 0.03
ax_hist = [[p_l+p_w+p_hbuff+p_wi,p_b+p_h+p_buff,p_wh,p_h],[p_l+p_w+p_hbuff+p_wi,p_b,p_wh,p_h]]
for p in range(2):
    ax = plt.axes(ax_hist[p])
    x = ch_hist[:,p,:]

    x_mean=nanmean(x[:,args.gl:args.gh],axis=1)

    plt.plot(np.hstack(([0],np.flipud(x_mean),[0],[0])),[-3,-2,-1,0,1,2,3],drawstyle='steps',label='mean over band')
    plt.plot([0,16,32,32,16,0,0],[-3,-2,-1,0,1,2,3],color=(0.7,0.7,0.7),drawstyle='steps',linestyle='--',label='ideal')
    plt.xlim([0,100])
    plt.ylim([-2,2])
    plt.grid()
    if p==0:
        ax.set_xticklabels([])
    else:
        ax.set_xlabel('state count (%)')
    ax.set_yticklabels([])
    plt.title('Mean ch {0}-{1}'.format(args.gl,args.gh))
    plt.legend()


## now new figure for correlation
plt.figure(figsize=(19,6))

# data is bcounts, by n chunks (2), by nchans (16384), by nsamps(128)
# mult by complex conj and sum over nsamps

data_sq = data*np.conj(data)
data_cr = data[:,0,:,:]*np.conj(data[:,1,:,:])

# now sum over all bcounts, and all samples
data_auto = nanmean(nanmean(data_sq,axis=3),axis=0)
data_cross= nanmean(nanmean(data_cr,axis=2),axis=0)

N = 2**14
k = np.arange(N)
Fs = args.sample_rate # MHz
freq = k*Fs/2/N

ax_corrs = [[0.05,0.1+0.25,0.9,0.55],[0.05,0.1,0.9,0.2]]

ax = plt.axes(ax_corrs[0])
plt.plot(freq,10*np.log10(np.abs(data_auto[0])),'.',label='p0xp0')
plt.plot(freq,10*np.log10(np.abs(data_auto[1])),'.',label='p1xp1')
plt.plot(freq,10*np.log10(np.abs(data_cross)),'k.',label='p0xp1')
plt.grid()
plt.ylabel('Power (dB rel)')
ax.set_xticklabels([])
plt.xlim([0,args.sample_rate/2])
plt.ylim([-10,5])
plt.title('Autos and Cross Corr Log Mag')
plt.legend()


ax = plt.axes(ax_corrs[1])
plt.plot(freq,np.angle(data_cross),'kx')
plt.ylim([-np.pi,np.pi])
plt.xlim([0,3328./2])
plt.ylabel('Phase (rad)')
plt.xlabel('Frequency (MHz)')
plt.title('Angle of Cross')
plt.grid()


plt.show()




