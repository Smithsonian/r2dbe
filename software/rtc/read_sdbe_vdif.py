#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  read_sdbe_vdif.py
#  Apr 01, 2015 10:33:15 HST
#  Copyright 2015
#         
#  Andre Young <andre.young@cfa.harvard.edu>
#  Harvard-Smithsonian Center for Astrophysics
#  60 Garden Street, Cambridge
#  MA 02138
#  
#  Changelog:
#  	AY: Created 2015-04-01

"""
Define utilities for handling SWARM DBE data product.
"""

# This module is loaded from r2dbe repo on the swarm2dbe branch.
import swarm

# nump, scipy
from numpy import empty, zeros, int8, array, concatenate, ceil, arange, roll, complex64, any, mean, median, nan, nonzero, isnan
from numpy.fft import irfft
from scipy.interpolate import interp1d

# other useful ones
from logging import getLogger
from datetime import datetime

# This module is loaded from the wideband_sw repo on the swarm_half_rate branch.
from defines import SWARM_XENG_PARALLEL_CHAN, SWARM_N_INPUTS, SWARM_N_FIDS, SWARM_TRANSPOSE_SIZE, SWARM_CHANNELS

SWARM_CHANNELS_PER_PKT = 8
SWARM_PKTS_PER_BCOUNT = SWARM_CHANNELS/SWARM_CHANNELS_PER_PKT
SWARM_SAMPLES_PER_WINDOW = 2*SWARM_CHANNELS
SWARM_RATE = 4576e6 # 10/11
#~ SWARM_RATE = 3328e6 # 8/11 #
#~ SWARM_RATE = 2496e6 # 6/11 #

AUX11_BU_STEP = 1.0*32768*128/16 

# VDIF frame size
FRAME_SIZE_BYTES = 1056

#~ SWARM_XENG_PARALLEL_CHAN = 8
#~ SWARM_N_INPUTS = 2
#~ SWARM_N_FIDS = 8
#~ SWARM_TRANSPOSE_SIZE = 128
#~ SWARM_CHANNELS = 2**14
#~ SWARM_CHANNELS_PER_PKT = 8
#~ SWARM_PKTS_PER_BCOUNT = SWARM_CHANNELS/SWARM_CHANNELS_PER_PKT
#~ SWARM_SAMPLES_PER_WINDOW = 2*SWARM_CHANNELS
#~ SWARM_RATE = 2496e6

# R2DBE related constants, should probably be imported from some python
# source in the R2DBE git repo
R2DBE_SAMPLES_PER_WINDOW = 32768
R2DBE_RATE = 4096e6

