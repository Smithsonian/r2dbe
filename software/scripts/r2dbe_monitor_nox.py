#!/usr/bin/env python
import curses
import datetime
from numpy import arange, array, histogram
import re
import socket
from struct import pack
import subprocess
import sys
import telnetlib
import time

import corr
import r2dbe_snaps
from alc import get_th_16_84

# control key mappings
KEY_BACK=chr(27) # Esc key
KEY_ALC='a'
KEY_HELP='h'
KEY_TOGGLE_POWER='p'
KEY_QUIT='q'
KEY_SENSORS='s'
KEY_MAIN='m'

# state machine states
STATE_MAIN=0
STATE_HELP=1
STATE_SENSORS=2
STATE_NONE=-1

# status flags
MESSAGE_ACTIVE = 0
USE_COLOR = False

# threshold triggers
TH_LOLO = 20
TH_LO = 27
TH_HI = 33
TH_HIHI = 40
BIN_COUNT_IDEAL_8BIT = array([0,13,214,1359,3413,3413,1359,214,13,0])

# color pair indecies
COLOR_INDEX_DEFAULT = 1
COLOR_INDEX_TH_LOLO = 2
COLOR_INDEX_TH_LO = 3
COLOR_INDEX_TH_GOOD = 4
COLOR_INDEX_TH_HI = 5
COLOR_INDEX_TH_HIHI = 6
COLOR_INDEX_ERROR = 7
COLOR_INDEX_GOOD = 8

# sensors
SENSORS_TEMP = ['ambient','ppc','fpga','inlet','outlet']
SENSORS_FAN = ['chs1','chs2','fpga','chs0']
SENSORS_VOLTAGE = ['1v','1v5','1v8','2v5','3v3','5v','12v','3v3aux','5vaux']
SENSORS_CURRENT = ['3v3','2v5','1v8','1v5','1v','5v','12v']

# symbols
DEGREE = ''

# debugging
DEBUG_LINE = 42

class UTC(datetime.tzinfo):
    """ UTC tzinfo """
    
    def utcoffset(self, dt):
        return timedelta(0)
    
    def tzname(self, dt):
        return "UTC"
    
    def dst(self, dt):
        return datetime.timedelta(0)
    
def r2dbe_datetime(roach2,gps_cnt):
    
    # now how many usecs per frame
    usecs_per_frame = 8
    
    # get ref epoch and data_frame
    secs_since_ep = roach2.read_int('r2dbe_vdif_0_hdr_w0_sec_ref_ep')    
    ref_epoch     = roach2.read_int('r2dbe_vdif_0_hdr_w1_ref_ep')    
    
    # get the date
    date = datetime.datetime(year = 2000 + ref_epoch/2,
                    month = 1 + (ref_epoch & 1) * 6,
                    day = 1, tzinfo=UTC())
    
    # get the seconds from the start of the day
    secs = datetime.timedelta(seconds=secs_since_ep+gps_cnt)
    
    return date + secs

def get_sensors_states(sensors,host,port=7147,timeout_connect=10,timeout_read=10):
    """Interrogate ROACH2 via Telnet to get sensor value
    
    Parameters
    ----------
    sensors : list
        List of sensors to read.
    host : str
        ROACH2 hostname or IP address.
    port : int
        Port to use for Telnet connection (default is 7147).
    
    Return
    ------
    state : list
        List of sensor states, see parse_sensor_state for details.
    """
    tnc = telnetlib.Telnet(host,port,timeout=timeout_connect)
    tnc.write("?sensor-value\n")
    telnet_response = tnc.read_until("!sensor-value ok",timeout=timeout_read)
    states = []
    for s in sensors:
        parsed_state = parse_sensor_state(telnet_response,s)
        if parsed_state is not None:
            states.append(parse_sensor_state(telnet_response,s))
    return states

