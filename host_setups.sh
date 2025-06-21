#!/bin/bash

## Note: This may have been created for the simulator, won't work on a real device
source "./lldb_docker/env/logger.sh"
source ./config.cfg

# Do tcp forwarding from the mux port to the unix socket path
mux_pid=$(netstat -vanp tcp | grep "$MUX_PORT" | awk "/\\.$P/ {print \$11}")
log INFO "got mux pid: $mux_pid"
[ -n "$mux_pid" ] && kill "$mux_pid"



log INFO "starting mux from port to unix socket"
(socat TCP-LISTEN:$MUX_PORT,reuseaddr,fork UNIX-CONNECT:/var/run/usbmuxd) &

# The tunnel needs to be made on the host, I could not make that work from the container :/
log INFO "Sorry need your password to start the tunnel, must be sudo."
log INFO "If you don't feel safe you can open host_setups.sh file and see that that is my only sudo usage"

sudo -v || exit 1  # Ensure password is prompted synchronously

output_file=$(mktemp)
log INFO "output file: $output_file"

# find pid by default tunnel port to kill previous tunnel
prev_tunnel_pid=$(netstat -vanp tcp | grep 49151 | awk "/\\.$P/ {print \$11}")
log INFO "got tunnel pid: $prev_tunnel_pid"
[ -n "$prev_tunnel_pid" ] && sudo kill "$prev_tunnel_pid"

sudo pymobiledevice3 remote tunneld > "$output_file" 2>&1 &
pid=$!

# Wait for it to initialize (adjust message as needed)
while ! grep -q "Created tunnel" "$output_file"; do
  sleep 0.2
  log INFO "waiting"
done

# Read captured output
output=$(cat "$output_file")
log INFO "$output"

tunnel_info=$(grep 'Created tunnel' "$output_file" | awk '{for (i=1;i<=NF;i++) if ($i=="--rsd") print $i, $(i+1), $(i+2)}')
log INFO "tunnel-info: $tunnel_info"





