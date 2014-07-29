from datetime import datetime, time

is_test = 1

station_id  = 65536

# set thread id for both blocks
# perhaps thread is always 0?
thread_id_0 = 1024
thread_id_1 = 1024

# set pol for both blocks
# dual pol
pol_block0  = 1
pol_block1  = 1


roach2.progdev('r2dbe_top_2014_Jul_29_1224.bof.gz')

roach2.wait_connected()



# set 10 gbe vals
# set for card 0 port 0 sfp+
name = 'tengbe_0'
fid  = 5

arp = [0xffffffffffff] * 256
arp[30] = 0x000f530cd110 # mac address of tenzing p6p1

src_ip = (192<<24) + (168<<16) + (10<<8) + 20
src_mac = (2<<40) + (2<<32) + 20 + src_ip
# tenzing
#dest_ip= (192<<24) + (168<<16) + (10<<8) + 30
# mark6 eth3
dest_ip= (192<<24) + (168<<16) + (1<<8) + 3

roach2.config_10gbe_core('r2dbe_'+name+'_core', src_mac, src_ip, 4000, arp)

roach2.write_int('r2dbe_'+name+'_dest_ip', dest_ip)
roach2.write_int('r2dbe_'+name+'_dest_port', 4001)

# reset tengbe (this is VITAL)
roach2.write_int('r2dbe_'+name+'_rst',1)
roach2.write_int('r2dbe_'+name+'_rst',0)




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
sec_ref_ep  = delta.total_seconds()

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
roach2.write_int('r2dbe_vdif_0_hdr_w3_thread_id',  thread_id_0)
roach2.write_int('r2dbe_vdif_1_hdr_w3_thread_id',  thread_id_1)

roach2.write_int('r2dbe_vdif_0_hdr_w3_station_id', station_id)
roach2.write_int('r2dbe_vdif_1_hdr_w3_station_id', station_id)


############
#   W4
############
# begin extra header, match ALMA 
roach2.write_int('r2dbe_vdif_0_hdr_w4_magic_word', 678629)
roach2.write_int('r2dbe_vdif_1_hdr_w4_magic_word', 678629)

if is_test:
    bl_or_2ant0 = 1
    bl_or_2ant1 = 1
    alma0       = 3
    alma1       = 3
else:
    bl_or_2ant0 = 0
    bl_or_2ant1 = 0
    alma0       = 0
    alma1       = 0

roach2.write_int('r2dbe_vdif_0_hdr_w4_bl_or_2ant', bl_or_2ant0)
roach2.write_int('r2dbe_vdif_1_hdr_w4_bl_or_2ant', bl_or_2ant1)

roach2.write_int('r2dbe_vdif_0_hdr_w4_alma_bl_quad', alma0)
roach2.write_int('r2dbe_vdif_1_hdr_w4_alma_bl_quad', alma1)

roach2.write_int('r2dbe_vdif_0_hdr_w4_pol0_or_pol1',pol_block0)
roach2.write_int('r2dbe_vdif_1_hdr_w4_pol0_or_pol1',pol_block1)


############
#   W5
############
pic_status0 = 54321
pic_status1 = 54321

roach2.write_int('r2dbe_vdif_0_hdr_w5_pic_status',pic_status0)
roach2.write_int('r2dbe_vdif_1_hdr_w5_pic_status',pic_status1)

mark60 = 12765
mark61 = 12765

roach2.write_int('r2dbe_vdif_0_hdr_w5_mark6',mark60)
roach2.write_int('r2dbe_vdif_1_hdr_w5_mark6',mark61)


############
#   W6
############

# nothing to do

############
#   W7
############

# nothing to do




# select test data 
roach2.write_int('r2dbe_'+'vdif_0_test_sel',is_test)
roach2.write_int('r2dbe_'+'vdif_1_test_sel',is_test)

# enable data transmission
roach2.write_int('r2dbe_'+'vdif_0_enable',1)
