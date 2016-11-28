#!/bin/bash

# Captures single VDIF packet on the given network interface, extracts timestamp and maser drift numbers, and
# append to log file. Should typically be run with superuser privileges in the background
# 	$ sudo ./pps-monitor.sh &
# The log file is stored by default in /var/log/r2dbe/pps-drift.log but can be changed by passing the -l 
# argument to the python script (see capture_pps_offset.py for more information). The log file is CSV format
# with a single header line that describes the data fields.

# default values
# python script should be at this path
ROOT_DIR="/usr/local/src/r2dbe/software"
# log file location
LOG_DIR="/var/log/r2dbe"
# log file name
LOG_FILE="pps-drift.log"
# network interface for incoming VDIF
IFACE="eth5"

USAGE="Monitor PPS

Usage: $(basename "$0") [-h] [-i IFACE] [-l LOG_FILE] [-d LOG_DIR] \\
       [-r ROOT_DIR]

    -d LOG_DIR     store log file in this location
                   (default is '/var/log/r2dbe')
    -h             show this help message and exit
    -i IFACE       use this ethernet interface to capture VDIF packets
                   (default is 'eth5')
    -l LOG_FILE    use this name for log file, so the full path of the 
                   log file is LOG_DIR/LOG_FILE
                   (default is 'pps-drift.log')
    -r ROOT_DIR    path to R2DBE software
                   (default is '/usr/local/src/r2dbe/software')

This script needs to be run with the privileges necessary to call
tcpdump. Best to run this in the background, but remember to kill it 
before doing any serious recording.
"
while getopts ':d:hi:l:r:' option ; do
	case "$option" in
		d)	LOG_DIR=$OPTARG
			;;
		h)	echo "$USAGE"
			exit
			;;
		i)	IFACE=$OPTARG
			;;
		l)	LOG_FILE=$OPTARG
			;;
		r)	ROOT_DIR=$OPTARG
			;;
		:)	echo "Option -$OPTARG requires an argument." >&2
			exit 1
			;;
		\?)	echo "Invalid option -$OPTARG" >&2
			;;
	esac
done
LOG_PATH="$LOG_DIR/$LOG_FILE"

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
	if capture_packet $IFACE && python $ROOT_DIR/capture_pps_offset.py -l $LOG_PATH /tmp/cap1pkt.vdif ; then
		# only capture every 64 seconds, give it 2 seconds extra time
		sleep 62
	else 
		break
	fi
done
	
