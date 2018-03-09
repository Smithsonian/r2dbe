#include <endian.h>
#include <stdio.h>
#include <stdint.h>

#include "vdif.h"

// Do byte reordering on received data
void ntoh_data(uint64_t *dat, int nmem) {
	int ii;
	for (ii=0; ii<nmem; ii++) {
		dat[ii] = be64toh(dat[ii]);
	}
}

// Human-readable display of packet header information
void print_header(vdif_r2dbe_header_t *hdr) {
	printf("%02u@%010u+%06u > %c%c#%u {%s, %s, %s}; PPS=%010u; PSN=%020lu",
	hdr->w2.ref_epoch,hdr->w1.secs_inre,hdr->w2.df_num_insec,
	(hdr->w4.stationID>>8)&0xFF,hdr->w4.stationID&0xFF,hdr->w4.threadID,
	hdr->w5.pol == POL_RCP_VAL ? POL_RCP_STR : POL_LCP_STR,
	hdr->w5.bdc_band == BDC_HIGH_VAL ? BDC_HIGH_STR : BDC_LOW_STR,
	hdr->w5.rx_band == RX_HIGH_VAL ? RX_HIGH_STR : RX_LOW_STR,
	hdr->w6.clk_int_to_ext_pps,hdr->edh_psn);
}
