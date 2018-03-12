from struct import pack, unpack
from datetime import datetime, timedelta, tzinfo
from numpy import arange, concatenate, int32, uint32, uint64, array, zeros, float64, complex64, roll
from vdif import VDIFFrame

use_half_sec_standard = True

from logging import getLogger

MASK3 = 0x07
MASK8 = 0xFF
MASK24 = 2**24 - 1
MASK25 = 2**25 - 1
MASK29 = 2**29 - 1
MASK30 = 2**30 - 1
MASK32 = 2**32 - 1
MASK53 = 2**53 - 1

SDBE_CHAN = 16384
SDBE_VDIF_SIZE = 1056

class MaxIntegerTimeDiff(Exception):
	pass

class DBEFrame(VDIFFrame):
    def __init__(self):
        super(DBEFrame, self).__init__()
        self.bdata = {'p0':{}, 'p1':{}}
        self.b = 0
        self.z = 0
        self.f = 0
        self.c = 0 

    @classmethod
    def from_bin(cls, bin_frame, roll_by=0):
        # create our instance
        inst = super(DBEFrame, cls).from_bin(bin_frame)

        #### UPDATE, use raw binary data for B-eng header ####
        beng_hdr_0 = unpack('<I',bin_frame[16:20])[0]
        beng_hdr_1 = unpack('<I',bin_frame[20:24])[0]
        beng_hdr = (uint64(beng_hdr_0)<<uint64(32)) + uint64(beng_hdr_1)
        #~ print "0x{0:08x}".format(beng_hdr)
        inst.c = int32((beng_hdr>>uint64(0)) & uint64(MASK8))
        inst.c = ((inst.c + 0) % 256)
        inst.f = int32((beng_hdr>>uint64(8)) & uint64(MASK3))
        inst.u = int32((beng_hdr>>uint64(11)) & uint64(MASK29))
        inst.s = int32((beng_hdr>>uint64(40)) & uint64(MASK24))
        inst.z = int32(0)
        
        #### UPDATE, vvv this is old
        #~ # b-engine is in W45 of the VDIF header, found in eud[0,1]
        #~ beng0 = inst.eud[1]
        #~ beng1 = inst.eud[0]
        #~ beng2 = inst.eud_vers
#~ #        inst.c =  beng0      & MASK8
#~ #        inst.f = (beng0>>8)  & MASK8 & 0x07
#~ #        inst.z = (beng0>>16) & MASK8
#~ #        b_bott = (beng0>>24) & MASK8
#~ #        b_mid  = (beng1 & MASK24)*2**8
#~ #        b_top  = (beng2 &  MASK8)*2**32
#~ #        inst.b = b_bott+b_mid+b_top

        #~ B64 = beng2*(2**56) + (beng1*(2 **32) & MASK24) + beng0
        #~ inst.s = (B64>>40)&MASK24
        #~ inst.u = (B64>>11)&MASK29
        #~ inst.c = (B64)&MASK8
        #~ inst.f = (B64>>8)&MASK3
        #~ inst.B64 = B64
        #~ inst.z = 0 # obsolete
        #~ inst.b = (B64>>11)&MASK53
        #### UPDATE, ^^^ this is old
        
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
 
            inst.bdata['p1']['ch{0}'.format(ch)]['data']=roll(p1[ch_start[ch]::8],roll_by)
            inst.bdata['p0']['ch{0}'.format(ch)]['data']=roll(p0[ch_start[ch]::8],roll_by)

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
    

def channel_index_by_fid(fid):
    idx_0 = 16*fid+arange(0,16384-128,128)
    idx = idx_0
    for ii in range(1,16):
        idx = concatenate((idx,idx_0+ii))
    idx.sort()
    return idx

def read_bytes_from_file(filename,n_pkts,skip_pkts=0):
    with open(filename,'rb') as fh:
        if skip_pkts > 0:
            fh.seek(skip_pkts*1056)
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
        return n_pkts_read, b

def read_packets_from_file(filename,n_pkts,skip_pkts=0):
    n_pkts_read,b = read_bytes_from_file(filename,n_pkts,skip_pkts=skip_pkts)
    vdif_list = [None]*n_pkts_read
    for ii in xrange(n_pkts_read):
        vdif_list[ii] = DBEFrame.from_bin(b[ii*1056:(ii+1)*1056],roll_by=0)#(128-70))
    return vdif_list

def read_packets_from_bytes(b,n_pkts_read):
    vdif_list = [None]*n_pkts_read
    for ii in xrange(n_pkts_read):
        vdif_list[ii] = DBEFrame.from_bin(b[ii*1056:(ii+1)*1056],roll_by=0)#(128-70))
    return vdif_list

