#!/bin/bash
set -Eeuo pipefail
trap 'echo "${0}: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# Args
server=
interface=
ports='0,0'
delay='1000'  # in milliseconds
duration='60' # in seconds
repetitions='30'
streams='32'

usage() {
	printf -- "%s\n" "${0}"
	printf -- "\n"
	printf -- "\tThe following options are available:\n"
	printf -- "\n"
	printf -- "--help\n"
	printf -- "  Prints this message.\n"
	printf -- "\n"
	printf -- "--server=str\n"
	printf -- "  String in the form of 'user@hostname' that indicates the server to run bpfwavelet.\n"
	printf -- "\n"
	printf -- "--interface=str\n"
	printf -- "  Interface to attach bpfwavelet in the server.\n"
	printf -- "\n"
	printf -- "--ports=str\n"
	printf -- "  Ports TRex will use to send/receive traffic. Passed to PDR, see ./pdr.py --help.\n"
	printf -- "  Default is '%s'\n" "${ports}"
	printf -- "\n"
	printf -- "--delay=str\n"
	printf -- "  Delay in milliseconds. Passed to PDR, see ./pdr.py --help\n"
	printf -- "  Default is '%s'\n" "${delay}"
	printf -- "\n"
	printf -- "--duration=str\n"
	printf -- "  Duration in seconds. Passed to PDR, see ./pdr.py --help\n"
	printf -- "  Default is %s\n" "${duration}"
	printf -- "\n"
	printf -- "--repetitions=str\n"
	printf -- "  Number of repetitions. Passed to PDR, see ./pdr.py --help\n"
	printf -- "  Default is %s\n" "${repetitions}"
}
if ! opts="$(getopt -o 'h' --longoptions 'help,server:,interface:,ports:,delay:,duration:,repetitions:' -n "${0}" -- "${@}")"; then
	usage >&2
	exit 1
fi

eval set -- "$opts"
unset opts

while true; do
	case "${1}" in
	-h | --help)
		shift 1
		usage
		exit 0
		;;
	--server)
		server="${2}"
		shift 2
		continue
		;;
	--interface)
		interface="${2}"
		shift 2
		continue
		;;
	--ports)
		ports="${2}"
		shift 2
		continue
		;;
	--delay)
		delay="${2}"
		shift 2
		continue
		;;
	--duration)
		duration="${2}"
		shift 2
		continue
		;;
	--repetitions)
		repetitions="${2}"
		shift 2
		continue
		;;
	--)
		shift
		break
		;;
	*)
		echo "ERROR: Internal error" >&2
		exit 1
		;;
	esac
done

if [ -z "${server}" ]; then
	echo "ERROR: No server provided" >&2
	usage >&2
	exit 1
fi

if [ -z "${interface}" ]; then
	echo "ERROR: No interface provided" >&2
	usage >&2
	exit 1
fi

if [ "$#" -gt 0 ]; then
	echo "ERROR: Unexpected arguments: ${*}" >&2
	usage >&2
	exit 1
fi

readonly pkt_sizes=('64' '128' '256' '512' '1024' '1280' '1518')
readonly sampling_intervals=('250000' '1000000000') # 250µs and 1s in nanoseconds
readonly decomposition_levels=('0' '1' '2' '4' '8' '16' '32')

readonly pid_file='/tmp/bpfwavelet-bench.pid'

benchdir="$(dirname -- "$(realpath -- "$0")")"
timestamp="$(date -Iseconds)"
readonly benchdir
readonly timestamp

# Args:
# - Command string
# - Path of log dir
# - Packet size (for logging)
remote_spawn() {
	local -r cmd="${1}"
	local -r log_dir="${2}"
	local -r pkt_size="${3}"

	local -r save_pid="echo \$! >${pid_file}"
	local -r nohup_cmd_save_pid="mkdir -p '${log_dir}'; nohup ${cmd} 1>${log_dir}/${pkt_size}.stdout 2>${log_dir}/${pkt_size}.stderr & ${save_pid}"

	ssh "${server}" -- "${nohup_cmd_save_pid}"
	echo "On ${server} running: ${cmd}"
	echo "Logs being saved to: ${log_dir}/${pkt_size}.{stdout,stderr}"
}

remote_kill() {
	ssh "${server}" -- sudo kill -SIGTERM '"$(cat '${pid_file}')"'
}

# Args:
# - Packet size
# - Commmand string
# - Tag that identifies what is being benchmarked
run-pdr() {
	local -r pkt_size="${1}"
	local -r cmd="${2}"
	local -r tag="${3}"

	local -r run_dir="${benchdir}/results/${tag}/${timestamp}"
	mkdir -p "${run_dir}"

	remote_spawn "${cmd}" "bpfwaveletbench/${tag}/${timestamp}" "${pkt_size}"
	sleep 5 # give it some time to make sure the XDP program is attached

	echo "Running PDR with packets of ${pkt_size} bytes"
	"${benchdir}/pdr.py" \
		--ports "${ports}" \
		--size "${pkt_size}" \
		--delay "${delay}" \
		--duration "${duration}" \
		--repetitions "${repetitions}" \
		--streams 32 \
		--results "${run_dir}/${pkt_size}.json"
	echo "Results written to: ${run_dir}/${pkt_size}.json"

	remote_kill "${server}"
}

cleanup() {
	rc="${?}"
	trap '' EXIT INT QUIT TERM HUP

	remote_kill 2>/dev/null || true # or-true: when exiting gracefully no remote process is left running

	exit "${rc}"
}
trap cleanup EXIT INT QUIT TERM HUP

for pkt_size in "${pkt_sizes[@]}"; do
	# Run with xdp-bench: our baseline
	cmd="sudo xdp-bench tx --packet-operation=no-touch ${interface}"
	tag='xdp-bench-tx'
	run-pdr "${pkt_size}" "${cmd}" "${tag}"

	# Run with bpfwavelet varying parameters
	for sampling_interval in "${sampling_intervals[@]}"; do
		for decomposition_level in "${decomposition_levels[@]}"; do
			cmd="sudo bpfwavelet -d -t ${sampling_interval} -l ${decomposition_level} -r ${interface} -v"
			tag="bpfwavelet-${sampling_interval}-${decomposition_level}"
			run-pdr "${pkt_size}" "${cmd}" "${tag}"
		done
	done
done