def read_spectra_from_file(filename,bcount_offset=1,num_bcount=1):
	"""
	Like read_spectra_from_files but just read from a flat file.
	"""
	
		# some benchmarking statistics
	t0_total = datetime.now()
	T_read_vdif = 0.0
	T_unpack_vdif = 0.0
	T_build_spectra = 0.0
	T_overhead = 0.0
	T_total_time = 0.0
	
	# create logger for this
	logger = getLogger(__name__)
	
	# build filename list -- just a single file
	input_filenames = [filename]
	
	logger.info('B-engine counter offset from first encountered is %d' % bcount_offset)

	num_files = len(input_filenames)
	logger.info('Found %d files for given base: %s' % (num_files,str(input_filenames)))

	spectra_real = empty([SWARM_N_INPUTS,SWARM_TRANSPOSE_SIZE*num_bcount,SWARM_CHANNELS], dtype=int8)
	spectra_imag = empty([SWARM_N_INPUTS,SWARM_TRANSPOSE_SIZE*num_bcount,SWARM_CHANNELS], dtype=int8) 
	spectra_real[:] = 0
	spectra_imag[:] = 0
	
	# set the bcount where we want to start
	bcount_start = -1
	logger.debug('bcount_start set to %d' % bcount_start)

	t0 = datetime.now()
	for this_file in input_filenames:
		with open(this_file,'r') as fh:
			this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
			if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
				logger.error('EoF prematurely encountered in B-engine counter scouting loop %s' % this_file)
			
			# read one frame
			this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
			# get bcount
			this_bcount = this_frame.b
			
			logger.debug('First bcount in "%s" is %d' % (this_file,this_bcount))
			
			if (this_bcount > bcount_start):
				logger.debug('This bcount is greater than global: %d > %d, updating global.' % (this_bcount,bcount_start))
				bcount_start = this_bcount
	
	# this is the B-engine count we want
	bcount_start = bcount_start + bcount_offset
	bcount_end = bcount_start + num_bcount
	T_overhead = T_overhead + (datetime.now() - t0).total_seconds()

	logger.info('Reading B-engine packets within counter values [%d,%d)' % (bcount_start,bcount_end))
	
	timestamps_at_first_usable_packet = list()
	for this_file in input_filenames:
		logger.debug('Processing file "%s"' % this_file)
		
		# reset timestamp for this stream
		timestamps_at_first_usable_packet.append(datetime(2015,01,01,0,0,0))
		with open(this_file,'r') as fh:
			while True:
				t0 = datetime.now()
				this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
				T_read_vdif = T_read_vdif + (datetime.now() - t0).total_seconds()
				if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
					# EoF
					logger.error('EoF prematurely encountered in data parsing loop "%s".' % this_file)
					break
				
				# build frame from bytes
				t0 = datetime.now()
				this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
				if this_frame.invalid_data:
					logger.warning('Packet marked invalid data, skipping')
					continue
				T_unpack_vdif = T_unpack_vdif + (datetime.now() - t0).total_seconds()
				
				# check the B-engine count for valid range
				if (this_frame.b < bcount_start):
					t0 = datetime.now()
					# update timestamp for this stream
					timestamps_at_first_usable_packet[-1] = this_frame.datetime()
					# skip ahead if we're from the right bcount, assuming
					# packets are in order that bcount increases monotonically
					if (this_frame.b < (bcount_start-1)):
						bcount_deficit = (bcount_start-1) - this_frame.b
						vdif_deficit = bcount_deficit*(SWARM_PKTS_PER_BCOUNT/len(ETH_IFACE_LIST))
						logger.debug('bcount is behind by at least %d whole frames, skipping %d VDIF frames' % (bcount_deficit,vdif_deficit))
						fh.seek(vdif_deficit*FRAME_SIZE_BYTES,1)
					T_overhead = T_overhead + (datetime.now() - t0).total_seconds()
					continue
				elif (this_frame.b >= bcount_end):
					# we got all the bcount
					logger.debug('bcount is %d (> %d), stop reading from %s' % (this_frame.b,bcount_end,this_file))
					break
					
				# find absolute channel positions
				t0 = datetime.now()
				chan_id = this_frame.c #chan_id
				fid = this_frame.f #fid
				start_chan = SWARM_XENG_PARALLEL_CHAN * (chan_id * SWARM_N_FIDS + fid)
				stop_chan = start_chan + SWARM_XENG_PARALLEL_CHAN
				# set time-offset of this data
				start_snap = (this_frame.b-bcount_start)*SWARM_TRANSPOSE_SIZE
				stop_snap = start_snap+SWARM_TRANSPOSE_SIZE
				
				logger.debug('bcount = %d, chan_id = %d, fid = %d: [start_snap:stop_snap, start_chan:stop_chan] = [%d:%d, %d:%d]' % (this_frame.b,chan_id,fid,start_chan,stop_chan,start_snap,stop_snap))
				
				for i_input in range(SWARM_N_INPUTS):
					p_key = 'p' + str(i_input)
					for k_parchan in range(SWARM_XENG_PARALLEL_CHAN):
						ch_key = 'ch' + str(k_parchan)
						spectra_real[i_input,start_snap:stop_snap,start_chan+k_parchan] = array(this_frame.bdata[p_key][ch_key].real,dtype=int8)
						spectra_imag[i_input,start_snap:stop_snap,start_chan+k_parchan] = array(this_frame.bdata[p_key][ch_key].imag,dtype=int8)
				
				T_build_spectra = T_build_spectra + (datetime.now() - t0).total_seconds()
	
	#~ # logging cleanup
	#~ logger.removeHandler(log_handler)
	#~ log_handler.close()
	T_total_time = T_total_time + (datetime.now() - t0_total).total_seconds()
	
	T_recording = 1.0 * num_bcount * SWARM_TRANSPOSE_SIZE * SWARM_SAMPLES_PER_WINDOW / SWARM_RATE
	
	logger.info('''Benchmark results:
	\tTotals\t\t\t\t\t\t        Time [s]\t      Per rec time
	\tUsed data recording time:\t\t\t%16.6f\t\t%10.3f
	\tTotal reading time:\t\t\t\t%16.6f\t\t%10.3f
	
	\tComponents\t\t\t\t\t        Time [s]\t      Per rec time
	\tRead raw data from file:\t\t\t%16.6f\t\t%10.3f
	\tPack into VDIF frames:\t\t\t\t%16.6f\t\t%10.3f
	\tBuild spectral data:\t\t\t\t%16.6f\t\t%10.3f
	\tOverhead:\t\t\t\t\t%16.6f\t\t%10.3f
	''' % (T_recording,T_recording/T_recording,T_total_time,T_total_time/T_recording,T_read_vdif,T_read_vdif/T_recording,T_unpack_vdif,T_unpack_vdif/T_recording,T_build_spectra,T_build_spectra/T_recording,T_overhead,T_overhead/T_recording))
	
	return spectra_real,spectra_imag,timestamps_at_first_usable_packet

