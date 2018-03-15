#!/usr/bin/env python
import argparse

import json
import netifaces as ni

from datetime import datetime, time, timedelta
from tempfile import NamedTemporaryFile
from socket import inet_ntoa
from struct import pack
from subprocess import Popen, PIPE
from time import sleep

import adc5g, corr

SWARM_BENGINE_MACBASE = 0x000f530ce000
SWARM_BENGINE_IPBASE = 0xc0a80a00
SWARM_BENGINE_PORT = 0xbea3
SWARM_BENGINE_SIDEBANDS = ('USB','LSB')
SWARM_BENGINE_SIDEBAND_MACIP_OFFSET = 4

SWARM_DBE_MACBASE = 0x000f9d9de000
SWARM_DBE_IPBASE = SWARM_BENGINE_IPBASE
SWARM_DBE_PORT = 4000
SWARM_DBE_N_RX_CORE = 4

class SwarmDBEInterface(object):

	def __init__(self, qid, iface_n, sideband="USB"):

		# Set base values
		my_mac = SWARM_DBE_MACBASE + (qid << 8) + 0x20 + iface_n
		my_ip = SWARM_DBE_IPBASE + (qid << 8) + 0x20 + iface_n

		# Check if sideband specification is valid
		sideband_upper = sideband.upper()
		if sideband_upper not in SWARM_BENGINE_SIDEBANDS:
			raise RuntimeError("{0} sideband should be one of {1}".format(self.__class__,SWARM_BENGINE_SIDEBANDS))

		# Determine offset per sideband
		mac_ip_offset = SWARM_BENGINE_SIDEBANDS.index(sideband_upper) * SWARM_BENGINE_SIDEBAND_MACIP_OFFSET
		my_mac += mac_ip_offset
		my_ip += mac_ip_offset

		# Create interface
		self.mac = my_mac
		self.ip = my_ip
		self.port = SWARM_BENGINE_PORT

def _system_call(cmd):
	p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
	stdout, stderr = p.communicate()
	rc = p.returncode
	# Return call return code, stdout, and stderr as 3-tuple
	return (rc, stdout, stderr)

def _remote_python_call(py_code, hostname, user):
	# Excute Python source in py_code and return stdout
	with NamedTemporaryFile(mode="w+",suffix=".py",delete=True) as tmp_fh:
		tmp_fh.write(py_code)
		tmp_fh.flush()
		py_cmd = "cat {tmp} | ssh {user}@{host} python -".format(tmp=tmp_fh.name, user=user, host=hostname)
		rc, stdout, stderr = _system_call(py_cmd)
		if rc != 0:
			print "ERROR, Python call failed, received error code {code} with message '{msg}'".format(code=rc,
			  msg=stderr)
			raise RuntimeError("Python call failed")

		return stdout

def _safe_remote_python_call(py_code, hostname, user, *args):
	# Execute Python source and return variables using json.dumps()
	wrapper_code = "" \
	  "try:\n" \
	  "    import json\n" \
	  "    {code}\n" \
	  "    print json.dumps((True, ({rvar})))\n" \
	  "except Exception as ex:\n" \
	  "    print json.dumps((False, (str(ex.__class__), str(ex))))\n".format(code="\n    ".join(py_code.split("\n")),
	  rvar=" ".join(["{0},".format(a) for a in args]))
	rstr = _remote_python_call(wrapper_code, hostname, user)
	res, rv = json.loads(rstr)

	# Log possible error
	if not res:
		ex_name = rv[0]
		ex_msg = rv[1]
		print "ERROR, A {name} exception occurred during Python call: {msg}".format(name=ex_name, msg=ex_msg)

	# Then return the result and return value
	return res, dict(zip(args,[r for r in rv]))


def get_remote_iface_mac_ip(iface, hostname, user):
	code_str = "" \
	  "from netifaces import ifaddresses\n" \
	  "iface = ifaddresses('{iface}')\n" \
	  "mac = iface[17][0]['addr']\n" \
	  "ip = iface[2][0]['addr']".format(iface=iface)

	# Get call result
	res, rv = _safe_remote_python_call(code_str, hostname, user, "mac", "ip")

	if res:
		mac_str = str(rv["mac"])
		ip_str = str(rv["ip"])
		return mac_str, ip_str

