#!/usr/bin/env python

from argparse import ArgumentParser
from numpy import array
from struct import pack, unpack
import sys

stdin = sys.stdin
stdout = sys.stdout

VDIF_PER_8PAC = 8
VTP_BYTE_SIZE = 8
VDIF_BYTE_SIZE = 1056
VDIF_4BYTE_SIZE = VDIF_BYTE_SIZE/4
VDIF_8BYTE_SIZE = VDIF_BYTE_SIZE/8

if __name__ == "__main__":
    parser = ArgumentParser(description='Enque quick recording')
    parser.add_argument('-n','--num-pkts',metavar='NPKT',type=int,default=-1,
        help="unpack NPKT VDIF frames from the 8pac file, -1 for all (default is -1)")
    parser.add_argument('-v','--verbose',action='count',
        help="add verbosity to output, use multiple times for more detail")
    parser.add_argument('infile',metavar='INPUT_FILE',type=str,
        help="read 8pac VDIF from INPUT_FILE")
    parser.add_argument('outfile',metavar='OUTPUT_FILE',type=str,nargs='?',default='tmp.vdif',
        help="write unpacked VDIF to OUTPUT_FILE (default is 'tmp.vdif')")
    args = parser.parse_args()
    
    with open(args.infile,'r') as fh_in:
        with open(args.outfile,'w') as fh_out:
            n_vdif = 0
            while True:
                # read packet
                b_pkt = fh_in.read(VDIF_BYTE_SIZE)
                if len(b_pkt) == 0:
                    break
                elif len(b_pkt) != VDIF_BYTE_SIZE:
                    raise RuntimeError("Packet {0} short, only {1}/{2} bytes".format(n_vdif,len(b_pkt),VDIF_BYTE_SIZE))
                # fix VDIF frame length
                w_pkt = array(unpack('<{0}I'.format(VDIF_4BYTE_SIZE),b_pkt))
                word2 = w_pkt[2]
                #~ print "word2 = 0x{0:08x}".format(word2)
                word2 = (word2 & 0xFF000000) | VDIF_8BYTE_SIZE
                #~ print "word2 = 0x{0:08x}".format(word2)
                w_pkt[2] = word2
                b_pkt = pack('<{0}I'.format(VDIF_4BYTE_SIZE),*w_pkt)
                fh_out.write(b_pkt)
                n_vdif += 1
                if args.num_pkts != -1 and n_vdif >= args.num_pkts:
                    break
            
                if n_vdif % VDIF_PER_8PAC == 0:
                    continue
            
                # skip VTP
                b_vtp = fh_in.read(VTP_BYTE_SIZE)
                if len(b_vtp) == 0:
                    break
                elif len(b_vtp) != VTP_BYTE_SIZE:
                    raise RuntimeError("VTP {0} short, only {1}/{2} bytes".format(n_vdif,len(b_pkt),VTP_BYTE_SIZE))
    
    if args.verbose > 0:
        print("unpacked {0} VDIF frames".format(n_vdif))
