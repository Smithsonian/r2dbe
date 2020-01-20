#!/usr/bin/env python
from argparse import ArgumentParser
from configparser import NoOptionError, NoSectionError, RawConfigParser
from datetime import datetime, timedelta
from socket import gethostname
from subprocess import call
from time import sleep
from threading import Thread

import numpy as np
#import scipy.interpolate as ip

import matplotlib.pyplot as plt

import cross_corr
import read_r2dbe_vdif
import read_sdbe_vdif
import swarm

import sys

from rtc_define import *

if __name__ == "__main__":
    parser = ArgumentParser(description='Do cross-correlation')
    parser.add_argument('-c','--config',metavar='FILE',type=str,default=CONFIG_FILENAME,
        help='read configuration from FILE')
    args = parser.parse_args()
    
    # read config
    rcp = RawConfigParser()
    rcp.read(args.config)
    # misc
    misc_exp = rcp.get(CONFIG_MISC_SECTION,CONFIG_MISC_EXP)
    # corr
    corr_sets = rcp.get(CONFIG_CORR_SECTION,CONFIG_CORR_SETS).split(',')
    # scan
    scan_name = rcp.get(CONFIG_SCAN_SECTION,CONFIG_SCAN_NAME)
    
    chan_freq = np.fft.fftfreq(32768,1./4576e6)[:16384]
    idx_freq = np.nonzero(np.bitwise_and(chan_freq > 150e6, chan_freq < 2150e6))[0]
    lim_freq = [chan_freq[idx_freq[ii]]/1e6 for ii in [0,-1]]
    fh_autos = plt.figure()
    fh_histo = plt.figure()
    sbplt = 1
    
    print("Processing {0}_{1}".format(misc_exp,scan_name))
    for icorr,cs in enumerate(corr_sets):
        config_corrN_section = CONFIG_CORRN_SECTION_FMT.format(int(cs))
        sdbe_name,sdbe_receiver = rcp.get(config_corrN_section,CONFIG_CORRN_SDBE).split(',')
        print("Check #{0} of {2}: {1}".format(icorr+1,sdbe_name,len(corr_sets)))
        
        # read SBDE data
        print("   read SBDE data")
        st = None
        X_sdbe = None
        N_sdbe_frames = 512
        for ii in [0,1,2,3]:#range(4):
            sdbe_filename = "/".join(["dat",get_flatfile_filename(misc_exp,sdbe_name,scan_name,ii)])
            #~ _X_sdbe,tmp_sdbe = swarm.read_spectra_from_file_cf_no_b(sdbe_filename,N_sdbe_frames)
            #~ if X_sdbe is None:
                #~ X_sdbe = _X_sdbe[sdbe_receiver,:,:]
            #~ else:
                #~ X_sdbe = X_sdbe + _X_sdbe[sdbe_receiver,:,:]
            if st is None:
                st,rt = swarm.read_stream_from_file(sdbe_filename,N_sdbe_frames)
            else:
                st,rt = swarm.read_stream_from_file(sdbe_filename,N_sdbe_frames,ref_time=rt,stream=st)
            #~ print rt
        sdbe_t0 = str(rt)
        X_s = swarm.stream_to_spectra(st)
        X_sdbe = X_s[int(sdbe_receiver),:,:]
        S_s = (X_s * X_s.conj()).mean(axis=1).transpose()
        xx = X_s[:,:,idx_freq]
        xx = np.concatenate((xx.real,xx.imag),axis=-1).astype(np.int8).reshape((2,-1)).transpose()
        yy = [np.histogram(xx[:,ii],[-2.5,-1.5,-0.5,0.5,1.5]) for ii in range(2)]
        zz = np.array([yy[ii][0].astype(float)/yy[ii][0].sum() for ii in range(2)]).transpose()

        plt.figure(fh_autos.number)
        plt.subplot(len(corr_sets),1,sbplt)
        plt.plot(chan_freq/1e6,S_s)
        if sbplt == 2:
            plt.xlabel("Frequency [MHz]")
        plt.ylabel("Power spectrum magnitude")
        plt.legend(("RxA","RxB"))
        plt.title("{0}".format(sdbe_name))

        plt.figure(fh_histo.number)
        plt.subplot(len(corr_sets),1,sbplt)
        [plt.bar(np.array([-2,-1,0,1])+[-0.25,0][ii],zz[:,ii],width=0.25,color='bg'[ii]) for ii in range(2)]
        plt.ylim((0,1))
        plt.grid()
        plt.xticks((-2,-1,0,1))
        if sbplt == 2:
            plt.xlabel("2-bit state")
        plt.ylabel("Fraction")
        plt.title("{0}".format(sdbe_name))

        sbplt += 1

    plt.show()
