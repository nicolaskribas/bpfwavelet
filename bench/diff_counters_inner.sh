#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

if [ -z "${1-}" ]; then
	echo 'No argument supplied' >&2
	exit 1
fi

interface="${1}"
interface_counters_file="/tmp/${interface}_stats"

ethtool -S "${interface}" >"${interface_counters_file}"
printf 'time: %s' "$(date '+%s')" >>"${interface_counters_file}"

[ -f "${interface_counters_file}.old" ] && awk '
	NR == FNR {
		key=$1;
		val[key]=$2;
	}

	NR != FNR {
		key=$1;
		diff = $2 - val[key];

		if (diff != 0) {
			sign = (diff > 0) ? "+" : "";
			printf "%s %s%'\''d\n", key, sign, diff;
		}
	}
' "${interface_counters_file}.old" "${interface_counters_file}"

mv "${interface_counters_file}" "${interface_counters_file}.old"
