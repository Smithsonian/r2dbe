import adc5g, corr

def get_th_16_84(x):
    # sort data
    L = len(x8)
    y = sorted(x8)
    # find value 16% of the way through
    Lt = int(L*0.16)
    th1 = abs(y[Lt-1])
    # find value at 84% of the way through
    Lt2 = int(L*0.84)
    th2 = abs(y[Lt2-1])
    # average these threshold values
    th = (th1+th2)/2
    return th

import argparse
parser = argparse.ArgumentParser(description='Set 2-bit quantization threshold')
parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
    help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
parser.add_argument('-v','--verbose',action='count',
    help="control verbosity, use multiple times for more detailed output")
parser.add_argument('host',metavar='R2DBE',type=str,nargs='?',default='r2dbe-1',
    help="hostname or ip address of r2dbe (default is 'r2dbe-1')")
args = parser.parse_args()

# connect to roach2
roach2 = corr.katcp_wrapper.FpgaClient(args.host)
if not roach2.wait_connected(timeout=args.timeout):
    msg = "Could not establish connection to '{0}' within {1} seconds, aborting".format(
        args.host,args.timeout)
    raise RuntimeError(msg)

if args.verbose > 1:
    print "connected to '{0}'".format(args.host)

for ii in ['0','1']:
    # grab snapshot of 8 bit data from each input
    if args.verbose > 2:
        print "get snapshot form 'r2dbe_snap_8bit_{0}_data'".format(ii)
    x8 = adc5g.get_snapshot(roach2,'r2dbe_snap_8bit_'+ii+'_data')
    
    th = get_th_16_84(x8)

    if args.verbose > 0:
        print "threshold {0} = {1}".format(ii,th)
    # write threshold to FPGA
    if args.verbose > 2:
        print "write threshold to 'r2dbe_quantize_{0}_thresh'".format(ii)
    roach2.write_int('r2dbe_quantize_'+ii+'_thresh', th)
