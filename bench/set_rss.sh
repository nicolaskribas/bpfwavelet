#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

if [ -z "${1-}" ]; then
	echo 'no interfaces provided' >&2
	echo "Usage: ${0} INTERFACE"
	exit 1
fi
interface="${1}"

if [ ! -e "/sys/class/net/${interface}" ]; then
	echo "invalid interface ${interface}" >&2
	exit 1
fi

start_port='49152' # must match value used in the generated traffic, check profile used pdr.py
num_rings="$(ethtool -n "${interface}" | grep -E '[0-9]+ RX rings available' | cut -d ' ' -f 1)"

# delete all previous flow classification rules
# or-true: grep return code is 1 when no match is found
ethtool -n "${interface}" | { grep -Ex 'Filter: [0-9]+' || true; } | cut -d ' ' -f 2 | while read -r rule; do
	ethtool -N "${interface}" delete "${rule}"
done

# create new flow classification rules distributing traffic over all available queues based on source port
for ring in $(seq 0 "$((num_rings - 1))"); do
	port="$((start_port + ring))"
	ethtool -N "${interface}" flow-type udp4 src-port "${port}" queue "${ring}"
done

# or-true: irqbalance may be already killed
pkill irqbalance || true

# set affinity using script provided by `mlnx-tools` package.
set_irq_affinity.sh "${interface}"
