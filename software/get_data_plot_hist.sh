#!/bin/bash

./grab_consec.sh get_data 2048 eth2
./grab_consec.sh get_data 2048 eth3
./grab_consec.sh get_data 2048 eth4
./grab_consec.sh get_data 2048 eth5

python plot_hist_corrs.py -v -t -gl 800 -gh 14000 get_data*vdif

rm get_data_eth2.vdif
rm get_data_eth3.vdif
rm get_data_eth4.vdif
rm get_data_eth5.vdif
