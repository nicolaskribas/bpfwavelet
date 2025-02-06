#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
	echo "Need root priviliges" >&2
	exit 1
fi

BENCHDIR="$(dirname -- "$(realpath -- "$0")")"

"${BENCHDIR}/disable-dynamic-cpu-features.sh"
"${BENCHDIR}/enable-hugepages.sh"

pushd /opt/trex/current >/dev/null || {
	echo "Error changing directory to /opt/trex/current. Is TRex installed?" >&2
	exit 1
}
./t-rex-64 -i &
TREX_PID=$!
popd

kill -INT $TREX_PID
