#!/usr/bin/env python
from argparse import ArgumentParser
from configparser import NoOptionError, NoSectionError, RawConfigParser
from datetime import datetime, timedelta
from socket import gethostname
from subprocess import call
from time import sleep
from threading import Thread

from multiprocessing import Process

import numpy as np
#import scipy.interpolate as ip

import matplotlib.pyplot as plt

import cross_corr
import read_r2dbe_vdif
import read_sdbe_vdif
import swarm

import sys

from rtc_define import *

def _corr_iter(rcp, misc_exp, corr_sets, scan_name, icorr, cs):
    if True:
        config_corrN_section = CONFIG_CORRN_SECTION_FMT.format(int(cs))
        r2dbe_name,r2dbe_stream = rcp.get(config_corrN_section,CONFIG_CORRN_R2DBE).split(',')
        sdbe_name,sdbe_receiver = rcp.get(config_corrN_section,CONFIG_CORRN_SDBE).split(',')
        print("Cross-correlation #{0} of {3}: {1}.if{4} x {2}.rx{5}".format(icorr+1,r2dbe_name,sdbe_name,len(corr_sets),r2dbe_stream,['A','B'][int(sdbe_receiver)]))
        
        solution_sdbe_sample_lead = 0
        if rcp.has_option(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_SAMPLE_LEAD):
            solution_sdbe_sample_lead = int(rcp.get(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_SAMPLE_LEAD))
            print("   using prior sample delay {0}".format(solution_sdbe_sample_lead))
        solution_sdbe_window_lag = 0
        if rcp.has_option(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_WINDOW_LAG):
            solution_sdbe_window_lag = int(rcp.get(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_WINDOW_LAG))
            print("   using prior window {0}".format(solution_sdbe_window_lag))
        solution_phase_slope = 0.0
        if rcp.has_option(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_PHASE_SLOPE):
            solution_phase_slope = float(rcp.get(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_PHASE_SLOPE))
            print("   using prior phase slope {0}".format(solution_phase_slope))
        
        # read R2DBE data
        r2dbe_filename = get_flatfile_filename(misc_exp,r2dbe_name,scan_name,r2dbe_stream)
        print("   read R2DBE data")
        N_r2dbe_frames = 1024
        x_r2dbe,v_r2dbe = read_r2dbe_vdif.read_from_file("/".join(['dat',r2dbe_filename]),N_r2dbe_frames)
        r2dbe_t0 = "{0}+{1}".format(v_r2dbe.secs_since_epoch,v_r2dbe.data_frame)
        X_r2dbe = np.fft.fft(x_r2dbe.reshape((-1,32768)),axis=1)
        S_r2dbe = (X_r2dbe * X_r2dbe.conj()).mean(axis=0)
        S_r2dbe[0] = 0
        f_r2dbe = 4096e6*np.arange(0,S_r2dbe.size)/S_r2dbe.size
        
        # interpolate R2DBE data at 11/11 SWARM rate
        print("   interpolate R2DBE data at 11/11 SWARM rate")
        t_r2dbe = np.arange(0,x_r2dbe.size)/4096e6
        t_sdbe = np.arange(0,x_r2dbe.size)/4576e6
        #ip_r2dbe = ip.interp1d(t_r2dbe,x_r2dbe,kind='linear')
        #x_r2dbe_ip = np.roll(ip_r2dbe(t_sdbe),-solution_sdbe_sample_lead)
        x_r2dbe_ip = np.interp(t_sdbe,t_r2dbe,x_r2dbe)
        X_r2dbe_ip = np.fft.fft(x_r2dbe_ip.reshape((-1,32768)),axis=1)
        S_r2dbe_ip = (X_r2dbe_ip * X_r2dbe_ip.conj()).mean(axis=0)
        S_r2dbe_ip[0] = 0
        
        # read SBDE data
        print("   read SBDE data")
        st = None
        X_sdbe = None
        N_sdbe_frames = 4096
        for ii in [0,1,2,3]:#range(4):
            sdbe_filename = get_flatfile_filename(misc_exp,sdbe_name,scan_name,ii)
            #~ _X_sdbe,tmp_sdbe = swarm.read_spectra_from_file_cf_no_b(sdbe_filename,N_sdbe_frames)
            #~ if X_sdbe is None:
                #~ X_sdbe = _X_sdbe[sdbe_receiver,:,:]
            #~ else:
                #~ X_sdbe = X_sdbe + _X_sdbe[sdbe_receiver,:,:]
            if st is None:
                st,rt = swarm.read_stream_from_file('/'.join(['dat',sdbe_filename]),N_sdbe_frames)
            else:
                st,rt = swarm.read_stream_from_file('/'.join(['dat',sdbe_filename]),N_sdbe_frames,ref_time=rt,stream=st)
            #~ print rt
        sdbe_t0 = str(rt)
        X_sdbe = swarm.stream_to_spectra(st)[int(sdbe_receiver),:,:]
        # apply corrective data-reordering
        atoh_shift_vec = np.array([0,0,0,0,0,0,0,0])
        idx_shift_range = None#np.array([70,128])
        X_sdbe = read_sdbe_vdif.corrective_reordering(X_sdbe,atoh_shift_vec,idx_shift_range)
        X_sdbe = X_sdbe * np.exp(-1j*solution_phase_slope*np.arange(16384)/16384)
        f_sdbe = 4576e6/2*np.arange(0,16384)/16384
        S_sdbe = (X_sdbe * X_sdbe.conj()).mean(axis=0)
        
        # remove DC
        print("   removing DC in full spectra")
        X_r2dbe_ip[:,[0]] = 0
        X_sdbe[:,[0]] = 0
        
        # cross-correlate over wide window with lower averaging
        print("   cross-correlate over wide search")
        r = np.arange(-256,257) + solution_sdbe_window_lag
        print("X_r2dbe_ip.shape = %s" % str(X_r2dbe_ip.shape))
        print("X_sdbe.shape = %s" % str(X_sdbe.shape))
        s_0x1,S_0x1,s_peaks = cross_corr.corr_Xt_search(X_r2dbe_ip[:,:16384],X_sdbe,fft_window_size=32768,search_range=r,search_avg=128)
        noise = s_0x1[s_peaks.argmax(),:].std()
        signal = abs(s_0x1[s_peaks.argmax(),:]).max()
        peak_window = r[s_peaks.argmax()]
        print("   cross-correlation peak of {1:.3f} with SNR of {0:.2f} in window {2}".format(signal/noise,signal,peak_window))
        
        plt.figure()
        plt.subplot(2,2,1)
        plt.plot(r,s_peaks)
        plt.xlabel('FFT window offset')
        plt.ylabel('Cross-correlation amplitude')
        plt.title('Peak per window: {0}:if{1} x {2}:rx{3}'.format(r2dbe_name,r2dbe_stream,sdbe_name,['A','B'][int(sdbe_receiver)]))
        #~ plt.title('Maximum cross-correlation peak per window: {0}:if{1} x {2}:rx{3}'.format(r2dbe_name,r2dbe_stream,sdbe_name,sdbe_receiver))
        
        plt.subplot(2,2,2)
        plt.plot(s_0x1[s_peaks.argmax(),])
        plt.xlabel('Sample offset')
        plt.ylabel('Cross-correlation amplitude')
        plt.title('Max peak window: {0}:if{1} x {2}:rx{3}'.format(r2dbe_name,r2dbe_stream,sdbe_name,['A','B'][int(sdbe_receiver)]))
        #~ plt.title('Cross-correlation in window with highest peak: {0}:if{1} x {2}:rx{3}'.format(r2dbe_name,r2dbe_stream,sdbe_name,sdbe_receiver))
        
        # cross-correlate over narrow window with higher averaging
        print("   cross-correlate over narrow search")
        r_ = np.arange(-4,5) + peak_window #+ Offset_beng_frames*128
        s_0x1_,S_0x1_,s_peaks_ = cross_corr.corr_Xt_search(X_r2dbe_ip[:,:16384],X_sdbe,fft_window_size=32768,search_range=r_,search_avg=256)
        
        plt.subplot(2,1,2)
        f = np.arange(16384)
        for fid in range(8):
            if fid < 7:
                m = 'x'
            else:
                m = '+'
            plt.plot(f[swarm.channel_index_by_fid(fid)],np.abs(S_0x1_[s_peaks_.argmax(),swarm.channel_index_by_fid(fid)]),m,label='fid {0}'.format(fid))
        plt.xlabel('Channel number')
        plt.ylabel('Cross-power spectrum magnitude')
        plt.title('Max peak spectrum: {0}:if{1} x {2}:rx{3}'.format(r2dbe_name,r2dbe_stream,sdbe_name,['A','B'][int(sdbe_receiver)]))
        #~ plt.title('Cross-power spectrum in window with highest peak: {0}:if{1} x {2}:rx{3}'.format(r2dbe_name,r2dbe_stream,sdbe_name,sdbe_receiver))
        plt.legend()
        
        # update config with solution
        rcp.set(config_corrN_section,CONFIG_CORRN_R2DBE_FIRST_SAMPLE,r2dbe_t0)
        rcp.set(config_corrN_section,CONFIG_CORRN_SDBE_FIRST_SAMPLE,sdbe_t0)
        solution_sdbe_window_lag = r[s_peaks.argmax()]
        rcp.set(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_WINDOW_LAG,solution_sdbe_window_lag)
        peak_three = s_peaks[s_peaks.argmax()-1:s_peaks.argmax()+2]
        noise_three = s_0x1[s_peaks.argmax()-1:s_peaks.argmax()+2,:].std(axis=-1)
        if abs(s_0x1[s_peaks.argmax(),:]).argmax() > 16384:
            solution_sdbe_sample_lead = abs(s_0x1[s_peaks.argmax(),:]).argmax()-32768+solution_sdbe_sample_lead
        else:
            solution_sdbe_sample_lead = abs(s_0x1[s_peaks.argmax(),:]).argmax()+solution_sdbe_sample_lead
        rcp.set(config_corrN_section,CONFIG_CORRN_PRIOR_SDBE_SAMPLE_LEAD,solution_sdbe_sample_lead)
        rcp.set(config_corrN_section,CONFIG_CORRN_COEFF,signal)
        rcp.set(config_corrN_section,CONFIG_CORRN_SNR,signal/noise)
        real_time_r2dbe = v_r2dbe.secs_since_epoch + v_r2dbe.data_frame/125000.0
        real_time_sdbe = rt.sec + rt.clk/286e6 + (32768*(solution_sdbe_window_lag)-solution_sdbe_sample_lead)/4576e6
        print("Relative lag: {0}".format(real_time_sdbe - real_time_r2dbe))
        plt.show()

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
    
    print("Processing {0}_{1}".format(misc_exp,scan_name))
    
    procs = []
    for icorr,cs in enumerate(corr_sets):
        procs.append(Process(target=_corr_iter, args=(rcp, misc_exp, corr_sets, scan_name, icorr, cs)))
    [p.start() for p in procs]
    # write solution to scan-specific configuration file
    out_cfg_filename = "conf/rtc_{0}_{1}.conf".format(misc_exp,scan_name)
    print("Saving solution to configuration file '{0}'".format(out_cfg_filename))
    with open(out_cfg_filename,'w') as fh_out:
        rcp.write(fh_out)
    
    
