#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# This scrips start TRex server on a pair of veths.
# Useful to test our benchmark scripts when there is no NIC with DPDK

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
	echo "Need root priviliges" >&2
	exit 1
fi

finish() {
	ip link delete "$VETH0" || true # may fail if the interface doesn't exist
	[ -n "${TEMP_CFG-}" ] && [ -f "$TEMP_CFG" ] && rm "$TEMP_CFG" >&2
}
trap finish EXIT

VETH0='veth0'
VETH1='veth1'
ip link add "$VETH0" type veth peer name "$VETH1" >&2
ip link set "$VETH0" up >&2
ip link set "$VETH1" up >&2
# tc qdisc add dev "$VETH0" root netem delay 10ms duplicate 0% limit 1000

pushd /opt/trex/current >/dev/null || {
	echo "Error changing directory to /opt/trex/current. Is TRex installed?" >&2
	exit 1
}

TEMP_CFG="$(mktemp)"

cat <<EOF >"$TEMP_CFG"
- version: 2
  interfaces: ['veth0', 'veth1']
  port_info:
      - ip: 1.1.1.1
        default_gw: 2.2.2.2
      - ip: 2.2.2.2
        default_gw: 1.1.1.1

  platform:
      master_thread_id: 0
      latency_thread_id: 1
      dual_if:
        - socket: 0
          threads: [2,3,4,5,6,7,8,9,10,11,12,13,14,15]
EOF

./t-rex-64 -i --cfg "$TEMP_CFG" || true # TRex returns an error when you Ctrl+C it

popd >/dev/null
