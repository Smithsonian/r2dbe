#!/usr/bin/env python2.7

import logging

import os.path
import sys

from datetime import datetime
from matplotlib.pyplot import figure, ion, pause
from numpy import abs, log10
from redis import StrictRedis
from time import sleep
from threading import Semaphore

from mandc.monitor.defines import *
from mandc.monitor import (
  build_key,
  decode_attribute_data,
)

from mandc.r2dbe import (
  R2DBE_INPUTS,
  R2DBE_OUTPUTS,
)

_color_map = ["b", "g"]

_stop_lock = Semaphore()
_stop = False

def handle_close(evt):
	global _stop_lock
	global _stop

	# Acquire lock and set stop condition
	with _stop_lock:

		_stop = True

class Panel(object):

	def __init__(self, axes, source, parent_logger=logging.getLogger(__file__)):
		# Set axes
		self._axes = axes

		# Set data source
		self._source = source

		# Set logger
		self.logger = logging.getLogger("{name}".format(name=".".join((parent_logger.name, self.__class__.__name__))))

	def retrieve_data(self, key):
		raw = self._source.get(key)
		if raw is not None:
			return decode_attribute_data(raw)

	def update(self):
		pass

class HistogramPanel(Panel):

	def __init__(self, axes, source, key_bin, key_height, xlim=None, ylim=None, xticks=None, yticks=None, bin_width=0.5,
	  color="b", auto_xtick=False, auto_ytick=False, grid=False, title=None, xlabel=None, ylabel=None, **kwargs):

		# Generic Panel
		super(HistogramPanel, self).__init__(axes, source, **kwargs)

		# Set data source keys
		self._key_b = key_bin
		self._key_h = key_height

		# Set some properties
		if xlim is not None:
			self._axes.set_xlim(xlim)
		if ylim is not None:
			self._axes.set_ylim(ylim)
		if xticks is not None:
			self._axes.set_xticks(xticks)
		if yticks is not None:
			self._axes.set_yticks(yticks)
		if grid:
			self._axes.grid()
		if title is not None:
			self._axes.set_title(title)
		if xlabel is not None:
			self._axes.set_xlabel(xlabel)
		if ylabel is not None:
			self._axes.set_ylabel(ylabel)
		self._auto_xtick = auto_xtick
		self._auto_ytick = auto_ytick
		self._bin_width = bin_width
		self._color = color

	def update(self):

		# Try to retrieve data
		proxy_b = self.retrieve_data(self._key_b)
		proxy_h = self.retrieve_data(self._key_h)

		# Check if None returned
		if any([p is None for p in [proxy_b, proxy_h]]):
			# Do not update, maybe log
			self.logger.warn("Missing data for certain attributes, not updating panel")
			return

		# Data received, carry on
		self._data_b = proxy_b
		self._data_h = 1.0 * proxy_h / proxy_h.sum()

		# Update x- and y-ticks according to data
		if self._auto_xtick:
			self._axes.set_xticks(self._data_b)
		if self._auto_ytick:
			self._axes.set_yticks(sorted(set(self._data_h)))
			self._axes.set_yticklabels(["%.2f" % y for y in sorted(set(self._data_h))])

		# If not plotted yet, initiate
		if not hasattr(self, "_bars"):
			self._bars = self._axes.bar(self._data_b, self._data_h)

			# Modify some display parameters
			for b, bar in zip(self._data_b, self._bars):
				bar.set_x(b - self._bin_width / 2.0)
				bar.set_width(self._bin_width)
				bar.set_color(self._color)

		# Update
		for b, new_height, bar in zip(self._data_b, self._data_h, self._bars):
			bar.set_height(new_height)