def parse_sensor_state(telnet_response,sensor):
    """Parse telnet response to determine sensor state
    
    Parameters
    ----------
    telnet_response : str
        String data read from Telnet after issuing ?sensor-value. See
        get_sensors_states for more details.
    sensor : str
        Name of sensor.
    
    Return
    ------
    state : dict or None
        If successful, state is a dictionary that contains sensor name 
        ['name'], sensor condition ['condition'], value ['value'], and 
        measurement ['unit']. The name is the same name received in the 
        parameter list, condition is 'normal', 'error', or some other 
        qualitative description of the measurement value, value is the 
        measured value, and units is the unit of measurement for the 
        given value. If the given telnet_response does not contain a 
        valid sensor-value response for requested sensor, then state is 
        None.
    """
    units = {'current':'A','temp':'C','voltage':'V','fan':'RPM'}
    repat = "#sensor-value.*{0}[\s]*[\S]*[\s]*[\d]*".format(sensor)
    lines = re.findall(repat,telnet_response)
    if len(lines) == 0:
        return None
    split_line = lines[-1].split()
    if len(split_line) < 6:
        return None
    #~ print split_line
    n = split_line[-3]
    c = split_line[-2]
    v = split_line[-1]
    #~ n,c,v = lines[-1].split()[-3:]
    v = float(v)/1000.0
    t = n.split('.')[1]
    u = units[t]
    return {'name':n,'condition':c,'value':v,'unit':u}

def display_summary(scr,roach2,debug=False):
    """Gather basic R2DBE information"""
    # general
    is_conn = roach2.is_connected()
    str_conn = ('   ' if is_conn else 'not') + ' connected'
    host = roach2.host.rjust(7)[:7]
    ip = socket.gethostbyname(roach2.host).rjust(15)[:15]
    if debug:
        scr.addstr(DEBUG_LINE,0,'120')
        scr.refresh()
    #timestamp = datetime.datetime.now().strftime('%a %d %b %Y %Hh%Mm%S')
    # clock
    #~ clk = roach2.est_brd_clk()
    gps_cnt = roach2.read_uint('r2dbe_onepps_gps_pps_cnt')
    msr_cnt = roach2.read_uint('r2dbe_onepps_msr_pps_cnt')
    offset_samp = roach2.read_int('r2dbe_onepps_offset')
    #~ offset_ns   = float(offset_samp)/clk*1e3
    timestamp = r2dbe_datetime(roach2,gps_cnt).strftime('%d %b %Y %H:%M:%S %Z')
    if debug:
        scr.addstr(DEBUG_LINE,0,'130')
        scr.refresh()
    # station_id
    st0num  = roach2.read_uint('r2dbe_vdif_0_hdr_w3_station_id')
    st1num  = roach2.read_uint('r2dbe_vdif_1_hdr_w3_station_id')
    st0     = ''.join([chr((st0num>>8) & 0xff), chr(st0num & 0xff)])
    st1     = ''.join([chr((st1num>>8) & 0xff), chr(st1num & 0xff)])
    # polarization
    pol_chr = ['L/X', 'R/Y']
    bdc_sb_chr = ['LSB', 'USB']
    rec_sb_chr = ['LSB', 'USB']
    sb_sb_pol_0 = roach2.read_uint('r2dbe_vdif_0_hdr_w4')
    sb_sb_pol_1 = roach2.read_uint('r2dbe_vdif_1_hdr_w4')
    pol0 = pol_chr[sb_sb_pol_0 & 0x1]
    pol1 = pol_chr[sb_sb_pol_1 & 0x1]
    bdc0 = bdc_sb_chr[sb_sb_pol_0>>1 & 0x1]
    bdc1 = bdc_sb_chr[sb_sb_pol_1>>1 & 0x1]
    rec0 = bdc_sb_chr[sb_sb_pol_0>>2 & 0x1]
    rec1 = bdc_sb_chr[sb_sb_pol_1>>2 & 0x1]
    # networking
    if debug:
        scr.addstr(DEBUG_LINE,0,'150')
        scr.refresh()
    dip0 = socket.inet_ntoa(pack('!i',roach2.read_int('r2dbe_tengbe_0_dest_ip'))).rjust(15)[:15]
    dip1 = socket.inet_ntoa(pack('!i',roach2.read_int('r2dbe_tengbe_1_dest_ip'))).rjust(15)[:15]
    dpr0 = str(roach2.read_int('r2dbe_tengbe_0_dest_port')).ljust(5)
    dpr1 = str(roach2.read_int('r2dbe_tengbe_1_dest_port')).ljust(5)
    ncfg0 = roach2.get_10gbe_core_details('r2dbe_tengbe_0_core')
    ncfg1 = roach2.get_10gbe_core_details('r2dbe_tengbe_1_core')
    sip0 = socket.inet_ntoa(pack('!I',ncfg0['my_ip'])).rjust(15)[:15]
    sip1 = socket.inet_ntoa(pack('!I',ncfg1['my_ip'])).rjust(15)[:15]
    spr0 = ncfg0['fabric_port']
    spr1 = ncfg1['fabric_port']
    net_str_0 = "{0}:{1} -> {2}:{3}".format(sip0,spr0,dip0,dpr0)
    net_str_1 = "{0}:{1} -> {2}:{3}".format(sip1,spr1,dip1,dpr1)
    # print to screen
    # top line
    scr.addstr(1,2,'{0}'.format(timestamp))
    scr.addstr(1,35,'{0}'.format(host))
    scr.addstr(1,48,'{0}'.format(ip))
    if is_conn:
        scr.addstr(1,65,'{0}'.format(str_conn))
    else:
        scr.addstr(1,65,'{0}'.format(str_conn),curses.A_STANDOUT)
    if debug:
        scr.addstr(DEBUG_LINE,0,'173')
        scr.refresh()
    # channel table
    scr.addstr(6,9,'{0}'.format(st0))
    scr.addstr(7,9,'{0}'.format(st1))
    scr.addstr(6,14,'{0}'.format(pol0))
    scr.addstr(7,14,'{0}'.format(pol1))
    scr.addstr(6,20,'{0}'.format(bdc0))
    scr.addstr(7,20,'{0}'.format(bdc1))
    scr.addstr(6,26,'{0}'.format(rec0))
    scr.addstr(7,26,'{0}'.format(rec1))
    scr.addstr(6,32,'{0}'.format(net_str_0))
    scr.addstr(7,32,'{0}'.format(net_str_1))

