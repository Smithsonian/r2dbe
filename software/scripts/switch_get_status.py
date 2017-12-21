import httplib

print "\n\n\n"
print "________________________________________________"
print "Getting Status of the 4-way network switch"
print "________________________________________________"
print "\n"

# connect to 4-way switch with ip address and port (default is port 80)
connection = httplib.HTTPConnection("192.52.63.28",80)

# send queries via HTTP to switch and get response

# check DC power is plugged in and working power
print "Check 24 V DC power "
connection.request("GET","/PWR?")
response = connection.getresponse()
data = response.read()
if data=='0':
   print "    Not connected\n"
if data=='1':
   print "    Connected\n"

# check that the fan is running  
print "Check Fan status"
connection.request("GET","/FAN?")
response = connection.getresponse()
data = response.read()
if data=='0':
   print "    Off\n"
if data=='1':
   print "    On\n"

# check for a heat alarm
print "Check for Heat Alarm"
connection.request("GET","/HEATALARM?")
response = connection.getresponse()
data = response.read()
if data=='0':
   print "    None\n"
if data=='1':
   print "    Alarm!\n"

# check temperature values
print "Check Temp Sensor Values"
connection.request("GET","/TEMP1?")
response = connection.getresponse()
data = response.read()
print "    %s deg C" %(data)
connection.request("GET","/TEMP2?")
response = connection.getresponse()
data = response.read()
print "    %s deg C\n" %(data)

# check for a heat alarm
print "Switch Status"
connection.request("GET","/SWPORT?")
response = connection.getresponse()
data = response.read()
A = int(data)    & 1
B = int(data)>>1 & 1
C = int(data)>>2 & 1
D = int(data)>>3 & 1

Com = [('   IF',1),('Noise',2)]
print "    Switch A: %s (Com > %d)  " %(Com[A][0],Com[A][1])
print "    Switch B: %s (Com > %d)  " %(Com[B][0],Com[B][1])
print "    Switch C: %s (Com > %d)  " %(Com[C][0],Com[C][1])
print "    Switch D: %s (Com > %d)\n" %(Com[D][0],Com[D][1])




# this could also be done in a browser from the local net
# http://192.52.63:80/SWPORT?

# a list of other commands
#
# /SETA=1
#        This will set switch A = 1 (com set to 2, noise).  Can set A, B,
#        C, or D to 0 or 1 (0 is IF is com set to 1, 1 is noise is com set
#        to 2)
#
# /SETP=15
#        Set all 4 switches at once, using binary string of 4 bits, each 
#        controlling A, B, C, D (0 is IF, 1 is noise).  15 will set all
#        ports to noise


# a list of queries
#
# /SWPORT?
#        returns decimal value of 4-bit binary, where each bit represents 
#        switch A, B, C, and D, with 0 being for comm set to 1 and 1 being
#        for comm set to 2.  2 is noise, so if all are set to noise this
#        will return the value 15.  If only A is set to noise, returns value 1.
#
# /MN?
#        returns model name
#
# /SN?
#        returns serial number
#
# /TEMP1?
#        returns internal temperature sensor for one of 2 sensors: 1 and 2.
#        the units are in degrees celsius
#        
# /PWR?
#        get DC power status.  0 for no, 1 for yes.
#
# /HEATALARM?
#        get head alarm. 0 for no alarm, within operating limits. 1 for alarm,
#        unit exceeded recommended limits
#
# /FAN?
#        get fan status.  0 fan is off, 1 fan is on.
#


# this information was found in this document
# http://www.minicircuits.com/softwaredownload/Programming%20Manual-2-Switch-A0.pdf