class LinePanel(Panel):

	def __init__(self, axes, source, keys_x, keys_y, xlim=None, ylim=None, xticks=None, yticks=None,
	  color_map=["b", "g", "r", "c", "y", "m", "k"], grid=False, title=None, xlabel=None, ylabel=None, line_labels=None,
	  xconv=None, yconv=None, **kwargs):

		# Generic Panel
		super(LinePanel, self).__init__(axes, source, **kwargs)

		# Set data source keys
		self._keys_x = keys_x
		self._keys_y = keys_y

		# Set some properties
		if xlim is not None:
			self._axes.set_xlim(xlim)
		if ylim is not None:
			self._axes.set_ylim(ylim)
		if xticks is not None:
			self._axes.set_xticks(xticks)
		if yticks is not None:
			self._axes.set_yticks(yticks)
		if grid:
			self._axes.grid()
		if title is not None:
			self._axes.set_title(title)
		if xlabel is not None:
			self._axes.set_xlabel(xlabel)
		if ylabel is not None:
			self._axes.set_ylabel(ylabel)
		if line_labels is not None:
			self._line_labels = line_labels
		if xconv is not None:
			self._xconv = xconv
		if yconv is not None:
			self._yconv = yconv
		self._color_map = color_map

	def update(self):

		# Try to retrieve data
		proxy_x = [self.retrieve_data(k) for k in self._keys_x]
		proxy_y = [self.retrieve_data(k) for k in self._keys_y]

		# Check if None returned
		if any([x is None for x in proxy_x]) or any([y is None for y in proxy_y]):
			self.logger.warn("Missing data for certain attributes, not updating panel")
			return

		# Data received, apply conversion functions
		if hasattr(self, "_xconv"):
			proxy_x = [self._xconv(x) for x in proxy_x]
		if hasattr(self, "_yconv"):
			proxy_y = [self._yconv(y) for y in proxy_y]
		self._datas_x = proxy_x
		self._datas_y = proxy_y
		self._colors = [self._color_map[ii % len(self._color_map)] for ii, _ in enumerate(self._datas_y)]

		# If not plotted yet, initiate
		if not hasattr(self, "_lines"):
			self._lines = [self._axes.plot(x, y, c)[0] for x, y, c in zip(self._datas_x, self._datas_y, self._colors)]

		# If line labels, set them
		if hasattr(self, "_line_labels"):
			for label, line in zip(self._line_labels, self._lines):
				line.set_label(label)
			# If legend not displayed yet, do it
			if not hasattr(self, "_legend"):
				self._legend = self._axes.legend()

		# Update
		for new_x, new_y, line in zip(self._datas_x, self._datas_y, self._lines):
			line.set_xdata(new_x)
			line.set_ydata(new_y)