def read_spectra_from_files(filename_base,bcount_offset=1,num_bcount=1,suffix='_eth{0:d}',sfx_list=range(1,5)):
	"""
	Read SWARM DBE spectral data from multiple files.
	
	Arguments:
	----------
	filename_base -- Base of the filenames in which the data is written.
	The collection of files take the form <filename_base>_eth<x>.vdif
	where x is one of (and all) {2,3,4,5}.
	bcount_offset -- The offset from the first encountered B-engine counter
	value, should be at least 1 (default is 1).
	num_bcount -- Read data equivalent to this many B-engine counter values
	(default is 1).
	
	Returns:
	--------
	spectra_real -- Real component of spectral data as numpy int8 array 
	and takes values in {-2,-1,0,1} or -128 for missing data. The array 
	M x 16384 where M is equal to 128*num_bcount.
	spectra_imag -- Same as spectra_real, except contains the imaginary
	component of the spectral data.
	timestamps_at_first_usable_packet -- The VDIF timestamps applied to
	the last unusable packet in each file.
	
	Notes:
	------
	Only the positive half of the spectrum is returned, as obtained from 
	a real discrete Fourier transform.
	"""

	print "hello world!"
	
	# some benchmarking statistics
	t0_total = datetime.now()
	T_read_vdif = 0.0
	T_unpack_vdif = 0.0
	T_build_spectra = 0.0
	T_overhead = 0.0
	T_total_time = 0.0
	
	# assume all data comes from 4 seperate and equally divided load stream
	ETH_IFACE_LIST = sfx_list
	
	# create logger for this
	logger = getLogger(__name__)
	
	
	# build filename list
	input_filenames = list()
	for i_eth_if in ETH_IFACE_LIST:
		input_filenames.append(('%s%s.vdif' % (filename_base,suffix)).format(i_eth_if))
	
	logger.info('B-engine counter offset from first encountered is %d' % bcount_offset)

	num_files = len(input_filenames)
	logger.info('Found %d files for given base: %s' % (num_files,str(input_filenames)))

	spectra_real = empty([SWARM_N_INPUTS,SWARM_TRANSPOSE_SIZE*num_bcount,SWARM_CHANNELS], dtype=int8)
	spectra_imag = empty([SWARM_N_INPUTS,SWARM_TRANSPOSE_SIZE*num_bcount,SWARM_CHANNELS], dtype=int8) 
	spectra_real[:] = 0
	spectra_imag[:] = 0
	
	# set the bcount where we want to start
	bcount_start = -1
	logger.debug('bcount_start set to %d' % bcount_start)

	b_list = []
	print "hello world!"
	t0 = datetime.now()
	for this_file in input_filenames:
		with open(this_file,'r') as fh:
			this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
			if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
				logger.error('EoF prematurely encountered in B-engine counter scouting loop %s' % this_file)
			
			# read one frame
			this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
			# get bcount
			this_bcount = this_frame.b
			this_scount = this_frame.s
			this_ucount = this_frame.u
			
			logger.debug('First Xcount in "%s" is s:%10d, u%10d, b:%d' % (this_file,this_scount,this_ucount,this_bcount))
			
			if (this_bcount > bcount_start):
				logger.debug('This bcount is greater than global: %d > %d, updating global.' % (this_bcount,bcount_start))
				bcount_start = this_bcount
				scount_start = this_scount
				ucount_start = this_ucount
				logger.debug('Start at s:%10d, u%10d' % (scount_start,ucount_start))
	
	# this is the B-engine count we want
	b_list.append(bcount_start)
	b_list_len = bcount_offset + num_bcount
	
	bcount_start = bcount_start + bcount_offset
	bcount_end = bcount_start + num_bcount
	T_overhead = T_overhead + (datetime.now() - t0).total_seconds()

	logger.info('Reading B-engine packets within counter values [%d,%d)' % (bcount_start,bcount_end))
	
	timestamps_at_first_usable_packet = list()
	for this_file in input_filenames:
		logger.debug('Processing file "%s"' % this_file)
		
		# reset timestamp for this stream
		timestamps_at_first_usable_packet.append(datetime(2015,01,01,0,0,0))
		with open(this_file,'r') as fh:
			while True:
				t0 = datetime.now()
				this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
				T_read_vdif = T_read_vdif + (datetime.now() - t0).total_seconds()
				if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
					# EoF
					logger.error('EoF prematurely encountered in data parsing loop "%s".' % this_file)
					break
				
				# build frame from bytes
				t0 = datetime.now()
				this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
				if this_frame.invalid_data:
					logger.warning('Packet marked invalid data, skipping')
					continue
				T_unpack_vdif = T_unpack_vdif + (datetime.now() - t0).total_seconds()
				
				# check the B-engine count for valid range
				if (this_frame.b < bcount_start):
					t0 = datetime.now()
					# update timestamp for this stream
					timestamps_at_first_usable_packet[-1] = this_frame.datetime()
					# skip ahead if we're from the right bcount, assuming
					# packets are in order that bcount increases monotonically
					if (this_frame.b < (bcount_start-1)):
						bcount_deficit = (bcount_start-1) - this_frame.b
						vdif_deficit = bcount_deficit*(SWARM_PKTS_PER_BCOUNT/len(ETH_IFACE_LIST))
						logger.debug('bcount is behind by at least %d whole frames, skipping %d VDIF frames' % (bcount_deficit,vdif_deficit))
						fh.seek(vdif_deficit*FRAME_SIZE_BYTES,1)
					T_overhead = T_overhead + (datetime.now() - t0).total_seconds()
					continue
				elif (this_frame.b >= bcount_end):
					# we got all the bcount
					logger.debug('bcount is %d (> %d), stop reading from %s' % (this_frame.b,bcount_end,this_file))
					break
					
				# find absolute channel positions
				t0 = datetime.now()
				chan_id = this_frame.c #chan_id
				fid = this_frame.f #fid
				start_chan = SWARM_XENG_PARALLEL_CHAN * (chan_id * SWARM_N_FIDS + fid)
				stop_chan = start_chan + SWARM_XENG_PARALLEL_CHAN
				# set time-offset of this data
				start_snap = (this_frame.b-bcount_start)*SWARM_TRANSPOSE_SIZE
				stop_snap = start_snap+SWARM_TRANSPOSE_SIZE
				
				logger.debug('bcount = %d, chan_id = %d, fid = %d: [start_snap:stop_snap, start_chan:stop_chan] = [%d:%d, %d:%d]' % (this_frame.b,chan_id,fid,start_chan,stop_chan,start_snap,stop_snap))
				
				for i_input in range(SWARM_N_INPUTS):
					p_key = 'p' + str(i_input)
					for k_parchan in range(SWARM_XENG_PARALLEL_CHAN):
						ch_key = 'ch' + str(k_parchan)
						spectra_real[i_input,start_snap:stop_snap,start_chan+k_parchan] = array(this_frame.bdata[p_key][ch_key].real,dtype=int8)
						spectra_imag[i_input,start_snap:stop_snap,start_chan+k_parchan] = array(this_frame.bdata[p_key][ch_key].imag,dtype=int8)
				
				T_build_spectra = T_build_spectra + (datetime.now() - t0).total_seconds()
	
	#~ # logging cleanup
	#~ logger.removeHandler(log_handler)
	#~ log_handler.close()
	T_total_time = T_total_time + (datetime.now() - t0_total).total_seconds()
	
	T_recording = 1.0 * num_bcount * SWARM_TRANSPOSE_SIZE * SWARM_SAMPLES_PER_WINDOW / SWARM_RATE
	
	logger.info('''Benchmark results:
	\tTotals\t\t\t\t\t\t        Time [s]\t      Per rec time
	\tUsed data recording time:\t\t\t%16.6f\t\t%10.3f
	\tTotal reading time:\t\t\t\t%16.6f\t\t%10.3f
	
	\tComponents\t\t\t\t\t        Time [s]\t      Per rec time
	\tRead raw data from file:\t\t\t%16.6f\t\t%10.3f
	\tPack into VDIF frames:\t\t\t\t%16.6f\t\t%10.3f
	\tBuild spectral data:\t\t\t\t%16.6f\t\t%10.3f
	\tOverhead:\t\t\t\t\t%16.6f\t\t%10.3f
	''' % (T_recording,T_recording/T_recording,T_total_time,T_total_time/T_recording,T_read_vdif,T_read_vdif/T_recording,T_unpack_vdif,T_unpack_vdif/T_recording,T_build_spectra,T_build_spectra/T_recording,T_overhead,T_overhead/T_recording))
	
	return spectra_real,spectra_imag,timestamps_at_first_usable_packet
	

