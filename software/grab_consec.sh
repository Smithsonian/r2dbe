(tcpdump -B 32768 -xnn -i eth5 -c ${pnum-'32'} -w $1_e5.pcap;
python pcap_to_vdif.py < $1_e5.pcap > $1_e5.vdif;
rm $1_e5.pcap) &
wait
