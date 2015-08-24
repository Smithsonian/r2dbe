import adc5g, corr
from time import sleep
from datetime import datetime, time, timedelta
import netifaces as ni

is_test = 0

station_id_0  = 'lh'  # dummy, chose lh for laura, high band (7-9 GHz)
station_id_1  = 'll'  # dummy, chose ll for laura, low band (5-7 GHz)

# set pol for both blocks
# dual pol
# 0 is X or L
# 1 is Y or R
pol_block0  = 1
pol_block1  = 0

# set thread id for both blocks
# perhaps thread is always 0?
thread_id_0 = 0
thread_id_1 = 0


roach2 = corr.katcp_wrapper.FpgaClient('r2dbe-1')
roach2.wait_connected()
roach2.progdev('r2dbe_rev2.bof')

roach2.wait_connected()

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
    dest_ip = (ip_b3<<24) + (ip_b2<<16) + (i<<8) + ip_b0

    roach2.config_10gbe_core('r2dbe_' + name + '_core', src_mac, src_ip, 4000, arp)
    roach2.write_int('r2dbe_' + name + '_dest_ip', dest_ip)
    roach2.write_int('r2dbe_' + name + '_dest_port', 4001)

    # reset tengbe (this is VITAL)
    roach2.write_int('r2dbe_' + name + '_rst', 1)
    roach2.write_int('r2dbe_' + name + '_rst', 0)


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

delta       = datetime.utcnow()-ref_ep_date
sec_ref_ep  = delta.seconds + 24*3600*delta.days

roach2.write_int('r2dbe_vdif_0_hdr_w0_reset',0)
roach2.write_int('r2dbe_vdif_1_hdr_w0_reset',0)

roach2.write_int('r2dbe_vdif_0_hdr_w0_sec_ref_ep',sec_ref_ep)
roach2.write_int('r2dbe_vdif_1_hdr_w0_sec_ref_ep',sec_ref_ep)

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

w4_0 = eud_vers*2**24 + pol_block0
w4_1 = eud_vers*2**24 + pol_block1

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
execfile('alc.py')

# must wait to set the enable signal until pps signal is stable
sleep(2)
roach2.write_int('r2dbe_vdif_0_enable', 1)
roach2.write_int('r2dbe_vdif_1_enable', 1)



