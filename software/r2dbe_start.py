import adc5g, corr
from time import sleep
from datetime import datetime, time, timedelta
import netifaces as ni
from socket import inet_ntoa
from struct import pack
import subprocess
import sys

import argparse
parser = argparse.ArgumentParser(description='Set 2-bit quantization threshold')
parser.add_argument('-b','--boffile',metavar='BOFFILE',type=str,default='r2dbe_rev2.bof',
    help="program the fpga with BOFFILE (default is 'r2dbe_rev2.bof')")
parser.add_argument('-f','--file',metavar="CONFIG",type=str,default=None,
    help="read configuration from file CONFIG, if None then use default values hard-coded in script (default is None)")
parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
    help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
parser.add_argument('-v','--verbose',action='count',
    help="control verbosity, use multiple times for more detailed output")
parser.add_argument('host',metavar='R2DBE',type=str,nargs='?',default='r2dbe-1',
    help="hostname or ip address of r2dbe (default is 'r2dbe-1')")
args = parser.parse_args()

is_test = 0

# polarization configuration constants
_POL_XL = 0
_POL_YR = 1
_POL_CHAR_TO_FLAG = {
    'L':_POL_XL,
    'X':_POL_XL,
    '0':_POL_XL,
    'R':_POL_YR,
    'Y':_POL_YR,
    '1':_POL_YR
}
# BDC sideband configuration constants
_BDC_LSB = 0
_BDC_USB = 1
_BDC_CHAR_TO_FLAG = {
    'L':_BDC_LSB,
    '0':_BDC_LSB,
    'U':_BDC_USB,
    '1':_BDC_USB
}
# receiver sideband configuration constants
_REC_LSB = 0
_REC_USB = 1
_REC_CHAR_TO_FLAG = {
    'L':_REC_LSB,
    '0':_REC_LSB,
    'U':_REC_USB,
    '1':_REC_USB
}

_DEFAULT_CONFIG = {
    'if0':
        {'station_id':'lh','pol':'1','bdc_sideband':'0','rec_sideband':'0'},
    'if1':
        {'station_id':'ll','pol':'1','bdc_sideband':'0','rec_sideband':'0'}
}

config = _DEFAULT_CONFIG
if args.file is not None:
    from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
    rcp = RawConfigParser()
    if rcp.read(args.file):
        if args.verbose > 1:
            print "reading configuration from file '{0}'".format(args.file)
        for sec in ['if0','if1']:
            for key in ['station_id','pol','bdc_sideband','rec_sideband']:
                try:
                    config[sec][key] = rcp.get(sec,key)
                except (NoOptionError, NoSectionError) as e:
                    print "WARNING: <{0}.{1}> not in configuration file, using default value '{2}'".format(
                        sec,key,config[sec][key])
    else:
        msg = "Could not read configuration form file '{0}'".format(args.file)
        raise RuntimeError(msg)

station_id_0 = config['if0']['station_id']
station_id_1 = config['if1']['station_id']

# set pol for both blocks
# dual pol
# 0 is X or L
# 1 is Y or R
pol_block0 = _POL_CHAR_TO_FLAG[config['if0']['pol']]
pol_block1 = _POL_CHAR_TO_FLAG[config['if1']['pol']]

# set EHT BDC sideband
bdc_sb0 = _BDC_CHAR_TO_FLAG[config['if0']['bdc_sideband']]
bdc_sb1 = _BDC_CHAR_TO_FLAG[config['if1']['bdc_sideband']]

# set RX sideband
rec_sb0 = _REC_CHAR_TO_FLAG[config['if0']['rec_sideband']]
rec_sb1 = _REC_CHAR_TO_FLAG[config['if1']['rec_sideband']]

# set thread id for both blocks
# perhaps thread is always 0?
thread_id_0 = 0
thread_id_1 = 0

if args.verbose > 0:
    print "################## Configuration for {0} ##################".format(args.host)
    print ""
    print "[if0]"
    print "station_id={0}".format(station_id_0)
    print "pol={0}".format(pol_block0)
    print "bdc_sideband={0}".format(bdc_sb0)
    print "rec_sideband={0}".format(rec_sb0)
    print ""
    print "[if1]"
    print "station_id={0}".format(station_id_1)
    print "pol={0}".format(pol_block1)
    print "bdc_sideband={0}".format(bdc_sb1)
    print "rec_sideband={0}".format(rec_sb1)
    print ""
    print "########################### {0} ###########################".format(args.host)

