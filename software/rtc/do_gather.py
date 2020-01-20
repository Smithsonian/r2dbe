#!/usr/bin/env python
from argparse import ArgumentParser
from configparser import NoOptionError, NoSectionError, RawConfigParser
from datetime import datetime, timedelta
from socket import gethostname
from time import sleep
from threading import Thread

from rtc_define import *

SCATTER_GATHER_FILENAME_TEMPLATE = "{0}_{1}_{2}.vdif"
SGLINEARIZE_TEMPLATE = "/home/oper/obs/bin/sglinearize.py -b 4 -s {0} -o {1} {2}"
REMOTE_SGLINEARIZE_TEMPLATE = "ssh {0} '/home/oper/obs/bin/sglinearize.py -b {4} -s {1} -o {2} {3}'"
COPY_TEMPLATE = "cp {0} {1}"
REMOTE_COPY_TEMPLATE = "scp {0}:{1} {2}"
UNPACK_8PAC_TEMPLATE = "python2 express_8unpac.py -n {2} {0} {1}"
RM_8PAC_TEMPLATE = "rm {0}"

def stride(dut_type):
    if dut_type == 'r2dbe':
        return -1
    elif dut_type == 'sdbe_8pac_11':
        return -1
    else:
        raise ValueError("Invalid dut_type {0}".format(dut_type))

def input_stream_paths(dut_type):
    if dut_type in ['r2dbe','sdbe_8pac_11']:
        if dut_type == 'r2dbe':
            mods = ['[12]','[34]']
        elif dut_type == 'sdbe_8pac_11':
            mods = ['1','2','3','4']
        return [ '/mnt/disks/{0}/?/data'.format(mod) for mod in mods ]
    elif dut_type in ['r2dbe_sma']:
        channels = ['0','1']
        return [ '/home/oper/data' for ch in channels ]
    else:
        raise ValueError("Invalid dut_type {0}".format(dut_type))
    

