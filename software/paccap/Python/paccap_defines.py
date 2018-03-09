############################################################### Defaults
DEFAULT_CTRL_HOST="localhost"
DEFAULT_CTRL_PORT=1973
DEFAULT_LOG_FILE="/var/log/paccap/paccap.log"
DEFAULT_CFG_FILE="/usr/local/etc/paccap.conf"
DEFAULT_DATA_PATH="/home/ayoung/data"
DEFAULT_DATA_NAME_FMT="{exp}_{daq}_{name}_{ch}.vdif"

CMD_MAX_LEN=256
CMD_TERMINATE=";"
CMD_ACTIONSEP="="
CMD_PARAMSSEP=":"

PACCAP_EXEC="/home/ayoung/paccap/paccap"

############################################################ Config file
# System section
CFG_SEC_SYSTEM="sys"
CFG_OPT_SYSTEM_LOG_FILE="log_file"
CFG_OPT_SYSTEM_CTRL_HOST="ctrl_host"
CFG_OPT_SYSTEM_CTRL_PORT="ctrl_port"
# Data section
CFG_SEC_DATA="dat"
CFG_OPT_DATA_PATH="path"
CFG_OPT_DATA_NAME_FMT="name_fmt"
# Data acquisition section
CFG_SEC_DAQ="daq"
CFG_OPT_DAQ_LIST="list"
# R2DBE section (options only)
R2DBE_CHANNELS=(0,1)
CFG_OPT_R2DBE_CHN_IFACE="ch{n}_iface"
CFG_OPT_R2DBE_CHN_PORT="ch{n}_port"
