import logging, sys

from mandc import Station

### Setup logging
# Setup root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if "-v" in sys.argv:
	logger.setLevel(logging.DEBUG)
# Stream to stdout
stdout = logging.StreamHandler(sys.stdout)
if "-v" in sys.argv:
	stdout.setLevel(logging.DEBUG)
logger.addHandler(stdout)
# Create and set formatting
formatter = logging.Formatter('%(name)-30s: %(asctime)s : %(levelname)-8s %(message).140s')
stdout.setFormatter(formatter)
# Silence all katcp messages
katcp_logger = logging.getLogger('katcp')
katcp_logger.setLevel(logging.CRITICAL)
###

s = Station.from_file('station.conf')

s.setup()
