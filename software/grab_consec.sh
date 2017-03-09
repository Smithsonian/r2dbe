(tcpdump -B 32768 -xnn -i $3 -c $2 -w $1_$3.pcap;
pcap_to_vdif.py < $1_$3.pcap > $1_$3.vdif;
rm $1_$3.pcap) &
wait
