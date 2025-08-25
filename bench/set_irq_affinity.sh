#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# modified from https://github.com/tohojo/xdp-paper/blob/master/benchmarks/jbrouer_setup05_no_netfilter.sh

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
	echo "Need root priviliges" >&2
	exit 1
fi

pkill irqbalance

for irq_name_dir in /proc/irq/*/mlx5_comp*/; do
	irq_dir="$(dirname "${irq_name_dir}")"
	cat "${irq_dir}/affinity_hint" >"${irq_dir}/smp_affinity"
done
grep -H . /proc/irq/*/mlx5_comp*/../smp_affinity_list
