#!/bin/bash
set -Eeuo pipefail
trap 'echo "$0: Error on line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# modified from https://github.com/perftool-incubator/bench-trafficgen/blob/main/trafficgen/install-trex.sh

base_dir="/opt/trex"
tmp_dir="/tmp"
trex_ver="v3.06"
insecure_curl=0
force_install=0

if ! opts=$(getopt -q -o c: --longoptions "tmp-dir:,base-dir:,version:,insecure,force" -n "getopt.sh" -- "$@"); then
	printf -- "%s\n" "$*"
	printf -- "\n"
	printf -- "\tThe following options are available:\n\n"
	printf -- "\n"
	printf -- "--tmp-dir=str\n"
	printf -- "  Directory where temporary files should be stored.\n"
	printf -- "  Default is %s\n" "${tmp_dir}"
	printf -- "\n"
	printf -- "--base-dir=str\n"
	printf -- "  Directory where TRex will be installed.\n"
	printf -- "  Default is %s\n" "${base_dir}"
	printf -- "\n"
	printf -- "--version=str\n"
	printf -- "  Version of TRex to install\n"
	printf -- "  Default is %s\n" "${trex_ver}"
	printf -- "\n"
	printf -- "--insecure\n"
	printf -- "  Disable SSL cert verification for the TRex download site.\n"
	printf -- "  Some environments require this due to the usage of an uncommon CA.\n"
	printf -- "  Do not use this option if you do not understand the implications.\n"
	printf -- "\n"
	printf -- "--force\n"
	printf -- "  Download and install TRex even if it is already present.\n"
	exit 1
fi

eval set -- "$opts"
unset opts

while true; do
	case "${1}" in
	--tmp-dir)
		shift
		if [ -n "${1}" ]; then
			tmp_dir=${1}
			shift
		fi
		;;
	--base-dir)
		shift
		if [ -n "${1}" ]; then
			base_dir=${1}
			shift
		fi
		;;
	--version)
		shift
		if [ -n "${1}" ]; then
			trex_ver=${1}
			shift
		fi
		;;
	--insecure)
		shift
		insecure_curl=1
		;;
	--force)
		shift
		force_install=1
		;;
	--)
		break
		;;
	*)
		if [ -n "${1}" ]; then
			echo "ERROR: Unrecognized option ${1}"
		fi
		exit 1
		;;
	esac
done

trex_url=https://trex-tgn.cisco.com/trex/release/${trex_ver}.tar.gz
trex_dir="${base_dir}/${trex_ver}"

if [ -d "${trex_dir}" ] && [ "${force_install}" == "0" ]; then
	echo "TRex ${trex_ver} already installed"
else
	if [ -d "${trex_dir}" ]; then
		/bin/rm -Rf "${trex_dir}"
	fi

	mkdir -p "${base_dir}"
	if pushd "${base_dir}" >/dev/null; then
		tarfile="${tmp_dir}/${trex_ver}.tar.gz"
		/bin/rm -f "${tarfile}"
		curl_args=""
		if [ "${insecure_curl}" == "1" ]; then
			curl_args="-k"
		fi
		echo "Downloading TRex ${trex_ver} from ${trex_url}..."
		if curl ${curl_args} --retry 3 --retry-all-errors --silent --output "${tarfile}" "${trex_url}"; then
			if tar -xzf "${tarfile}"; then
				/bin/rm "${tarfile}"
				echo "installed TRex ${trex_ver} from ${trex_url}"

				if pushd "${base_dir}/${trex_ver}" >/dev/null; then
					if tar -xzf "trex_client_${trex_ver}.tar.gz"; then
						echo "extracted client"
					fi
					popd >/dev/null
				fi

			else
				echo "ERROR: could not unpack ${tarfile} for TRex ${trex_ver}"
				exit 1
			fi
		else
			curl_rc=$?
			if [ "${curl_rc}" == "60" ]; then
				echo "ERROR: SSL certificate failed validation on TRex download.  Run --help and see --insecure option"
				exit 1
			else
				echo "ERROR: TRex download failed (curl return code is ${curl_rc})"
				exit 1
			fi
		fi
		popd >/dev/null
	else
		echo "ERROR: Could not use ${base_dir}"
		exit 1
	fi
fi

# we need a symlink so our trex scripts can always point to
# same location for trex
if pushd "${base_dir}" >/dev/null; then
	/bin/rm -f current 2>/dev/null
	ln -sf "${trex_ver}" current
	popd >/dev/null
fi