def display_power(scr,roach2,debug=False):
    # get snapshots of 8bit and 2bit data
    try:
        x=corr.snap.snapshots_get(
            [roach2,roach2,roach2,roach2],
            ['r2dbe_snap_8bit_0_data',
            'r2dbe_snap_8bit_1_data',
            'r2dbe_snap_2bit_0_data',
            'r2dbe_snap_2bit_1_data']
        )
    except RuntimeError:
        display_message(scr,"Getting snapshot data failed",curses.color_pair(COLOR_INDEX_ERROR))
        return None
    L = x['lengths'][0]
    x0_8 = r2dbe_snaps.data_from_snap_8bit(x['data'][0],L) 
    x1_8 = r2dbe_snaps.data_from_snap_8bit(x['data'][1],L)
    x0_2 = r2dbe_snaps.data_from_snap_2bit(x['data'][2],L) 
    x1_2 = r2dbe_snaps.data_from_snap_2bit(x['data'][3],L)
    if debug:
        scr.addstr(30,0,'201')
        scr.refresh()
    # build histograms
    bins8 = arange(-128,128.01,128/5.0)
    h0_8 = 1.0*histogram(x0_8, bins=bins8, normed=False)[0]/x0_8.size*10000
    h1_8 = 1.0*histogram(x1_8, bins=bins8, normed=False)[0]/x1_8.size*10000
    bins2 = arange(-2,2.01,1)
    h0_2 = 1.0*histogram(x0_2, bins=bins2, normed=False)[0]/x0_2.size*100
    h1_2 = 1.0*histogram(x1_2, bins=bins2, normed=False)[0]/x1_2.size*100
    # recompute threshold to see if data should be flagged
    th0_expected = get_th_16_84(x0_8)
    th1_expected = get_th_16_84(x1_8)
    b0_color = curses.A_BOLD#curses.color_pair(COLOR_INDEX_DEFAULT)
    b1_color = curses.A_BOLD#curses.color_pair(COLOR_INDEX_DEFAULT)
    if USE_COLOR:
        if th0_expected < TH_LOLO:
            b0_color = curses.color_pair(COLOR_INDEX_TH_LOLO)
        elif th0_expected < TH_LO:
            b0_color = curses.color_pair(COLOR_INDEX_TH_LO)
        elif th0_expected < TH_HI:
            b0_color = curses.color_pair(COLOR_INDEX_TH_GOOD)
        elif th0_expected < TH_HIHI:
            b0_color = curses.color_pair(COLOR_INDEX_TH_HI)
        else:
            b0_color = curses.color_pair(COLOR_INDEX_TH_HIHI)
        if th1_expected < TH_LOLO:
            b1_color = curses.color_pair(COLOR_INDEX_TH_LOLO)
        elif th1_expected < TH_LO:
            b1_color = curses.color_pair(COLOR_INDEX_TH_LO)
        elif th1_expected < TH_HI:
            b1_color = curses.color_pair(COLOR_INDEX_TH_GOOD)
        elif th1_expected < TH_HIHI:
            b1_color = curses.color_pair(COLOR_INDEX_TH_HI)
        else:
            b1_color = curses.color_pair(COLOR_INDEX_TH_HIHI)
    # read threshold values
    th0 = roach2.read_int('r2dbe_quantize_0_thresh')
    th1 = roach2.read_int('r2dbe_quantize_1_thresh')
    th0_color = curses.A_BOLD#curses.color_pair(COLOR_INDEX_DEFAULT)
    th1_color = curses.A_BOLD#curses.color_pair(COLOR_INDEX_DEFAULT)
    if USE_COLOR:
        if th0 < TH_LOLO:
            th0_color = curses.color_pair(COLOR_INDEX_TH_LOLO)
        elif th0 < TH_LO:
            th0_color = curses.color_pair(COLOR_INDEX_TH_LO)
        elif th0 < TH_HI:
            th0_color = curses.color_pair(COLOR_INDEX_TH_GOOD)
        elif th0 < TH_HIHI:
            th0_color = curses.color_pair(COLOR_INDEX_TH_HI)
        else:
            th0_color = curses.color_pair(COLOR_INDEX_TH_HIHI)
        if th1 < TH_LOLO:
            th1_color = curses.color_pair(COLOR_INDEX_TH_LOLO)
        elif th1 < TH_LO:
            th1_color = curses.color_pair(COLOR_INDEX_TH_LO)
        elif th1 < TH_HI:
            th1_color = curses.color_pair(COLOR_INDEX_TH_GOOD)
        elif th1 < TH_HIHI:
            th1_color = curses.color_pair(COLOR_INDEX_TH_HI)
        else:
            th1_color = curses.color_pair(COLOR_INDEX_TH_HIHI)
    # print to screen
    scr.addstr(13,3,'0')
    scr.addstr(14,3,'1')
    scr.addstr(13,5,'{0:3d}'.format(th0),th0_color | curses.A_BOLD)
    scr.addstr(14,5,'{0:3d}'.format(th1),th1_color | curses.A_BOLD)
    for ib in arange(10):
        scr.addstr(13,10+ib*7,"{0:5d}".format(int(round(h0_8[ib]))),b0_color)
        scr.addstr(14,10+ib*7,"{0:5d}".format(int(round(h1_8[ib]))),b1_color)
    scr.addstr(21,5,'0')
    scr.addstr(22,5,'1')
    for ib in arange(4):
        scr.addstr(21,9+ib*9,"{0:6.2f}".format(h0_2[ib]))
        scr.addstr(22,9+ib*9,"{0:6.2f}".format(h1_2[ib]))
    # show legend
    scr.addstr(19,45,'Legend (th):')
    if USE_COLOR:
        scr.addstr(19,58,'LOW power    (  -{0:02d})'.format(TH_LOLO-1),curses.color_pair(COLOR_INDEX_TH_LOLO))
        scr.addstr(20,58,'low power    ({0:02d}-{1:02d})'.format(TH_LOLO,TH_LO-1),curses.color_pair(COLOR_INDEX_TH_LO))
        scr.addstr(21,58,'okay power   ({0:02d}-{1:02d})'.format(TH_LO,TH_HI-1),curses.color_pair(COLOR_INDEX_TH_GOOD))
        scr.addstr(22,58,'high power   ({0:02d}-{1:02d})'.format(TH_HI,TH_HIHI-1),curses.color_pair(COLOR_INDEX_TH_HI))
        scr.addstr(23,58,'HIGH power   ({0:02d}-  )'.format(TH_HIHI),curses.color_pair(COLOR_INDEX_TH_HIHI))

