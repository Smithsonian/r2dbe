#!/bin/bash

num_pkts=${1-'16'}

for ii in {2..5} ; do
	grab_consec.sh get_data_8pac ${num_pkts} eth${ii} &
done

wait

for ii in {2..5} ; do
	vdif_8pac_to_vdif.py < get_data_8pac_eth${ii}.vdif > get_data_eth${ii}.vdif
done

for ii in {2..5} ; do
	swarm_check.py get_data_eth${ii}.vdif
done

rm get_data*_eth?.vdif


