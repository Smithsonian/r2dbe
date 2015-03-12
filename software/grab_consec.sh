(tcpdump -B 32768 -xnn -i p6p2 -c ${pnum-'2048'} -w $1_p6p2.pcap;
python pcap_to_vdif.py < $1_p6p2.pcap > $1_p6p2.vdif;
rm $1_p6p2.pcap) &
wait