def run_alc(scr,roach2):
    display_message(scr,'Running alc.py...')
    alc_args = [sys.executable, 'alc.py']
    alc_args.append(roach2.host)
    try:
        subprocess.check_call(alc_args)
        display_message(scr,'Running alc.py...done.')
    except CalledProcessError:
        display_message(scr,'Running alc.py failed!',opt=curses.A_STANDOUT)

def display_message(scr,msg,opt=None):
    global MESSAGE_ACTIVE
    MESSAGE_ACTIVE = 1
    if opt is None:
        scr.addstr(26,12,msg.ljust(65)[:65])
    else:
        scr.addstr(26,12,msg.ljust(65)[:65],opt)
    scr.refresh()

def clear_message(scr):
    global MESSAGE_ACTIVE
    if MESSAGE_ACTIVE > 0:
        MESSAGE_ACTIVE = MESSAGE_ACTIVE - 1
        scr.addstr(26,76," ")
    else:
        scr.addstr(26,12," ".ljust(65)[:65])

def toggle_power(scr,do_power):
    if not do_power:
        scr.addstr(9,16,"                                         ")
    else:
        scr.addstr(9,16,"not updating (press 'p' to toggle update)",curses.A_STANDOUT | curses.A_BLINK)
    return not do_power

def get_key_line():
    #~ key_line = "|Press '{0}' to quit, '{1}' to run ALC, '{2}' to toggle power info ".format(
        #~ KEY_QUIT,KEY_ALC,KEY_TOGGLE_POWER
    #~ ).ljust(79) + "|"
    key_line = "| Press '{0}' for help".format(
        KEY_HELP
    ).ljust(79) + "|"
    return key_line

