#!/usr/bin/env python2.7
import logging
import datetime
import sys, socket, struct

from vdif import VDIFFrame

logging.basicConfig(format='%(asctime)-15s - %(message)s')
logger = logging.getLogger('vdif_recv')
logger.setLevel(logging.DEBUG)

CHANNELS = 2
FRAME_HDR_SIZE = 32
FRAME_DAT_SIZE = 8192
FRAME_SIZE = FRAME_HDR_SIZE + FRAME_DAT_SIZE

frames_to_capture = int(sys.argv[1])

sock = []
sock.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
sock[-1].bind(("192.168.1.3", 4001))
sock.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
sock[-1].bind(("192.168.1.5", 4001))

data_str = []
data_str.append("")
data_str.append("")

pkt = [None,] * CHANNELS
for i in range(frames_to_capture):
    for chan in range(CHANNELS):
        pkt[chan], addr = sock[chan].recvfrom(FRAME_SIZE)
    for chan in range(CHANNELS):
        data_str[chan] += pkt[chan]

for s in sock:
    s.close()

logger.info("Finished capturing {0} frames from {1} channel(s)".format(frames_to_capture, CHANNELS))

dropped_pkts = 0
for chan in range(CHANNELS):
    last_sec_ref_ep = None
    last_data_frame = None
    for i in range(frames_to_capture):
        pkt = data_str[chan][i*FRAME_SIZE:i*FRAME_SIZE+FRAME_SIZE]
        frame = VDIFFrame.from_bin(pkt)

        sec_ref_ep = frame.secs_since_epoch
        data_frame = frame.data_frame
        ref_epoch = frame.ref_epoch

        frame_dt = datetime.datetime(year = 2000+(ref_epoch/2), month = (ref_epoch&1)*6, day = 1) + \
            datetime.timedelta(seconds = sec_ref_ep)

        if i == 0:
            logger.info("Chan #{0} first frame time: {1} at frame #{2}".format(chan, frame_dt.isoformat(' '), data_frame))

        if i == frames_to_capture - 1:
            logger.info("Chan #{0} last frame time:  {1} at frame #{2}".format(chan, frame_dt.isoformat(' '), data_frame))

        if i > 0:
            if not data_frame == last_data_frame + 1:
                if not sec_ref_ep == last_sec_ref_ep + 1:
                    # print "Data frame incontinuity: {0} --> {1}".format(last_data_frame, data_frame)
                    dropped_pkts += data_frame - last_data_frame
    
        last_sec_ref_ep = sec_ref_ep
        last_data_frame = data_frame

logger.info("Total dropped frames: {0}".format(dropped_pkts))
logger.info("Lost frame rate: {0:5.2f}%".format(100. * dropped_pkts / (frames_to_capture*CHANNELS)))

for chan in range(CHANNELS):
    vdif_file = sys.argv[2] + "_chan{0}.vdif".format(chan)
    with open(vdif_file, 'wb') as file_:
        file_.write(data_str[chan])
