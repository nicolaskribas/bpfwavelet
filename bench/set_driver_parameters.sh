#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# modified from https://github.com/tohojo/xdp-paper/blob/master/benchmarks/jbrouer_setup05_no_netfilter.sh

# Basic setup steps used for benchmarking of XDP

DOC='Setting driver parameters: disable flow control'

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
	echo "Need root priviliges" >&2
	exit 1
fi

if [ -z "${1-}" ]; then
	echo 'No devname supplied' >&2
	exit 1
fi

devname="${1}"
queues=32

echo "$DOC"

# Disable flow control
ethtool -A "${devname}" rx off tx off

# Number of queues
ethtool -L "${devname}" combined "${queues}"

# Queue size
ethtool -G "${devname}" rx 1024 tx 1024

# Set hash table
ethtool -X "${devname}" equal "${queues}"