def display_help(scr):
    key_line = get_key_line()
    help_dict = {
        'Esc':'Go back',
        KEY_MAIN:'Main page',
        KEY_ALC:'Run alc.py (main page only)',
        KEY_HELP:'Display this page',
        KEY_TOGGLE_POWER:'Toggle hist (main page only)',
        KEY_QUIT:'Quit monitor',
        KEY_SENSORS:'Sensor data page'
    }
    scr.addstr( 0,0,"|------------------------------------------------------------------------------|")
    scr.addstr( 1,0,"|                              R2DBE Monitor Help                              |")
    scr.addstr( 2,0,"|------------------------------------------------------------------------------|")
    scr.addstr( 3,0,"| Commands:                                                                    |")
    scr.addstr( 4,0,"| =========                                                                    |")
    for ii in xrange(5,24):
        scr.addstr(ii,0,"|                                                                              |")
    il = 5
    jl = 0
    for k in sorted(help_dict.keys()):
        key_help = "{0} - {1}".format(k.rjust(3),help_dict[k])
        scr.addstr(il,4+40*jl,key_help)
        jl = (jl + 1) % 2
        if jl == 0:
            il = il + 1
    scr.addstr(24,0,"|------------------------------------------------------------------------------|")
    scr.addstr(25,0,key_line)
    scr.addstr(26,0,"| Messages:                                                                    |")
    scr.addstr(27,0,"|------------------------------------------------------------------------------|")

def compile_sensors_list(scr,temp=[],fan=[],voltage=[],current=[]):
    sensors = {'temp':[],'fan':[],'voltage':[],'current':[]}
    if len(temp) > 0:
        sensor_list = []
        for t in temp:
            sensor_list.append('raw.temp.{0}'.format(t))
        states = get_sensors_states(sensor_list,roach2.host)
        #~ ii = 0
        for state in states:
            #~ scr.addstr(DEBUG_LINE+ii,0,"{0}".format(str(state['name'].split('.')[-1])))
            #~ ii = ii +1
            sensors['temp'].append({
                'name':state['name'].split('.')[-1],
                'value':state['value'],
                'unit':'{0}{1}'.format(DEGREE,state['unit']),
                'cond':state['condition']})
    if len(fan) > 0:
        sensor_list = []
        for f in fan:
            sensor_list.append('raw.fan.{0}'.format(f))
        states = get_sensors_states(sensor_list,roach2.host)
        for state in states:
            sensors['fan'].append({
                'name':state['name'].split('.')[-1],
                'value':state['value'],
                'unit':'{0}'.format(state['unit']),
                'cond':state['condition']})
    if len(voltage) > 0:
        sensor_list = []
        for v in voltage:
            sensor_list.append('raw.voltage.{0}'.format(v))
        #~ try:
        states = get_sensors_states(sensor_list,roach2.host)
        #~ except ValueError as ex:
            #~ scr.addstr(DEBUG_LINE,0,'{0}'.format(ex))
        #~ ii = 0
        for state in states:
            #~ scr.addstr(DEBUG_LINE+ii,0,"{0}".format(str(state['name'].split('.')[-1])))
            #~ ii = ii +1
            sensors['voltage'].append({
                'name':state['name'].split('.')[-1],
                'value':state['value'],
                'unit':'{0}'.format(state['unit']),
                'cond':state['condition']})
    if len(current) > 0:
        sensor_list = []
        for c in  current:
            sensor_list.append('raw.current.{0}'.format(c))
        states = get_sensors_states(sensor_list,roach2.host)
        for state in states:
            sensors['current'].append({
                'name':state['name'].split('.')[-1],
                'value':state['value'],
                'unit':'{0}'.format(state['unit']),
                'cond':state['condition']})
    return sensors

