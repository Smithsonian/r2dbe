(tcpdump -B 32768 -xnn -i eth3 '(udp[20]<=0x20)and(udp[21:2]=0)and(udp[16]&0xf=0)' -c ${pnum-'32'} -w $1_e3.pcap;
python pcap_to_vdif.py < $1_e3.pcap > $1_e3.vdif;
rm $1_e3.pcap) &
(tcpdump -B 32768 -xnn -i eth5 '(udp[20]<=0x20)and(udp[21:2]=0)and(udp[16]&0xf=0)' -c ${pnum-'32'} -w $1_e5.pcap;
python pcap_to_vdif.py < $1_e5.pcap > $1_e5.vdif;
rm $1_e5.pcap) &
wait
