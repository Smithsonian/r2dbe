from subprocess import call

CONFIG_FILENAME='rtc.conf'

# [misc]
CONFIG_MISC_SECTION='misc'
CONFIG_MISC_EXP='exp'

# [scan]
CONFIG_SCAN_SECTION='scan'
CONFIG_SCAN_NAME='name'
CONFIG_SCAN_DURATION='duration'
CONFIG_SCAN_SIZE='size'
CONFIG_SCAN_TIME='time'

# [dut]
CONFIG_DUT_SECTION='dut'
CONFIG_DUT_HOST='host'
CONFIG_DUT_NAME='name'
CONFIG_DUT_TYPE='type'

# [data]
CONFIG_DATA_SECTION='data'
CONFIG_DATA_PATH='path'

# [corr]
CONFIG_CORR_SECTION='corr'
CONFIG_CORR_SETS='sets'

# [corrN]
CONFIG_CORRN_SECTION_FMT='corr{0:d}'
CONFIG_CORRN_R2DBE='r2dbe'
CONFIG_CORRN_SDBE='sdbe'
CONFIG_CORRN_R2DBE_FIRST_SAMPLE='r2dbe_t0'
CONFIG_CORRN_SDBE_FIRST_SAMPLE='sdbe_t0'
CONFIG_CORRN_PRIOR_SDBE_SAMPLE_LEAD='prior_sdbe_sample_lead'
CONFIG_CORRN_PRIOR_SDBE_WINDOW_LAG='prior_sdbe_window_lag'
CONFIG_CORRN_PRIOR_SDBE_PHASE_SLOPE='prior_sdbe_phase_slope'
CONFIG_CORRN_COEFF='correlation_coeff'
CONFIG_CORRN_SNR='correlation_snr'

SCAN_TIME_FMT = '%Yy%jd%Hh%Mm%Ss'
SCAN_NAME_FMT = '%j-%H%M%S'

FLATFILE_FILENAME_TEMPLATE = "{0}_{1}_{2}_{3}.vdif"
def get_flatfile_filename(exp,dut,scan,stream):
    return FLATFILE_FILENAME_TEMPLATE.format(
        exp,
        dut,
        scan,
        stream
    )

def threaded_call(call_str):
    print(call_str)
    call(call_str,shell=True)

