from struct import pack, unpack
from datetime import datetime, timedelta, tzinfo
from numpy import arange, int32, uint32, uint64, array, zeros, float64, complex64
from vdif import VDIFFrame

use_half_sec_standard = True

from logging import getLogger

MASK3 = 0x07
MASK8 = 0xFF
MASK24 = 2**24 - 1
MASK25 = 2**25 - 1
MASK29 = 2**29 - 1
MASK30 = 2**30 - 1
MASK53 = 2**53 - 1

SDBE_CHAN = 16384
SDBE_VDIF_SIZE = 1056

class DBEFrame(VDIFFrame):
    def __init__(self):
        super(DBEFrame, self).__init__()
        self.bdata = {'p0':{}, 'p1':{}}
        self.b = 0
        self.z = 0
        self.f = 0
        self.c = 0 

    @classmethod
    def from_bin(cls, bin_frame):
        # create our instance
        inst = super(DBEFrame, cls).from_bin(bin_frame)

        # b-engine is in W45 of the VDIF header, found in eud[0,1]
        beng0 = inst.eud[1]
        beng1 = inst.eud[0]
        beng2 = inst.eud_vers
#        inst.c =  beng0      & MASK8
#        inst.f = (beng0>>8)  & MASK8 & 0x07
#        inst.z = (beng0>>16) & MASK8
#        b_bott = (beng0>>24) & MASK8
#        b_mid  = (beng1 & MASK24)*2**8
#        b_top  = (beng2 &  MASK8)*2**32
#        inst.b = b_bott+b_mid+b_top
        B64 = beng2*(2**56) + beng1*(2 **32) + beng0
        inst.s = (B64>>40)&MASK24
        inst.u = (B64>>11)&MASK29
        inst.c = (B64)&MASK8
        inst.f = (B64>>8)&MASK3
        inst.B64 = B64
        inst.z = 0 # obsolete
        inst.b = (B64>>11)&MASK53
        
        # data is reordered in 16 by vdif class
        # thus our data order is (p1i3,p1r3,p0i3,p0r3,p1i2...p0r0)
        # and the next four ch   (p1i7,p1r7,p0i6,p0i6,p1i5...p0r4)
        # + .5 to remove dc offset
        p1 = array(inst.data[1::4]+1j*inst.data[0::4])#+.5*(1+1j)
        p0 = array(inst.data[3::4]+1j*inst.data[2::4])#+.5*(1+1j)

        # data is in channel order: 3 2 1 0 7 6 5 4 3 2 1 0...
        ch_start = [3, 2, 1, 0, 7, 6, 5, 4]
        # update @ 11/11: data is in channel order 0 1 2 3 4 5 6 7
        #~ ch_start = [0, 1, 2, 3, 4, 5, 6, 7]
        for ch in range(8):
            inst.bdata['p1']['ch{0}'.format(ch)]={}
            inst.bdata['p0']['ch{0}'.format(ch)]={}
 
            inst.bdata['p1']['ch{0}'.format(ch)]['data']=p1[ch_start[ch]::8]
            inst.bdata['p0']['ch{0}'.format(ch)]['data']=p0[ch_start[ch]::8]

            #~ if inst.c == 66 and inst.f == 1:
                #~ print "max(bdata,c={0},f={1})[p0][{3}] = {2}".format(inst.c,inst.f,inst.bdata['p0']['ch{0}'.format(ch)]['data'].max(),'ch{0}'.format(ch))
                #~ print "min(bdata,c={0},f={1})[p0][{3}] = {2}".format(inst.c,inst.f,inst.bdata['p0']['ch{0}'.format(ch)]['data'].min(),'ch{0}'.format(ch))
                
        
            #~ inst.bdata['p1']['ch{0}'.format(ch)]['freq']=8*(inst.c*8+inst.f)+ch_start[ch]
            #~ inst.bdata['p0']['ch{0}'.format(ch)]['freq']=8*(inst.c*8+inst.f)+ch_start[ch]
            inst.bdata['p1']['ch{0}'.format(ch)]['freq']=8*((inst.c>>1)*16+(inst.c%2)+2*inst.f)+ch#ch_start[ch]
            inst.bdata['p0']['ch{0}'.format(ch)]['freq']=8*((inst.c>>1)*16+(inst.c%2)+2*inst.f)+ch#ch_start[ch]
            #~ print "c:{0}, f:{1} ch{3}-> {2}".format(inst.c,inst.f,inst.bdata['p1']['ch{0}'.format(ch)]['freq'],ch)

        return inst

