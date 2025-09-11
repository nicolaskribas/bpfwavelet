#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# modified from https://github.com/tohojo/xdp-paper/blob/master/benchmarks/enable_huge_pages.sh

doc='For DPDK, enable huge pages'

if ((EUID)); then
	echo "Need root priviliges" >&2
	exit 1
fi

echo "$doc"

echo 1024 >/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

mkdir -p /mnt/huge

mount -t hugetlbfs nodev /mnt/huge

df /mnt/huge/