def read_b11_from_files(filename_base,bcount_offset=1,num_bcount=1,suffix='_eth{0:d}',sfx_list=range(1,5)):
	"""
	Read B-engine data in 11/11 format from the given files and 
	reconstruct the spectrum.
	
	Arguments:
	----------
	filename_base -- Relative path prefix used to construct the path for 
	each of the files to read.
	bcount_offset -- Number of B-engine frames to skip at the start of
	the stream.
	num_bcount -- Number of B-engine frames to read.
	suffix -- Format string suffix used to fill out complete filenames.
	sfx_list -- List of format-string replacements.
	
	Returns:
	--------
	spectra_real -- Real component of spectral data as numpy int8 array 
	and takes values in {-2,-1,0,1} or -128 for missing data. The array 
	M x 16384 where M is equal to 128*num_bcount.
	spectra_imag -- Same as spectra_real, except contains the imaginary
	component of the spectral data.
	timestamps_at_first_usable_packet -- The VDIF timestamps applied to
	the last unusable packet in each file.
	
	Notes:
	------
	Each filename is constructed using
		`'%s%s.vdif' % (filename_base,suffix)).format(sfx_list[ii])`
	where `ii` is in `range(len(sfx_list))`
	"""
	
		# some benchmarking statistics
	t0_total = datetime.now()
	T_read_vdif = 0.0
	T_unpack_vdif = 0.0
	T_build_spectra = 0.0
	T_overhead = 0.0
	T_total_time = 0.0
	
	# assume all data comes from 4 seperate and equally divided load stream
	ETH_IFACE_LIST = sfx_list
	
	# create logger for this
	logger = getLogger(__name__)
	
	
	# build filename list
	input_filenames = list()
	for i_eth_if in ETH_IFACE_LIST:
		input_filenames.append(('%s%s.vdif' % (filename_base,suffix)).format(i_eth_if))
	
	logger.info('B-engine counter offset from first encountered is %d' % bcount_offset)

	num_files = len(input_filenames)
	logger.info('Found %d files for given base: %s' % (num_files,str(input_filenames)))

	spectra_real = empty([SWARM_N_INPUTS,SWARM_TRANSPOSE_SIZE*num_bcount,SWARM_CHANNELS], dtype=int8)
	spectra_imag = empty([SWARM_N_INPUTS,SWARM_TRANSPOSE_SIZE*num_bcount,SWARM_CHANNELS], dtype=int8) 
	spectra_real[:] = 0
	spectra_imag[:] = 0
	
	# set the bcount where we want to start
	bcount_start = -1
	logger.debug('bcount_start set to %d' % bcount_start)

	b_list = [-1]*8
	bs_list = [-1]*8
	bu_list = [-1]*8
	SKIP_FRAMES = 1
	for this_file in input_filenames:
		with open(this_file,'r') as fh:
			# for now skip a few thousand frames at the start, just to get across the second-boundary (+ transients)
			fh.read(SKIP_FRAMES*FRAME_SIZE_BYTES)
			logger.warning('Skipping %d frames at the start in %s' % (SKIP_FRAMES,this_file))
			
			while True:
				# now read until we get a CID==0
				this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
				if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
					logger.error('EoF prematurely encountered in B-engine counter scouting loop %s' % this_file)
					break
				
				# read one frame
				this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
				# get bcount
				this_bcount = this_frame.b
				this_scount = this_frame.s
				this_ucount = this_frame.u
				this_fid = this_frame.f
				this_cid = this_frame.c
				if this_cid == 1:
					break
			
			if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
				break
			
			logger.debug(' First Xcount in "%s" is s:%10d, u:%10d, b:%d, f:%d, c:%3d' % (this_file,this_scount,this_ucount,this_bcount,this_fid,this_cid))
			b_list[this_fid],bs_list[this_fid],bu_list[this_fid] = this_bcount,this_scount,this_ucount
			
			other_fid = this_fid
			max_tries = 16384
			while other_fid == this_fid:
				max_tries = max_tries - 1
				if max_tries == 0:
					logger.error('EoF prematurely encountered in B-engine counter scouting loop %s (max_tries ran out on next-fid search)' % this_file)
					break
				this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
				if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
					logger.error('EoF prematurely encountered in B-engine counter scouting loop %s (next-fid search)' % this_file)
					break
				this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
				this_bcount = this_frame.b
				this_scount = this_frame.s
				this_ucount = this_frame.u
				this_fid = this_frame.f
				this_cid = this_frame.c
				
				#~ print this_fid,other_fid
				if other_fid != this_fid:
					logger.debug('Second Xcount in "%s" is s:%10d, u:%10d, b:%d, f:%d, c%d' % (this_file,this_scount,this_ucount,this_bcount,this_fid,this_cid))
					b_list[this_fid],bs_list[this_fid],bu_list[this_fid] = this_bcount,this_scount,this_ucount
					break
	
	# make B-engine reference start time
	clst,bsu_ref = aux11_is_cluster(bs_list,bu_list)
	logger.debug('Using (s:%10d, u:%10d) as reference' % (bsu_ref[0],bsu_ref[1]))
	logger.debug('The following FIDs are clustered around the reference: %s' % (nonzero(clst)[0]))
	
	bsu_master = [bsu_ref]
	bsu_ref = (bsu_ref[0],0)
	logger.warning('Using manual B-engine timestamping')
	# get a rough estimate of the number of frames expected to be read:
	#	512 frames / B-count in each of four streams (2 x FIDs / stream)
	#	num_bcount number of B-counts
	#	factor 2 just to be safe
	# then limit the total number of frames read per file to this number
	MAX_FRAMES_PER_STREAM = 512 * num_bcount * 4
	cid_is_zero = {}
	for this_file in input_filenames:
		cid_is_zero[this_file] = False
		with open(this_file,'r') as fh:
			# for now skip a few thousand frames at the start, just to get across the second-boundary (+ transients)
			fh.read(SKIP_FRAMES*FRAME_SIZE_BYTES)
			logger.warning('Skipping %d frames at the start in %s' % (SKIP_FRAMES,this_file))
			
			n_frames = 0
			first_frame_in_stream = True
			first_spectrum = True
			idx_bsu = -1
			
			while True:
				if n_frames >= MAX_FRAMES_PER_STREAM:
					logger.warning('Interrupting read, MAX_FRAMES_PER_STREAM reached in %s' % this_file)
					break
				this_frame_bytes = fh.read(FRAME_SIZE_BYTES)
				if (len(this_frame_bytes) < FRAME_SIZE_BYTES):
					logger.error('EoF prematurely encountered in B-engine counter scouting loop %s' % this_file)
					break
				n_frames = n_frames+1
				
				this_frame = swarm.DBEFrame.from_bin(this_frame_bytes)
				this_bcount = this_frame.b
				this_scount = this_frame.s
				this_ucount = this_frame.u
				this_fid = this_frame.f
				this_cid = this_frame.c
				
				if True:#this_fid == 7:
					if this_cid == 0 and not cid_is_zero[this_file]:
						idx_bsu = idx_bsu + 1
						cid_is_zero[this_file] = True
						logger.debug(' ============================================== increment idx_bsu')
					elif this_cid == 254 and cid_is_zero[this_file]:
						cid_is_zero[this_file] = False
				else:
					idx_bsu = aux11_map_bsu_index(this_scount,this_ucount,bsu_master)
				#~ print idx_bsu
				if idx_bsu >= 0:
					if idx_bsu < num_bcount:
						if first_frame_in_stream:
							logger.debug(' First used frame (index = %d) for spectrum-building in "%s" is s:%10d, u:%10d, b:%d, f:%d, c:%d' % (idx_bsu,this_file,this_scount,this_ucount,this_bcount,this_fid,this_cid))
							first_frame_in_stream = False
						
						# if index fits in snapshot range (defined by B-counts to read) insert immediately
						chan_id = this_frame.c #chan_id
						fid = this_frame.f #fid
						#~ start_chan = SWARM_XENG_PARALLEL_CHAN * (chan_id * SWARM_N_FIDS + fid)
						#~ stop_chan = start_chan + SWARM_XENG_PARALLEL_CHAN
						# should it be this?
						if chan_id % 2 == 0:
							start_chan = 16 * (int(chan_id/2) * SWARM_N_FIDS + fid)
							stop_chan = start_chan + 8
						else:
							start_chan = 16 * (int(chan_id/2) * SWARM_N_FIDS + fid) + 8
							stop_chan = start_chan + 8
						
						# set time-offset of this data
						start_snap = idx_bsu*SWARM_TRANSPOSE_SIZE
						stop_snap = (idx_bsu+1)*SWARM_TRANSPOSE_SIZE
						
						#~ if first_spectrum:
						logger.debug('bcount = %d, chan_id = %d, fid = %d: [start_snap:stop_snap, start_chan:stop_chan] = [%d:%d, %d:%d]' % (this_frame.b,chan_id,fid,start_snap,stop_snap,start_chan,stop_chan))
							#~ first_spectrum = False
						
						for i_input in range(SWARM_N_INPUTS):
							p_key = 'p' + str(i_input)
							for k_parchan in range(SWARM_XENG_PARALLEL_CHAN):
								ch_key = 'ch' + str(k_parchan)
								spectra_real[i_input,start_snap:stop_snap,start_chan+k_parchan] = array(this_frame.bdata[p_key][ch_key]['data'].real,dtype=int8)
								spectra_imag[i_input,start_snap:stop_snap,start_chan+k_parchan] = array(this_frame.bdata[p_key][ch_key]['data'].imag,dtype=int8)
					
	return spectra_real,spectra_imag,bsu_ref
	
