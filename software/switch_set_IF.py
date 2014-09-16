import httplib

# connect to 4-way switch with ip address and port (default is port 80)
connection = httplib.HTTPConnection("192.52.63.28",80)

# send command via HTTP to switch and get response
connection.request("GET","/SETP=0")
response = connection.getresponse()
data = response.read()
if data=='0':
   print "Error returned from command\n"
if data=='1':
   print "Command executed successfully."

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
