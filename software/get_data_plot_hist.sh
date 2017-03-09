#!/bin/bash

num_pkts=${1-'16'}

for ii in {2..5} ; do
	grab_consec.sh get_data_8pac ${num_pkts} eth${ii}
done

for ii in {2..5} ; do
	vdif_8pac_to_vdif.py < get_data_8pac_eth${ii}.vdif > get_data_eth${ii}.vdif
done

plot_hist_corrs.py -v -gl 800 -gh 14000 get_data_eth?.vdif

rm get_data*_eth?.vdif


