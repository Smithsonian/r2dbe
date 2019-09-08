from datetime import datetime, timedelta

from numpy import array, nonzero

from vdif import VDIFTime

class AutoRefillList(list):

	def __init__(self, refill_func, *args, **kwargs):
		super(AutoRefillList, self).__init__(*args)

		self._refill_func = refill_func
		self._refill_len = kwargs.pop("refill_len", 2)

	def _auto_refill(self):
		# If list is short enough, call the refill method
		if len(self) <= self._refill_len:
			self.extend(self._refill_func())

	def pop(self, *args):
		# Usual pop
		super(AutoRefillList, self).pop(*args)

		self._auto_refill()

	def remove(self, it):
		# Usual remove
		super(AutoRefillList, self).remove(it)

		self._auto_refill()

class PowerData(object):

	def __init__(self, msec, sec, pwr):

		self._millisecond = array([int(m) for m in msec])
		self._second = array([int(s) for s in sec])
		self._power = array([int(p) for p in pwr])

	@classmethod
	def list_from_dump(cls, msec, sec, pwr, batch_size=1000):
		# Sort data
		total_msec = msec + 1000 * sec
		grp = zip(msec, sec, pwr)
		grp = [g for _, g in sorted(zip(total_msec, grp))]

		# Batch the data
		n_batch = len(grp) / batch_size
		grp = array(grp)[-n_batch*batch_size:, :]
		pd_list = []
		for ibatch in range(n_batch):
			idx_s = ibatch * batch_size
			idx_e = (ibatch + 1) * batch_size
			pd_list.append(cls(grp[idx_s:idx_e, 0], grp[idx_s:idx_e, 1], grp[idx_s:idx_e, 2]))

		return pd_list

	def avg(self):
		return self._power.mean()

	@property
	def time(self):
		# Get current VDIF epoch
		epoch = VDIFTime.from_datetime(datetime.utcnow()).epoch
		# Create datetime for each second
		datetimes = [VDIFTime(epoch, s).to_datetime() for s in self._second]
		# Add millisecond offset
		deltas = [timedelta(microseconds=m * 1000) for m in self._millisecond]
		datetimes = [dt + d for dt, d in zip(datetimes, deltas)]

		return datetimes

	@property
	def power(self):
		return self._power

class StateCount8bitData(object):

	def __init__(self, sec, cnt, val):

		self._time = sec
		self._value = val
		self._count = count

	@property
	def time(self):
		return self._time

	@property
	def value(self):
		return self._value

	@property
	def count(self):
		return self._count