class TextInfoPanel(Panel):

	def __init__(self, axes, source, r2dbe_host, **kwargs):

		# Generic Panel
		super(TextInfoPanel, self).__init__(axes, source, **kwargs)

		# Set R2DBE hostname
		self._r2dbe_host = r2dbe_host

		# Clear x- and y-ticks
		self._axes.set_xticks([])
		self._axes.set_yticks([])

		# Set x- and y-limits
		self._axes.set_xlim([0, 1])
		self._axes.set_ylim([0, 1])

		# Set geomtry parameters
		xlim = self._axes.get_xlim()
		ylim = self._axes.get_ylim()
		self._left_x = xlim[0]
		self._full_x = xlim[1] - xlim[0]
		self._top_y = ylim[1]
		self._full_y = ylim[1] - ylim[0]

	@property
	def _keys(self):
		keys = []
		# Add VDIF group keys
		for inp in R2DBE_OUTPUTS:
			keys.extend([build_key(R2DBE_MCLASS, self._r2dbe_host, R2DBE_GROUP_VDIF, attr, arg=arg) for attr, arg in [
			  (R2DBE_ATTR_VDIF_STATION, R2DBE_ARG_VDIF_STATION % inp),
			  (R2DBE_ATTR_VDIF_POLARIZATION, R2DBE_ARG_VDIF_POLARIZATION % inp),
			  (R2DBE_ATTR_VDIF_RECEIVER_SIDEBAND, R2DBE_ARG_VDIF_POLARIZATION % inp),
			  (R2DBE_ATTR_VDIF_BDC_SIDEBAND, R2DBE_ARG_VDIF_BDC_SIDEBAND % inp)
			]])
		# Add snap group keys
		for inp in R2DBE_INPUTS:
			keys.extend([build_key(R2DBE_MCLASS, self._r2dbe_host, R2DBE_GROUP_SNAP, attr, arg=arg) for attr, arg in [
			  (R2DBE_ATTR_SNAP_2BIT_THRESHOLD, R2DBE_ARG_SNAP_2BIT_THRESHOLD % inp),
			]])
		# Add Time group keys
		keys.extend([build_key(R2DBE_MCLASS, self._r2dbe_host, R2DBE_GROUP_TIME, attr, arg=None) for attr in [
		  R2DBE_ATTR_TIME_NOW,
		  R2DBE_ATTR_TIME_GPS_PPS_COUNT,
		  R2DBE_ATTR_TIME_GPS_PPS_OFFSET_TIME,
		  R2DBE_ATTR_TIME_GPS_PPS_OFFSET_CYCLE,
		  R2DBE_ATTR_TIME_ALIVE
		]])

		return keys

	@property
	def _names(self):
		# Trim off the mclass and instance, and replace dots with underscores
		names = ["_".join(k.split(".")[2:]).replace(".", "_") for k in self._keys]

		return names

	def _build_name(self, group, attr, arg=None):
		components = [group, attr]
		if arg is not None:
			components.extend([arg])
		return "_".join(components)

	def update(self):
		# Retrieve necessary data
		proxy_values = [self.retrieve_data(k) for k in self._keys]
		if any([v is None for v in proxy_values]):
			self.logger.warn("Missing data for certain attributes, not updating panel")
			return

		values = dict(zip(self._names, proxy_values))

		# Build lines to display
		lines = []
		# Add some spacing
		for ii in range(3):
			lines.append(" ")
		# Display R2DBE hostname
		lines.append("R2DBE host: {0}".format(self._r2dbe_host))
		# Add a break
		lines.append("_________________________________________________")
		# Add some spacing
		for ii in range(2):
			lines.append(" ")
		# Display current time
		time_name = self._build_name(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_NOW)
		time_str = values[time_name]
		lines.append("Current time: {0}".format(time_str))
		# Display external PPS vs internal PPS offset
		pps_clk_off_name = self._build_name(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_GPS_PPS_OFFSET_CYCLE)
		pps_clk_off_str = values[pps_clk_off_name]
		pps_sec_off_name = self._build_name(R2DBE_GROUP_TIME, R2DBE_ATTR_TIME_GPS_PPS_OFFSET_TIME)
		pps_sec_off_str = values[pps_sec_off_name]
		lines.append("External vs internal PPS offset is:")
		lines.append("              {clk} cycles @ FPGA clock rate".format(clk=pps_clk_off_str))
		lines.append("              {sec:.2f} ns".format(sec=pps_sec_off_str / 1e-9))
		# Add some spacing
		for ii in range(2):
			lines.append(" ")
		# Per-input lines
		for inp in R2DBE_INPUTS:
			# Display IF signal parameters and station code
			pol_name = self._build_name(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_POLARIZATION, R2DBE_ARG_VDIF_POLARIZATION % inp)
			pol_str = values[pol_name]
			rx_name = self._build_name(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_RECEIVER_SIDEBAND,
			  R2DBE_ARG_VDIF_RECEIVER_SIDEBAND % inp)
			rx_str = values[rx_name].split("=")[-1]
			bdc_name = self._build_name(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_BDC_SIDEBAND, R2DBE_ARG_VDIF_BDC_SIDEBAND % inp)
			bdc_str = values[bdc_name].split("=")[-1]
			stid_name = self._build_name(R2DBE_GROUP_VDIF, R2DBE_ATTR_VDIF_STATION, R2DBE_ARG_VDIF_STATION % inp)
			stid_str = values[stid_name]
			lines.append("IF{inp}:".format(inp=inp))
			lines.append("----")
			lines.append("Pol={pol}, Rx={rx}, BDC={bdc}, Station={stid}".format(pol=pol_str, rx=rx_str, bdc=bdc_str, stid=stid_str))
			# 2-bit quantization threshold
			th_name = self._build_name(R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_THRESHOLD, R2DBE_ARG_SNAP_2BIT_THRESHOLD % inp)
			th_str = values[th_name]
			lines.append("2-bit threshold = {0}".format(th_str))
			# Add some spacing between channels
			for ii in range(5):
				lines.append(" ")
		# Add some more spacing
		for ii in range(14):
			lines.append(" ")

		if not hasattr(self, "_annotates"):
			self._annotates = []
			dy = 1.0 * self._full_y / len(lines)
			x0 = self._left_x + self._full_x / 20.0
			for ii, line in enumerate(lines):
				y = self._top_y - (ii + 0.5)*dy
				self._annotates.append(self._axes.annotate(line, xy=(x0, y)))
		else:
			for an, line in zip(self._annotates, lines):
				an.set_text(line)

