#!/bin/bash

# Fed-BioMed - node container launch script
# - launched as root to handle VPN
# - may drop privileges to CONTAINER_USER at some point

# read functions
source /entrypoint_functions.bash

# read config.env
source ~/bashrc_entrypoint

check_vpn_environ
init_misc_environ
start_wireguard
configure_wireguard

trap finish TERM INT QUIT

# Cannot launch node at this step because VPN is not yet fully established
# thus it cannot connect to mqtt

sleep infinity &

wait $!