def display_sensors(scr):
    key_line = get_key_line()
    scr.addstr( 0,0,"|------------------------------------------------------------------------------|")
    scr.addstr( 1,0,"|                          | host:             (               )               |")
    scr.addstr( 2,0,"|------------------------------------------------------------------------------|")
    # general
    is_conn = roach2.is_connected()
    str_conn = ('   ' if is_conn else 'not') + ' connected'
    host = roach2.host.rjust(7)[:7]
    ip = socket.gethostbyname(roach2.host).rjust(15)[:15]
    #timestamp = datetime.datetime.now().strftime('%a %d %b %Y %Hh%Mm%S')
    # clock
    #~ clk = roach2.est_brd_clk()
    gps_cnt = roach2.read_uint('r2dbe_onepps_gps_pps_cnt')
    msr_cnt = roach2.read_uint('r2dbe_onepps_msr_pps_cnt')
    offset_samp = roach2.read_int('r2dbe_onepps_offset')
    #~ offset_ns   = float(offset_samp)/clk*1e3
    timestamp = r2dbe_datetime(roach2,gps_cnt).strftime('%d %b %Y %H:%M:%S %Z')
    # get sensors values
    sensors = compile_sensors_list(scr,temp=SENSORS_TEMP,fan=SENSORS_FAN,voltage=SENSORS_VOLTAGE,current=SENSORS_CURRENT)
    # top line
    scr.addstr(1,2,'{0}'.format(timestamp))
    scr.addstr(1,35,'{0}'.format(host))
    scr.addstr(1,48,'{0}'.format(ip))
    if is_conn:
        scr.addstr(1,65,'{0}'.format(str_conn))
    else:
        scr.addstr(1,65,'{0}'.format(str_conn),curses.A_STANDOUT)
    scr.addstr( 3,0,"| Sensor status:                                                               |")
    scr.addstr( 4,0,"| ==============                                                               |")
    scr.addstr( 5,0,"|   Temperature:                                                               |")
    scr.addstr( 6,0,"|                                                                              |")
    scr.addstr( 7,0,"|                                                                              |")
    scr.addstr( 8,0,"|                                                                              |")
    scr.addstr( 9,0,"|           Fan:                                                               |")
    scr.addstr(10,0,"|                                                                              |")
    scr.addstr(11,0,"|                                                                              |")
    scr.addstr(12,0,"|       Voltage:                                                               |")
    scr.addstr(13,0,"|                                                                              |")
    scr.addstr(14,0,"|                                                                              |")
    scr.addstr(15,0,"|                                                                              |")
    scr.addstr(16,0,"|                                                                              |")
    scr.addstr(17,0,"|                                                                              |")
    scr.addstr(18,0,"|       Current:                                                               |")
    scr.addstr(19,0,"|                                                                              |")
    scr.addstr(20,0,"|                                                                              |")
    scr.addstr(21,0,"|                                                                              |")
    scr.addstr(22,0,"|                                                                              |")
    scr.addstr(23,0,"|                                                                              |")
    scr.addstr(24,0,"|------------------------------------------------------------------------------|")
    scr.addstr(25,0,key_line)
    scr.addstr(26,0,"| Messages:                                                                    |")
    scr.addstr(27,0,"|------------------------------------------------------------------------------|")
    row = 5
    col = 0
    for itemp in sensors['temp']:
        if not USE_COLOR:
            sensor_color = curses.A_BOLD
        elif not itemp['cond'] == 'nominal':
            sensor_color = curses.color_pair(COLOR_INDEX_ERROR)
        else:
            sensor_color = curses.color_pair(COLOR_INDEX_GOOD)
        scr.addstr(row,18+col*25,"{0:9s} = ".format(itemp['name']))
        scr.addstr(row,18+col*25+12,"{0:5.1f}{1}".format(itemp['value'],itemp['unit']),sensor_color)
        col = (col + 1) % 2
        if col == 0:
            row = row+1
    row = 9
    col = 0
    for ifan in sensors['fan']:
        if not USE_COLOR:
            sensor_color = curses.A_BOLD
        elif not ifan['cond'] == 'nominal':
            sensor_color = curses.color_pair(COLOR_INDEX_ERROR)
        else:
            sensor_color = curses.color_pair(COLOR_INDEX_GOOD)
        scr.addstr(row,18+col*25,"{0:9s} = ".format(ifan['name']))
        scr.addstr(row,18+col*25+12,"{0:5d}{1}".format(int(ifan['value']*1000),ifan['unit']),sensor_color)
        col = (col + 1) % 2
        if col == 0:
            row = row+1
    row = 12
    col = 0
    for ivoltage in sensors['voltage']:
        if not USE_COLOR:
            sensor_color = curses.A_BOLD
        elif not ivoltage['cond'] == 'nominal':
            sensor_color = curses.color_pair(COLOR_INDEX_ERROR)
        else:
            sensor_color = curses.color_pair(COLOR_INDEX_GOOD)
        scr.addstr(row,18+col*25,"{0:9s} = ".format(ivoltage['name']))
        scr.addstr(row,18+col*25+12,"{0:5.1f}{1}".format(ivoltage['value'],ivoltage['unit']),sensor_color)
        col = (col + 1) % 2
        if col == 0:
            row = row+1
    row = 18
    col = 0
    for icurrent in sensors['current']:
        if not USE_COLOR:
            sensor_color = curses.A_BOLD
        elif not icurrent['cond'] == 'nominal':
            sensor_color = curses.color_pair(COLOR_INDEX_ERROR)
        else:
            sensor_color = curses.color_pair(COLOR_INDEX_GOOD)
        scr.addstr(row,18+col*25,"{0:9s} = ".format(icurrent['name']))
        scr.addstr(row,18+col*25+12,"{0:5.1f}{1}".format(icurrent['value'],icurrent['unit']),sensor_color)
        col = (col + 1) % 2
        if col == 0:
            row = row+1
    

