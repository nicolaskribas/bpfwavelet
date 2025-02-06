#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

DOC='Disables simultaneous multithreading (SMT), boost and C-states, and set scaling governor to performance'

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
	echo "Need root priviliges" >&2
	exit 1
fi

echo "$DOC"

# disable SMT
echo off >/sys/devices/system/cpu/smt/control

# disable boost
echo 0 >/sys/devices/system/cpu/cpufreq/boost

# disable C-states
echo 1 | tee /sys/devices/system/cpu/cpu*/cpuidle/state*/disable >/dev/null

# set scaling governor to performance
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null || true