if __name__ == "__main__":
    parser = ArgumentParser(description='Linearize scatter-gather')
    parser.add_argument('-c','--config',metavar='FILE',type=str,default=CONFIG_FILENAME,
        help='read configuration from FILE')
    parser.add_argument('-n','--num-unpack',metavar="NPKT",type=int,default=32768,
        help='unpack this many B-engine packets (passed to -n parameter in express_8unpack.py, default is 32768)')
    parser.add_argument('-b','--num-blocks',metavar="NBLK",type=int,default=1,
        help='copy this many blocks per mk6 input stream (passed to -b parameter in sglinearize.py, default is 10)')
    args = parser.parse_args()
    
    # read config
    rcp = RawConfigParser()
    rcp.read(args.config)
    # misc
    misc_exp = rcp.get(CONFIG_MISC_SECTION,CONFIG_MISC_EXP)
    # dut
    dut_hosts = rcp.get(CONFIG_DUT_SECTION,CONFIG_DUT_HOST).split(',')
    dut_names = rcp.get(CONFIG_DUT_SECTION,CONFIG_DUT_NAME).split(',')
    dut_types = rcp.get(CONFIG_DUT_SECTION,CONFIG_DUT_TYPE).split(',')
    # scan
    scan_name = rcp.get(CONFIG_SCAN_SECTION,CONFIG_SCAN_NAME)
    scan_time = rcp.get(CONFIG_SCAN_SECTION,CONFIG_SCAN_TIME)
    scan_duration = int(rcp.get(CONFIG_SCAN_SECTION,CONFIG_SCAN_DURATION))
    # data
    data_path = rcp.get(CONFIG_DATA_SECTION,CONFIG_DATA_PATH)
    
    # wait until scan is done
    scan_done = datetime.strptime(scan_time,SCAN_TIME_FMT) + timedelta(seconds=scan_duration+3)
    now = datetime.utcnow()
    while datetime.utcnow() < scan_done:
        dsleep = (scan_done - now).seconds
        print("Scan not yet recorded, sleeping for {0} seconds...".format(dsleep))
        sleep(dsleep)
        print("...should be done now.")
        sleep(1)
    
    # submit the gathers
    threads = []
    n_thread = 0
    for jj in range(len(dut_names)):
        dut_name = dut_names[jj]
        dut_host = dut_hosts[jj]
        dut_type = dut_types[jj]
        if dut_type in ['r2dbe_sma']:
            # this device does not need gathering
            continue
        # create input file patterns
        sg_filename = SCATTER_GATHER_FILENAME_TEMPLATE.format(
            misc_exp,
            dut_name,
            scan_name
        )
        
        sg_paths = input_stream_paths(dut_type)
        for ii,sg_path in enumerate(sg_paths):
            input_pattern = '/'.join((sg_path,sg_filename))
            print(input_pattern)
            
            # create output filename
            out_filename = get_flatfile_filename(misc_exp,dut_name,scan_name,ii)
            out_path = '/'.join((data_path,out_filename))
            
            # linearize data
            if gethostname() == dut_host:
                call_str = SGLINEARIZE_TEMPLATE.format(stride(dut_type),out_path,input_pattern)
            else:
                call_str = REMOTE_SGLINEARIZE_TEMPLATE.format("@".join(["oper",dut_host]),stride(dut_type),out_path,input_pattern,args.num_blocks)
            threads.append(Thread(target=threaded_call,args=(call_str,)))
            threads[n_thread].start()
            n_thread += 1
    for nn in range(n_thread):
        threads[nn].join()
    
    # do the copies
    threads = []
    n_thread = 0
    for jj in range(len(dut_names)):
        dut_name = dut_names[jj]
        dut_host = dut_hosts[jj]
        dut_type = dut_types[jj]
        sg_paths = input_stream_paths(dut_type)
        for ii in range(len(sg_paths)):
            # get filename
            out_filename = get_flatfile_filename(misc_exp,dut_name,scan_name,ii)
            out_path = '/'.join((data_path,out_filename))
            
            # set destination
            dest = './'
            if dut_type == 'sdbe_8pac_11':
                dest = ''.join((dest,'8pac_'))
            dest = ''.join((dest,out_filename))
            
            # copy
            if gethostname() == dut_host:
                call_str = COPY_TEMPLATE.format(out_path,dest)
            else:
                call_str = REMOTE_COPY_TEMPLATE.format("@".join(["oper",dut_host]),out_path,dest)
            print("Executing: {call}".format(call=call_str))
            threads.append(Thread(target=threaded_call,args=(call_str,)))
            threads[n_thread].start()
            n_thread += 1
    for nn in range(n_thread):
        threads[nn].join()
    
    # do unpack, if necessary
    threads = []
    n_thread = 0
    for jj in range(len(dut_names)):
        dut_name = dut_names[jj]
        dut_type = dut_types[jj]
        if dut_type != 'sdbe_8pac_11':
            continue
        
        sg_paths = input_stream_paths(dut_type)
        for ii in range(len(sg_paths)):
            # get filename
            out_filename = get_flatfile_filename(misc_exp,dut_name,scan_name,ii)
            in_filename = ''.join(('./8pac_',out_filename))
            
            call_str = UNPACK_8PAC_TEMPLATE.format(in_filename,out_filename,args.num_unpack)
            threads.append(Thread(target=threaded_call,args=(call_str,)))
            threads[n_thread].start()
            n_thread += 1
    for nn in range(n_thread):
        threads[nn].join()
    
    # delete 8pac files
    threads = []
    n_thread = 0
    for jj in range(len(dut_names)):
        dut_name = dut_names[jj]
        dut_type = dut_types[jj]
        if dut_type != 'sdbe_8pac_11':
            continue
        
        sg_paths = input_stream_paths(dut_type)
        for ii in range(len(sg_paths)):
            # get filename
            in_filename = get_flatfile_filename(misc_exp,dut_name,scan_name,ii)
            in_filename = ''.join(('./8pac_',in_filename))
            
            call_str = RM_8PAC_TEMPLATE.format(in_filename)
            threads.append(Thread(target=threaded_call,args=(call_str,)))
            threads[n_thread].start()
            n_thread += 1
    for nn in range(n_thread):
        threads[nn].join()
    
    # finally, move all VDIF files to ./dat
    threaded_call("mv *{exp}*{name}*.vdif ./dat".format(exp=misc_exp,name=scan_name))