#~ class BEnginePacket():
    #~ @property
    #~ def fid(self):
        #~ return self._fid

    #~ @property
    #~ def ch(self):
        #~ return self._ch
    
    #~ @property
    #~ def sec(self):
        #~ return self._sec
    
    #~ @property
    #~ def clk(self):
        #~ return self._clk
    
    #~ def __init__(self,dbe_frame)
        #~ self._fid = dbe_frame.f
        #~ self._ch = dbe_frame

class BeeFrame:
    @property
    def spectra(self):
        return self._spectra
    
    def __init__(self,bdata):
        self._spectra = zeros((2,128,16384),dtype=complex64)
    
    def append(self,bdata):
        for p in range(2):
            p_key = 'p{0}'.format(p)
            for ch in range(8):
                ch_key = 'ch{0}'.format(ch)
                f = bdata[p_key][ch_key]['freq']
                self._spectra[p,:,f] = bdata[p_key][ch_key]['data']

class BeeStream:
    @property
    def ref_epoch(self):
        return self._ref_epoch
    
    @property
    def ref_second(self):
        return self._ref_second
    
    @property
    def ref_subsecond(self):
        return self._ref_subsecond
    
    @property
    def frames(self):
        return self._frames
    
    @property
    def keys(self):
        return self._frames.keys()
    
    def __init__(self,vdif):
        # set reference time for start of this stream
        self._ref_epoch = vdif.ref_epoch
        self._ref_second = vdif.s
        if use_half_sec_standard:
            print "WARNING: Using half-second standard"
            self._ref_second *= 2
        self._ref_subsecond = vdif.u/286e6
        # get key for first frame
        k = 0
        # create first frame
        f = BeeFrame(vdif.bdata)
        self._frames = {k:f}
    
    def append(self,vdif):
        k = self.vdif_to_context_key(vdif)
        if k in self.keys:
            self.frames[k].append(vdif.bdata)
        else:
            f = BeeFrame(vdif.bdata)
            self._frames[k] = f
    
    def vdif_to_context_key(self,vdif):
        k = self.vdif_to_key(vdif)
        ck = self.keys
    
    @classmethod
    def vdif_to_key(cls,vdif):
        if use_half_sec_standard:
            return (2*vdif.s,vdif.u)
        return (vdif.s,vdif.u)
    


def read_packets_from_file(filename,n_pkts):
    with open(filename,'rb') as fh:
        n_pkts_read = n_pkts
        bytes_to_read = n_pkts * 1056
        b = fh.read(bytes_to_read)
        bytes_read = len(b)
        if bytes_read < bytes_to_read:
            n_pkts_read = int(bytes_read/1056)
            if n_pkts_read * 1056 < bytes_read:
                print "WARNING: Incomplete packet encountered, trimming {0} garbage bytes at the end".format(bytes_read - n_pkts_read*1056)
                b = b[:n_pkts_read*1056]
            print "INFO: Eof encountered after {0} packets".format(n_pkts_read)
        vdif_list = [None]*n_pkts_read
        for ii in xrange(n_pkts_read):
            vdif_list[ii] = DBEFrame.from_bin(b[ii*1056:(ii+1)*1056])
        return vdif_list

def read_spectra_from_file(filename,n_pkts,spectra=None):
    vdif_list = read_packets_from_file(filename,n_pkts)
    if spectra is None:
        spectra = {}
    s0 = vdif_list[0].s
    u0 = vdif_list[0].u
    f0 = vdif_list[0].f
    for v in vdif_list:
        if v.f != f0:
            continue
        key_diff = vdif_to_diffkey(v,s0,u0)
        if key_diff != 0: 
            print "({0},{1}) --> ({2},{3}): d={4}".format(s0,u0,v.s,v.u,key_diff)
        v_key = vdif_to_key(v)
        s0 = v.s
        u0 = v.u
        if not v_key in spectra.keys():
            spectra[v_key] = zeros((2,128,16384),dtype=complex)
        for p in range(2):
            p_key = 'p{0}'.format(p)
            for ch in range(8):
                ch_key = 'ch{0}'.format(ch)
                f = v.bdata[p_key][ch_key]['freq']
                spectra[v_key][p,:,f] = v.bdata[p_key][ch_key]['data']
    return spectra

