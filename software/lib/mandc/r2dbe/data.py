from numpy import array, concatenate

class TimeSeriesData(object):

	def __init__(self, t_arr, d_arr):

		# Check if input valid
		self._check_valid_time_data_pair(t_arr, d_arr)

		# Extract unique samples and sort
		t_sorted, d_sorted = self._unique_sort(t_arr, d_arr)

		self.time = array(t_sorted)
		self.data = array(d_sorted)

	def _check_valid_time_data_pair(self, t_arr, d_arr):

		# Check if equal number of time and data samples
		if len(t_arr) != len(d_arr):
			raise RuntimeError("Number of time and data samples must be equal.")

		return True

	def _unique_sort(self, t_arr, d_arr):

		# Zip for easy handling
		z = zip(t_arr, d_arr)

		# Remove possible duplicate entries
		z_set = set(z)

		# Check that set of time samples is same size
		t_set = set(t_arr)
		if len(t_set) != len(z_set):
			raise RuntimeError("Multiple data values associated with same time value.")

		# Sort input time-order
		z_sorted = sorted(z_set)

		# Split into samples and store
		t_sorted, d_sorted = zip(*z_sorted)

		return t_sorted, d_sorted

	def update(self, t_arr_upd, d_arr_upd):

		# Check if input valid
		self._check_valid_time_data_pair(t_arr_upd,d_arr_upd)

		# Append new time and data samples
		t_arr = concatenate((self.time, t_arr_upd), axis=0)
		d_arr = concatenate((self.data, d_arr_upd),  axis=0)

		# Extract unique samples and sort
		t_sorted, d_sorted = self._unique_sort(t_arr, d_arr)

		self.time = array(t_sorted)
		self.data = array(d_sorted)

class PowerData(TimeSeriesData):

	pass

class CountData(TimeSeriesData):

	pass
