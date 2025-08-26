#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

if [ -z "${1-}" ]; then
	echo 'no interfaces provided' >&2
	exit 1
fi
interface="${1}"

tmux new-session -d -A -s monitor-counters

tmux rename-window monitor-counters
tmux send-keys -t monitor-counters "watch -n 0.983 /tmp/diff_counters_inner.sh ${interface}" C-m
shift
for interface in "$@"; do
	tmux split-window -t monitor-counters
	tmux send-keys -t monitor-counters "watch -n 0.983 /tmp/diff_counters_inner.sh ${interface}" C-m
done
tmux select-layout -t monitor-counters even-horizontal
tmux attach -t monitor-counters
