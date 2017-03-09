import argparse

import netifaces as ni

from datetime import datetime, time, timedelta
from socket import inet_ntoa
from struct import pack
from time import sleep

import adc5g, corr

parser = argparse.ArgumentParser(description='Configure and start up SDBE')
parser.add_argument('-b','--boffile',metavar='BOFFILE',type=str,default='sdbe_8pac_11.bof',
    help="program the fpga with BOFFILE (default is 'sdbe_8pac_11.bof')")
# temporarily disable file configuration
#parser.add_argument('-f','--file',metavar="CONFIG",type=str,default=None,
#    help="read configuration from file CONFIG, if None then use default values hard-coded in script (default is None)")
parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
    help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
parser.add_argument('-v','--verbose',action='count',default=0,
    help="control verbosity, use multiple times for more detailed output")
parser.add_argument('quadrant',metavar='QUAD',type=int,nargs=1,
    help="set the SWARM quadrant associated with this SDBE to QUAD")
# disable hostname, it is defined by the quadrant
#parser.add_argument('host',metavar='SDBE',type=str,nargs='?',default='sdbe-1',
#    help="hostname or ip address of SDBE (default is 'sdbe-1')")
args = parser.parse_args()

is_test = 0

# This is how the B-engine network is configured
#Q1: MAC = 0x000f9d9d9d1[0,1,2,3] ; IP = 192.168.11.[100,101,102,103] ; Port = 48803
#Q2: MAC = 0x000f9d9d9d2[0,1,2,3] ; IP = 192.168.12.[100,101,102,103] ; Port = 48803
#Q3: MAC = 0x000f9d9d9d3[0,1,2,3] ; IP = 192.168.13.[100,101,102,103] ; Port = 48803
#Q4: MAC = 0x000f9d9d9d4[0,1,2,3] ; IP = 192.168.14.[100,101,102,103] ; Port = 48803
quad = args.quadrant[0]
_DEFAULT_QUAD_CONFIG = {
    1:
        {'hostname'  :'sdbe-1',
         'station_id':'S1',
         'mac'       :[0x000f9d9d9d10,0x000f9d9d9d11,0x000f9d9d9d12,0x000f9d9d9d13],
         'ip'        :['192.168.11.100','192.168.11.101','192.168.11.102','192.168.11.103'],
         'port'      :[48803,48803,48803,48803]
        },
    2:
        {'hostname'  :'sdbe-2',
         'station_id':'S2',
         'mac'       :[0x000f9d9d9d20,0x000f9d9d9d21,0x000f9d9d9d22,0x000f9d9d9d23],
         'ip'        :['192.168.12.100','192.168.12.101','192.168.12.102','192.168.12.103'],
         'port'      :[48803,48803,48803,48803]
        },
    3:
        {'hostname'  :'sdbe-3',
         'station_id':'S3',
         'mac'       :[0x000f9d9d9d30,0x000f9d9d9d31,0x000f9d9d9d32,0x000f9d9d9d33],
         'ip'        :['192.168.13.100','192.168.13.101','192.168.13.102','192.168.13.103'],
         'port'      :[48803,48803,48803,48803]
        },
    4:
        {'hostname'  :'sdbe-4',
         'station_id':'S4',
         'mac'       :[0x000f9d9d9d40,0x000f9d9d9d41,0x000f9d9d9d42,0x000f9d9d9d43],
         'ip'        :['192.168.14.100','192.168.14.101','192.168.14.102','192.168.14.103'],
         'port'      :[48803,48803,48803,48803]
        }
}
_DEFAULT_CONFIG = _DEFAULT_QUAD_CONFIG[quad]

config = _DEFAULT_CONFIG
# add config file functionality here

if args.verbose > 0:
    print "################## Configuration for quadrant {0} ##################".format(quad)
    print "hostname={0}".format(config['hostname'])
    print "station_id={0}".format(config['station_id'])
    print "mac"
    for ii in range(4):
        print "   .{0}=0x{1:012x}".format(ii,config['mac'][ii])
    print "ip"
    for ii in range(4):
        print "   .{0}={1}:{2}".format(ii,config['ip'][ii],config['port'][ii])
    print "########################### end ###########################"

roach2 = corr.katcp_wrapper.FpgaClient(config['hostname'])
roach2.wait_connected(args.timeout)
if args.verbose > 2:
    print 'connected'

roach2.progdev(args.boffile)
roach2.wait_connected(args.timeout)
if args.verbose > 2:
    print 'progdevd'

# arm the one pps
roach2.write_int('onepps_ctrl', 1<<31)
roach2.write_int('onepps_ctrl', 0)
sleep(2)

# set up tx interfaces
if args.verbose > 2:
    print "TX interfaces configuration:"
mac_str = {}
mac_int = {}
ip_bytes = {}
for ii in ('eth2','eth3','eth4','eth5'):
    mac_str[ii] = ni.ifaddresses(ii)[17][0]['addr']
    mac_int[ii] = int(mac_str[ii].translate(None,':'),16)
    ip = ni.ifaddresses(ii)[2][0]['addr']
    ip_bytes[ii] = [x for x in map(str.strip, ip.split('.'))]

