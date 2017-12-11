from ConfigParser import RawConfigParser

from defines import *
from remote import remote_python

PYTHON_IP_ADDRESS = \
"from netifaces import ifaddresses\n\
iface=ifaddresses('%s')\n\
print iface[2][0]['addr']"

PYTHON_MAC_ADDRESS = \
"from netifaces import ifaddresses\n\
iface=ifaddresses('%s')\n\
print iface[17][0]['addr']"

PYTHON_MACIP_ADDRESS = \
"from netifaces import ifaddresses\n\
iface=ifaddresses('%s')\n\
print iface[17][0]['addr'], ',', iface[2][0]['addr']"


def get_iface_macip_str(iface,host,user=None):
	mac_str,ip_str = remote_python(PYTHON_MACIP_ADDRESS%iface,host,user=user).split(',')
	return mac_str.strip(), ip_str.strip()

class SignalPath(object):

	def __init__(self,name,stn,pol="0",rx="0",bdc="0",iface="eth3",mods="12"):
		self.name = name
		self.station = stn
		self.pol = pol
		self.rec_sideband = rx
		self.bdc_sideband = bdc
		self.iface = iface
		self.modules = mods

	@classmethod
	def from_config_backend_option_if(cls,name,stn,lst):
		return cls(name,stn,**dict(zip(CONFIG_BACKEND_INPUT_ORDER,lst)))

	def set_iface_macip(self,host,user=None):
		mac,ip = get_iface_macip_str(self.iface,host,user=user)
		self.mac = mac
		self.ip = ip

	def to_config(self,rcp_init=None):
		rcp = rcp_init
		if rcp is None:
			rcp = RawConfigParser()
		sec = self.name
		rcp.add_section(sec)
		rcp.set(sec,'station_id',self.station)
		rcp.set(sec,'pol',self.pol)
		rcp.set(sec,'rec_sideband',self.rec_sideband)
		rcp.set(sec,'bdc_sideband',self.bdc_sideband)
		if hasattr(self,'mac') and hasattr(self,'ip'):
			rcp.set(sec,'iface','%s,%s'%(self.mac,self.ip))
		else:
			rcp.set(sec,'iface',self.iface)
		rcp.set(sec,'modules',self.modules)
		return rcp

class Backend(object):

	def __init__(self,name,station,r2dbe,mark6,if0,if1):
		self.name = name
		self.station = station
		self.r2dbe = r2dbe
		self.mark6 = mark6
		self.if0 = SignalPath.from_config_backend_option_if('if0',
		   station,if0.split(','))
		self.if0.set_iface_macip(self.mark6)
		self.if1 = SignalPath.from_config_backend_option_if('if1',
		  station,if1.split(','))
		self.if1.set_iface_macip(self.mark6)

	@classmethod
	def from_config_backend_section(cls,sec,stn,opts):
		return cls(sec,stn,opts['r2dbe'],opts['mark6'],
		  opts['if0'],opts['if1'])

	def to_config(self,rcp_init=None):
		rcp = rcp_init
		if rcp is None:
			rcp = RawConfigParser()
		for sp in ('if0','if1'):
			if hasattr(self,sp):
				rcp = getattr(self,sp).to_config(rcp_init=rcp)
		return rcp

	def to_file(self,filename=None):
		if filename is None:
			filename = "%s.conf"%self.name
		rcp = self.to_config()
		with open(filename,"w") as fh:
			fh.write("# Configuration file for %s backend %s\n"%(self.station,self.name))
			fh.write("# R2DBE: %s\n"%self.r2dbe)
			fh.write("# Mark6: %s\n"%self.mark6)
			rcp.write(fh)

class Station(object):

	def __init__(self,name,backends):
		self.name = name
		self.backends = backends

	@classmethod
	def from_config_file(cls,filename):
		rcp = RawConfigParser()
		if len(rcp.read(filename)) < 1:
			raise RuntimeError("Unable to read station configuration from file '%s'"%filename)
		name = rcp.get(CONFIG_SECTION_GLOBAL,CONFIG_GLOBAL_OPTION_STATION)
		backend_list = rcp.get(CONFIG_SECTION_GLOBAL,CONFIG_GLOBAL_OPTION_BACKENDS).split(',')
		backends = {}
		for be in backend_list:
			opts = dict(rcp.items(be))
			backends[be] = Backend.from_config_backend_section(be,name,opts)
		return cls(name,backends)
