#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

if [ -z "${1-}" ]; then
	echo 'no destination provided ([user@]hostname)' >&2
	exit 1
fi

destination="${1}"
shift

scp monitor_counters_inner.sh "${destination}":/tmp/monitor_counters_inner.sh
scp diff_counters_inner.sh "${destination}":/tmp/diff_counters_inner.sh
ssh "${destination}" -t -- /tmp/monitor_counters_inner.sh "$@"
