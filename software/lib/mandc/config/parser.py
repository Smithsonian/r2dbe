import logging

from ConfigParser import RawConfigParser

from r2dbe import R2DBE_INPUTS
from defines import *
from ..primitives import IFSignal, 

module_logger = logging.getLogger(__name__)

class BackendConfig(object):

	def __init__(self, r2dbe, mark6):
		self.r2dbe = r2dbe
		self.mark6 = mark6
		self.logger = logging.getLogger("{name}[r2dbe={r2dbe}, mark6={mark6}]".format(name=".".join((parent_logger.name, 
		  self.__class__.__name__)), r2dbe=self.filename, mark6=self.mark6))

	@classmethod
	def from_dict(cls, options):
		r2dbe = options[BACKEND_OPTION_R2DBE]
		mark6 = options[BACKEND_OPTION_MARK6]
		for input_n in R2DBE_INPUTS:
			self.

class StationConfig(object):

	def __init__(self, station, backends, parent_logger=module_logger):
		self.station = station
		self.backends = backends
		self.logger = logging.getLogger("{name}[file={filename}]".format(name=".".join((parent_logger.name, 
		  self.__class__.__name__)), filename=self.filename,))

	@classmethod
	def from_file(cls, filename):
		rcp = RawConfigParser()
		if len(rcp.read(filename)) < 1:
			module_logger.error("Unable to parse station configuration file '{0}'".format(filename))
			return
		station = rcp.get(GLOBAL_SECTION, GLOBAL_OPTION_STATION)
		backend_list = rcp.get(GLOBAL_SECTION, GLOBAL_OPTION_BACKENDS).split(",")
		backends = {}
		for be in backend_list:
			options = rcp.items(be)
			backends[be] = BackendConfig.from_dict(options)

		return cls(station, backends)

