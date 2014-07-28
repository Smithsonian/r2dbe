#!/usr/bin/env python2.7
import sys, socket, struct

UDP_IP = "192.168.1.3"
UDP_PORT = 4001

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

for i in range(int(sys.argv[1])):
    pkt, addr = sock.recvfrom(8224) # buffer size is 8224 bytes
    header = struct.unpack('>8I', pkt[:32])
    data = struct.unpack('>%dI' % (len(pkt[32:])/4), pkt[32:])

    print "received packet %d" % i
    print "received header: "
    for h in range(8):
        print "{0:4d}: 0x{1:08X}".format(h, header[h])
    print
    print "received data: "
    for d in range(8):
        print "{0:4d}: 0x{1:08X}".format(d, data[d])
    print ". . . . . . . ."
    for d in range(len(data)-8, len(data)):
        print "{0:4d}: 0x{1:08X}".format(d, data[d])
    print 
    print
