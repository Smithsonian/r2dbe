#ifndef __VDIF_H__
#define __VDIF_H__

#define VDIF_R2DBE_PAYLOAD_BYTE_SIZE 8192
#define VDIF_R2DBE_PAYLOAD_WORD_SIZE VDIF_R2DBE_PAYLOAD_BYTE_SIZE/8

#define POL_LCP_VAL 0
#define POL_RCP_VAL 1
#define POL_LCP_STR "LCP"
#define POL_RCP_STR "RCP"

#define BDC_LOW_VAL 0
#define BDC_HIGH_VAL 1
#define BDC_LOW_STR "BLO"
#define BDC_HIGH_STR "BHI"

#define RX_LOW_VAL 0
#define RX_HIGH_VAL 1
#define RX_LOW_STR "RLO"
#define RX_HIGH_STR "RHI"

// VDIF header as implemented in R2DBE firmware
typedef struct vdif_r2dbe_header {
	struct word1 {
		uint32_t secs_inre:30;
		uint32_t legacy:1;
		uint32_t invalid:1;
	} w1;
	struct word2 {
		uint32_t df_num_insec:24;
		uint32_t ref_epoch:6;
		uint32_t UA:2;
	} w2;
	struct word3 {
		uint32_t df_len:24;
		uint32_t num_channels:5;
		uint32_t ver:3;
	} w3;
	struct word4 {
		uint32_t stationID:16;
		uint32_t threadID:10;
		uint32_t bps:5;
		uint32_t dt:1;
	} w4;
	struct word5 {
		uint32_t pol:1;
		uint32_t bdc_band:1;
		uint32_t rx_band:1;
		uint32_t eud5_rem:21;
		uint32_t edv5:8;
	} w5;
	struct word6 {
		uint32_t clk_int_to_ext_pps;
	} w6;
	uint64_t edh_psn;
} vdif_r2dbe_header_t;

// VDIF packet as implemented in R2DBE firmware
typedef struct vdif_r2dbe_packet {
	vdif_r2dbe_header_t header;
	uint64_t payload[VDIF_R2DBE_PAYLOAD_WORD_SIZE];
} vdif_r2dbe_packet_t;

// Actual UDP payload contains a single 8-byte word before the VDIF packet
typedef struct vdif_r2dbe_vtp {
	uint64_t psn;
	vdif_r2dbe_packet_t pkt;
} vdif_r2dbe_vtp_t;

// Do byte reordering on received data
void ntoh_data(uint64_t *dat, int nmem);

// Human-readable display of packet header information
void print_header(vdif_r2dbe_header_t *hdr);

#endif // _VDIF_H_
