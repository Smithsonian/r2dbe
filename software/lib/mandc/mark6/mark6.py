import logging

from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile

from ..primitives.base import IPAddress, MACAddress
from defines import *

module_logger = logging.getLogger(__name__)

def _system_call(cmd):
	p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
	stdout, stderr = p.communicate()
	rc = p.returncode
	module_logger.debug("Call '{0}' returned {1:d}\n<stdout>{2}</stdout><stderr>{3}</stderr>".format(cmd, rc, stdout, 
	  stderr))
	# Return call return code, stdout, and stderr as 3-tuple
	return (rc, stdout, stderr)

class Mark6(object):

	def __init__(self, mark6_host, mark6_user=MARK6_DEFAULT_USER, parent_logger=module_logger):
		self.host = mark6_host
		self.user = mark6_user
		self.logger = logging.getLogger("{name}[host={host!r}]".format(name=".".join((parent_logger.name,
		  self.__class__.__name__)), host=self.host,))
		# connect to Mark6
		if self.host:
			self._connect()

	def _connect(self):
		pass

	def _daclient_call(self, cmd, *args):
		cmd_args = "{cmd}?{param}".format(cmd=cmd, param=":".join([str(arg) for arg in args]))
		echo_cmd = "echo '{cmd}' | da-client".format(cmd=cmd_args)
		rc, stdout, stderr = self._system_call(echo_cmd)
		if rc != 0:
			self.logger.error("da-client call failed, received error code {code} with message '{msg}'".format(code=rc,
			  msg=stderr))
			raise RuntimeError("da-client call failed")
		# Extract response message
		response = stdout
		# Start with "!<cmd>?" section
		response = response[response.find("!{cmd}?".format(cmd=cmd)):]
		# End before next ">>"
		response = response[:response.find(">>")]
		# Trim any whitespace characters
		response = response.strip()

		return response

	def _python_call(self, py_code):
		# Excute Python source in py_code and return stdout
		with NamedTemporaryFile(mode="w+",suffix=".py",delete=True) as tmp_fh:
			tmp_fh.write(py_code)
			tmp_fh.flush()
			py_cmd = "cat {tmp} | ssh {user}@{host} python -".format(tmp=tmp_fh.name, user=self.user, host=self.host)
			rc, stdout, stderr = _system_call(py_cmd)
			if rc != 0:
				self.logger.error("Python call failed, received error code {code} with message '{msg}'".format(code=rc,
				  msg=stderr))
				raise RuntimeError("Python call failed")

			return stdout

	def _system_call(self, cmd):
		ssh_cmd = "ssh {user}@{host} {cmd}".format(user=self.user, host=self.host, cmd=cmd)
		return _system_call(ssh_cmd)

	def get_iface_mac_ip(self, iface):
		rstr = self._python_call(""
		  "from netifaces import ifaddresses\n"
		  "iface=ifaddresses('{iface}')\n"
		  "print iface[17][0]['addr'], ',', iface[2][0]['addr']".format(iface=iface))
		mac_str, ip_str = rstr.split(",")
		return MACAddress(mac_str), IPAddress(ip_str)

	def get_module_status(self, mod_n):
		return self._daclient_call("mstat", str(mod_n))

	def setup(self):
		pass

