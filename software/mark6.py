from subprocess import Popen, PIPE


def mstat(num):
    cmd = 'echo "mstat?{0}" | da-client'.format(num)

    proc     = Popen(cmd, shell=True, stdout = PIPE, stderr = PIPE)
    out, err = proc.communicate()
    lines = out.split('\n')
    
    # line[1] has the output, lets split at :
    vals = lines[1].split(':')
    info = vals[4].split('/')
    return_code = vals[0].split('?')

    module_info = {
    'Return code': vals[0], 
    'Cplane return code': vals[1],
    'Group': vals[2],
    'Slot':  vals[3],
    'eMSN':  vals[4],
    'Disks found': vals[5],
    'Disks registered': vals[6],
    'GB remaining': vals[7],
    'GB total': vals[8],
    'Status 1': vals[9],
    'Status 2': vals[10],
    'Type':     vals[11][:-1]
    }

    return module_info

def get_status():
    for k in range(1,5):
       x = mstat(k)
       print 'Module {0} is {1}, {2}'.format(x['Slot'],x['Status 1'],x['Status 2'])
    return

