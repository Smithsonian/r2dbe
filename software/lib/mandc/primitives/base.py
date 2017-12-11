import logging

from socket import inet_aton, inet_ntoa
from struct import pack, unpack

from defines import *

module_logger = logging.getLogger(__name__)

class Sideband(object):

	def __init__(self, sideband_spec=None):
		if sideband_spec is None:
			self.sb = None
		elif isinstance(sideband_spec, Sideband):
			self.sb = sideband_spec.sb
		elif str(sideband_spec).upper() in SIDEBAND_LOW_SPEC:
			self.sb = SIDEBAND_LOW
		elif str(sideband_spec).upper() in SIDEBAND_HIGH_SPEC:
			self.sb = SIDEBAND_HIGH
		else:
			raise ValueError(
			  "Invalid sideband specification '{0}'".format(sideband_spec))

	def __repr__(self):
		if self.sb == SIDEBAND_LOW:
			return SIDEBAND_LOW_SPEC[0]
		elif self.sb == SIDEBAND_HIGH:
			return SIDEBAND_HIGH_SPEC[0]
		else:
			return repr(None)

class RxSideband(Sideband):

	def __repr__(self):
		sb_str = super(RxSideband, self).__repr__()
		return "RX={0}".format(sb_str)

class BDCSideband(Sideband):

	def __repr__(self):
		sb_str = super(BDCSideband, self).__repr__()
		return "BDC={0}".format(sb_str)

class Polarization(object):

	def __init__(self, polarization_spec=None):
		if polarization_spec is None:
			self.pol = None
		elif isinstance(polarization_spec, Polarization):
			self.pol = polarization_spec.pol
		elif str(polarization_spec).upper() in POLARIZATION_LEFT_SPEC:
			self.pol = POLARIZATION_LEFT
		elif str(polarization_spec).upper() in POLARIZATION_RIGHT_SPEC:
			self.pol = POLARIZATION_RIGHT
		else:
			raise ValueError(
			  "Invalid polarization specification '{0}'".format(polarization_spec))

	def __repr__(self):
		if self.pol == POLARIZATION_LEFT:
			return POLARIZATION_LEFT_SPEC[0]
		elif self.pol == POLARIZATION_RIGHT:
			return POLARIZATION_RIGHT_SPEC[0]
		else:
			return repr(None)

class IFSignal(object):

	def __init__(self, receiver_sideband=None, blockdownconverter_sideband=None, polarization=None, 
	  parent_logger=module_logger):
		self.rx_sb = RxSideband(receiver_sideband)
		self.bdc_sb = BDCSideband(blockdownconverter_sideband)
		self.pol = Polarization(polarization)
	
	def __repr__(self):
		repr_str = "{name}({rx_sb!r}, {bdc_sb!r}, Pol={pol!r})"
		return repr_str.format(name=self.__class__.__name__, rx_sb=self.rx_sb, bdc_sb=self.bdc_sb, pol=self.pol)

	def __getitem__(self,key):
		if key == "RxSB":
			return self.rx_sb.sb
		elif key == "BDCSB":
			return self.bdc_sb.sb
		elif key == "Pol":
			return self.pol.pol
		else:
			raise KeyError(
			  "Parameter '{0}' undefined for type {1}".format(key, self.__class__.__name__))

class MACAddress(object):

	def __init__(self, mac_int_or_str):
		if type(mac_int_or_str) == int:
			self.address = mac_int_or_str
		elif type(mac_int_or_str) == str:
			self.address = self.__class__.str2int(mac_int_or_str)

	def __repr__(self):
		hex_str = "{0:012x}".format(self.address)
		return ':'.join([''.join(z) for z in zip(hex_str[::2], hex_str[1::2])])

	@classmethod
	def str2int(cls, mac_str):
		"""Convert MAC address from colon- / hypen-separated hexadecimal bytes to int"""
		mac_int = int(mac_str.strip().translate(None, ":").translate(None, "-"), 16)
		return mac_int

class IPAddress(object):

	def __init__(self, ip_int_or_str):
		if type(ip_int_or_str) == int:
			self.address = ip_int_or_str
		elif type(ip_int_or_str) == str:
			self.address = self.__class__.str2int(ip_int_or_str)

	def __repr__(self):
		return inet_ntoa(pack('!I',self.address))

	@classmethod
	def str2int(cls, ip_str):
		"""Convert IP address from dot-decimal notation to int"""
		ip_int = unpack("!I",inet_aton(ip_str.strip()))[0]
		return ip_int

class Port(object):

	def __init__(self, port_int_or_str):
		if type(port_int_or_str) == int:
			self.port = port_int_or_str
		elif type(port_int_or_str) == str:
			self.port = int(port_int_or_str)

	def __repr__(self):
		return "{0:d}".format(self.port)

class EthEntity(object):

	def __init__(self, mac_addr_entity=None, ip_addr_entity=None, port_entity=None, parent_logger=module_logger):
		self.mac = mac_addr_entity
		self.ip = ip_addr_entity
		self.port = port_entity

	def __repr__(self):
		repr_str = "(MAC={mac!r}; socket={ip!r}:{port!r})"
		return repr_str.format(mac=self.mac, ip=self.ip, port=self.port)

	def __getitem__(self, key):
		if key == "IP":
			return self.ip.address
		elif key == "Port":
			return self.port.port
		elif key == "MAC":
			return self.mac.address
		else:
			raise KeyError("Parameter '{0}' undefined for type {1}".format(key, self.__class__.__name__))

class EthRoute(object):

	def __init__(self, source_entity=None, destination_entity=None, parent_logger=module_logger):
		self.src = source_entity
		self.dst = destination_entity
	
	def __repr__(self):
		repr_str = "{name}({src!r} --> {dst!r})"
		return repr_str.format(name=self.__class__.__name__, src=self.src, dst=self.dst)

class ModSubGroup(object):

	def __init__(self, mods):
		self.mods = ''.join([str(m) for m in mods])

	def __repr__(self):
		repr_str = "{name}({grp})"
		return repr_str.format(name=self.__class__.__name__, grp=[", ".format(self.mods)])

class SignalPath(object):

	def __init__(self, if_signal=None, eth_route=None, mod_subgroup=None, parent_logger=module_logger):
		self.ifs = if_signal
		self.ethrt = eth_route
		self.modsg = mod_subgroup

	def __repr__(self):
		repr_str = "{name}({ifs!r} >> {eth!r} >> {mods!r})"
		return repr_str.format(name=self.__class__.__name__, ifs=self.ifs, eth=self.ethrt, mods=self.modsg)
