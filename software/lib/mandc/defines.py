##### Config file defintions
# Global section
CONFIG_SECTION_GLOBAL="global"
# Default station code to apply if none given in backend definition
CONFIG_GLOBAL_OPTION_STATION="station"
# List backend definitions
CONFIG_GLOBAL_OPTION_BACKENDS="backends"

# Hostname of the R2DBE (backend definition)
CONFIG_BACKEND_OPTION_R2DBE="r2dbe"
# Hostname of the Mark6 (backend definition)
CONFIG_BACKEND_OPTION_MARK6="mark6"
# Input definitions for IF0 and IF1
CONFIG_BACKEND_OPTION_IF0="if0"
CONFIG_BACKEND_OPTION_IF1="if1"
# Each input definition should be in order:
#   1) polarization (left/right or X/Y)
#   2) receiver sideband (upper/lower)
#   3) block downconverter band (high/low)
#   4) Mark6 network interface
#   5) module slots to record to
CONFIG_BACKEND_INPUT_ORDER=["pol","rx","bdc","iface","mods"]