class DisplayR2dbeMonitor(object):

	def __init__(self, r2dbe_host, redis_source, rows=2, cols=4, parent_logger=logging.getLogger(__file__)):

		# Set R2DBE host
		self._r2dbe_host = r2dbe_host

		# Set logger
		self.logger = logging.getLogger("{name}[{host}]".format(name=".".join((parent_logger.name,
		  self.__class__.__name__)), host=self._r2dbe_host))

		# Set redis
		self._redis = redis_source

		# Create figure
		self._fig = figure()

		# Register close handler
		self._fig.canvas.mpl_connect('close_event', handle_close)

		# Adjust subplot parameters
		self._fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95, top=0.95, wspace=None, hspace=None)

		# Set layout
		self._rows = rows
		self._cols = cols

		# Initialize panels
		self._panels = []

	@property
	def next_order(self):
		return len(self._panels) + 1

	def add_panel(self, order, cls, *args, **kwargs):
		# Create axes
		axes = self._fig.add_subplot(self._rows, self._cols, order)

		# Instantiate panel object
		panel = cls(axes, self._redis, parent_logger=self.logger, *args, **kwargs)

		# Add to panel list
		self._panels.append(panel)

		return panel

	def close(self):
		# Allow some last updates
		pause(1)

	def update(self):
		for panel in self._panels:
			panel.update()