def display_blank(scr):
    key_line = get_key_line()
    scr.addstr( 0,0,"|------------------------------------------------------------------------------|")
    scr.addstr( 1,0,"|                          | host:             (               )               |")
    scr.addstr( 2,0,"|------------------------------------------------------------------------------|")
    scr.addstr( 3,0,"| VDIF / Network configuration:                                                |")
    scr.addstr( 4,0,"| =============================                                                |")
    scr.addstr( 5,0,"| Ch | StID | Pol | BDC |  Rx | Network                                        |")
    scr.addstr( 6,0,"|  0 |      |     |     |     |                                                |")
    scr.addstr( 7,0,"|  1 |      |     |     |     |                                                |")
    scr.addstr( 8,0,"|------------------------------------------------------------------------------|")
    scr.addstr( 9,0,"| Power levels:                                                                |")
    scr.addstr(10,0,"| =============                                                                |")
    scr.addstr(11,0,"|        | <<<<<<<<<<<<<<<< 8-bit histogram [#/bin/10'000 Sa] >>>>>>>>>>>>>>>> |")
    scr.addstr(12,0,"| Ch| th |   b0 |   b1 |   b2 |   b3 |   b4 |   b5 |   b6 |   b7 |   b8 |   b9 |")
    scr.addstr(13,0,"|   |    |      |      |      |      |      |      |      |      |      |      |")
    scr.addstr(14,0,"|   |    |      |      |      |      |      |      |      |      |      |      |")
    scr.addstr(15,0,"| Ideal  | {0:4d} | {1:4d} | {2:4d} | {3:4d} | {4:4d} | {5:4d} | {6:4d} | {7:4d} | {8:4d} | {9:4d} |".format(*BIN_COUNT_IDEAL_8BIT))
    scr.addstr(16,0,"| Hi edge| -103 |  -77 |  -52 |  -26 |   -1 |   25 |   51 |   76 |  102 |  127 |")
    scr.addstr(17,0,"| Lo edge| -128 | -102 |  -76 |  -51 |  -25 |    0 |   26 |   52 |   77 |  103 |")
    scr.addstr(18,0,"| ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|")
    scr.addstr(19,0,"|      | <<< 2-bit histogram [%Sa/bin] >>> | Legend (th): LOW power   (  -19)  |")
    scr.addstr(20,0,"|   Ch |     00 |     01 |     10 |     11 |              low power   (20-26)  |")
    scr.addstr(21,0,"|      |        |        |        |        |              okay        (27-33)  |")
    scr.addstr(22,0,"|      |        |        |        |        |              high power  (34-39)  |")
    scr.addstr(23,0,"| Ideal|  15.87 |  34.13 |  34.13 |  15.87 |              HIGH power  (40-  )  |")
    scr.addstr(24,0,"|------------------------------------------------------------------------------|")
    scr.addstr(25,0,key_line)
    scr.addstr(26,0,"| Messages:                                                                    |")
    scr.addstr(27,0,"|------------------------------------------------------------------------------|")

