import adc5g, corr
from time import sleep
from datetime import datetime, time, timedelta

dstart = datetime(2014, 9, 8, 21, 5, 0, 0)

is_test = 0

station_id_0  = 0
station_id_1  = 1

# set thread id for both blocks
# perhaps thread is always 0?
thread_id_0 = 0
thread_id_1 = 0

# set pol for both blocks
# dual pol
pol_block0  = 1
pol_block1  = 1


roach2 = corr.katcp_wrapper.FpgaClient('r2dbe-1')
roach2.wait_connected()
roach2.progdev('r2dbe_rev2.bof')

roach2.wait_connected()

# arm the one pps
roach2.write_int('r2dbe_onepps_ctrl', 1<<31)
roach2.write_int('r2dbe_onepps_ctrl', 0)

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

# set 10 gbe vals

arp = [0xffffffffffff] * 256
arp[3] = 0x0060dd448941 # mac address of mark6-4015 eth3
arp[5] = 0x0060dd44893b # mac address of mark6-4015 eth5

ip_b3 = 172
ip_b2 = 16
ip_b0 = 16

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
ref_ep_num = 29 #2014 part 2 = 29
ref_ep_date = datetime(2014,7,1,0,0,0) # date of start of epoch July 1 2014

##############
#   W0
##############
utcnow = datetime.utcnow()


delta       = utcnow-ref_ep_date
sec_ref_ep  = delta.seconds

# to check
nday = sec_ref_ep/24/3600

#secs_ref_ep_nday, number of days since reference epoch began
#print delta.total_seconds()
#print 'secs since ref ep: %d' %sec_ref_ep
#print 'days since ref ep: %d' %nday
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

roach2.write_int('r2dbe_vdif_0_hdr_w3_station_id', station_id_0)
roach2.write_int('r2dbe_vdif_1_hdr_w3_station_id', station_id_1)


############
#   W4
############

# nothing to do

############
#   W5
############

# nothing to do

############
#   W6
############

# nothing to do

############
#   W7
############

# nothing to do


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
roach2.write_int('r2dbe_quantize_0_thresh', 16)
roach2.write_int('r2dbe_quantize_1_thresh', 16)

# enable data transmission
while(datetime.utcnow() < dstart):
    sleep(.1)

roach2.write_int('r2dbe_vdif_0_enable', 1)
roach2.write_int('r2dbe_vdif_1_enable', 1)