def read_spectra_from_file(filename,n_pkts,spectra=None,skip_pkts=0,f0=None):
    vdif_list = read_packets_from_file(filename,n_pkts,skip_pkts=skip_pkts)
    if spectra is None:
        spectra = {}
    v0 = vdif_list[0]
    s0 = v0.s
    u0 = v0.u
    if f0 is None:
        f0 = v0.f
    key_list = []
    for v in vdif_list:
        if v.f != f0:
            #~ print "alternate"
            continue
        key_diff = diffkey(vdif_to_key(v),vdif_to_key(v0))
        v0 = v
        if key_diff != 0: 
            print "({0},{1}) --> ({2},{3}): d={4} (f0={5},f={6})".format(v0.s,v0.u,v.s,v.u,key_diff,f0,v.f)
            key_list.append(v_key)
        v_key = vdif_to_key(v)
        #~ print "s = {0}, u = {1}, f = {2}, c = {3}".format(v.s,v.u,v.f,v.c)
        if not v_key in spectra.keys():
            spectra[v_key] = zeros((2,128,16384),dtype=complex)
        for p in range(2):
            p_key = 'p{0}'.format(p)
            for ch in range(8):
                ch_key = 'ch{0}'.format(ch)
                f = v.bdata[p_key][ch_key]['freq']
                spectra[v_key][p,:,f] = v.bdata[p_key][ch_key]['data']
    if len(spectra.keys()) == 0:
        print "WARNING: no packets found for given FID={0}".format(f0)
    return spectra,key_list

def read_stream_from_vdif_list(vdif_list,n_pkts,skip_pkts=0,ref_time=None,stream=None):
    if stream is None:
        stream = {}
    front_trimmed = True
    if ref_time is None:
        front_trimmed = False
    npkts = 0
    warned_packet_timestamp_earlier_by_more_than_one = False
    printed_first_timestamp = {}
    for v in vdif_list:
        if not front_trimmed:
            if v.c != 0 or v.invalid_data:
                npkts += 1
                continue
            else: 
                front_trimmed = True
                ref_time = IntegerTime.from_vdif(v)
                if npkts > 0:
                    print "front trimmed {0} packets in total".format(npkts)
        t = IntegerTime.from_vdif(v)
        #~ print "v.s = {0}, v.u = {1}, f = {2}, c = {3}".format(v.s,v.u,v.f,v.c)
        #~ print "t={0}, ref_time={1}".format(t,ref_time)
        try:
            dt = t - ref_time
        except MaxIntegerTimeDiff:
            print "WARNING, MaxIntegerTimeDiff caught: dt = t - ref_time = {0} - {1}".format(t, ref_time)
            continue
        if dt < 0:
            if dt < -1:
                if not warned_packet_timestamp_earlier_by_more_than_one:
                    print "WARNING, packet timestamp earlier than reference time by more than one B-engine frame"
                    print "v.s = {0}, v.u = {1}, f = {2}, c = {3}".format(v.s,v.u,v.f,v.c)
                    print "t={0}, ref_time={1}: dt = ".format(t,ref_time,dt)
                    warned_packet_timestamp_earlier_by_more_than_one = True
            continue
        if not v.f in printed_first_timestamp.keys():
            #~ print "{0}: {1}".format(v.f,t)
            printed_first_timestamp[v.f] = True
        #~ print "t - ref_time = {0} - {1} = {2}".format(t,ref_time,dt)
        #~ print "s = {0}, u = {1}, f = {2}, c = {3}".format(v.s,v.u,v.f,v.c)
        if not dt in stream.keys():
            stream[dt] = zeros((2,128,16384),dtype=complex)
        for p in range(2):
            p_key = 'p{0}'.format(p)
            for ch in range(8):
                ch_key = 'ch{0}'.format(ch)
                f = v.bdata[p_key][ch_key]['freq']
                stream[dt][p,:,f] = v.bdata[p_key][ch_key]['data']
    return stream,ref_time

def read_stream_from_file(filename,n_pkts,skip_pkts=0,ref_time=None,stream=None):
    vdif_list = read_packets_from_file(filename,n_pkts,skip_pkts=skip_pkts)
    return read_stream_from_vdif_list(vdif_list,n_pkts,skip_pkts=skip_pkts,ref_time=ref_time,stream=stream)

def stream_to_spectra(stream):
    k = sorted(stream.keys())
    spectra = zeros((2,128*len(k),16384),dtype=complex)
    prev_key = k[0]-1
    for ii,kk in enumerate(k):
        if kk > prev_key+1:
            print "WARNING, key > prev_key + 1: {0} > {1}+1, aborting".format(kk,prev_key+1)
            break
        spectra[:,ii*128:(ii+1)*128,:] = stream[kk]
        prev_key = kk
    return spectra
    
def read_spectra_from_file_cf_no_b(filename,n_pkts,skip_pkts=0):
    vdif_list = read_packets_from_file(filename,n_pkts,skip_pkts=skip_pkts)
    front_trimmed = False
    npkts = 0
    fid_idx = {}
    spectra = []
    for v in vdif_list:
        if not front_trimmed:
            if v.c != 0 or v.invalid_data:
                npkts += 1
                continue
            else: 
                front_trimmed = True
                #~ if npkts > 0:
                    #~ print "front trimmed {0} packets in total".format(npkts)
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

def diffkey_offset_to_ref(k,k_ref):
    """Compute number of B-engine frames that k1 is offset from reference k0"""
    t = IntegerTime.from_vdif(k)
    t_ref = IntegerTime.from_vdif(k_ref)
    return t - t_ref
    
