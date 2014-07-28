#!/usr/bin/env python2.6
import sys, socket, struct

vdif = 0

if vdif==0:
    UDP_IP = "192.168.1.3"
else:
    UDP_IP = "192.168.1.5" # or 4 or 2 

UDP_PORT = 4001

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

print "____________________"
print
print "VDIF Stream %d" %vdif
print "____________________"

for i in range(int(sys.argv[1])):
    pkt, addr = sock.recvfrom(8224) # buffer size is 8224 bytes
    header = struct.unpack('>8I', pkt[:32])

    print "received packet %d" % i

    #########
    #   W0
    #########
    i1         = (header[0]>>31) & (1)
    l1         = (header[0]>>30) & (1)
    sec_ref_ep = (header[0]>>2)  & (2**30-1)

    print "W0:   Invalid data          : %d" %(i1)
    print "      Legacy mode           : %d" %(l1)
    print "      Secs since ref ep     : %d" %(sec_ref_ep) 

    #########
    #   W1
    #########
    ref_ep    = (header[1]>>24) & (2**30-1)
    data_frame= (header[1])     & (2**24-1)

    print "W1:   Reference Epoch       : %d" %(ref_ep)
    print "      Data frame (w/in pps) : %d" %(data_frame)

    #########
    #   W2
    #########
    v3   = (header[2]>>29) & (2**29-1)
    l2ch = (header[2]>>24) & (2**5-1)
    flen = (header[2])     & (2**24-1)

    print "W2:   Version               : %d" %(v3)
    print "      Log2 num chans        : %d" %(l2ch)
    print "      Frame Length          : %d" %(flen)

    #########
    #   W3
    #########
    c1    =  (header[3]>>31) & (1)
    bps_1 =  (header[3]>>26) & (2**5-1)
    th_id =  (header[3]>>16) & (2**10-1)
    st_id =  (header[3])     & (2**10-1)

    print "W3:   Real (or Complex)     : %d" %c1
    print "      Bits per samp, minus 1: %d" %bps_1
    print "      Thread ID             : %d" %th_id
    print "      Station ID            : %d" %st_id


    #########
    #   W4
    #########
    
    edv        = (header[4]>>25) & (2**8-1)
    magic_wd   = (header[4]>>4)  & (2**25-1)
    bl_or_2ant = (header[4]>>3)  & (1)
    alma_quad  = (header[4]>>1)  & (3)
    pol        = (header[4])     & (1)
 
    print "W4:   EDV number            : %d" %edv
    print "      Magic Word            : %d" %magic_wd
    print "      BL Corr (or 2 ant)    : %d" %bl_or_2ant
    print "      ALMA Baseline Quadrant: %d" %alma_quad
    print "      Pol X/L (or Pol Y/R)  : %d" %pol

    #########
    #   W5
    #########
    
    pic_stat = (header[5]>>16) & (2**16-1)
    mark6    = (header[5])     & (2**16-1)

    print "W5:   PIC Status            : %d" %pic_stat
    print "      Mark 6 Status         : %d" %mark6


    #########
    #   W6 
    #########
    print "W6:   Least sig word PSN    : %d" %(int(header[6])) 

    #########
    #   W7
    #########
    print "W7:   Most sig word PSN     : %d" %(int(header[7])) 

    print 