def aux11_make_bsu_ref(bs_list,bu_list):
	bs_ref = min(bs_list)
	idx_bs_ref = nonzero(array(bs_list)==bs_ref)[0]
	idx_bu_ref = int(ceil(median(idx_bs_ref)))
	bu_ref = bu_list[idx_bu_ref]
	bsu_ref = (bs_ref,bu_ref)
	return bsu_ref

def aux11_is_cluster(bs_list,bu_list,bsu_ref=None):
	# exact step size in bu expected between consecutive B-engine frames
	#~ print bs_list
	#~ print bu_list
	#~ print ":",bsu_ref
	# if no reference (bs,bu) pair given, make one up
	if not bsu_ref:
		bsu_ref = aux11_make_bsu_ref(bs_list,bu_list)
	bs_ref = bsu_ref[0]
	bu_ref = bsu_ref[1]
	# return value is a boolean list which indicates indecies of bs/bu items that belong in given cluster
	clst = [False]*len(bs_list)
	for idx,bs,bu in zip(xrange(len(bs_list)),bs_list,bu_list):
		if bs == bs_ref:
			# if in same second as reference, need to be within nth of a step from bu_ref
			if (bu > (bu_ref - AUX11_BU_STEP/16)) and (bu < (bu_ref + AUX11_BU_STEP/16)):
				#~ print "bu > (bu_ref - AUX11_BU_STEP/16) = %d > (%d - %d): %s" % (bu,bu_ref,AUX11_BU_STEP/16,(bu > (bu_ref - AUX11_BU_STEP/16)))
				#~ print "bu < (bu_ref + AUX11_BU_STEP/16) = %d > (%d - %d): %s" % (bu,bu_ref,AUX11_BU_STEP/16,(bu < (bu_ref + AUX11_BU_STEP/16)))
				#~ print 'a',bu,bu_ref
				clst[idx] = True
		elif bs == bs_ref + 1:
			# if in the next second as reference, need to be within step-delta from zero
			if bu < AUX11_BU_STEP - 1:
				#~ print 'b'
				clst[idx] = True
		# in all other cases, assume not in cluster; in particular:
		#	1) for bs < bs_ref: bs is less than the minimum second in all (bs,bu) pairs
		#	2) for bs > bs_ref + 1: bs is more than one second ahead of other elements
		#	3) |bu - bu_ref| >= AUX11_BU_STEP/16: bu is much more than expected from reference
	return clst, bsu_ref

