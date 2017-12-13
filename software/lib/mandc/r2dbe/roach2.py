import logging

from datetime import datetime, timedelta
from numpy import arange, array, nonzero, sqrt, roll, uint32, uint64
from struct import pack, unpack
from time import ctime, sleep

import adc5g

from corr.katcp_wrapper import FpgaClient

import adc
from ..primitives.base import IFSignal, EthEntity, EthRoute, IPAddress, MACAddress, Port
from defines import *
from ..data import VDIFTime

module_logger = logging.getLogger(__name__)

def format_bitcode_version(rcs):
	if "app_last_modified" in rcs.keys():
		return "compiled {0}".format(ctime(rcs["app_last_modified"]))
	if "app_rcs_type" in rcs.keys():
		if rcs["app_rcs_type"] == "git" and "app_rev" in rcs.keys():
			dirty_suffix = "-dirty" if "app_dirty" in rcs.keys() and rcs["app_dirty"] else ""
			return "git hash {0:07x}{1}".format(rcs["app_rev"], dirty_suffix)
	return "unknown"

class Roach2(object):

	def __init__(self, roach2_host, parent_logger=module_logger):
		self.roach2_host = roach2_host
		self.logger = logging.getLogger("{name}[host={host!r}]".format(name=".".join((parent_logger.name, 
		  self.__class__.__name__)), host=self.roach2_host,))
		# connect to ROACH2
		if self.roach2_host:
			self._connect()

	def _connect(self):
		self.roach2 = FpgaClient(self.roach2_host)
		if not self.roach2.wait_connected(timeout=5):
			raise RuntimeError("Timeout trying to connect to {0}. Is it up and running?".format(self.roach2.host))

	def _program(self, bitcode):
		try:
			self.roach2.progdev(bitcode)
		except RuntimeError as re:
			self.logger.critical("Failed to program {roach2!r} with bitcode {code!r}. Is the BOF file installed?".format(
			  roach2=self.roach2_host, code=bitcode))
			raise re
		return format_bitcode_version(self.roach2.get_rcs())

	def _read_int(self, name):
		value = self.roach2.read_int(name)
		self.logger.debug("read_int: {0} --> 0x{1:08x}".format(name, value))
		return value

	def _write_int(self, name, value):
		self.roach2.write_int(name, value)
		self.logger.debug("write_int: {0} <-- 0x{1:08x}".format(name, value))

