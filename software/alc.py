import adc5g, corr

# connect to roach2
roach2 = corr.katcp_wrapper.FpgaClient('r2dbe-1')
roach2.wait_connected()

for ii in ['0','1']:
   # grab snapshot of 8 bit data from each input
   x8 = adc5g.get_snapshot(roach2,'r2dbe_snap_8bit_'+ii+'_data')

   # sort data
   L    = len(x8)
   y    = sorted(x8)

   # find value 16% of the way through
   Lt   = int(L*0.16)
   th1   = abs(y[Lt-1])

   # find value at 84% of the way through
   Lt2  = int(L*0.84)
   th2  = abs(y[Lt2-1])

   # average these threshold values
   th   = (th1+th2)/2

   # write threshold to FPGA
   roach2.write_int('r2dbe_quantize_'+ii+'_thresh', th)

   