def diffkey(k,k0):
    s = k[0]
    u = k[1]
    s0 = k0[0]
    u0 = k0[1]
    du = 262144.0
    tol_u = 1023.0
    wrap_add = 286000000
    max_frames_per_two_second = int(2*286e6/262144) + 1
    if s == s0:
        #~ print 1
        # second counters are equal
        if abs(u0 - u) < tol_u:
            #~ print 2# sub-second counters are equal, frames are concurrent
            #~ print "a"
            return 0
        elif u > u0:
            #~ print 3# new frame later than reference
            if (u - u0)%du > tol_u:
                #~ print 4# new frame cannot appear later and not be close to
                # an integer number of frames later, error
                print "ERROR: v = ({0},{1}), (s0,u0) = ({2},{3}); tol_u = {4}, du = {5}, (u - u0)%du = {6}".format(
                    s,u,s0,u0,tol_u,du,(u-u0)%du
                )
                #~ print "b"
                return -1
            else:
                #~ print 5# sub-second difference is within tolerance of an
                # integer number of frames
                #~ print "c"
                return int(round((u-u0)/du))
        else:
            #~ print 6# u < u0, new frame appears earlier than reference
            if (u+wrap_add - u0)%du > tol_u:
                #~ print 7# unwrapped new frame cannot appear later and not be 
                # close to an integer number of frames later, error
                print "ERROR: v = ({0},{1}), (s0,u0) = ({2},{3}); tol_u = {4}, du = {5}, (u+wrap_add - u0)%du = {6}".format(
                    s,u,s0,u0,tol_u,du,(u+wrap_add - u0)%du
                )
                #~ print "d"
                return -1
            else:
                #~ print 8# unwrapped sub-second difference is within tolerance of 
                # an integer number of frames
                #~ print "e"
                return int(round((u+wrap_add - u0)/du))
    elif s > s0:
        #~ print 9# new frame is in next second, count number of frames into new
        # second (assume reference was at last frame in old second)
        #~ print "f"
        return int(u / du) + 1
    else:
        #~ print 10# if new frame is in previous second, error
        #~ print "g"
        return -1

class IntegerTime:
    def __init__(self,sec=0,clk=0,vdif_sec=0,vdif_dfm=0):
        self.sec = sec
        self.clk = clk
        self.vdif_sec = vdif_sec
        self.vdif_dfm = vdif_dfm
    
    @property
    def real_time(self):
        return self.sec + 1.0*self.clk/self.wrap_clk
    
    @property
    def tol_clk(self):
        return self.step_clk / 4
    
    @property
    def wrap_clk(self):
        return 286000000
    
    @property
    def step_clk(self):
        return 262144
    
    @property
    def max_diff(self):
        return 10000
    
    @classmethod
    def from_vdif(cls,vdif):
        inst = cls(sec=vdif.s, clk=vdif.u, vdif_sec=vdif.secs_since_epoch, vdif_dfm=vdif.data_frame)
        return inst
    
    def advance(self, by=1):
        self.clk += self.step_clk*by
        if self.clk > self.wrap_clk:
            self.sec += self.clk / self.wrap_clk
            self.clk = self.clk % self.wrap_clk
    
    def __str__(self):
        return "{0}+{1}".format(self.sec,self.clk)
    
    def __add__(self, other):
        approach = IntegerTime(sec=self.sec,clk=other.clk)
        approach.sec += other.sec
        approach.clk += other.clk
        if approach.clk > approach.wrap_clk:
            approach.sec += approach.clk / approach.wrap_clk
            approach.clk = approach.clk % approach.wrap_clk
        return approach
    
    def __sub__(self, other):
        result = 0
        if self == other:
            return 0
        if self > other:
            #~ print "self > other =", self > other
            approach = IntegerTime(sec=other.sec,clk=other.clk)
            #~ print approach
            while self > approach:
                result += 1
                if result > approach.max_diff:
                    #~ print self, other
                    #~ print "self > other =", self > other
                    raise MaxIntegerTimeDiff("Maximum IntegerTime difference reached")
                approach.clk += approach.step_clk
                #~ print approach
                if approach.clk > approach.wrap_clk:
                    approach.sec += approach.clk / approach.wrap_clk
                    approach.clk = approach.clk % approach.wrap_clk
                #~ print approach
            #~ print "self > approach: {0} > {1}".format(self,approach)
            return result
        return -(other - self)
    
    def __lt__(self, other):
        if self.sec < other.sec:
            return True
        if self.sec > other.sec:
            return False
        if self.clk < other.clk and abs(self.clk - other.clk) > self.tol_clk:
            return True
        return False
    
    def __le__(self, other):
        if self < other or self == other:
            return True
        return False
    
    def __eq__(self, other):
        if self.sec == other.sec and abs(self.clk - other.clk) < self.tol_clk:
            return True
        return False
    
    def __ne__(self, other):
        return not self == other
    
    def __ge__(self, other):
        return not self < other
    
    def __gt__(self, other):
        return not self <= other
    
def vdif_to_key(v):
    return (v.s,v.u)