for iif in range(0,4):
    # generate configuration
    eth_name = 'eth{0}'.format(iif+2)#mac_int.keys()[iif]
    name = 'tengbe_' + str(iif)
    ip_b3 = int(ip_bytes[eth_name][0])
    ip_b2 = int(ip_bytes[eth_name][1])
    ip_b1 = int(ip_bytes[eth_name][2])
    ip_b0 = int(ip_bytes[eth_name][3])
    src_ip  = (ip_b3<<24) + (ip_b2<<16) + (ip_b1<<8) + ip_b0+1
    src_port = 4000
    src_mac = (2<<40) + (2<<32) + 20 + src_ip
    dest_ip = (ip_b3<<24) + (ip_b2<<16) + (ip_b1<<8) + ip_b0
    dest_port = 4001
    arp = [0xffffffffffff] * 256
    arp[ip_b0] = mac_int[eth_name]

    # write configuration
    roach2.config_10gbe_core('' + name + '_core', src_mac, src_ip, src_port, arp)
    roach2.write_int('' + name + '_dest_ip', dest_ip)
    roach2.write_int('' + name + '_dest_port', dest_port)

    # reset tengbe
    roach2.write_int('' + name + '_rst', 1)
    roach2.write_int('' + name + '_rst', 0)

    if args.verbose > 1:
        print "{4}: {0}:{1} --> {2}:{3}".format(
            inet_ntoa(pack('!I',src_ip)),src_port,
            inet_ntoa(pack('!I',dest_ip)),dest_port,
            name)

# set up rx interfaces
if args.verbose > 2:
    print "RX interfaces configuration:"
arp = [0xffffffffffff] * 256
for iif in range(0,4):
    # generate configuration
    name = 'tengbe_rx' + str(iif)
    ip_b3 = int(config['ip'][iif].split('.')[0])
    ip_b2 = int(config['ip'][iif].split('.')[1])
    ip_b1 = int(config['ip'][iif].split('.')[2])
    ip_b0 = int(config['ip'][iif].split('.')[3])
    rx_ip  = (ip_b3<<24) + (ip_b2<<16) + (ip_b1<<8) + ip_b0
    rx_mac = config['mac'][iif]
    rx_port = config['port'][iif]

    # write configuration
    roach2.config_10gbe_core('' + name + '_core', rx_mac, rx_ip, rx_port, arp)

    # reset tengbe
    roach2.write_int('' + name + '_rst', 1)
    roach2.write_int('' + name + '_rst', 0)

    if args.verbose > 1:
        print "{3}: --> {0}:{1} @ 0x{2:012x}".format(
            inet_ntoa(pack('!I',rx_ip)),rx_port,rx_mac,
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
if args.verbose > 2:
    print "In epoch {0} (starting on {1})".format(ref_ep_num,ref_ep_date.strftime('%Y/%b/%d %H:%M:%S'))

##############
#   W0
##############

# wait until middle of second for calculation
while abs(datetime.utcnow().microsecond-5e5)>1e5:
    sleep(0.1)

delta = datetime.utcnow()-ref_ep_date
sec_ref_ep = delta.seconds + 24*3600*delta.days

# to check
nday = sec_ref_ep/24/3600

for ii in range(0,4):
    dev_name = 'vdif_%d_hdr_w0_reset' % ii
    roach2.write_int(dev_name,1)
    roach2.write_int(dev_name,0)

for ii in range(0,4):
    dev_name = 'vdif_%d_hdr_w0_sec_ref_ep' % ii
    roach2.write_int(dev_name,sec_ref_ep)

#############
#   W1
#############

# write epoch number
for ii in range(0,4):
    dev_name = 'vdif_%d_hdr_w1_ref_ep' % ii
    roach2.write_int(dev_name,ref_ep_num)

#############
#   W2
#############

# nothing to do

############
#   W3 
############

# write thread id
thread_id = (0,1,2,3)
for ii in range(0,4):
    dev_name = 'vdif_%d_hdr_w3_thread_id' % ii
    roach2.write_int(dev_name,thread_id[ii])

# write station code
station_id_2code = ord(config['station_id'][0])*2**8 + ord(config['station_id'][1])
for ii in range(0,4):
    dev_name = 'vdif_%d_hdr_w3_station_id' % ii
    roach2.write_int(dev_name,station_id_2code)

############
#   W4
############

# nothing to do

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
for ii in range(0,4):
    dev_name = 'vdif_%d_test_sel' % ii
    roach2.write_int(dev_name, is_test)

#roach2.write_int('vdif_0_test_sel', is_test)
#roach2.write_int('vdif_1_test_sel', is_test)

# use little endian word order
for ii in range(0,4):
    dev_name = 'vdif_%d_little_end' % ii
    roach2.write_int(dev_name, 1)

#roach2.write_int('vdif_0_little_end', 1)
#roach2.write_int('vdif_1_little_end', 1)

# reverse time order (per vdif spec)
for ii in range(0,4):
    dev_name = 'vdif_%d_reorder_2b_samps' % ii
    roach2.write_int(dev_name, 0)

#roach2.write_int('vdif_0_reorder_2b_samps', 0)
#roach2.write_int('vdif_1_reorder_2b_samps', 1)

# set to test-vector noise mode
#execfile('alc.py')
for ii in range(0,4):
    dev_name = 'quantize_%d_thresh' % ii
    roach2.write_int(dev_name,2)

#roach2.write_int('quantize_0_thresh', 2)
#roach2.write_int('quantize_1_thresh', 2)


# must wait to set the enable signal until pps signal is stable
sleep(2)
for ii in range(0,4):
    dev_name = 'vdif_%d_enable' % ii
    roach2.write_int(dev_name, 1)

#roach2.write_int('vdif_0_enable', 1)
#roach2.write_int('vdif_1_enable', 1)

