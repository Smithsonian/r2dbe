import logging

from datetime import datetime
from numpy import nonzero
from numpy.fft import fft, fftfreq
from pickle import dumps, loads
from redis import StrictRedis
from time import sleep
from threading import Semaphore, Thread

from ..r2dbe import R2dbe, R2DBE_INPUTS, R2DBE_OUTPUTS, R2DBE_SAMPLE_RATE

from defines import *

module_logger = logging.getLogger(__name__)

_register_lock = Semaphore()
_register = {}

def build_key(mclass, entity, group, attribute, arg=None):
	key = KEY_FORMAT_STRING.format(ksp=KEY_SPLIT, mclass=mclass, instance=entity,
	  group=group, attribute=attribute)
	if arg is not None:
		key = KEY_ARG_FORMAT_STRING.format(key=key, arg=arg)

	return key

def decode_attribute_data(enc):
	return loads(enc)

def encode_attribute_data(arr):
	return dumps(arr)

def _register_monitor(monitor):
		global _registry_lock
		
		# Acquire lock
		_register_lock.acquire(True)

		# Register the monitor
		monitoree = monitor.who
		new_id = 0
		try:
			new_id = max(_register[monitoree]) + 1
			_register[monitoree].append(new_id)
		except KeyError:
			# No other monitors registered yet, keep initial new_id
			_register[monitoree] = [new_id]

		module_logger.info("Registered monitor '{monid}' for entity '{who}'".format(monid=new_id, who=monitoree))

		# Release lock
		_register_lock.release()

		return new_id

def _deregister_monitor(monitor):
		global _registry_lock
		
		# Acquire lock
		_register_lock.acquire(True)

		# Register the monitor
		monitoree = monitor.who
		try:
			_register[monitoree].pop(_register[monitoree].index(monitor.identity))
			if len(_register[monitoree]) == 0:
				_register.pop(monitoree)
		except IndexError:
			module_logger.error("Monitor '{monid}' for entity '{who}' is not registered".format(monid=monitor.identity,
			  who=monitoree))
		except KeyError:
			module_logger.error("No monitors are registered for entity '{who}'".format(monid=monitor.identity,
			  who=monitoree))

		module_logger.info("Deregistered monitor '{monid}' for entity '{who}'".format(monid=monitor.identity,
		  who=monitoree))

		# Release lock
		_register_lock.release()

class MonitorStopped(Exception):
	pass