# connect to roach2
roach2 = corr.katcp_wrapper.FpgaClient(args.host)
if not roach2.wait_connected(timeout=args.timeout):
    msg = "Could not establish connection to '{0}' within {1} seconds, aborting".format(
        args.host,args.timeout)
    raise RuntimeError(msg)
if args.verbose > 1:
    print "connected to '{0}'".format(args.host)
# program bitcode
roach2.progdev(args.boffile)
if not roach2.wait_connected(timeout=args.timeout):
    msg = "Could not establish connection to '{0}' within {1} seconds, aborting".format(
        args.host,args.timeout)
    raise RuntimeError(msg)
if args.verbose > 1:
    print "programmed bitcode '{0}'".format(args.boffile)


# set data mux to ADC
roach2.write_int('r2dbe_data_mux_0_sel', 1)
roach2.write_int('r2dbe_data_mux_1_sel', 1)

# calibrate ADCs
adc5g.set_test_mode(roach2, 0)
adc5g.set_test_mode(roach2, 1)
adc5g.sync_adc(roach2)
opt, glitches = adc5g.calibrate_mmcm_phase(roach2, 0, ['r2dbe_snap_8bit_0_data',])
print opt, glitches
opt, glitches = adc5g.calibrate_mmcm_phase(roach2, 1, ['r2dbe_snap_8bit_1_data',])
print opt, glitches
adc5g.unset_test_mode(roach2, 0)
adc5g.unset_test_mode(roach2, 1)

# arm the one pps
roach2.write_int('r2dbe_onepps_ctrl', 1<<31)
roach2.write_int('r2dbe_onepps_ctrl', 0)
sleep(2)

# set 10 gbe vals

arp = [0xffffffffffff] * 256
mac_eth3 = ni.ifaddresses('eth3')[17][0]['addr']
mac_hex3  = int(mac_eth3.translate(None,':'),16)
mac_eth5 = ni.ifaddresses('eth5')[17][0]['addr']
mac_hex5  = int(mac_eth5.translate(None,':'),16)


arp[3] = mac_hex3
arp[5] = mac_hex5

# can be entered manually
#arp[3] = 0x0060dd448941 # mac address of mark6-4015 eth3
#arp[5] = 0x0060dd44893b # mac address of mark6-4015 eth5

ip = ni.ifaddresses('eth3')[2][0]['addr']
ipb = [x for x in map(str.strip, ip.split('.'))]

ip_b3 = int(ipb[0])
ip_b2 = int(ipb[1])
ip_b0 = int(ipb[3])


# can be entered manually
#ip_b3 = 172
#ip_b2 = 16
#ip_b0 = 15 #should be last 2 digits of name: Mark6-40**

for i, name in ((3, 'tengbe_0'), (5, 'tengbe_1')):

    src_ip  = (ip_b3<<24) + (ip_b2<<16) + ((i*10)<<8) + ip_b0
    src_mac = (2<<40) + (2<<32) + 20 + src_ip
    src_port = 4000
    dest_ip = (ip_b3<<24) + (ip_b2<<16) + (i<<8) + ip_b0
    dest_port = 4001

    roach2.config_10gbe_core('r2dbe_' + name + '_core', src_mac, src_ip, src_port, arp)
    roach2.write_int('r2dbe_' + name + '_dest_ip', dest_ip)
    roach2.write_int('r2dbe_' + name + '_dest_port', dest_port)

    # reset tengbe (this is VITAL)
    roach2.write_int('r2dbe_' + name + '_rst', 1)
    roach2.write_int('r2dbe_' + name + '_rst', 0)
    
    if args.verbose > 1:
        print "{4}: {0}:{1} --> {2}:{3}".format(
            inet_ntoa(pack('!I',src_ip)),src_port,
            inet_ntoa(pack('!I',dest_ip)),dest_port,
            name)