def configure_backend_pair(qid,sideband,sdbe,mark6,
  verbose=0,user="oper",iface_list=['eth2','eth3','eth4','eth5'],boffile='sdbe_8pac_11.bof',timeout=5.0):

	roach2 = corr.katcp_wrapper.FpgaClient(sdbe)

	roach2.wait_connected(timeout)
	if verbose > 2:
		print 'connected'

	roach2.progdev(boffile)
	roach2.wait_connected(timeout)
	if args.verbose > 2:
		print 'progdevd'

	# arm the one pps
	roach2.write_int('onepps_ctrl', 1<<31)
	roach2.write_int('onepps_ctrl', 0)
	sleep(2)

	# set up tx interfaces
	if verbose > 2:
		print "TX interfaces configuration:"
	mac_str = {}
	mac_int = {}
	ip_bytes = {}
	for ii in iface_list:#('eth2','eth3','eth4','eth5'):
		#mac_str[ii] = ni.ifaddresses(ii)[17][0]['addr']
		mac_str[ii], ip = get_remote_iface_mac_ip(ii, mark6, user)
		mac_int[ii] = int(mac_str[ii].translate(None,':'),16)
		#ip = ni.ifaddresses(ii)[2][0]['addr']
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
	for iif in range(0,SWARM_DBE_N_RX_CORE):
		# generate configuration
		name = 'tengbe_rx' + str(iif)
		sdbe_iface = SwarmDBEInterface(qid,iif,sideband=sideband)
		rx_ip = sdbe_iface.ip
		rx_mac = sdbe_iface.mac
		rx_port = sdbe_iface.port

		# write configuration
		roach2.config_10gbe_core('' + name + '_core', rx_mac, rx_ip, rx_port, arp)

		# reset tengbe
		roach2.write_int('' + name + '_rst', 1)
		roach2.write_int('' + name + '_rst', 0)

		if args.verbose > 1:
			print "{3}: --> {0}:{1} @ 0x{2:012x}".format(
				inet_ntoa(pack('!I',rx_ip)),rx_port,rx_mac,
				name)

	# calculate reference epoch
	utcnow = datetime.utcnow()
	ref_start = datetime(2000,1,1,0,0,0)
	nyrs = utcnow.year - ref_start.year
	ref_ep_num = 2*nyrs+1*(utcnow.month>6)
	ref_ep_date = datetime(utcnow.year,6*(utcnow.month>6)+1,1,0,0,0) # date of start of epoch July 1 2014
	if args.verbose > 2:
		print "In epoch {0} (starting on {1})".format(ref_ep_num,ref_ep_date.strftime('%Y/%b/%d %H:%M:%S'))

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

	# write epoch number
	for ii in range(0,4):
		dev_name = 'vdif_%d_hdr_w1_ref_ep' % ii
		roach2.write_int(dev_name,ref_ep_num)

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

	# select test data 
	for ii in range(0,4):
		dev_name = 'vdif_%d_test_sel' % ii
		roach2.write_int(dev_name, is_test)

	# use little endian word order
	for ii in range(0,4):
		dev_name = 'vdif_%d_little_end' % ii
		roach2.write_int(dev_name, 1)

	# reverse time order (per vdif spec)
	for ii in range(0,4):
		dev_name = 'vdif_%d_reorder_2b_samps' % ii
		roach2.write_int(dev_name, 0)

	# set to test-vector noise mode
	for ii in range(0,4):
		dev_name = 'quantize_%d_thresh' % ii
		roach2.write_int(dev_name,2)

	# must wait to set the enable signal until pps signal is stable
	sleep(2)
	for ii in range(0,4):
		dev_name = 'vdif_%d_enable' % ii
		roach2.write_int(dev_name, 1)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Configure and start up SDBE')
	parser.add_argument('-b','--boffile',metavar='BOFFILE',type=str,default='sdbe_8pac_11.bof',
		help="program the fpga with BOFFILE (default is 'sdbe_8pac_11.bof')")
	parser.add_argument('-i','--interface-list',metavar='IFACE',type=str,nargs=4,default=['eth2','eth3','eth4','eth5'],
		help="list of exactly 4 NICs which receive data FIDs {01,23,45,67} (default is ['eth2','eth3','eth4','eth5'])")
	parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
		help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
	parser.add_argument('-u','--user',metavar='LOGIN',type=str,default='oper',
		help="login to use for Mark6 (default is 'oper')")
	parser.add_argument('-v','--verbose',action='count',default=0,
		help="control verbosity, use multiple times for more detailed output")
	parser.add_argument('quadrant',metavar='QUAD',type=int,
		help="set the SWARM quadrant associated with this SDBE to QUAD (should match qid in SWARM)")
	parser.add_argument('sideband',metavar='SIDEBAND',type=str,
		help="set the sideband associated with this backend pair (should be 'LSB' or 'USB')")
	parser.add_argument('sdbe',metavar='SDBE',type=str,
		help="hostname of the SDBE")
	parser.add_argument('mark6',metavar='MARK6',type=str,
		help="Mark6 host to which the SDBE will transmit data")
	args = parser.parse_args()

	configure_backend_pair(args.quadrant,args.sideband,args.sdbe,args.mark6,
	  verbose=args.verbose,boffile=args.boffile,iface_list=args.interface_list,timeout=args.timeout,user=args.user)
