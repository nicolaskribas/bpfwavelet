#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# Parameters
DELAY=1000
DURATION=60
PKT_SIZES=('64' '128' '256' '512' '1024' '1280' '1518')
SAMPLING_INTERVALS=('250000' '1000000000') # 250µs and 1s in nanoseconds
DECOMPOSITION_LEVELS=('0' '1' '2' '4' '8' '16' '32')

SERVER=p4server3
PORT=enp132s0f0np0

BENCHDIR="$(dirname -- "$(realpath -- "$0")")"
TIMESTAMP="$(date -Iseconds)"

PID_FILE='/tmp/pid'
remote_spawn() {
	DESTINATION="$1"
	CMD="$2"
	LOG="$3"

	SAVE_PID='echo $! >'"${PID_FILE}"
	NOHUP_CMD_SAVE_PID="nohup ${CMD} 1>${LOG}.stdout 2>${LOG}.stderr & ${SAVE_PID}"

	ssh "${DESTINATION}" -- "${NOHUP_CMD_SAVE_PID}"
}

remote_kill() {
	DESTINATION="$1"

	ssh "${DESTINATION}" -- sudo kill -SIGTERM '"$(cat '"${PID_FILE}"')"'
}

run-binary-search() {
	REMOTE_PID="$(remote_spawn "${SERVER}" "${CMD}")"

	RUN_DIR="${BENCHDIR}/results/${TAG}/${TIMESTAMP}"
	mkdir -p "${RUN_DIR}"
	uv run main.py \
		--ports 0,0 \
		--size "${PKT_SIZE}" \
		--delay "${DELAY}" \
		--duration "${DURATION}" \
		--results "${RUN_DIR}/${PKT_SIZE}.json"

	remote_kill "${SERVER}" "${REMOTE_PID}"
}

for PKT_SIZE in "${PKT_SIZES[@]}"; do
	# Run with xdp-bench: our baseline
	CMD="sudo xdp-bench tx ${PORT}"
	TAG='xdp-bench-tx'
	run-binary-search

	# Run with bpfwavelet varying parameters
	for SAMPLING_INTERVAL in "${SAMPLING_INTERVALS[@]}"; do
		for DECOMPOSITION_LEVEL in "${DECOMPOSITION_LEVELS[@]}"; do
			CMD="sudo bpfwavelet -d -t ${SAMPLING_INTERVAL} -l ${DECOMPOSITION_LEVEL} -r ${PORT} -v"
			TAG="bpfwavelet-${SAMPLING_INTERVAL}-${DECOMPOSITION_LEVEL}"
			run-binary-search "${CMD}" "${TAG}"
		done
	done
done
