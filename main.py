import argparse
import json
import math
import sys
import time

sys.path.append("/opt/trex/current/trex_client/interactive")
import trex.stl.api as trex
from trex.stl.api import Ether, IP, UDP  # pyright: ignore[reportAttributeAccessIssue]


"""
Design
======

If --profile is given, it's loaded; otherwise, a built-in one is used. The
profile is added to the even-numbered --ports.

To measure:
- Wait for --wait seconds.
- Start traffic for --duration seconds.
- Wait --delay ms after transmission ends.

Packet loss is checked against --threshold to adjust the binary search bounds.
The process stops when the difference between lower and upper bounds is less
than --precision. Final results are saved to --results in JSON format.
"""


def get_full_stats(client: trex.STLClient, ports: set[int]) -> dict:
    return {
        "stats": client.get_stats(list(ports)),
        "xstats": {port: client.get_xstats(port) for port in ports},
        "pgid": client.get_pgid_stats(),
        "util": client.get_util_stats(),
    }


def measure(
    client: trex.STLClient,
    ports: list[int],
    duration_s: int,
    rx_delay_ms: int,
    rate: str,
) -> dict:
    client.clear_stats(
        ports=list(set(ports)),
        clear_global=True,
        clear_flow_stats=True,
        clear_latency_stats=True,
        clear_xstats=True,
    )

    client.start(
        ports[::2],
        mult=rate,
        duration=duration_s,
        core_mask=trex.STLClient.CORE_MASK_PIN,
    )
    start_time_ns = time.monotonic_ns()

    timeout_s = math.ceil(1.1 * duration_s)  # Timeout is 110% of the duration

    try:
        client.wait_on_traffic(ports[::2], timeout=timeout_s, rx_delay_ms=rx_delay_ms)
        stopped_early = False
    except trex.TRexTimeoutError:
        client.stop(ports[::2], rx_delay_ms=rx_delay_ms)
        stopped_early = True
    finally:
        actual_duration_ns = time.monotonic_ns() - start_time_ns

    stats = get_full_stats(client, set(ports))

    # Calculate metrics
    tx = stats["stats"]["total"]["opackets"]
    rx = stats["stats"]["total"]["ipackets"]
    lost: int = tx - rx
    lost_percentage: float = lost / tx * 100

    return {
        "ports": ports,
        "expected_duration_ms": duration_s * 1000,
        "rx_delay_ms": rx_delay_ms,
        "rate": rate,
        "timeout_ms": timeout_s * 1000,
        "stopped_early": stopped_early,
        "actual_duration_ms": actual_duration_ns / 1000000,
        "lost": lost,
        "lost_percentage": lost_percentage,
        **stats,
    }


def ndr(
    client: trex.STLClient,
    ports: list[int],
    precision_bps: float,
    threshold: float,
    wait_time_s: int,
    duration_s: int,
    rx_delay_ms: int,
) -> list[dict]:
    log = []
    iteration: int = 0

    # get the maximum transmission speed of TRex to use as upper bound, this also warms up the system
    warmup_result = measure(client, ports, duration_s, rx_delay_ms, rate="100%")

    warmup_tx_bits = warmup_result["stats"]["total"]["obytes"] * 8
    warmup_duration_s = warmup_result["actual_duration_ms"] / 1000

    lower_bps: int = 0
    upper_bps: int = math.floor(warmup_tx_bits / warmup_duration_s)

    warmup_stats = {
        "precision_bps": precision_bps,
        "threshold": threshold,
        "wait_time_s": wait_time_s,
        "iteration": iteration,
        "lower_bps": lower_bps,
        "upper_bps": upper_bps,
        **warmup_result,
    }
    log.append(warmup_stats)

    while (upper_bps - lower_bps) > precision_bps:
        iteration += 1

        # Calculate middle point
        rate_bps = math.floor((lower_bps + upper_bps) / 2)
        rate_str = str(rate_bps) + "bps"

        # Wait then run
        time.sleep(wait_time_s)
        result = measure(client, ports, duration_s, rx_delay_ms, rate=rate_str)

        # Adjust bounds
        if result["lost_percentage"] > threshold:
            upper_bps = rate_bps
        else:
            lower_bps = rate_bps

        # Log
        stats = {
            "precision_bps": precision_bps,
            "threshold": threshold,
            "wait_time_s": wait_time_s,
            "iteration": iteration,
            "lower_bps": lower_bps,
            "upper_bps": upper_bps,
            **result,
        }
        log.append(stats)

    return log


