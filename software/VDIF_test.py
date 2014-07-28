#roach2.progdev('r2dbe_top_2014_Jul_21_1805.bof.gz')

#roach2.progdev('r2dbe_top_2014_Jul_14_1412.bof.gz') # top level
roach2.progdev('r2dbe_10gbe_e_2014_Jul_10_1226.bof.gz') # compiled with ddr3_devel to see if 10gbe block had changed, still issue persisted until reset of tengbe, then performance is perfect 
#roach2.progdev('r2dbe_10gbe_e_2014_Jul_09_1650.bof.gz') # fixed the 65 bit issue, but packet issue has not changed
#roach2.progdev('r2dbe_10gbe_e_2014_Jul_09_0858.bof.gz') # fixed tx issue from prev, still first packet data length issue persists
#roach2.progdev('r2dbe_10gbe_e_2014_Jul_02_1534.bof.gz') # add vdif headers, expect same issue but instead get no TX: compiled without SFP+ and card 0 and large TX frames selected in 10 gbe block
#roach2.progdev('r2dbe_10gbe_d_2014_Jun_30_1430.bof.gz') # no header, same issue
#roach2.progdev('r2dbe_10gbe_d_2014_Jun_30_1351.bof.gz') # restructured, but still bit error
#roach2.progdev('r2dbe_10gbe_c_2014_Jun_27_1602.bof.gz') # recreate bit error
#roach2.progdev('r2dbe_10gbe_c_2014_Jun_27_1524.bof.gz') # shift eof, nothing comes through
#roach2.progdev('r2dbe_10gbe_c_2014_Jun_27_1040.bof.gz') # bit error
roach2.wait_connected()
# set arbiter override 



#registers are enable, tx_dest_ip, tx_dest_port


# set 10 gbe vals
# set for card 0 port 0 sfp+
name = 'ten_Gbe_v2'
fid  = 5

arp = [0xffffffffffff] * 256
arp[30] = 0x000f530cd110 # mac address of tenzing p6p1

src_ip = (192<<24) + (168<<16) + (10<<8) + 20
src_mac = (2<<40) + (2<<32) + 20 + src_ip
dest_ip= (192<<24) + (168<<16) + (10<<8) + 30

roach2.config_10gbe_core(''+name+'', src_mac, src_ip, 4000, arp)

roach2.write_int('dest_ip', dest_ip)
roach2.write_int('dest_port', 4001)

# reset tengbe (this is VITAL)
roach2.write_int('rst',1)
roach2.write_int('rst',0)

# select test data 
#roach2.write_int(''+'vdif_0_test_sel',1)
roach2.write_int('vdif_enable',1)
roach2.write_int('en_data',1)

# set headers
#roach2.write_int('vdif_header_gen_w0',0) 
#roach2.write_int('vdif_header_gen_w1',1) 
#roach2.write_int('vdif_header_gen_w2',2) 
#roach2.write_int('vdif_header_gen_w3',3) 
#roach2.write_int('vdif_header_gen_w4',4) 
#roach2.write_int('vdif_header_gen_w5',5) 
#roach2.write_int('vdif_header_gen_w6',6) 
#roach2.write_int('vdif_header_gen_w7',7) 