def read_spectra_from_file_cf_no_b(filename,n_pkts):
    vdif_list = read_packets_from_file(filename,n_pkts)
    front_trimmed = False
    npkts = 0
    fid_idx = {}
    spectra = []
    for v in vdif_list:
        npkts += 1
        if not front_trimmed:
            if v.c != 0:
                continue
            else: 
                front_trimmed = True
                print "front trimmed {0} packets in total".format(npkts)
        f = v.f
        c = v.c
        if f not in fid_idx.keys():
            fid_idx[f] = {'window':0,'last_cid':c,'npkts':0}
        if c < fid_idx[f]['last_cid']:
            str_before = str(fid_idx[f])
            fid_idx[f]['window'] += 1
            fid_idx[f]['npkts'] = 0
            fid_idx[f]['last_cid'] = c
            str_after = str(fid_idx[f])
            #~ print "update {0} from {1} to {2}: (v.f={3},v.c={3})".format(f,str_before,str_after,f,c)
            print "new B: s = {0:12d} , u = {1:12d}".format(v.s,v.u)
        fid_idx[f]['last_cid'] = c
        fid_idx[f]['npkts'] += 1
        w = fid_idx[f]['window']
        if w >= len(spectra):
            spectra.append(zeros((2,128,16384),dtype=complex))
        for p in range(2):
            p_key = 'p{0}'.format(p)
            for ch in range(8):
                ch_key = 'ch{0}'.format(ch)
                i = v.bdata[p_key][ch_key]['freq']
                try:
                    spectra[w][p,:,i] = v.bdata[p_key][ch_key]['data']
                except IndexError:
                    print "Index error: tried to access spectra[{0}], but len(spectra) = {1}".format(w,len(spectra))
    s = zeros((2,128*len(spectra),16384),dtype=complex)
    for ii in range(len(spectra)):
        s[:,128*ii + arange(128),:] = spectra[ii]
    return s,fid_idx

def spectra_timestamps(spectra):
    keys = spectra.keys()
    t = zeros(len(keys),dtype=float64)
    for (ii,key) in enumerate(keys):
        t[ii] = key_to_timestamp(key)
    return t

def relative_spectra_keys(spectra):
    # the time for one complete B-engine frame
    dt = 32768/16*128/286e6
    t = spectra_timestamps(spectra)
    t0 = t.min()
    idx_sorted = t.argsort()
    return (t[idx_sorted]-t0)/dt

def key_to_timestamp(k):
    t = k[0] + k[1]/286e6
    return t

def vdif_to_diffkey(v,s0,u0):
    du = 262144.0
    tol_u = 1023.0
    wrap_add = 2**29
    max_frames_per_two_second = int(2*286e6/262144) + 1
    if v.s == s0:
        # second counters are equal
        if abs(u0 - v.u) < tol_u:
            # sub-second counters are equal, frames are concurrent
            #~ print "a"
            return 0
        elif v.u > u0:
            # new frame later than reference
            if (v.u - u0)%du > tol_u:
                # new frame cannot appear later and not be close to
                # an integer number of frames later, error
                print "ERROR: v = ({0},{1}), (s0,u0) = ({2},{3}); tol_u = {4}, du = {5}, (v.u - u0)%du = {6}".format(
                    v.s,v.u,s0,u0,tol_u,du,(v.u-u0)%du
                )
                #~ print "b"
                return -1
            else:
                # sub-second difference is within tolerance of an
                # integer number of frames
                #~ print "c"
                return int(round((v.u-u0)/du))
        else:
            # v.u < u0, new frame appears earlier than reference
            if (v.u+wrap_add - u0)%du > tol_u:
                # unwrapped new frame cannot appear later and not be 
                # close to an integer number of frames later, error
                print "ERROR: v = ({0},{1}), (s0,u0) = ({2},{3}); tol_u = {4}, du = {5}, (v.u+wrap_add - u0)%du = {6}".format(
                    v.s,v.u,s0,u0,tol_u,du,(v.u+wrap_add - u0)%du
                )
                #~ print "d"
                return -1
            else:
                # unwrapped sub-second difference is within tolerance of 
                # an integer number of frames
                #~ print "e"
                return int(round((v.u+wrap_add - u0)/du))
    elif v.s > s0:
        # new frame is in next second, count number of frames into new
        # second (assume reference was at last frame in old second)
        #~ print "f"
        return int(v.u / du) + 1
    else:
        # if new frame is in previous second, error
        #~ print "g"
        return -1

def vdif_to_key(v):
    return (v.s,v.u)
