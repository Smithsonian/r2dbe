from struct import pack, unpack
from datetime import datetime, timedelta, tzinfo
from numpy import int32, uint32, uint64, array, zeros
from vdif import VDIFFrame

MASK7 = 0x7F
MASK8 = 0xFF
MASK39= 0x7FFFFFFFFF
MASK40= 0xFFFFFFFFFF

class DBEFrame(VDIFFrame):
    def __init__(self):
        super(DBEFrame, self).__init__()
        self.bdata = {'p0':{}, 'p1':{}}
        self.bdata['p0'] = {'ch0':array([],dtype=complex),
                   'ch1':array([],dtype=complex),
                   'ch2':array([],dtype=complex),
                   'ch3':array([],dtype=complex)}
        self.bdata['p1'] = {'ch0':array([],dtype=complex),
                   'ch1':array([],dtype=complex),
                   'ch2':array([],dtype=complex),
                   'ch3':array([],dtype=complex)}
        self.b = 0
        self.z = 0
        self.f = 0
        self.c = 0 

    @classmethod
    def from_bin(cls, bin_frame):

        # create our instance
        inst = super(DBEFrame, cls).from_bin(bin_frame)

        # data is reordered in 16 (p1i3,p1r3,p0i3,p0r3,p1i2...p0r0)
        for ch in range(4):
            idstart = 16-4*(ch+1)
            inst.bdata['p1']['ch{0}'.format(ch)]=array(inst.data[idstart+1::16] 
                                          +1j*inst.data[idstart+0::16])
            inst.bdata['p0']['ch{0}'.format(ch)]=array(inst.data[idstart+3::16]
                                          +1j*inst.data[idstart+2::16])

        # b-engine is in W45 of the VDIF header, found in eud[0,1]
        beng = inst.eud[1]
        c_bot  =  beng      & MASK8
        inst.z = (beng>>8)  & MASK8
        inst.f = (beng>>16) & MASK8
        inst.b = (beng>>24) & MASK8+2**8*(inst.eud[0] & MASK39)
        c_top  = (inst.eud[0]>>31)   & 0x1
        inst.c = c_top*2**7+c_bot
 
        return inst        