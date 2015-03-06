from struct import pack, unpack
import argparse

# parse the user's command line arguments
parser = argparse.ArgumentParser(
         description='Convert Little End VDIF file to Big End BENG file'
         )
parser.add_argument('filename', 
                    type=str,  
                    help='.vdif file to be converted to .beng file'
                    )
args = parser.parse_args()

fin = args.filename
fout= fin[:-5]+'.beng'

print 'Converting little end {0} to {1} big end'.format(fin,fout)

file_in  = open(fin,'rb')
file_out = open(fout,'w')


pkt_size = 1056
rd_size = pkt_size/4
wr_size = pkt_size/4-6

end_of_frames = False
while not end_of_frames:
    pkt = file_in.read(pkt_size)
    
    if not len(pkt)==pkt_size:
        end_of_frames=True
        break

    # read in full packet in 32 bit words
    words = list(unpack('<{0}I'.format(rd_size), pkt))
    # remove words 0 and 1
    del words[0:4]
    
    # remove the last VDIF hdr
    del words[2:4]
    
    pkt_to_write = pack('>{0}I'.format(wr_size), *words)
    
    file_out.write(pkt_to_write)


file_in.close()
file_out.close()
    
