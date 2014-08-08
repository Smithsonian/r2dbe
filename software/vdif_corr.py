import logging
import argparse
from itertools import combinations

import pylab
from numpy.fft import fftshift, rfft, irfft
from numpy import (
    pi, log10, angle, sqrt, real, conjugate, 
    split, arange, zeros_like
    )

from vdif import VDIFFrameHeader, VDIFFrame

# parse the user's command line arguments
parser = argparse.ArgumentParser(description='Simulate VDIF data from multiple stations')
parser.add_argument('-v', dest='verbose', action='store_true', help='display debugging logs')
parser.add_argument('--nfft', dest='NFFT', default=1024, type=int, help='size of FFT to use')
parser.add_argument('-n', '--frames-to-check', dest='frames_to_check', default=-1, 
                    type=int, help='number of frames (from the beginning) to check (default: all)')
parser.add_argument('files', type=str, nargs='+', help='VDIF files with data to correlate')
args = parser.parse_args()

# set up some basic logging
logging.basicConfig(format='%(asctime)-15s - %(message)s')
logger = logging.getLogger('vdif_corr')
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
 
# open all files into a list
logger.debug('opening files for reading')
files = list(open(filename, 'rb') for filename in args.files)

# get the first VDIF headers for all files
logger.debug('grabbing first header from every file')
first_hdrs = list(VDIFFrameHeader.from_bin(file_.read(32)) for file_ in files)

# must remember to seek all back to zero
logger.debug('seeking back to zero before parsing files')
for file_ in files:
    file_.seek(0)

# set some global values (from first header)
ref_epoch = first_hdrs[0].ref_epoch
legacy_mode = first_hdrs[0].legacy_mode
frame_length = first_hdrs[0].frame_length
bits_per_sample = first_hdrs[0].bits_per_sample

# do some sanity checks
for hdr in first_hdrs:

    # print station ID's
    logger.info('found station ID#{0}'.format(hdr.station_id))

    # check all have the same reference epoch
    if not hdr.ref_epoch == ref_epoch:
        err_msg = 'mismatched ref_epoch {0}, expected {1}'.format(hdr.ref_epoch, ref_epoch)
        logger.error(err_msg)
        raise ValueError(err_msg)

    # check all have same legacy mode
    if not hdr.legacy_mode == legacy_mode:
        err_msg = 'mismatched legacy_mode {0}, expected {1}'.format(hdr.legacy_mode, legacy_mode)
        logger.error(err_msg)
        raise ValueError(err_msg)

    # check all frame lengths are the same
    if not hdr.frame_length == frame_length:
        err_msg = 'mismatched frame_length {0}, expected {1}'.format(hdr.frame_length, frame_length)
        logger.error(err_msg)
        raise ValueError(err_msg)

    # check all have the same sample bitwidth
    if not hdr.bits_per_sample == bits_per_sample:
        err_msg = 'mismatched bits_per_sample {0}, expected {1}'.format(hdr.bits_per_sample, bits_per_sample)
        logger.error(err_msg)
        raise ValueError(err_msg)

# determine the packet size
pkt_size = (16 if legacy_mode else 32) + frame_length * 8
logger.debug('packet size: {0} bytes'.format(pkt_size))

# determine frame offsets needed to correlate
frame_offsets = list(-hdr.data_frame + first_hdrs[0].data_frame for hdr in first_hdrs)
frame_offsets = list(off + abs(min(frame_offsets)) for off in frame_offsets)
logger.debug('frame offsets determined: {0}'.format(frame_offsets))

# seek forward files by their offsets
for i, file_ in enumerate(files):
    file_.seek(frame_offsets[i] * pkt_size)

# set some initial values
autos = {}
cross = {}
elements = list(file_.name for file_ in files)
baselines = list(combinations(elements, 2)) + list((e, e) for e in elements)

# keep track of frame counts
frame_n = 0

# go through every frame
end_of_frames = False
while not end_of_frames:

    # grab a single packet from each file
    spectra = dict((file_.name, None) for file_ in files)
    for file_ in files:

        # read one packet
        pkt = file_.read(pkt_size)

        # check if we reached eof
        if not len(pkt) == pkt_size:
            logger.debug('reach eof for {0}'.format(file_.name))
            end_of_frames = True
            break

        # create frame object
        frame = VDIFFrame.from_bin(pkt)

        # do an FFT on each frame
        spectra[file_.name] = rfft(split(frame.data, len(frame.data)/args.NFFT), axis=1)

    # integrate the cross spectra
    if not end_of_frames:
        for baseline in baselines:
            left = spectra[baseline[0]]
            right = spectra[baseline[1]]
            prod = (left * conjugate(right)).sum(axis=0)
            if baseline[0] == baseline[1]:
                part_autos = autos.get(baseline[0], zeros_like(prod))
                autos[baseline[0]] = part_autos + prod
            else:
                part_cross = cross.get(baseline, zeros_like(prod))
                cross[baseline] = part_cross + prod

    # increment frame count
    frame_n += 1

    # every so often tell user we're still alive
    if frame_n % 2048 == 0:
        logger.info('still alive! currently on frame {0}'.format(frame_n))

    # exit if we've check all requested frames
    if frame_n == args.frames_to_check:
        end_of_frames = True

# plot the auto spectra
pylab.figure()
for name, auto in autos.iteritems():
    pylab.plot(10*log10(abs(auto)), label=name)
pylab.xlim(0, args.NFFT/2)
pylab.legend()

# plot the cross phase spectra
for baseline in cross:
    pylab.figure()
    pylab.plot(angle(cross[baseline]), '.', label='{0} X {1}'.format(*baseline))
    pylab.xlim(0, args.NFFT/2)
    pylab.ylim(-pi, pi)
    pylab.legend()

# plot the cross lags
for baseline in cross:
    pylab.figure()
    norm = sqrt(real(irfft(autos[baseline[0]]).max() * irfft(autos[baseline[1]]).max()))
    corr_coeff = fftshift(irfft(cross[baseline]))/norm
    peak = corr_coeff.max().real
    noise = corr_coeff.sum().real / len(corr_coeff)
    snr = 10*log10(peak/noise)
    lags = arange(-len(corr_coeff)/2, len(corr_coeff)/2)
    delay = lags[corr_coeff.argmax()]
    pylab.plot(lags, corr_coeff)
    pylab.title('{0} (x) {1}'.format(*baseline))
    pylab.annotate('\nCorr. coef.:{0:.2f}\nSNR: {1:.2f} dB\nDelay: {2} samples'.format(peak, snr, delay), 
                   xy=(delay, peak), xytext=(0.8, 0.8), textcoords='axes fraction', backgroundcolor='white',
                   arrowprops=dict(facecolor='black', width=0.1, headwidth=4, shrink=0.1))
    pylab.xlim(-args.NFFT/32, args.NFFT/32)

# show all plots
pylab.show()

# close all files in the list
logger.debug('closing all open files')
for file_ in files: 
    file_.close()