def aux11_map_bsu_index(bs,bu,bsu_master):
	# first reference
	bsu_0 = bsu_master[0]
	clst,_bsu_ref = aux11_is_cluster([bs],[bu],bsu_ref=bsu_0)
	if clst[0]:
		# if in clustered around bsu_0, index is zero
		#~ print 1
		#~ print (bs,bsu_master[0][0])
		#~ print (bu,bsu_master[0][1])
		return 0
	else:
		# if not in cluster around bsu_0, but before bsu_0, then invalid
		if bs < bsu_0[0] or (bs == bsu_0[0] and bu < bsu_0[1]):
			#~ print 2
			return -1
	# last reference
	bsu_X = bsu_master[-1]
	clst,_bsu_ref = aux11_is_cluster([bs],[bu],bsu_ref=bsu_X)
	if clst[0]:
		# if in cluster around bsu_X, index of last element
		#~ print 3
		return len(bsu_master)-1
	else:
		# if not in cluster around bsu_X, but after bsu_X, then need to see if reasonable indexing possible
		if bs > bsu_X[0]:
			# for now don't allow future-indexing beyond a second-boundary unless within cluster
			#TODO: find suitable course of action in this case
			#~ print 4
			return -1
		elif bs == bsu_X[0]:
			# if within same second, test how many steps ahead (can be negative)
			n_step = int(round((bu-bsu_X[1]) / AUX11_BU_STEP))
			#~ print 5
			return len(bsu_master)-1+n_step
	# last resort, manually check all existing references (possible duplication of n_step
	for idx in xrange(1,len(bsu_master)-1):
		if aux11_is_cluster(bs,bu,bsu_ref=bsu_master[idx])[0]:
			#~ print 6
			return idx
	#~ print 7
	return -1

