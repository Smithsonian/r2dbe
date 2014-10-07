import sys
import logging
import argparse
from datetime import datetime
from itertools import combinations

import pylab
from numpy.fft import fftshift, rfft, irfft
from numpy import (
    pi, log10, angle, sqrt, real, conjugate, 
    split, arange, zeros_like
    )

import checks
from vdif import VDIFFrameHeader, VDIFFrame

# parse the user's command line arguments
parser = argparse.ArgumentParser(description='check a VDIF file for header/data quality')
parser.add_argument('-v', dest='verbose', action='store_true', help='display debugging logs')
parser.add_argument('-t', '--time', dest='tc_only', action='store_true', help='do the time-check only')
parser.add_argument('-s', '--skip-bytes', metavar="SKIP_BYTES", dest='skip_bytes', type=int, default=0,
                    help='if given the script will ignore the first SKIP_BYTES of file')
parser.add_argument('-n', '--frames-to-check', dest='frames_to_check', default=-1, 
                    type=int, help='number of frames (from the beginning) to check (default: all)')
parser.add_argument('filename', type=str, help='VDIF filename to check for quality')
args = parser.parse_args()

# create logger object
logger = logging.getLogger()
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

# set up the logging handler
handler = logging.StreamHandler()
quiet = logging.Formatter(fmt='%(message)s')
verbose = logging.Formatter(fmt='%(name)s - %(message)s')
handler.setFormatter(verbose if args.verbose else quiet)

# add handler to logger
logger.addHandler(handler)

# find current ref. epocj
today = datetime.today()
this_epoch = 2 * (today.year - 2000) + (today.month / 6)
logger.debug('current ref. epoch: {0}'.format(this_epoch))

# error-type checks
error_checks = (
    checks.CountNotEqualTo('non-null VDIF vers', 'vdif_vers', 0),
    checks.CountEqualTo('legacy mode frames', 'legacy_mode', True),
    checks.CountEqualTo('invalid data frames', 'invalid_data', True),
    checks.CountOutOfRange('out-of-range log2(chans)', 'log2_chans', 0, 31),
    checks.CountOutOfRange('out-of-range length', 'frame_length', 1, 2**23),
    checks.CountOutOfRange('invalid ref. epochs', 'ref_epoch', 0, this_epoch),
    checks.CountOutOfRange('out-of-range secs since epoch', 'secs_since_epoch', 0, 6*31*24*3600),
    checks.CountNotIncrementingBy('out-of-order frames', 'data_frame', 1),
    )

# sanity-type checks
sanity_checks = (
    checks.CountEqualTo('real-data frames', 'complex', False),
    checks.CountEqualTo('complex-data frames', 'complex', True),
    checks.ListingCheck('unique thread IDs found', 'thread_id'),
    checks.ListingCheck('unique station IDs found', 'station_id'),
    checks.ListingCheck('unique sample bitwidths found', 'bits_per_sample'),
    checks.ListingCheck('EDV versions found', 'eud_vers'),
    checks.CountNotEqualTo('Non-zero EUDs', 'eud', [0, 0, 0, 0]),
    )

# open the VDIF file
logger.debug('opening: {0}'.format(args.filename))
with open(args.filename, 'rb') as file_:

    # skip bytes if requested
    file_.seek(args.skip_bytes)

    # get the first VDIF header
    first_hdr = VDIFFrameHeader.from_bin(file_.read(32))
    logger.debug('first header: {0}'.format(repr(first_hdr)))

    # determine the packet size
    pkt_size = first_hdr.frame_length * 8
    logger.debug('packet size: {0} bytes'.format(pkt_size))

    # is pkt_size possbily too big?
    if pkt_size > 8224:
        logger.warning('packet size possibly too big. check start byte offset')

    # get the last VDIF header
    file_.seek(-pkt_size, 2)
    last_hdr = VDIFFrameHeader.from_bin(file_.read(32))
    logger.debug('last header: {0}'.format(repr(last_hdr)))

    # print out time-check info
    logger.info('start time: {0:%d %b %Y %Z %X.%f}'.format(first_hdr.datetime()))
    logger.info('stop time:  {0:%d %b %Y %Z %X.%f}'.format(last_hdr.datetime(end=True)))

    # exit if user wants only time check
    if args.tc_only:
        sys.exit()

    # must remember to seek back to start
    file_.seek(args.skip_bytes)
    
    # keep track of frame counts
    frame_n = 0

    # go through every frame
    end_of_frames = False
    while not end_of_frames:
    
        # read one packet
        pkt = file_.read(pkt_size)
    
        # check if we reached eof
        if not len(pkt) == pkt_size:
            logger.debug('reach eof for {0}'.format(file_.name))
            end_of_frames = True
            break

        # create frame object
        header = VDIFFrameHeader.from_bin(pkt)

        # go through every error-type check
        for check in error_checks:
            check(header)

        # go through every sanity-type check
        for check in sanity_checks:
            check(header)

        # increment frame count
        frame_n += 1

        # every so often tell user we're still alive
        if frame_n % 2048 == 0:
            logger.info('still alive! currently on frame {0}'.format(frame_n))

        # exit if we've check all requested frames
        if frame_n == args.frames_to_check:
            end_of_frames = True

    # tell user we finished
    logger.info('finished checking {0} frames. printing summary...'.format(frame_n))

    # show results from error-type checks
    logger.info('\nprinting error-type check results...')
    for i, check in enumerate(error_checks):
        logger.info('error-type  check #{0}. {1}'.format(i, check))

    # show results from sanity-type checks
    logger.info('\nprinting sanity-type check results...')
    for i, check in enumerate(sanity_checks):
        logger.info('sanity-type check #{0}. {1}'.format(i, check))

    # finish up
    logger.info('\nchecked quality for {0} frames of {1}'.format(frame_n, args.filename))
