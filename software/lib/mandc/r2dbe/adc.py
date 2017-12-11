from numpy import array

import adc5g

OFFSET_LSB_STEP = 0.2
OFFSET_LSB_TO_MV_MULTIPLIER = 2.0
OFFSET_MV_MAX = 49.8
OFFSET_MV_MIN = -49.8
GAIN_PER_STEP = 0.14
GAIN_PER_MAX = 17.9
GAIN_PER_MIN = -17.9

def set_core_offsets(roach2, zdok, offsets_lsb):
	# Convert offset in LSb to mV
	offsets_mv = array(offsets_lsb) * OFFSET_LSB_TO_MV_MULTIPLIER

	for core_n, offset_n in enumerate(offsets_mv):
		# Limit offset to allowable range
		offset_n = min(OFFSET_MV_MAX, offset_n)
		offset_n = max(OFFSET_MV_MIN, offset_n)

		# Apply this offset
		adc5g.set_spi_offset(roach2, zdok, core_n + 1, offset_n)

def get_core_offsets(roach2, zdok):
	# Get core values in mV
	offsets_mv = array([adc5g.get_spi_offset(roach2, zdok, core_n) for core_n in range(1,5)])

	# Convert to LSb
	return offsets_mv / OFFSET_LSB_TO_MV_MULTIPLIER

def adj_core_offsets(roach2, zdok, diff_offsets_lsb):
	# Get current core settigns
	offsets_lsb = get_core_offsets(roach2, zdok)

	# Add difference
	offsets_lsb += diff_offsets_lsb

	# Set updated offsets
	set_core_offsets(roach2, zdok, offsets_lsb)

	return offsets_lsb

def set_core_gains(roach2, zdok, gains):
	for core_n, gain_n in enumerate(gains):
		# Limit gain to allowable range
		gain_n = min(GAIN_PER_MAX, gain_n)
		gain_n = max(GAIN_PER_MIN, gain_n)

		# Apply this gain
		adc5g.set_spi_gain(roach2, zdok, core_n + 1, gain_n)

def get_core_gains(roach2, zdok):
	return array([adc5g.get_spi_gain(roach2, zdok, core_n) for core_n in range(1,5)])

def adj_core_gains(roach2, zdok, diff_gains):
	# Get current core settings
	gains = get_core_gains(roach2, zdok)

	# Add difference
	gains += diff_gains

	# Set updated gains
	set_core_gains(roach2, zdok, gains)

	return gains