class R2dbeMonitor(Thread):

	_MAP_GROUP_METHOD = {
	  R2DBE_GROUP_SNAP: "_get_group_snap",
	  R2DBE_GROUP_POWER: "_get_group_power",
	  R2DBE_GROUP_TIME: "_get_group_time",
	  R2DBE_GROUP_VDIF: "_get_group_vdif",
	}

	@property
	def identity(self):
		return self._id

	@property
	def who(self):
		return self._r2dbe_host

	def __init__(self, r2dbe_host, period=2.0, stale_after=None, redis_host="localhost", port=6379, db=0, parent_logger=module_logger,
	  *args, **kwargs):

		super(R2dbeMonitor, self).__init__(*args, **kwargs)

		# Set roach2 host and connect
		self._r2dbe_host = r2dbe_host
		self._R2dbe = R2dbe(self._r2dbe_host)

		# Register this monitor
		self._id = _register_monitor(self)

		# Set logger
		self.logger = logging.getLogger("{name}[host={host!r}, identity={monid}]".format(name=".".join((parent_logger.name,
		  self.__class__.__name__)), host=self._R2dbe, monid=self.identity))

		# Connect to redis server
		self._redis_host = redis_host
		self._redis = StrictRedis(self._redis_host, port=port, db=db)

		# Set characteristic times
		self._period = period
		self._stale_after = int(self._period + 1)
		if stale_after:
			self._stale_after = int(stale_after)

		# Create lock and terminate condition
		self._lock = Semaphore()
		self._stop = False

		# Initialize the parameters to monitor
		self._groups = set([])

	def _build_key(self, group, attribute, arg=None):
		key = build_key(R2DBE_MCLASS, self._r2dbe_host, group, attribute, arg=arg)

		return key

	def _call_by_group(self, group_name):
		try:
			# Find the method to call
			method_name = self._MAP_GROUP_METHOD[group_name]
			method = getattr(self, method_name)
		except KeyError:
			self.logger.error("Invalid group '{grp}' requested".format(grp=group_name))
			return
		except AttributeError:
			self.logger.error("Monitor method for group '{grp}' not implemented yet".format(grp=group_name))
			return
		method()

	def _is_stopped(self):
		# Acquire lock
		self._lock.acquire(True)

		# Read the stop flag
		stop = self._stop

		# Release lock
		self._lock.release()

		return stop

	def _get_group_snap(self):
		# Get snapshots for 2-bit and 8-bit data in a single read
		x2, x8 = self._R2dbe.get_2bit_and_8bit_snapshot(list(R2DBE_INPUTS))

		# Compute spectrum frequencies
		freq = fftfreq(R2DBE_SNAP_FFT_SIZE, 1.0 / R2DBE_SAMPLE_RATE)

		# Limit to only positive half-spectrum
		idx_pos_half = nonzero(freq >= 0)[0]
		freq = freq[idx_pos_half]

		# Compute state counts (2-bit data only), and spectral density
		for ii, inp in enumerate(R2DBE_INPUTS):
			# Compute 2-bit state counts (reuse snapshot data)
			counts2, values2 = self._R2dbe.get_2bit_state_counts(inp, reuse_samples=x2[ii])

			# State counts
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_COUNTS,
			  arg=R2DBE_ARG_SNAP_2BIT_COUNTS % inp)
			self._keys_values[key] = counts2

			# State values
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_VALUES,
			  arg=R2DBE_ARG_SNAP_2BIT_VALUES % inp)
			self._keys_values[key] = values2

			# 2-bit spectral density
			X2 = fft(x2[ii].reshape((-1,R2DBE_SNAP_FFT_SIZE)), axis=-1)
			S2 = (X2 * X2.conj()).mean(axis=0)[idx_pos_half]

			# Spectral density
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_DENSITY,
			  arg=R2DBE_ARG_SNAP_2BIT_DENSITY % inp)
			self._keys_values[key] = S2

			# Frequency bins
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_FREQUENCY,
			  arg=R2DBE_ARG_SNAP_2BIT_FREQUENCY % inp)
			self._keys_values[key] = freq

			# 8-bit spectral density
			X8 = fft(x8[ii].reshape((-1,R2DBE_SNAP_FFT_SIZE)), axis=-1)
			S8 = (X8 * X8.conj()).mean(axis=0)[idx_pos_half]

			# Spectral density
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_DENSITY,
			  arg=R2DBE_ARG_SNAP_8BIT_DENSITY % inp)
			self._keys_values[key] = S8

			# Frequency bins
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_FREQUENCY,
			  arg=R2DBE_ARG_SNAP_8BIT_FREQUENCY % inp)
			self._keys_values[key] = freq

		# Get state counts for 8-bit data (not from snapshot)
		counts8, values8 = self._R2dbe.get_8bit_state_counts(list(R2DBE_INPUTS))
		for ii, inp in enumerate(R2DBE_INPUTS):
			# State counts
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_COUNTS,
			  arg=R2DBE_ARG_SNAP_8BIT_COUNTS % inp)
			self._keys_values[key] = counts8[ii]
			# State values
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_VALUES,
			  arg=R2DBE_ARG_SNAP_8BIT_VALUES % inp)
			self._keys_values[key] = values8[ii]

		# Get 2-bit requantization thresholds
		thresholds = self._R2dbe.get_2bit_threshold(list(R2DBE_INPUTS))
		for ii, inp in enumerate(R2DBE_INPUTS):
			key = self._build_key(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_THRESHOLD,
			  arg=R2DBE_ARG_SNAP_2BIT_THRESHOLD % inp)
			self._keys_values[key] = thresholds[ii]

	def _get_group_power(self):
		pass

	def _get_group_time(self):
		# Current time
		key = self._build_key(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_NOW)
		self._keys_values[key] = self._R2dbe.get_time()

		# Up time
		key = self._build_key(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_ALIVE)
		self._keys_values[key] = self._R2dbe.get_up_time()

		# GPS PPS count
		key = self._build_key(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_GPS_PPS_COUNT)
		self._keys_values[key] = self._R2dbe.get_gps_pps_count()

		# GPS PPS offset seconds
		key = self._build_key(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_GPS_PPS_OFFSET_TIME)
		self._keys_values[key] = self._R2dbe.get_gps_pps_time_offset()

		# GPS PPS offset clock cycles
		key = self._build_key(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_GPS_PPS_OFFSET_CYCLE)
		self._keys_values[key] = self._R2dbe.get_gps_pps_clock_offset()

	def _get_group_vdif(self):
		# Get station codes
		station_ids = self._R2dbe.get_station_id(list(R2DBE_OUTPUTS))
		for ii, outp in enumerate(R2DBE_OUTPUTS):
			key = self._build_key(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_STATION, arg=R2DBE_ARG_VDIF_STATION % outp)
			self._keys_values[key] = station_ids[ii]

		# Get IFSignal
		inputs = self._R2dbe.get_input(list(R2DBE_INPUTS))
		for ii, inp in enumerate(R2DBE_INPUTS):
			# Receiver sideband
			key = self._build_key(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_RECEIVER_SIDEBAND,
			  arg=R2DBE_ARG_VDIF_RECEIVER_SIDEBAND % inp)
			self._keys_values[key] = str(inputs[ii].rx_sb)
			# BDC sideband
			key = self._build_key(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_BDC_SIDEBAND, arg=R2DBE_ARG_VDIF_BDC_SIDEBAND % inp)
			self._keys_values[key] = str(inputs[ii].bdc_sb)
			# Polarization
			key = self._build_key(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_POLARIZATION, arg=R2DBE_ARG_VDIF_POLARIZATION % inp)
			self._keys_values[key] = str(inputs[ii].pol)

	def _monitor_groups(self):
		# Initialize local result storage
		self._keys_values = {}

		for group in self._groups:
			self._call_by_group(group)

		# Register the results
		for key, value in self._keys_values.items():
			self._store_attribute(key, encode_attribute_data(value), expire_after=self._stale_after)

	def _store_attribute(self, name, value, expire_after=0):
		self._redis.set(name, value, ex=expire_after)

	def add_group(self, group):
		if group in self._groups:
			self.logger.warn("Group '{grp}' already in monitor list".format(grp=group))
			return

		self._groups.add(group)

		self.logger.info("Added '{grp}' to monitor list".format(grp=group))

	def del_group(self, group):
		try:
			self._groups.remove(group)

			self.logger.info("Removed '{grp}' from monitor list".format(grp=group))

		except KeyError:
			self.logger.error("Could not remove '{grp}', not in monitor list".format(grp=group))

	def set_stop(self):
		# Acquire lock
		self._lock.acquire(True)

		# Set the stop flag
		self._stop = True

		# Release lock
		self._lock.release()

	def run(self):

		# Subtract this from the wait time for start of next monitoring period
		SLEEP_OFFSET = 0.001
		# In case calculated wait time is negative, sleep for at least 
		SLEEP_MIN = 0.000001
		# Set maximum sleep time for faster external interrupt
		SLEEP_MAX = 1.0

		time_prev = datetime.utcnow()

		try:

			while True:

				time_curr = datetime.utcnow()
				while True:

					# First check if stop condition reached
					if self._is_stopped():
						self.logger.info("Received stop signal, quiting.")
						raise MonitorStopped()

					# Then check if it is time to update data
					wait_for = self._period - (time_curr - time_prev).total_seconds()
					if wait_for < 0:
						break

					# Otherwise wait a while
					sleep_time = min(wait_for, SLEEP_MAX)
					sleep_time = max(sleep_time - SLEEP_OFFSET, SLEEP_MIN)
					sleep(sleep_time)

					# Update current time
					time_curr = datetime.utcnow()

				# Update previous time
				time_prev = time_curr

				# Do the monitoring
				self._monitor_groups()

		except MonitorStopped:
			pass

		# Deregister this monitor
		_deregister_monitor(self)
		delattr(self, "_id")

