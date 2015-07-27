#!/bin/bash

# Captures single VDIF packet on the given network interface, extracts timestamp and maser drift numbers, and
# append to log file. Should typically be run with superuser privileges in the background
# 	$ sudo ./drift-monitor.sh &
# The log file is stored by default in /var/log/r2dbe/maser-drift.log but can be changed by passing the -l 
# argument to the python script (see get_drift_from_vdif.py for more information). The log file is CSV format
# with a single header line that describes the data fields.

# python script should be at this path
ROOT_DIR="/usr/local/src/r2dbe/software"

# logfile path
LOG_DIR="/var/log/r2dbe"
LOG_FILE="$LOG_DIR/maser-drift.log"

# network interface for incoming VDIF
IFACE="eth5"

# check if path exists for logfile
if [ ! -d "$LOG_DIR" ] ; then
	mkdir $LOG_DIR
fi

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
	if capture_packet $IFACE && python $ROOT_DIR/get_drift_from_vdif.py -l $LOG_FILE /tmp/cap1pkt.vdif ; then
		# only capture every 64 seconds, give it 2 seconds extra time
		sleep 62
	else 
		break
	fi
done
	
