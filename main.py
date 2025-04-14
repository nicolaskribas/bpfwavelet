import argparse
import json
import math
import sys
import time

sys.path.append("/opt/trex/current/trex_client/interactive")
import trex.stl.api as trex


def get_full_stats(client: trex.STLClient, ports: set[str]):
    return {
        "stats": client.get_stats(list(ports)),
        "xstats": {port: client.get_xstats(int(port)) for port in ports},
        "pgid": client.get_pgid_stats(),
        "util": client.get_util_stats(),
    }


def measure(client: trex.STLClient, ports: list[str], duration_s: int, rate: str):
    duration_timeout_s = duration_s * 2
    rx_delay_ms = 200

    client.clear_stats(
        ports=list(set(ports)),
        clear_global=True,
        clear_flow_stats=True,
        clear_latency_stats=True,
        clear_xstats=True,
    )

    client.start(ports[::2], mult=rate, duration=duration_s)
    start_time_ns = time.monotonic_ns()

    try:
        client.wait_on_traffic(timeout=duration_timeout_s, rx_delay_ms=rx_delay_ms)
        stoped_early = False
    except trex.TRexTimeoutError:
        client.stop(ports[::2], rx_delay_ms=rx_delay_ms)
        stoped_early = True
    finally:
        actual_duration_ns = time.monotonic_ns() - start_time_ns

    stats = get_full_stats(client, set(ports))

    # Calculate metrics
    tx = stats["stats"]["total"]["opackets"]
    rx = stats["stats"]["total"]["ipackets"]
    lost: int = tx - rx
    lost_percentage: float = lost / tx * 100

    return {
        "rate": rate,
        "lost": lost,
        "lost_percentage": lost_percentage,
        "expected_duration_ms": duration_s * 1000,
        "duration_timeout_ms": duration_timeout_s * 1000,
        "actual_duration_ms": actual_duration_ns / 1000000,
        "rx_delay_ms": rx_delay_ms,
        "stoped_early": stoped_early,
        **stats,
    }


def ndr(
    client: trex.STLClient,
    ports: list[str],
    precision: float,
    threshold: float,
    duration_s: int,
):
    log = []

    # get the maximum transmission speed of TRex to use as upper bound, this also warms up the system
    warmup_result = measure(client, ports, duration_s, rate="100%")
    warmup_stats = {
        "iteration": 0,
        "lower_bps": 0,
        "upper_bps": 0,
        **warmup_result,
    }
    log.append(warmup_stats)

    # use max tx from first measure as upper bound
    lower_bps: int = 0
    upper_bps: int = math.floor(
        (warmup_stats["stats"]["total"]["obytes"] * 8)
        / (warmup_stats["actual_duration_ms"] / 1000)
    )
    # upper_bps: int = math.floor(
    #     (warmup_stats["stats"]["total"]["obytes"] * 8) / duration_s
    # )

    iteration: int = 0
    while (upper_bps - lower_bps) > precision:
        iteration += 1

        # Calculate middle point
        rate_bps = math.floor((lower_bps + upper_bps) / 2)

        # Wait then run
        time.sleep(5)
        result = measure(client, ports, duration_s, rate=str(rate_bps) + "bps")

        # Log
        stats = {
            "iteration": iteration,
            "lower_bps": lower_bps,
            "upper_bps": upper_bps,
            **result,
        }
        log.append(stats)

        print(f"iteration: {iteration}")
        print(f"lower_bps: {lower_bps} upper_bps: {upper_bps}")
        print(f"lost: {stats['lost']} lost_percentage: {stats['lost_percentage']}")

        # Adjust bounds
        if stats["lost_percentage"] > threshold:
            upper_bps = rate_bps
        else:
            lower_bps = rate_bps

    # ndr = lower_bps
    return log


def port_list(astring):
    ports = [port.strip() for port in astring.split(",")]

    if len(ports) % 2 != 0:
        raise argparse.ArgumentTypeError(
            f"odd number of ports was provided: {astring}. ports should appear in pairs"
        )

    return ports


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
        default=100,
        help="precision in bps of the rate (default: %(default)s)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="udp_1pkt_simple.py",
        help="path to python file with the traffic profile (default: %(default)s)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="duration in seconds of each iteration (default: %(default)s)",
    )
    parser.add_argument(
        "--results",
        type=str,
        default="result.json",
        help="file where the results will be saved in json format (default: %(default)s)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    client = trex.STLClient(verbose_level="none")

    try:
        profile = trex.STLProfile.load(args.profile)
    except trex.TRexError as err:
        print(f"Error loading profile: {err}", file=sys.stderr)
        exit(1)

    try:
        client.connect()
    except trex.TRexError as err:
        print(f"Error connecting to TRex server: {err}", file=sys.stderr)
        exit(1)

    try:
        client.reset()
        client.add_streams(streams=profile, ports=args.ports[::2])
        results = ndr(client, args.ports, args.precision, args.threshold, args.duration)
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