class R2dbe(Roach2):

	def __init__(self, roach2_host, bitcode=R2DBE_DEFAULT_BITCODE, parent_logger=module_logger):
		super(R2dbe, self).__init__(roach2_host)
		self.logger = logging.getLogger("{name}[host={host!r}]".format(name=".".join((parent_logger.name, 
		  self.__class__.__name__)), host=self.roach2_host,))
		self.bitcode = bitcode
		self._inputs = [IFSignal(parent_logger=self.logger), ] * R2DBE_NUM_INPUTS
		self._outputs = [EthRoute(parent_logger=self.logger), ] * R2DBE_NUM_OUTPUTS

	def __repr__(self):
		repr_str = "{name}[\n  {inputs[0]!r} : {outputs[0]!r}\n  {inputs[1]!r} : {outputs[1]!r}\n]"
		return repr_str.format(name=self.roach2_host, inputs=self._inputs, outputs=self._outputs)

	def _dump_counts_buffer(self, input_n):
		# Read buffer and interpret
		raw_bin = self.roach2.read(R2DBE_COUNTS_BUFFER % input_n, R2DBE_COUNTS_BUFFER_NMEM * R2DBE_COUNTS_BUFFER_SIZET)
		raw_int = array(unpack(R2DBE_COUNTS_BUFFER_FMT % R2DBE_COUNTS_BUFFER_NMEM, raw_bin), dtype=uint64)
		sec = (raw_int >> R2DBE_COUNTS_RSHIFT_SEC) & R2DBE_COUNTS_MASK_SEC
		cnt = (raw_int >> R2DBE_COUNTS_RSHIFT_CNT) & R2DBE_COUNTS_MASK_CNT

		# Reshape counts
		cnt = cnt.reshape(R2DBE_COUNTS_SHAPE).astype(uint32)

		# Reorder cores
		cnt = cnt[:,R2DBE_COUNTS_CORE_ORDER,:]

		# Roll to take care of 2's complement representation
		cnt = roll(cnt,R2DBE_COUNTS_ROLL_BY,axis=R2DBE_COUNTS_ROLL_AXIS)

		# Only keep unique time values
		sec = sec.reshape(R2DBE_COUNTS_SHAPE)[:, 0, 0].astype(uint32)

		# Apply time offset to absolute reference
		sec = self._offset_alive_sec(sec)

		# Create sample value array to return
		val = arange(-R2DBE_COUNTS_SHAPE[-1]/2, R2DBE_COUNTS_SHAPE[-1]/2, 1).astype(int)

		return sec, cnt, val

	def _dump_counts_mean_variance(self, input_n):
		# Get counts
		sec, cnt, val = self._dump_counts_buffer(input_n)

		# Reshape val for proper broadcasting
		val = val.reshape((1, 1, -1))

		# Get discrete probability distribution
		p = cnt.astype(float) / cnt.sum(axis=-1).reshape((R2DBE_COUNTS_SHAPE[0], R2DBE_COUNTS_SHAPE[1], 1))

		# Calculate mean and variance
		means = (p*val).sum(axis=-1)
		variances = (p*(val - means.reshape((R2DBE_COUNTS_SHAPE[0], R2DBE_COUNTS_SHAPE[1], 1)))**2).sum(axis=-1)

		return sec, means, variances

	def _dump_power_buffer(self, input_n):
		# Read buffer and interpret
		raw_bin = self.roach2.read(R2DBE_POWER_BUFFER % input_n, R2DBE_POWER_BUFFER_NMEM * R2DBE_POWER_BUFFER_SIZET)
		raw_int = array(unpack(R2DBE_POWER_BUFFER_FMT % R2DBE_POWER_BUFFER_NMEM, raw_bin), dtype=uint64)
		msc = (raw_int >> R2DBE_POWER_RSHIFT_MSC) & R2DBE_POWER_MASK_MSC
		sec = (raw_int >> R2DBE_POWER_RSHIFT_SEC) & R2DBE_POWER_MASK_SEC
		pwr = (raw_int >> R2DBE_POWER_RSHIFT_SEC) & R2DBE_POWER_MASK_SEC

		# Apply time offset to absolute reference
		sec = self._offset_alive_sec(sec)

		return msc, sec, pwr

	def _offset_alive_sec(self, sec):
		abs_time = self._read_int(R2DBE_ONEPPS_SINCE_EPOCH)
		alive = self._read_int(R2DBE_ONEPPS_ALIVE)
		offset = abs_time - alive

		return sec + offset

	@classmethod
	def make_default_route_from_destination(cls, dst_mac, dst_ip, dst_port=Port(4001)):
		dst = EthEntity(mac_addr_entity=dst_mac, ip_addr_entity=dst_ip, port_entity=dst_port)
		src_ip = IPAddress((dst_ip.address & 0xFFFFFF00) + 254)
		src_mac = MACAddress((2<<40) + (2<<32) + src_ip.address)
		src_port = Port(dst_port.port - 1)
		src = EthEntity(mac_addr_entity=src_mac, ip_addr_entity=src_ip, port_entity=src_port)
		return EthRoute(source_entity=src, destination_entity=dst)

	def adc_interface_cal(self, input_n):
		# Set data input source to ADC (store current setting)
		data_select = self.get_input_data_source(input_n)
		self.set_input_data_source(input_n, R2DBE_INPUT_DATA_SOURCE_ADC)

		# Set ADC test mode
		adc5g.set_test_mode(self.roach2, input_n)
		adc5g.sync_adc(self.roach2)

		# Do calibration
		opt, glitches = adc5g.calibrate_mmcm_phase(self.roach2, input_n, [R2DBE_DATA_SNAPSHOT_8BIT % input_n,])
		gstr = adc5g.pretty_glitch_profile(opt, glitches)
		self.logger.info("ADC{0} calibration found optimal phase: {1} [{2}]".format(input_n, opt, gstr))

		# Unset ADC test mode
		adc5g.unset_test_mode(self.roach2, input_n)

		# Restore input source
		self.set_input_data_source(input_n, data_select)

	def adc_core_cal(self, input_n, max_iter=5, curb_gain_step=0.5, curb_offset_step=0.5):
		# Reset core gain parameters
		self.logger.debug("Resetting ADC{0} core gain parameters".format(input_n))
		adc.set_core_gains(self.roach2, input_n, [0]*4)

		# Get current gain settings
		gains_0 = adc.get_core_gains(self.roach2, input_n)

		# Wait for new settings to take effect
		sleep(3)

		# Get reset standard deviations
		sec, _, variances = self._dump_counts_mean_variance(input_n)
		std_0 = sqrt(variances[sec.argmax()-1, :])
		self.logger.debug("Initial ADC{0} standard deviations are [{1}]".format(input_n,
		  ", ".join(["{0:+.3f}".format(s) for s in std_0])))

		# Take reference standard deviation as mean across all cores
		std_ref = std_0.mean()
		self.logger.debug("Reference standard deviation for ADC{0} is {1:.3f}".format(input_n, std_ref))

		# Compute gain adjustment per core
		gain_adj = 100*(1.0 - std_0 / std_ref) * curb_gain_step

		# Store best offset / gain parameters
		best_gains = gains_0
		best_gains_adj = abs(gain_adj)
		best_gains_std = std_0

		# Feed back initial gain adjustment
		curr_gains = adc.adj_core_gains(self.roach2, input_n, gain_adj)
		self.logger.debug("Initial gain adjustments for ADC{0} are [{1}] % (updated values are [{2}] %)".format(input_n,
		  ", ".join(["{0:+.3f}".format(a) for a in gain_adj]), ", ".join(["{0:+.3f}".format(g) for g in curr_gains])))

		# Now iterate until gain solution converges
		tries = 0
		while True:
			# Wait for new settings to take effect
			sleep(3)

			# Measure new standard deviations
			sec, _, variances = self._dump_counts_mean_variance(input_n)
			std_u = sqrt(variances[sec.argmax()-1, :])
			self.logger.debug("Updated standard deviations for ADC{0} are [{1}]".format(input_n,
			  ", ".join(["{0:+.3f}".format(s) for s in std_u])))

			# Compute gain adjustment per core
			gain_adj = 100*(1.0 - std_u / std_ref) * curb_gain_step

			# Zero any gain adjustment smaller than the resolution
			gain_adj[abs(gain_adj) < adc.GAIN_PER_STEP * curb_gain_step] = 0

			# Keep settings that yield smallest absolute adjustment
			for ii in range(len(gain_adj)):
				if abs(gain_adj[ii]) < abs(best_gains_adj[ii]):
					best_gains[ii] = curr_gains[ii]
					best_gains_adj[ii] = gain_adj[ii]
					best_gains_std[ii] = std_u[ii]

			# If gain adjustments are zero, exit
			if (gain_adj == 0).all():
				self.logger.debug("ADC{0} core gain solution converged".format(input_n))
				break

			# Feed back update
			curr_gains = adc.adj_core_gains(self.roach2, input_n, gain_adj)

			self.logger.debug("Updated gain adjustments for ADC{0} are [{1}] % (updated values are [{2}] %)".format(input_n,
			  ", ".join(["{0:+.3f}".format(a) for a in gain_adj]),
			  ", ".join(["{0:+.3f}".format(g) for g in curr_gains])))

			# Increment tries and abort if necessary
			tries += 1
			if tries >= max_iter:
				self.logger.warn("Maximum number of iterations for ADC{0} core gain cal reached, using best result".format(
				  input_n))
				break

		self.logger.debug("ADC{0} core gain solution: [{1}] (standard deviations were [{2}])".format(input_n,
		  ", ".join(["{0:+.3f}".format(g) for g in best_gains]),
		  ", ".join(["{0:+.3f}".format(s) for s in best_gains_std])))

		# Reset core offset parameters
		self.logger.debug("Resetting ADC{0} core offset parameters".format(input_n))
		adc.set_core_offsets(self.roach2, input_n, [0]*4)

		# Get current offset settings
		offsets_0 = adc.get_core_offsets(self.roach2, input_n)

		# Wait for new settings to take effect
		sleep(3)

		# Get reset mean
		sec, means, _ = self._dump_counts_mean_variance(input_n)
		mean_0 = means[sec.argmax()-1, :]
		self.logger.debug("Initial ADC{0} means are [{1}]".format(input_n,
		  ", ".join(["{0:+.3f}".format(m) for m in mean_0])))

		# Compute offset adjustment per core
		offset_adj = -mean_0 * curb_offset_step

		# Store best offset / gain parameters
		best_offsets = offsets_0
		best_offsets_adj = abs(offset_adj)
		best_offsets_mean = mean_0

		# Feed back initial gain adjustment
		curr_offsets = adc.adj_core_offsets(self.roach2, input_n, offset_adj)
		self.logger.debug("Initial offset adjustments for ADC{0} are [{1}] (updated values are [{2}])".format(input_n,
		  ", ".join(["{0:+.3f}".format(a) for a in offset_adj]),
		  ", ".join(["{0:+.3f}".format(o) for o in curr_offsets])))

		# Now iterate until offset solution converges
		tries = 0
		while True:
			# Wait for new settings to take effect
			sleep(3)

			# Measure new means
			sec, means, _ = self._dump_counts_mean_variance(input_n)
			mean_u = means[sec.argmax()-1, :]
			self.logger.debug("Updated means for ADC{0} are [{1}]".format(input_n,
			  ", ".join(["{0:+.3f}".format(m) for m in mean_u])))

			# Compute offset adjustment per core
			offset_adj = -mean_u * curb_offset_step

			# Zero any offset adjustment smaller than the resolution
			offset_adj[abs(offset_adj) < adc.OFFSET_LSB_STEP * curb_offset_step] = 0

			# Keep settings that yield smallest absolute adjustment
			for ii in range(len(offset_adj)):
				if abs(offset_adj[ii]) < abs(best_offsets_adj[ii]):
					best_offsets[ii] = curr_offsets[ii]
					best_offsets_adj[ii] = offset_adj[ii]
					best_offsets_mean[ii] = mean_u[ii]

			# If gain adjustments are zero, exit
			if (offset_adj == 0).all():
				self.logger.debug("ADC{0} core offset solution converged".format(input_n))
				break

			# Feed back update
			curr_offsets = adc.adj_core_offsets(self.roach2, input_n, offset_adj)

			self.logger.debug("Updated offset adjustments for ADC{0} are [{1}] (updated values are [{2}])".format(input_n,
			  ", ".join(["{0:+.3f}".format(a) for a in offset_adj]),
			  ", ".join(["{0:+.3f}".format(o) for o in curr_offsets])))

			# Increment tries and abort if necessary
			tries += 1
			if tries >= max_iter:
				self.logger.warn("Maximum number of iterations for ADC{0} core offset cal reached, using best result".format(
				  input_n))
				break

		self.logger.debug("ADC{0} core offset solution: [{1}] (means were [{2}])".format(input_n,
		  ", ".join(["{0:+.3f}".format(o) for o in best_offsets]),
		  ", ".join(["{0:+.3f}".format(m) for m in best_offsets_mean])))

	def arm_one_pps(self):
		self._write_int(R2DBE_ONEPPS_CTRL, 1<<31)
		self._write_int(R2DBE_ONEPPS_CTRL, 0)

		# Wait until at least one full second has passed
		sleep(2)

	def get_input(self, input_n):
		return self._inputs[input_n]

	def get_input_data_source(self, input_n):
		return self._read_int(R2DBE_INPUT_DATA_SELECT % input_n)

	def get_output(self, output_n):
		return self._outputs[output_n]

	def get_pps_clock_offset(self):
		return self._read_int("r2dbe_onepps_offset")

	def get_pps_time_offset(self):
		return self.get_pps_clock_offset() / R2DBE_CLOCK_RATE

	def get_time(self, output_n=0):
		sec = self._read_int(R2DBE_ONEPPS_SINCE_EPOCH)
		ep = self._read_int(R2DBE_VDIF_REF_EPOCH % output_n)

		return VDIFTime(ep, sec).to_datetime()

	def set_2bit_threshold(self, input_n, threshold=None, outer_bin_frac=0.16, wait=0):
		# If threshold is not specified, compute it
		if threshold is None:
			# Wait given number of seconds, in case of recent power level change
			sleep(wait)

			# Read counts
			sec, cnt, val = self._dump_counts_buffer(input_n)

			# Use only data from second-to-last entry, and sum over cores
			cnt_1sec = cnt[sec.argmax()-1,:,:].sum(axis=0)

			# Compute cumulative distribution function
			cdf_1sec = cnt_1sec.cumsum(axis=0).astype(float)/cnt_1sec.sum()
			
			# Compute thresholds for positive and negative sides, then average
			th_pos = val[nonzero(cdf_1sec < 1.0-outer_bin_frac)[0][-1]]
			th_neg = val[nonzero(cdf_1sec > outer_bin_frac)[0][0]]
			threshold = int(round((abs(th_pos) + abs(th_neg))/2.0))

		self._write_int(R2DBE_QUANTIZATION_TREHSHOLD % input_n, threshold)
		self.logger.debug("Set 2-bit quantization threshold for input {0} to {1} (pos {2:+}, neg {3:+})".format(
		  input_n, threshold, th_pos, th_neg))

	def set_input(self, input_n, ifsig_inst):
		self._inputs[input_n] = ifsig_inst
		self.logger.info("(Analog) if{0} input is {1!r}".format(input_n, ifsig_inst))
		
		w4 = (R2DBE_VDIF_EUD_VERSION<<24) + (ifsig_inst["RxSB"]<<2) + (ifsig_inst["BDCSB"]<<1) + ifsig_inst["Pol"]
		self._write_int(R2DBE_VDIF_HDR_W4 % input_n, w4)

	def set_input_data_source(self, input_n, source):
		self._write_int(R2DBE_INPUT_DATA_SELECT % input_n, source)

	def set_output(self, output_n, ethrt_inst, thread_id=None):
		self._outputs[output_n] = ethrt_inst
		self.logger.info("(10GbE) SLOT0 CH{0} route is {1!r}".format(output_n, ethrt_inst))

		# Get source & destination addresses
		src_ip = ethrt_inst.src["IP"]
		src_port = ethrt_inst.src["Port"]
		src_mac = ethrt_inst.src["MAC"]
		dst_ip = ethrt_inst.dst["IP"]
		dst_port = ethrt_inst.dst["Port"]
		dst_mac = ethrt_inst.dst["MAC"]

		# Populate ARP table
		arp = [0xFFFFFFFF] * 256
		arp[dst_ip & 0x0FF] = dst_mac

		# Configure core and write destination parameters
		self.roach2.config_10gbe_core(R2DBE_TENGBE_CORE % output_n, 
		  src_mac, src_ip, src_port, arp)
		self._write_int(R2DBE_TENGBE_DEST_IP % output_n, dst_ip)
		self._write_int(R2DBE_TENGBE_DEST_PORT % output_n, dst_port)
		
		# Reset transmission
		self._write_int(R2DBE_TENGBE_RESET % output_n, 1)
		self._write_int(R2DBE_TENGBE_RESET % output_n, 0)

	def set_real_time(self):
		# reset VDIF time keeping
		for output_n in R2DBE_OUTPUTS:
			self._write_int(R2DBE_VDIF_RESET % output_n, 1)

		# Wait until the middle of a second to set absolute time
		while (abs(datetime.utcnow().microsecond - 5e5) > 1e5):
			sleep(0.1)

		# Calculate current time VDIF specification (discard frame)
		vdif_time = VDIFTime.from_datetime(datetime.utcnow(), frame_rate=R2DBE_FRAME_RATE, suppress_microsecond=True)

		# enable VDIF time keeping
		for output_n in R2DBE_OUTPUTS:
			self._write_int(R2DBE_VDIF_RESET % output_n, 0)
		
		# write time reference registers
		for output_n in R2DBE_OUTPUTS:
			self._write_int(R2DBE_VDIF_SEC_SINCE_REF_EPOCH % output_n, vdif_time.sec)
			self._write_int(R2DBE_VDIF_REF_EPOCH % output_n, vdif_time.epoch)

		self.logger.info("Time reference is {0!r}".format(vdif_time))

	def set_station_id(self, output_n, station_id):
		station_id_formatted = (ord(station_id[0])<<8) + ord(station_id[1])
		self._write_int(R2DBE_VDIF_STATION_ID % output_n, station_id_formatted)

	def set_thread_id(self, output_n, thread_id=None):
		# Use default if none given
		if thread_id is None:
			thread_id = R2DBE_VDIF_DEFAULT_THREAD_IDS[output_n]

		self._write_int(R2DBE_VDIF_THREAD_ID % output_n, thread_id)

	def set_vdif_data_mode(self, output_n, reorder_2bit=True, little_endian=True, data_not_test=True):
		self._write_int(R2DBE_VDIF_REORDER_2BIT % output_n, int(reorder_2bit))
		self._write_int(R2DBE_VDIF_LITTLE_ENDIAN % output_n, int(little_endian))
		self._write_int(R2DBE_VDIF_TEST_SELECT % output_n, int(not data_not_test))

	def setup(self, station, inputs, outputs, thread_ids=[None]*R2DBE_NUM_OUTPUTS):

		# Program bitcode
		bitcode_version = self._program(self.bitcode)
		self.logger.info("Programmed bitcode '{0}' ({1})".format(self.bitcode, bitcode_version))
		if bitcode_version.find(R2DBE_LATEST_VERSION_GIT_HASH) == -1:
			self.logger.warn("Bitcode does not correspond to latest version which has hash {0}".format(
			  R2DBE_LATEST_VERSION_GIT_HASH))

		# Do ADC interface calibration
		self.logger.info("Performing ADC interface calibration")
		for ii in R2DBE_INPUTS:
			self.adc_interface_cal(ii)

		# Set inputs
		self.logger.info("Defining analog inputs")
		for ii, inp in enumerate(inputs):
			self.set_input_data_source(ii, R2DBE_INPUT_DATA_SOURCE_ADC)
			self.set_input(ii, inp)

		# Arm 1PPS
		self.logger.info("Synchronizing to 1PPS")
		self.arm_one_pps()

		# Set absolute time reference
		self.logger.info("Setting absolute time reference")
		self.set_real_time()

		# Set outputs / VDIF parameters
		self.logger.info("Defining ethernet outputs")
		for ii, outp in enumerate(outputs):
			self.set_output(ii, outp)
			self.set_station_id(ii, station)
			self.set_thread_id(ii, thread_ids[ii])

			# Set the data source / format
			self.set_vdif_data_mode(ii)

		# Give PPS signal time to propagate
		sleep(2)

		# Enable VDIF cores
		self.logger.info("Enabling VDIF transmission")
		for ii, _ in enumerate(outputs):
			self._write_int(R2DBE_VDIF_ENABLE % ii, 1)

		# Do ADC core calibration
		self.logger.info("Performing ADC core calibration")
		for ii, _ in enumerate(inputs):
			self.adc_core_cal(ii)

		# Set 2-bit thresholds
		self.logger.info("Setting 2-bit quantization thresholds")
		for ii, _ in enumerate(inputs):
			self.set_2bit_threshold(ii)