def apply_per_atoh_channel_shift(Xs,shift_per_channel,truncate_invalid=False,in_128=True):
	"""
	Roll each channel along snapshots by given amounts.
	
	Arguments:
	----------
	Xs -- Spectrum snapshots as numpy array, zeroth dimension is along
	snapshots and first dimension is along frequency.
	shift_per_channel -- Array of shifts applied per channel.
	truncate_invalid -- Truncate the returned data to remove all wrapped
	content (default is False).
	in_128 -- Do a roll over each consecutive group of 128 snapshots (default
	is True). If True, then truncate_invalid is ignored.
	
	Returns:
	--------
	Xs_ret -- The spectral data after applying the necessary shifts and
	possibly truncation.
	
	Notes:
	------
	The shift per channel refers to the eight channels supplied in each
	VDIF-wrapped B-enginge packet.
	"""
	
	Xs_ret = zeros(Xs.shape,dtype=complex64)
	# apply shift per channel
	if (not in_128):
		for fid in range(SWARM_N_FIDS):
			for ch_id in range(SWARM_CHANNELS/(SWARM_N_FIDS*SWARM_XENG_PARALLEL_CHAN)):
				start_chan = ch_id*SWARM_N_FIDS*SWARM_XENG_PARALLEL_CHAN + fid*SWARM_N_FIDS
				for ii in range(SWARM_XENG_PARALLEL_CHAN):
					Xs_ret[:,start_chan+ii] = roll(Xs[:,start_chan+ii],shift_per_channel[ii],axis=0)
	else:
		N_passes = Xs.shape[0]/SWARM_TRANSPOSE_SIZE
		for ipass in range(N_passes):
			start_snap = ipass*SWARM_TRANSPOSE_SIZE
			stop_snap = start_snap + SWARM_TRANSPOSE_SIZE
			#~ for fid in range(SWARM_N_FIDS):
				#~ for ch_id in range(SWARM_CHANNELS/(SWARM_N_FIDS*SWARM_XENG_PARALLEL_CHAN)):
					#~ start_chan = ch_id*SWARM_N_FIDS*SWARM_XENG_PARALLEL_CHAN + fid*SWARM_N_FIDS
					#~ for ii in range(SWARM_XENG_PARALLEL_CHAN):
						#~ Xs_ret[start_snap:stop_snap,start_chan+ii] = roll(Xs[start_snap:stop_snap,start_chan+ii],shift_per_channel[ii],axis=0)
			for ii in range(SWARM_XENG_PARALLEL_CHAN):
				roll_idx = arange(ii,SWARM_CHANNELS,SWARM_XENG_PARALLEL_CHAN)
				Xs_ret[start_snap:stop_snap,roll_idx] = roll(Xs[start_snap:stop_snap,roll_idx],shift_per_channel[ii],axis=0)
	
	# truncate the data to remove wrapped content, ONLY if in_128 == False
	if (not in_128):
		if (truncate_invalid):
			min_shift = shift_per_channel.min()
			if (min_shift < 0):
				Xs_ret = Xs_ret[:min_shift,:]
			max_shift = shift_per_channel.max()
			if (max_shift > 0):
				Xs_ret = Xs_ret[max_shift:,:]
	
	return Xs_ret

