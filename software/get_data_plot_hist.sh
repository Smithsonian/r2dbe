#!/bin/bash

for ii in {2..5} ; do
	./grab_consec.sh get_data_8pac 256 eth${ii}
done

for ii in {2..5} ; do
	python vdif_8pac_to_vdif.py < get_data_8pac_eth${ii}.vdif > get_data_eth${ii}.vdif
done

python plot_hist_corrs.py -v -gl 800 -gh 14000 get_data_eth?.vdif

rm get_data*_eth?.vdif