def _configure_logging(logfilename=None, verbose=None):
	# Set up root logger
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)

	# Always add logging to stdout
	stdout_handler = logging.StreamHandler(sys.stdout)
	all_handlers = [stdout_handler]
	# And optionally to file
	if logfilename:
		file_handler = logging.FileHandler(logfilename, mode="a")
		all_handlers.append(file_handler)
	# Add handlers
	for handler in all_handlers:
		logger.addHandler(handler)

	# If verbose, set level to DEBUG on file, or stdout if no logging to file
	if verbose:
		# First set DEBUG on root logger
		logger.setLevel(logging.DEBUG)
		# Then revert to INFO on 0th handler (i.e. stdout)
		all_handlers[0].setLevel(logging.INFO)
		# Finally DEBUG again on 1th handler (file if it exists, otherwise stdout again)
		all_handlers[-1].setLevel(logging.DEBUG)

	# Create and set formatters
	formatter = logging.Formatter('%(name)-30s: %(asctime)s : %(levelname)-8s %(message)s')
	for handler in all_handlers:
		handler.setFormatter(formatter)

	# Initial log messages
	logger.info("Started logging in {filename}".format(filename=__file__))
	if logfilename:
		logger.info("Log file is '{log}'".format(log=logfilename))

	# Return root logger
	return logger

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description='Monitor R2DBE status')
	parser.add_argument("-l", "--log-file", dest="log", metavar="FILE", type=str,
	  help="write log messages to FILE in addition to stdout (default is $HOME/log/")
	parser.add_argument("-v", "--verbose", action="store_true", default=False,
	  help="set logging to level DEBUG")
	parser.add_argument("r2dbe_host", metavar="HOST", type=str,
	  help="control the daemon associated with HOST")
	args = parser.parse_args()

	# Configure logging
	_default_log_basename = os.path.extsep.join([os.path.basename(os.path.splitext(__file__)[0]), "log"])
	_default_log = os.path.sep.join([os.path.expanduser("~"), "log",_default_log_basename])
	logfile = _default_log
	if args.log:
		logfile = args.log
	logger = _configure_logging(logfilename=logfile, verbose=args.verbose)

	t0 = datetime.utcnow()
	logger.info("Please be patient while the monitor starts up (takes ~45 seconds)...")

	# Set redis server
	redis = StrictRedis("localhost")

	# Create display instance
	drm = DisplayR2dbeMonitor(args.r2dbe_host, redis)

	# Set pyplot interactive mode
	ion()

	# Add 8-bit state histogram panels
	for ii, inp in enumerate(R2DBE_INPUTS):
		key_b = build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_VALUES,
		  arg=R2DBE_ARG_SNAP_8BIT_VALUES % inp)
		key_h = build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_COUNTS,
		  arg=R2DBE_ARG_SNAP_8BIT_COUNTS % inp)
		title_str = "{attr}:{arg}".format(attr=R2DBE_ATTR_SNAP_8BIT_COUNTS, arg=R2DBE_ARG_SNAP_8BIT_COUNTS % inp)
		drm.add_panel(drm.next_order, HistogramPanel, key_b, key_h, color=_color_map[ii], title=title_str,
		  xlabel="Sample state", ylabel="Fraction", xticks=[-128, -64, 0, 64, 127])

	# Add 8-bit spectral density panel
	keys_x = [build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_FREQUENCY,
	  arg=R2DBE_ARG_SNAP_8BIT_FREQUENCY % inp) for inp in R2DBE_INPUTS]
	keys_y = [build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_8BIT_DENSITY,
	  arg=R2DBE_ARG_SNAP_8BIT_DENSITY % inp) for inp in R2DBE_INPUTS]
	title_str = "{attr}".format(attr=R2DBE_ATTR_SNAP_8BIT_DENSITY)
	drm.add_panel(drm.next_order, LinePanel, keys_x, keys_y, color_map=_color_map, title=title_str,
	  xlabel="Frequency [MHz]", ylabel="Normalized spectral density [dB]",
	  xlim=[0, 2048], xticks=[0, 1024, 2048],
	  xconv=lambda x: x/1e6, yconv=lambda y: 20*log10(abs(y)/max(abs(y))),
	  line_labels=["{arg}".format(arg=R2DBE_ARG_SNAP_8BIT_DENSITY % inp) for inp in R2DBE_INPUTS])

	# Add text information panel
	text_panel = drm.add_panel(drm.next_order, TextInfoPanel, args.r2dbe_host)

	# Add 2-bit state histogram panels
	for ii, inp in enumerate(R2DBE_INPUTS):
		key_b = build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_VALUES,
		  arg=R2DBE_ARG_SNAP_2BIT_VALUES % inp)
		key_h = build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_COUNTS,
		  arg=R2DBE_ARG_SNAP_2BIT_COUNTS % inp)
		title_str = "{attr}:{arg}".format(attr=R2DBE_ATTR_SNAP_2BIT_COUNTS, arg=R2DBE_ARG_SNAP_2BIT_COUNTS % inp)
		drm.add_panel(drm.next_order, HistogramPanel, key_b, key_h, color=_color_map[ii], title=title_str,
		  xlabel="Sample state", ylabel="Fraction", xticks=[-2, -1, 0, 1])

	# 2-bit spectral density panels
	keys_x = [build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_FREQUENCY,
	  arg=R2DBE_ARG_SNAP_2BIT_FREQUENCY % inp) for inp in R2DBE_INPUTS]
	keys_y = [build_key(R2DBE_MCLASS, args.r2dbe_host, R2DBE_GROUP_SNAP, R2DBE_ATTR_SNAP_2BIT_DENSITY,
	  arg=R2DBE_ARG_SNAP_2BIT_DENSITY % inp) for inp in R2DBE_INPUTS]
	title_str = "{attr}".format(attr=R2DBE_ATTR_SNAP_2BIT_DENSITY)
	line_panel = drm.add_panel(drm.next_order, LinePanel, keys_x, keys_y, color_map=_color_map, title=title_str,
	  xlabel="Frequency [MHz]", ylabel="Normalized spectral density [dB]",
	  xlim=[0, 2048], xticks=[0, 1024, 2048],
	  xconv=lambda x: x/1e6, yconv=lambda y: 20*log10(abs(y)/max(abs(y))),
	  line_labels=["{arg}".format(arg=R2DBE_ARG_SNAP_8BIT_DENSITY % inp) for inp in R2DBE_INPUTS])

	# Resize text panel
	new_bottom = line_panel._axes.get_position().p0[1] # <- get_position returns Bbox, p0 is lower left? and p0[1] is y?
	new_position = text_panel._axes.get_position()
	new_position.p0[1] = new_bottom
	text_panel._axes.set_position(new_position)

	t1 = datetime.utcnow()
	logger.info("Startup completed in {0:.3f} seconds".format((t1-t0).total_seconds()))

	while True:
		# Update monitor
		drm.update()
		pause(0.001)

		# Check if stop condition set
		with _stop_lock:

			is_stopped = _stop

		# If stopped, terminate
		if is_stopped:

			logger.info("Stop condition, terminating...")

			drm.close()
			break
