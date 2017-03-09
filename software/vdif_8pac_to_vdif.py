#!/usr/bin/env ipython

import sys, struct
from vdif import VDIFFrame, VDIFFrameHeader
from swarm import DBEFrame
from struct import unpack

stdin = sys.stdin
stdout = sys.stdout

# Loop until done
fh = open('vdif_8pac_to_vdif.log','w')
npkts_8pac = 0
while True:
	# initialize list of VDIF packets, and boundaries
	vpkts = [None]*8
	psn_boundary = 0
	data_frame_boundary = 0
	second_boundary = 8
	# read first inner packet
	hdr_bytes = stdin.read(32)
	if len(hdr_bytes) == 0:
		break
	elif len(hdr_bytes) != 32:
		raise RuntimeError("Error reading file. Incomplete 8PAC packet?")
	hdr = VDIFFrameHeader.from_bin(hdr_bytes)
	if hdr.invalid_data:
		fh.write("8pac #{0} has invalid data, skipping {1} payload bytes\n".format(npkts_8pac,hdr.frame_length*8-32))
		stdin.read(hdr.frame_length*8 - 32)
		continue
	hdr.frame_length = 1056/8
	hdr.station_id = (ord(hdr.station_id[0])<<8) | ord(hdr.station_id[1])
	pkt_bytes = "".join((hdr.to_bin(),stdin.read(1024)))
	vpkts[0] = DBEFrame.from_bin(pkt_bytes)
	# read remaining inner packets
	for ii in range(1,8):
		# read VTP interleaved between inner packets, and discard
		tmp = stdin.read(8)
		# read next header bytes
		hdr_bytes = stdin.read(32)
		if len(hdr_bytes) != 32:
			raise RuntimeError("Unexpected end-of-file, incomplete 8PAC packet?")
		hdr = VDIFFrameHeader.from_bin(hdr_bytes)
		hdr.frame_length = 1056/8
		hdr.station_id = (ord(hdr.station_id[0])<<8) | ord(hdr.station_id[1])
		pkt_bytes = "".join((hdr.to_bin(),stdin.read(1024)))
		vpkts[ii] = DBEFrame.from_bin(pkt_bytes)
		if vpkts[ii].psn != vpkts[ii-1].psn:
			psn_boundary = ii
		if vpkts[ii].data_frame != vpkts[ii-1].data_frame:
			if vpkts[ii].secs_since_epoch != vpkts[ii-1].secs_since_epoch:
				second_boundary = ii
			else:
				data_frame_boundary = ii
	#~ print "PSN boundary is {0}, data frame boundary is {1}".format(psn_boundary,data_frame_boundary)
	
	for ii,vv in enumerate(vpkts):
		# correct inner packet psn
		if ii < psn_boundary:
			vv.psn = (vv.psn+1)*8 + (ii-psn_boundary)
		else:
			vv.psn = (vv.psn)*8 + (ii-psn_boundary)
		# correct inner packet data_frame
		if ii < data_frame_boundary:
			vv.data_frame = (vv.data_frame+1)*8 + (ii-data_frame_boundary)
		else:
			vv.data_frame = vv.data_frame*8 + (ii-data_frame_boundary)
		# ...and if stream crosses a second-boundary, data_frame resets
		if ii >= second_boundary:
			vv.data_frame = ii - second_boundary
		#~ print vv.psn,vv.data_frame
		# count the ants and correct the bugs:
		#   1) station_id should be 16-bit integer
		vv.station_id = (ord(vv.station_id[0])<<8) | ord(vv.station_id[1])
		#   2) psn should be reinserted into eud
		vv.eud[2] = vv.psn & 0xFFFFFFFF
		vv.eud[3] = (vv.psn>>32) & 0xFFFFFFFF
		stdout.write(vv.to_bin())
		fh.write("{0}.{1} is {2} 8-byte words\n".format(vv.secs_since_epoch,vv.data_frame,vv.frame_length))
		#print "writing {0} bytes".format(len(vv.to_bin()))
	npkts_8pac += 1
fh.close()
