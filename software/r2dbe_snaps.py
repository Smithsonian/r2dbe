import struct
from numpy import int32, uint32, array, zeros, arange

## given r2dbe snapshot retrieval, make 8 bit stream and make 2 bit stream

# get 8 bit data
def data_from_snap_8bit(x,L):
   x8 = array(struct.unpack('>{0}b'.format(L),x), int32)
   return x8

def data_from_snap_2bit(x,L):
   x2 = zeros(L, int32)
   
   #unpack the 2 bit data
   # unpack data into array
   
   y  = array(struct.unpack('<{0}I'.format(L/16), x), uint32)

   # interpret the data given our bits-per-sample
   bits_per_sample = 2 
   samp_per_word   = 16
   
   samp_max = 2**bits_per_sample - 1
   
   for samp_n in range(samp_per_word):
   
       # get sample data from words
       shift_by = bits_per_sample * samp_n
       x2[samp_n::samp_per_word] = (y >> shift_by) & samp_max
   
   # we need to reinterpret as offset binary
   x2 = x2 - 2**(bits_per_sample-1)

   return x2