class R2dbeSyncMonitor(R2dbeMonitor):

	def __init__(self, r2dbe_host, ignore_late=False, usec_into=300000, usec_tol=100000, **kwargs):
		super(R2dbeSyncMonitor, self).__init__(r2dbe_host, **kwargs)

		# Set timing characteristics
		self._usec_into = usec_into
		self._usec_tol = usec_tol

		# Set whether late data is to be ignored
		self._ignore_late = ignore_late

	def _monitor_groups(self):
		# Initialize local result storage
		self._keys_values = {}

		# Wait until few 100s of ms into second
		t0 = datetime.utcnow()
		one_sec_usec = 1000000
		one_usec_sec = 1e-6
		while abs(t0.microsecond - self._usec_into) > self._usec_tol:
			if t0.microsecond > self._usec_into:
				# sleep until start of next second
				sleep_time_usec = one_sec_usec - t0.microsecond
			else:
				# sleep until earliest valid
				sleep_time_usec = self._usec_into - self._usec_tol - t0.microsecond
			sleep(max(sleep_time_usec * one_usec_sec, one_usec_sec))
			t0 = datetime.utcnow()

		for group in self._groups:
			self._call_by_group(group)

		# Check if all reads completed in the same second
		t1 = datetime.utcnow()
		if (t1.second != t0.second):
			self.logger.warn("Not all attributes for group '{grp}' were read within the same second (delta = {sec:.3f})".format(
			  grp=R2DBE_GROUP_TIME, sec=(t1 - t0).total_seconds()))

			# If late data is ignored, return without storing
			if self._ignore_late:
				return

		# Register the results
		for key, value in self._keys_values.items():
			self._store_attribute(key, encode_attribute_data(value), expire_after=self._stale_after)