def main(stdscr,roach2,pause=1,do_power=False,state=STATE_MAIN):
    global USE_COLOR
    old_state = STATE_NONE
    USE_COLOR = init_curses_color()
    stdscr.leaveok(0)
    stdscr.nodelay(True)
    stdscr.erase()
    stdscr.addstr(0,0,"Connecting to host...")
    stdscr.refresh()
    stdscr.erase()
    display_blank(stdscr)
    state_on_back = STATE_MAIN
    while True:
        # handle state change
        if not old_state == state:
            # udpate display to new state
            stdscr.erase()
            if state == STATE_MAIN:
                display_blank(stdscr)
            elif state == STATE_SENSORS:
                display_sensors(stdscr)
            elif state == STATE_HELP:
                state_on_back = old_state
                display_help(stdscr)
            # refresh, in case new background
            stdscr.refresh()
            # update old state
            old_state = state
        # do state-specific stuff
        if state == STATE_MAIN:
            ## do something
            display_summary(stdscr,roach2)
            if do_power:
                display_power(stdscr,roach2)
        elif state == STATE_SENSORS:
            ## do something
            display_sensors(stdscr)
        # do generic stuff
        clear_message(stdscr)
        # always refresh
        stdscr.refresh()
        time.sleep(pause)
        try:
            c = stdscr.getkey()
            if c == KEY_QUIT:
                break
            elif c == KEY_MAIN:
                state = STATE_MAIN
            elif c == KEY_SENSORS:
                state = STATE_SENSORS
            elif c == KEY_ALC and state == STATE_MAIN:
                run_alc(stdscr,roach2)
            elif c == KEY_TOGGLE_POWER and state == STATE_MAIN:
                do_power = toggle_power(stdscr,do_power)
            elif c == KEY_HELP:
                state = STATE_HELP
            elif c == KEY_BACK:
                state = state_on_back #STATE_MAIN
        except:
            continue
    return stdscr

def init_curses_color():
    if not curses.has_colors():
        return False
    curses.start_color()
    curses.init_pair(COLOR_INDEX_DEFAULT, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(COLOR_INDEX_TH_LOLO, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(COLOR_INDEX_TH_LO, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(COLOR_INDEX_TH_GOOD, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(COLOR_INDEX_TH_HI, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(COLOR_INDEX_TH_HIHI, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(COLOR_INDEX_ERROR, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(COLOR_INDEX_GOOD, curses.COLOR_GREEN, curses.COLOR_BLACK)
    return True

if __name__ == '__main__':
    
    import argparse
    parser = argparse.ArgumentParser(description='Set 2-bit quantization threshold')
    parser.add_argument('-t','--timeout',metavar='TIMEOUT',type=float,default=5.0,
        help="timeout after so many seconds if R2DBE not connected (default is 5.0)")
    parser.add_argument('-v','--verbose',action='count',
        help="control verbosity, use multiple times for more detailed output")
    parser.add_argument('host',metavar='R2DBE',type=str,nargs='?',default='r2dbe-1',
        help="hostname or ip address of r2dbe (default is 'r2dbe-1')")
    args = parser.parse_args()
    
    # connect to roach2
    roach2 = corr.katcp_wrapper.FpgaClient(args.host)
    if not roach2.wait_connected(timeout=args.timeout):
        msg = "Could not establish connection to '{0}' within {1} seconds, aborting".format(
            args.host,args.timeout)
        raise RuntimeError(msg)
    
    if args.verbose > 1:
        print "connected to '{0}'".format(args.host)
    
    scr = curses.wrapper(main,roach2) 