#######################################
# set headers
#######################################
# calculate reference epoch
utcnow = datetime.utcnow()
ref_start = datetime(2000,1,1,0,0,0)

nyrs = utcnow.year - ref_start.year 
ref_ep_num = 2*nyrs+1*(utcnow.month>6)

ref_ep_date = datetime(utcnow.year,6*(utcnow.month>6)+1,1,0,0,0) # date of start of epoch July 1 2014

##############
#   W0
##############

roach2.write_int('r2dbe_vdif_0_hdr_w0_reset',1)
roach2.write_int('r2dbe_vdif_1_hdr_w0_reset',1)

# wait until middle of second for calculation
while(abs(datetime.utcnow().microsecond-5e5)>1e5):
    sleep(0.1)
   
# rapidly calculate current time and reset hdr (~10 ms) 
delta       = datetime.utcnow()-ref_ep_date
sec_ref_ep  = delta.seconds + 24*3600*delta.days

roach2.write_int('r2dbe_vdif_0_hdr_w0_reset',0)
roach2.write_int('r2dbe_vdif_1_hdr_w0_reset',0)

roach2.write_int('r2dbe_vdif_0_hdr_w0_sec_ref_ep',sec_ref_ep)
roach2.write_int('r2dbe_vdif_1_hdr_w0_sec_ref_ep',sec_ref_ep)

if args.verbose > 1:
    print "VDIF start time is {0:d}@{1:d}+{2:06d}".format(
        ref_ep_num,sec_ref_ep,0)

#############
#   W1
#############
#print "reference epoch number: %d" %ref_ep_num
roach2.write_int('r2dbe_vdif_0_hdr_w1_ref_ep',ref_ep_num)
roach2.write_int('r2dbe_vdif_1_hdr_w1_ref_ep',ref_ep_num)


#############
#   W2
#############

# nothing to do


############
#   W3 
############
roach2.write_int('r2dbe_vdif_0_hdr_w3_thread_id', thread_id_0)
roach2.write_int('r2dbe_vdif_1_hdr_w3_thread_id', thread_id_1)

# convert chars to 16 bit int
st0 = ord(station_id_0[0])*2**8 + ord(station_id_0[1])
st1 = ord(station_id_1[0])*2**8 + ord(station_id_1[1])

roach2.write_int('r2dbe_vdif_0_hdr_w3_station_id', st0)
roach2.write_int('r2dbe_vdif_1_hdr_w3_station_id', st1)


############
#   W4
############

eud_vers = 0x02

w4_0 = eud_vers*2**24 + rec_sb0*4 + bdc_sb0*2 + pol_block0
w4_1 = eud_vers*2**24 + rec_sb1*4 + bdc_sb1*2 + pol_block1

roach2.write_int('r2dbe_vdif_0_hdr_w4',w4_0)
roach2.write_int('r2dbe_vdif_1_hdr_w4',w4_1)

############
#   W5
############

# the offset in FPGA clocks between the R2DBE internal pps
# and the incoming GPS pps

############
#   W6
############

#  PSN low word, written by FPGA to VDIF header

###########
#   W7
############

# PSN high word, written by FPGA to VDIF header


# select test data 
roach2.write_int('r2dbe_vdif_0_test_sel', is_test)
roach2.write_int('r2dbe_vdif_1_test_sel', is_test)

# use little endian word order
roach2.write_int('r2dbe_vdif_0_little_end', 1)
roach2.write_int('r2dbe_vdif_1_little_end', 1)

# reverse time order (per vdif spec)
roach2.write_int('r2dbe_vdif_0_reorder_2b_samps', 1)
roach2.write_int('r2dbe_vdif_1_reorder_2b_samps', 1)

# set to test-vector noise mode
alc_args = [sys.executable, 'alc.py']
alc_args.append('-t {0}'.format(args.timeout))
for add_v in xrange(args.verbose):
    alc_args.append('-v')
alc_args.append(args.host)
subprocess.call(alc_args)

# must wait to set the enable signal until pps signal is stable
sleep(2)
roach2.write_int('r2dbe_vdif_0_enable', 1)
roach2.write_int('r2dbe_vdif_1_enable', 1)



