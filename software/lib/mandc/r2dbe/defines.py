############################################################### Firmware
R2DBE_DEFAULT_BITCODE = "r2dbe_rev2_v1.1.bof"
R2DBE_LATEST_VERSION_GIT_HASH = "32aae4d"

######################################################### Time reference
# Misc parameters
R2DBE_CLOCK_RATE = 256e6
R2DBE_DEMUX_FACTOR = 16
R2DBE_SAMPLE_RATE = R2DBE_CLOCK_RATE * R2DBE_DEMUX_FACTOR
R2DBE_SAMPLES_PER_FRAME = 32768
R2DBE_FRAME_RATE = R2DBE_SAMPLE_RATE / R2DBE_SAMPLES_PER_FRAME
# Control registers
R2DBE_ONEPPS_CTRL = "r2dbe_onepps_ctrl"
R2DBE_ONEPPS_ALIVE = "r2dbe_onepps_alive"
R2DBE_ONEPPS_SINCE_EPOCH = "r2dbe_onepps_since_epoch"
R2DBE_ONEPPS_GPS_PPS_COUNT = "r2dbe_onepps_gps_pps_cnt"
R2DBE_ONEPPS_GPS_OFFSET = "r2dbe_onepps_offset"

########################################################## Analog inputs
# Misc paramaters
R2DBE_INPUTS = (0, 1)
R2DBE_INPUT_0_SPEC = ("IF0", )
R2DBE_INPUT_1_SPEC = ("IF1", )
R2DBE_NUM_INPUTS = len(R2DBE_INPUTS)
# Control registers
R2DBE_INPUT_DATA_SELECT = "r2dbe_data_mux_%d_sel"
R2DBE_INPUT_DATA_SOURCE_ZERO = 0
R2DBE_INPUT_DATA_SOURCE_ADC = 1
R2DBE_INPUT_DATA_SOURCE_NOISE = 2
R2DBE_INPUT_DATA_SOURCE_TONE = 3
# 2-bit quantization threshold
R2DBE_QUANTIZATION_THRESHOLD = "r2dbe_quantize_%d_thresh"

######################################################### Data snapshots
R2DBE_DATA_SNAPSHOT_8BIT = "r2dbe_snap_8bit_%d_data"
R2DBE_DATA_SNAPSHOT_2BIT = "r2dbe_snap_2bit_%d_data"

######################################################## Network outputs
R2DBE_OUTPUTS = (0, 1)
R2DBE_NUM_OUTPUTS = len(R2DBE_OUTPUTS)
# Control registers
R2DBE_TENGBE_CORE = "r2dbe_tengbe_%d_core"
R2DBE_TENGBE_DEST_IP = "r2dbe_tengbe_%d_dest_ip"
R2DBE_TENGBE_DEST_PORT = "r2dbe_tengbe_%d_dest_port"
R2DBE_TENGBE_RESET = "r2dbe_tengbe_%d_rst"    

###################################################### R2DBE VDIF header
# VDIF transmission
R2DBE_VTP_SIZE = 8
R2DBE_VDIF_SIZE = 8224
# Misc parameters
R2DBE_VDIF_EUD_VERSION = 0x02
R2DBE_VDIF_DEFAULT_THREAD_ID_0 = 0
R2DBE_VDIF_DEFAULT_THREAD_ID_1 = 0
R2DBE_VDIF_DEFAULT_THREAD_IDS = (R2DBE_VDIF_DEFAULT_THREAD_ID_0, R2DBE_VDIF_DEFAULT_THREAD_ID_1)
# Control registers
R2DBE_VDIF_RESET = "r2dbe_vdif_%d_hdr_w0_reset"
R2DBE_VDIF_ENABLE = "r2dbe_vdif_%d_enable"
R2DBE_VDIF_SEC_SINCE_REF_EPOCH = "r2dbe_vdif_%d_hdr_w0_sec_ref_ep"
R2DBE_VDIF_REF_EPOCH = "r2dbe_vdif_%d_hdr_w1_ref_ep"
R2DBE_VDIF_THREAD_ID = "r2dbe_vdif_%d_hdr_w3_thread_id"
R2DBE_VDIF_STATION_ID = "r2dbe_vdif_%d_hdr_w3_station_id"
R2DBE_VDIF_HDR_W4 = "r2dbe_vdif_%d_hdr_w4"
R2DBE_VDIF_TEST_SELECT = "r2dbe_vdif_%d_test_sel"
R2DBE_VDIF_LITTLE_ENDIAN = "r2dbe_vdif_%d_little_end"
R2DBE_VDIF_REORDER_2BIT = "r2dbe_vdif_%d_reorder_2b_samps"

# R2DBE power memory
R2DBE_POWER_BUFFER = "r2dbe_monitor%d_power"
R2DBE_POWER_BUFFER_NMEM = 16384
R2DBE_POWER_BUFFER_SIZET = 8
R2DBE_POWER_BUFFER_FMT = ">%dQ"
R2DBE_POWER_MASK_MSC = 0x3FF
R2DBE_POWER_RSHIFT_MSC = 0
R2DBE_POWER_MASK_SEC = 0x3FFFFF
R2DBE_POWER_RSHIFT_SEC = 10
R2DBE_POWER_MASK_PWR = 0xFFFFFFFF
R2DBE_POWER_RSHIFT_PWR = 32

# R2DBE 8-bit state count memory
R2DBE_COUNTS_BUFFER = "r2dbe_monitor%d_counts"
R2DBE_COUNTS_BUFFER_NMEM = 16384
R2DBE_COUNTS_BUFFER_SIZET = 8
R2DBE_COUNTS_BUFFER_FMT = ">%dQ"
R2DBE_COUNTS_MASK_SEC = 0x3FFFFF
R2DBE_COUNTS_RSHIFT_SEC = 10
R2DBE_COUNTS_MASK_CNT = 0x3FFFFFFF
R2DBE_COUNTS_RSHIFT_CNT = 32
# X number of seconds, by 4 cores, by 256 states
R2DBE_COUNTS_SHAPE = (-1, 4, 256)
R2DBE_COUNTS_ROLL_BY = 128
R2DBE_COUNTS_ROLL_AXIS = 2
# Core ordering along 1th axis
R2DBE_COUNTS_CORE_ORDER = (0, 2, 1, 3)
