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
        inst.c =  beng0      & MASK8
        inst.z = (beng0>>8)  & MASK8
        inst.f = (beng0>>16) & MASK8
        b_bott = (beng0>>24) & MASK8
        b_mid  = (beng1 & MASK24)*2**8
        b_top  = (beng2 &  MASK8)*2**32
        inst.b = b_bott+b_mid+b_top

        # data is reordered in 16 by vdif class
        # thus our data order is (p1i3,p1r3,p0i3,p0r3,p1i2...p0r0)
        # and the next four ch   (p1i7,p1r7,p0i6,p0i6,p1i5...p0r4)
        # + .5 to remove dc offset
        p1 = array(inst.data[1::4]+1j*inst.data[0::4])+.5*(1+1j)
        p0 = array(inst.data[3::4]+1j*inst.data[2::4])+.5*(1+1j)

        # data is in channel order: 3 2 1 0 7 6 5 4 3 2 1 0...
        ch_start = [3, 2, 1, 0, 7, 6, 5, 4]
        for ch in range(8):
            inst.bdata['p1']['ch{0}'.format(ch)]={}
            inst.bdata['p0']['ch{0}'.format(ch)]={}
 
            inst.bdata['p1']['ch{0}'.format(ch)]['data']=p1[ch_start[ch]::8]
            inst.bdata['p0']['ch{0}'.format(ch)]['data']=p0[ch_start[ch]::8]

            inst.bdata['p1']['ch{0}'.format(ch)]['freq']=8*(inst.c*8+inst.f)+ch_start[ch]
            inst.bdata['p0']['ch{0}'.format(ch)]['freq']=8*(inst.c*8+inst.f)+ch_start[ch]

        return inst        
