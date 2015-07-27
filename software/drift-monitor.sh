#!/bin/bash

# Captures single VDIF packet on the given network interface, extracts timestamp and maser drift numbers, and
# append to log file. Should typically be run with superuser privileges in the background
# 	$ sudo ./drift-monitor.sh &
# The log file is stored by default in /var/log/r2dbe/maser-drift.log but can be changed by passing the -l 
# argument to the python script (see get_drift_from_vdif.py for more information). The log file is CSV format
# with a single header line that describes the data fields.

# python script should be at this path
ROOT_DIR="/usr/local/src/r2dbe/software"

# network interface for incoming VDIF
IFACE="eth5"

function capture_packet() {
	tcpdump -B 1024 -xnn -i $1 '(udp[22]=0)and(udp[20:2]<=0x0001)and(udp[16]&0x3f=0)' -c 1 -w /tmp/cap1pkt.pcap 2>/dev/null
	python pcap_to_vdif.py < /tmp/cap1pkt.pcap > /tmp/cap1pkt.vdif
	rm /tmp/cap1pkt.pcap
}

function return_zero() {
        return 0
}

function do_exit() {
	echo "Exiting..."
	exit 0
}

# capture Ctrl+C to exit
trap do_exit SIGINT

# run indefinitely until told to stop
while return_zero ; do
	if capture_packet $IFACE && python $ROOT_DIR/get_drift_from_vdif.py /tmp/cap1pkt.vdif ; then
		sleep 0.1
	else 
		break
	fi
done
	
