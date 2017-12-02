from subprocess import Popen, PIPE

def _system_call(cmdstr):
	# Execute the system call in cmdstr
	p = Popen(cmdstr,shell=True,stdout=PIPE,stderr=PIPE)
	stdout,stderr = p.communicate()
	rc = p.returncode
	# Return call return code, stdout, and stderr as 3-tuple
	return (rc,stdout,stderr)

def _remote_system_call(cmdstr,host,user=None):
	# Execute the system call in cmdstr on host with login user
	user_prefix = "%s@"%user if user is not None else ""
	ssh_cmdstr = "ssh %s%s %s"%(user_prefix,host,cmdstr)
	return _system_call(ssh_cmdstr)

def _piped_remote_system_call(lcmdstr,rcmdstr,host,user=None):
	# Pipe output of cmdstr (on local machine) to rcmdstr on host with login user
	user_prefix = "%s@"%user if user is not None else ""
	ssh_cmdstr = "ssh %s%s %s"%(user_prefix,host,rcmdstr)
	full_cmdstr = "%s | %s"%(lcmdstr,ssh_cmdstr)
	return _system_call(full_cmdstr)

def remote_python(codestr,host,user=None):
	# Execute the Python source codestr on host with login user
	tmpfile = "tmp_%x.py"%abs(hash(codestr))
	with open(tmpfile,"w") as fh:
		fh.write(codestr)
	rc,stdout,stderr = _piped_remote_system_call("cat %s"%tmpfile,"python -",host,user)
	_system_call("rm %s"%tmpfile)
	if rc != 0:
		raise RuntimeError("Unable to run Python code on %s, received error %d '%s'"%(host,rc,stderr))
	return stdout.strip()
