#!/usr/bin/env python
from argparse import ArgumentParser
from configparser import NoOptionError, NoSectionError, RawConfigParser
from datetime import datetime, timedelta
from socket import gethostname
from subprocess import call
from threading import Thread

from rtc_define import *

RECORD_COMMAND_TEMPLATE='record={0}:{1}:{2}:{3}:{4}:{5};'
SEND_TO_DA_CLIENT_TEMPLATE = 'echo \'{0}\' | da-client'
SEND_TO_REMOTE_DA_CLIENT_TEMPLATE = 'ssh {0} "echo \'{1}\' | da-client"'
USER_MAKR6 = "oper"
SEND_TO_PACCAP_CMD_TEMPLATE = 'echo \'{0}\' | paccap_cmd.py'
SEND_TO_REMOTE_PACCAP_CMD_TEMPLATE = 'ssh {0} "echo \'{1}\' | paccap_cmd.py"'
USER_SSIDDG = "oper"

def record_gigabytes_per_second(dut_type):
    if dut_type in ['r2dbe','r2dbe_sma']:
        return 2
    if dut_type in ['sdbe_8pac_11']:
        return 2. * 4576./4096. * (1056.*8+8.*7)/(8224.)
    raise ValueError("Invalid dut_type {0}".format(dut_type))

def get_call_str(dut_type,dut_host,dut_name,misc_exp,scan_time,scan_duration,scan_size,scan_name):
    if dut_type in ["r2dbe","sdbe_8pac_11"]:
        rec_cmd = RECORD_COMMAND_TEMPLATE.format(
            scan_time,
            scan_duration,
            scan_size,
            scan_name,
            misc_exp,
            dut_name
        )
        if gethostname() == dut_host:
            return SEND_TO_DA_CLIENT_TEMPLATE.format(rec_cmd)
        else:
            return SEND_TO_REMOTE_DA_CLIENT_TEMPLATE.format("@".join([USER_SSIDDG,dut_host]),rec_cmd)
    elif dut_type in ["r2dbe_sma"]:
        rec_cmd = RECORD_COMMAND_TEMPLATE.format(
            scan_time,
            1024, # number of packets to capture
            "dummy", # not used
            scan_name,
            misc_exp,
            dut_name
        )
        if gethostname() == dut_host:
            return SEND_TO_PACCAP_CMD_TEMPLATE.format(rec_cmd)
        else:
            return SEND_TO_REMOTE_PACCAP_CMD_TEMPLATE.format("@".join([USER_SSIDDG,dut_host]),rec_cmd)

if __name__ == "__main__":
    parser = ArgumentParser(description='Enque quick recording')
    parser.add_argument('-c','--config',metavar='FILE',type=str,default=CONFIG_FILENAME,
        help='read configuration from FILE')
    parser.add_argument('-d','--delay',metavar='SECONDS',type=int,default=60,
        help="delay recording by SECONDS seconds from time-of-call (default is 60)")
    parser.add_argument('-n','--named-scan',metavar='NAME',type=str,
        help="use NAME for the scan name, instead of timestamp")
    parser.add_argument('-t','--record-time',metavar='SECONDS',type=int,
        help="set the scan duration to SECONDS")
    args = parser.parse_args()
    
    # timestamp
    utc = datetime.utcnow()
    utc_scan = utc + timedelta(seconds=args.delay)
    scan_time = utc_scan.strftime(SCAN_TIME_FMT)
    scan_name = utc_scan.strftime(SCAN_NAME_FMT)
    if args.named_scan is not None:
        scan_name = args.named_scan
    
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
    scan_duration = int(rcp.get(CONFIG_SCAN_SECTION,CONFIG_SCAN_DURATION))
    if args.record_time:
        scan_duration = args.record_time
    scan_sizes = [scan_duration*record_gigabytes_per_second(dut_type) for dut_type in dut_types]
    scan_size = ','.join([str(int(scan_size*1000)/1000.) for scan_size in scan_sizes])
    scan_sizes = scan_size.split(",")
    
    # update config
    rcp.set(CONFIG_SCAN_SECTION,CONFIG_SCAN_NAME,scan_name)
    rcp.set(CONFIG_SCAN_SECTION,CONFIG_SCAN_SIZE,scan_size)
    rcp.set(CONFIG_SCAN_SECTION,CONFIG_SCAN_TIME,scan_time)
    rcp.set(CONFIG_SCAN_SECTION,CONFIG_SCAN_DURATION,scan_duration)
    out_cfg_filename = "conf/rtc_{0}_{1}.conf".format(misc_exp,scan_name)
    with open(out_cfg_filename,'w') as fh:
        rcp.write(fh)
    
    # submit record command
    threads = []
    for ii in range(len(dut_names)):
        dut_name = dut_names[ii]
        dut_host = dut_hosts[ii]
        dut_type = dut_types[ii]
        call_str = get_call_str(dut_type,dut_host,dut_name,misc_exp,scan_time,scan_duration,scan_sizes[ii],scan_name)
        print("Executing: {call}".format(call=call_str))
        threads.append(Thread(target=threaded_call,args=(call_str,)))
        threads[ii].start()
    for ii in range(len(dut_names)):
        threads[ii].join()