def port_list(astring: str) -> list[int]:
    ports = [int(port.strip()) for port in astring.split(",")]

    if len(ports) % 2 != 0:
        raise argparse.ArgumentTypeError(
            f"odd number of ports was provided: {astring}. ports should appear in pairs"
        )

    return ports


def pad_packet(unpadded, size: int):
    size = size - 4  # deduct Ethernet FCS
    pad_size = max(0, size - len(unpadded))
    pad = "\0" * pad_size
    return unpadded / pad


def get_builtin_profile(packet_size: int):
    pkt = Ether() / IP(src="10.0.1.1", dst="10.0.0.0") / UDP(sport=2048, dport=2048)
    pkt = pad_packet(pkt, packet_size)

    multi_dst_vm = trex.STLScVmRaw(
        [
            trex.STLVmFlowVar(
                "dst",
                min_value="10.0.0.0",  # pyright: ignore[reportArgumentType]
                max_value="10.0.0.255",  # pyright: ignore[reportArgumentType]
                size=4,
                step=1,
                op="inc",
            ),
            trex.STLVmWrFlowVar("dst", pkt_offset="IP.dst"),
            trex.STLVmFixIpv4(offset="IP"),
        ],
        cache_size=256,  # It will only produce the first 256 packets following the VM rules and cache them
    )

    # Stream that will put pressure on the system. The rate is affected by multipliers
    pressure_stream = trex.STLStream(
        packet=trex.STLPktBuilder(pkt, vm=multi_dst_vm),
        mode=trex.STLTXCont(pps=1),
    )

    # Stream with latency information and fixed rate of 1000pps, for gathering latency statistics
    latency_stream = trex.STLStream(
        packet=trex.STLPktBuilder(pkt),
        mode=trex.STLTXCont(pps=1000),
        flow_stats=trex.STLFlowLatencyStats(pg_id=0),
    )

    return trex.STLProfile([pressure_stream, latency_stream])


def get_args():
    parser = argparse.ArgumentParser(description="Find the Non Drop Rate using TRex")
    parser.add_argument(
        "--ports",
        type=port_list,
        default="0,1",
        help="""
            comma separated list of ports.
            They should appear in pairs, the first of each pair will be used to transmit and the second to receive traffic.
            Ex: 0,1,1,0 to transmit bidirectional traffic. (default: %(default)s)
            """,
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1,
        help="maximum percentage of lost packets (default: %(default)s)",
    )
    parser.add_argument(
        "--precision",
        type=float,
        default=512,
        help="precision in bits per second of the rate (default: %(default)s)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=5,
        help="duration in seconds to wait before each iteration (default: %(default)s)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="duration in seconds of each iteration (default: %(default)s)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=200,
        help="""
        time to wait (in milliseconds) after last packet was sent, until RX filters used for measuring flow statistics and latency are removed.
        This value should reflect the time it takes packets which were transmitted to arrive to the destination.
        After this time, RX filters will be removed, and packets arriving for per flow statistics feature and latency flows will be counted as errors (default: %(default)s)
        """,
    )
    parser.add_argument(
        "--results",
        type=str,
        default="result.json",
        help="file where the results will be saved in json format (default: %(default)s)",
    )
    profile_group = parser.add_mutually_exclusive_group()
    profile_group.add_argument(
        "--size",
        type=int,
        default=64,
        help="packet size in bytes for the builtin traffic profile (default: %(default)s)",
    )
    profile_group.add_argument(
        "--profile",
        type=str,
        help="path to python file with the traffic profile to be used instead of the builtin one",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    client = trex.STLClient(verbose_level="none")

    if args.profile is not None:
        try:
            profile = trex.STLProfile.load(args.profile)
        except trex.TRexError as err:
            print(f"Error loading profile: {err}", file=sys.stderr)
            exit(1)
    else:
        profile = get_builtin_profile(args.size)

    try:
        client.connect()
    except trex.TRexError as err:
        print(f"Error connecting to TRex server: {err}", file=sys.stderr)
        exit(1)

    try:
        client.reset()
        client.add_streams(streams=profile, ports=args.ports[::2])
        results = ndr(
            client=client,
            ports=args.ports,
            precision_bps=args.precision,
            threshold=args.threshold,
            wait_time_s=args.wait,
            duration_s=args.duration,
            rx_delay_ms=args.delay,
        )
    except trex.TRexError as err:
        print(f"Error in TRex: {err}", file=sys.stderr)
        exit(1)
    except KeyboardInterrupt:
        print("Received Ctrl+c, exiting", file=sys.stderr)
        exit(1)
    finally:
        client.disconnect(stop_traffic=True, release_ports=True)

    with open(args.results, "w") as f:
        json.dump(results, f)
