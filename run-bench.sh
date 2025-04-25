#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

if [ -z "${1-}" ]; then
	echo 'No tag supplied' >&2
	exit 1
fi
TAG="$1" # give it a memorable name

BENCHDIR="$(dirname -- "$(realpath -- "$0")")"
TIMESTAMP="$(date -Iseconds)"

RUN_DIR="${BENCHDIR}/results/${TAG}/${TIMESTAMP}"
mkdir -p "${RUN_DIR}"

echo "Results will be saved to '${RUN_DIR}' directory"

for SIZE in '64' '128' '256' '512' '1024' '1280' '1518'; do
	uv run main.py \
		--ports 0,0 \
		--size "${SIZE}" \
		--delay 1000 \
		--duration 60 \
		--results "${RUN_DIR}/${SIZE}.json"
done
