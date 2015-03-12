from struct import pack, unpack
from datetime import datetime, timedelta, tzinfo
from numpy import int32, uint32, uint64, array, zeros
from vdif import VDIFFrame

MASK8 = 0xFF
MASK24 = 0xFFFFFF
MASK40= 0xFFFFFFFFFF

class DBEFrame(VDIFFrame):
    def __init__(self):
        super(DBEFrame, self).__init__()
        self.bdata = {'p0':{}, 'p1':{}}
        self.p0 = {'ch0':array([],dtype=complex),
                   'ch1':array([],dtype=complex),
                   'ch2':array([],dtype=complex),
                   'ch3':array([],dtype=complex),
                   'ch4':array([],dtype=complex),
                   'ch5':array([],dtype=complex),
                   'ch6':array([],dtype=complex),
                   'ch7':array([],dtype=complex)}
        self.p1 = {'ch0':array([],dtype=complex),
                   'ch1':array([],dtype=complex),
                   'ch2':array([],dtype=complex),
                   'ch3':array([],dtype=complex),
                   'ch4':array([],dtype=complex),
                   'ch5':array([],dtype=complex),
                   'ch6':array([],dtype=complex),
                   'ch7':array([],dtype=complex)}
        self.b = 0
        self.z = 0
        self.f = 0
        self.c = 0 

    @classmethod
    def from_bin(cls, bin_frame):

        # create our instance
        inst = super(DBEFrame, cls).from_bin(bin_frame)

        # data is reordered in 16 by vdif class
        # thus our data order is (p1i3,p1r3,p0i3,p0r3,p1i2...p0r0)
        # and the next four ch   (p1i7,p1r7,p0i6,p0i6,p1i5...p0r4)
        # + .5 to remove dc offset
        p1 = array(inst.data[1::4]+1j*inst.data[0::4])+.5*(1+1j)
        p0 = array(inst.data[3::4]+1j*inst.data[2::4])+.5*(1+1j)
        
        # data is in channel order: 3 2 1 0 7 6 5 4 3 2 1 0...
        ch_start = [3, 2, 1, 0, 7, 6, 5, 4]
        for ch in range(8):
            inst.bdata['p1']['ch{0}'.format(ch)]=p1[ch_start[ch]::8]
            inst.bdata['p0']['ch{0}'.format(ch)]=p0[ch_start[ch]::8]

        # b-engine is in W45 of the VDIF header, found in eud[0,1]
        beng0 = inst.eud[1]
        beng1 = inst.eud[0]
        beng2 = inst.eud_vers
        inst.c =  beng0      & MASK8
        inst.z = (beng0>>8)  & MASK8
        inst.f = (beng0>>16) & MASK8
        b_bott = (beng0>>24) & MASK8
        b_mid  = (beng1 & MASK24)*2**8
        b_top  = (beng2 &  MASK8)*2**32
        inst.b = b_bott+b_mid+b_top

        return inst        