def corrective_reordering(Xs,atoh_shift_vec=None,idx_shift_range=None):
	"""
	Reorder data so that it is correct.
	
	Arguments:
	----------
	Xs -- Spectra for phased sum
	atoh_shift_vec -- Shift-by-two within frame on half the channels
	idx_shift_range -- Shift-by-frame on half the windows, range that
	needs shifting as closed-left, open-right range (like in Python), 
	i.e. [a,b)
	
	Return:
	-------
	Xsc -- Corrected spectra for phased sum 0
	
	Notes:
	------
	Due to the nature of the corrective reordering the number of spectra
	in the returned values will be less than that in the arguments.
	"""
	
	Xsc = Xs

	if atoh_shift_vec is not None:
		# first do a-to-h channel shifts
		Xsc = apply_per_atoh_channel_shift(Xs,atoh_shift_vec,truncate_invalid=False,in_128=True)
	
	if idx_shift_range is not None:
		# do whole-spectrum shifts
		N_s = Xsc.shape[0]
		for jj in range(N_s/128):
			for ii in range(idx_shift_range[0],idx_shift_range[1]):
				if ii + 128*(jj+1) < N_s:
					Xsc[ii+128*jj,:] = Xsc[ii+128*(jj+1),:]
					Xsc[ii+128*(jj+1),:] = 1j*nan*zeros(Xsc.shape[1])
				
		# limit to only valid (after shifting)
		idx_end = nonzero(isnan(Xsc[:,0]))[0][0]
		Xsc = Xsc[:idx_end,:]
	
	return Xsc
	
def diagnose_window_offsets(Xs,Xr,offset):
	"""
	Determine which windows in each B-engine frame belong to the previous
	B-engine frame.
	
	Arguments:
	----------
	Xs -- SWARM spectra, after corrective ordering
	Xr -- Reference signal which correlates with corrected SWARM data
	offset -- Offset for cross-correlation, i.e. Xr[:-offset] will 
	correlate with Xs[offset:].
	
	Return:
	-------
	idx_shift -- 128-element array with False for windows in correct 
	B-engine frame, and True where windows need to be shifted
	s_peak_to_std_0 -- 128-element array containing peak-to-stddev ratio 
	for the FX cross-correlation computed in 128-window strides, starting
	at each index value.
	s_peak_to_std_1 -- Same as s_peak_to_std_0, but the SWARM data is
	shifted 128 (entire B-engine frame) back in time.

	Notes:
	-----
	So many to explain, but I'm lazy...
	"""
	import cross_corr
	
	s_peak_to_std_0 = zeros(128)
	for ii in range(128):
		s,S, = cross_corr.corr_Xt(Xr[ii:-offset:128,:],Xs[ii+offset::128,:])
		s_peak_to_std_0[ii] = s.max()/s.std()
	
	s_peak_to_std_1 = zeros(128)
	for ii in range(128):
		s,S, = cross_corr.corr_Xt(Xr[ii:-offset-128:128,:],Xs[ii+offset+128::128,:])
		s_peak_to_std_1[ii] = s.max()/s.std()
	
	idx_shift_ = s_peak_to_std_0 > mean((s_peak_to_std_0.max(),s_peak_to_std_0.min()))
	idx_shift = s_peak_to_std_1 > mean((s_peak_to_std_1.max(),s_peak_to_std_1.min()))
	# the two idx_shift truth-vectors should be complementary
	if (any(idx_shift & idx_shift_)):
		print "warning: result is not self-consistent"
	
	return idx_shift,s_peak_to_std_0,s_peak_to_std_1
