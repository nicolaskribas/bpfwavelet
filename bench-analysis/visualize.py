# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "matplotlib==3.10.7",
#     "pandas==2.3.3",
#     "scienceplots==2.1.1",
# ]
# ///

import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import glob
    import json
    import re
    import matplotlib.patches as mpatches

    import numpy as np
    import pandas as pd
    import scienceplots
    import matplotlib.pyplot as plt
    import marimo as mo
    from pandas import DataFrame
    return DataFrame, glob, json, mo, mpatches, np, pd, plt, re


@app.cell
def _(DataFrame, glob, json, pd, re):
    # Load results

    results_folder = "../bench/results"

    # results/<tag>/<timestamp>/<size>.json
    file_patter = re.compile(f"{results_folder}/([^/]+)/([^/]+)/([^/]+).json")
    file_glob = f"{results_folder}/*/*/*.json"


    def json_into_df(file_path: str) -> DataFrame:
        match = file_patter.fullmatch(file_path)
        if match is None:
            raise

        with open(file_path) as file:
            data = json.load(file)

        df = pd.json_normalize(data)
        df["tag"] = match.group(1)
        df["timestamp"] = match.group(2)
        df["size"] = int(match.group(3))
        df["tag/timestamp"] = df["tag"] + "/" + df["timestamp"]
        return df


    def get_all_results():
        jsons = glob.glob(file_glob)
        dfs = map(json_into_df, jsons)
        return pd.concat(dfs, ignore_index=True).copy()
    return (get_all_results,)


@app.cell
def _(get_all_results):
    # Derive metrics
    # creates new column 'rate_bps' with the integer value of 'rate'
    # most of the rows have a 'rate' like 123456bps, a minority have 'rate' like 100%, the later is converted to None
    def fix(row):
        try:
            return int(row.rate.removesuffix("bps"))
        except ValueError:
            return None


    df = get_all_results()

    df["rate_bps"] = df.apply(fix, axis=1)
    df[["interval", "level"]] = df["tag"].str.extract(r"^bpfwavelet-(\d+)-(\d+)$")
    df = df.astype({"interval": "UInt64", "level": "UInt8"})

    prog = df["tag"].str.extract(r"^(bpfwavelet)-\d+-\d+$|^(.*)$")
    df["prog"] = prog[0].fillna(prog[1])

    # older measurements doesn't have a 'stage', so they have the value None in this column.
    # 'stage' where added when we added the repetition stage, before that the first iteration were the warmup measure
    # and subsequent ones were searching
    df.loc[df["stage"].isna() & (df["iteration"] == 0), "stage"] = "warmup"
    df.loc[df["stage"].isna() & (df["iteration"] != 0), "stage"] = "search"

    # older measurements doesn't have the repetitions number, so we should set them to zero
    df["repetitions"] = df["repetitions"].fillna(0).astype(int)

    df["rate_gbps"] = df["rate_bps"] / 1000**3

    df["actual_duration_s"] = df["actual_duration_ms"] / 1000

    df["pps_out"] = df["stats.total.opackets"] / df["actual_duration_s"]
    df["mpps_out"] = df["pps_out"] / 1000000

    df["pps"] = df["stats.total.ipackets"] / df["actual_duration_s"]
    df["mpps"] = df["pps"] / 1000000

    df["actual_rate_bps_out"] = (
        df["stats.total.obytes"] * 8 / df["actual_duration_s"]
    )
    df["actual_rate_gbps_out"] = df["actual_rate_bps_out"] / 1000**3

    df["actual_rate_bps"] = df["stats.total.ibytes"] * 8 / df["actual_duration_s"]
    df["actual_rate_gbps"] = df["actual_rate_bps"] / 1000**3

    df["actual_rate_gbps_from_pps"] = (df["pps"] * (df["size"] * 8)) / 1000000000

    df["gap"] = df["actual_rate_bps_out"] / df["rate_bps"] * 100
    return (df,)


@app.cell
def _(df):
    df
    return


@app.cell
def _(df):
    df[
        (df["timestamp"] == "2025-09-15T15:58:30-03:00")
        & (df["stage"] != "repeat")
        & (df["size"] == 1024)
    ]
    return


@app.cell
def _(df, mo):
    timestamp = mo.ui.dropdown(sorted(df["timestamp"].unique()))
    timestamp
    return (timestamp,)


@app.cell
def _(df, mo):
    tag = mo.ui.dropdown(df["tag"].unique())
    tag
    return (tag,)


@app.cell
def _(df, mo):
    size = mo.ui.dropdown(df["size"].unique())
    size
    return (size,)


@app.cell
def _(df, size, tag, timestamp):
    df[
        (df["timestamp"] == timestamp.value)
        & (df["stage"] == "repeat")
        & (df["tag"] == tag.value)
        & (df["size"] == size.value)
    ][
        [
            "pgid.latency.0.latency.average",
            "pgid.latency.0.latency.jitter",
            "pgid.flow_stats.0.rx_pkts.0",
            "pgid.flow_stats.0.tx_pkts.0",
            "pgid.latency.0.latency.total_min",
            "pgid.latency.0.latency.total_max",
        ]
    ]
    return


@app.cell
def _(df, timestamp):
    df_latency = (
        df[(df["timestamp"] == timestamp.value) & (df["stage"] == "repeat")]
        .groupby(["tag", "size"])[
            ["pgid.latency.0.latency.jitter", "pgid.latency.0.latency.average"]
        ]
        .agg(["mean", "std"])
        .reset_index()
    )
    return


@app.function
def aggregate(dataf):
    return (
        dataf[(dataf["stage"] == "repeat")]
        .groupby(
            ["timestamp", "tag", "prog", "interval", "level", "size"],
            dropna=False,
        )[
            [
                "pgid.latency.0.latency.jitter",
                "pgid.latency.0.latency.average",
                "actual_rate_gbps_from_pps",
                "actual_rate_gbps",
                "mpps",
                # "",
            ]
        ]
        .agg(["mean", "std", "count"])
        .reset_index()
    )


@app.cell
def _(df):
    df_agg = df.pipe(aggregate)
    return (df_agg,)


@app.cell
def _(df_agg, plt):
    plt.rcdefaults()
    plt.style.use(["science", "ieee", "notebook"])
    a = df_agg[df_agg["timestamp"] == "2025-09-15T15:58:30-03:00"][
        [
            "tag",
            "size",
            "prog",
            "interval",
            "level",
            "actual_rate_gbps",
        ]
    ].sort_values(
        by=["size", "prog", "interval", "level"],
        ascending=[True, False, True, True],
    )

    fig, ax = plt.subplots()

    ax.errorbar(
        a["tag"] + a["size"].astype(str),
        a["actual_rate_gbps"]["mean"],
        a["actual_rate_gbps"]["std"],
    )

    plt.show()
    return


@app.cell
def _(df_agg, np, plt):
    plt.rcdefaults()
    plt.style.use(["science", "grid", "ieee"])


    def plot_rate(interval):
        fig, ax = plt.subplots()

        level = 32

        xticklabels = df_agg[(df_agg["timestamp"] == "2025-09-15T15:58:30-03:00")][
            "size"
        ].unique()
        xticks = np.arange(len(xticklabels))
        # base
        base_rate = df_agg[
            (df_agg["timestamp"] == "2025-09-15T15:58:30-03:00")
            & (df_agg["prog"] == "xdp-bench-tx")
        ].sort_values(by="size")["actual_rate_gbps"]
        ax.errorbar(xticks, base_rate["mean"], base_rate["std"], label="Baseline")

        # signal only
        signal_rate = df_agg[
            (df_agg["timestamp"] == "2025-09-15T15:58:30-03:00")
            & (df_agg["prog"] == "bpfwavelet")
            & (df_agg["level"] == 0)
            & (df_agg["interval"] == interval)
        ].sort_values(by="size")["actual_rate_gbps"]
        ax.errorbar(
            xticks, signal_rate["mean"], signal_rate["std"], label="Signal-only"
        )

        # levels
        decomposition_rate = df_agg[
            (df_agg["timestamp"] == "2025-09-15T15:58:30-03:00")
            & (df_agg["prog"] == "bpfwavelet")
            & (df_agg["level"] == level)
            & (df_agg["interval"] == interval)
        ].sort_values(by="size")["actual_rate_gbps"]
        ax.errorbar(
            xticks,
            decomposition_rate["mean"],
            decomposition_rate["std"],
            label="Algorithm 1",
        )

        overhead = (
            (base_rate["mean"].to_numpy() - signal_rate["mean"].to_numpy())
            / base_rate["mean"].to_numpy()
        ) * 100
        print(overhead)

        # for utag in df_ts["tag"].unique():
        #     actual_rate_gbps = df_ts[df_ts["tag"] == utag]["actual_rate_gbps"]
        #     ax.errorbar(
        #         xticks,
        #         actual_rate_gbps["mean"],
        #         actual_rate_gbps["std"],
        #         label=utag,
        #     )

        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)
        ax.xaxis.minorticks_off()
        ax.set_xlabel("Packet size (bytes)")

        ax.set_ylim(bottom=0)
        ax.set_ylabel("Throughput (Gbit/s)")
        ax.legend(loc="lower right")

        plt.show()
        # fig.savefig(f"rate-plot-{interval}-{level}.pdf")


    plot_rate(250000)
    plot_rate(1000000000)
    return


@app.cell
def _(df_agg, mpatches, pd, plt):
    plt.rcdefaults()
    plt.style.use(["science", "grid", "ieee", "bright"])


    def plot_rate_size(size):
        interval = 250000
        # base_rate = df_agg[
        #     (df_agg["timestamp"] == "2025-09-15T15:58:30-03:00")
        #     # & (df_agg["prog"] == "xdp-bench-tx")
        #     & (df_agg["interval"] == interval)
        #     & (df_agg["size"] == size)
        # ]

        base_rate = df_agg[
            (df_agg["timestamp"] == "2025-09-15T15:58:30-03:00")
            # & (df_agg["prog"] == "xdp-bench-tx")
            & (
                (df_agg["interval"] == interval)
                | (df_agg["prog"] == "xdp-bench-tx")
            )
            & (df_agg["size"] == size)
        ].sort_values(by=["prog", "level"], ascending=[False, True])

        fig, ax = plt.subplots()

        def coloring(x):
            match x:
                case ("xdp-bench-tx", _):
                    return "k"
                case (_, 0):
                    return "r"
                case (_, _):
                    return "b"

        colors = [
            coloring((prog, level))
            for prog, level in zip(base_rate["prog"], base_rate["level"])
        ]

        ax.bar(
            base_rate["tag"],
            base_rate["mpps"]["mean"],
            yerr=base_rate["mpps"]["std"],
            color=colors,
        )
        black_patch = mpatches.Patch(color="k", label="Baseline")
        red_patch = mpatches.Patch(color="r", label="Signal-only")
        green_patch = mpatches.Patch(color="b", label="Algorithm 1")

        # Add the legend to the plot using the handles
        ax.legend(handles=[black_patch, red_patch, green_patch])

        ax.set_ylabel("Throughput (Mpps)")

        ax.xaxis.minorticks_off()
        # ax.xaxis.majorticks_off()
        ax.set_xlabel("Decomposition levels")
        ax.set_xticks(base_rate["tag"])
        ax.set_xticklabels(["" if pd.isna(x) else x for x in base_rate["level"]])
        if size == 1518:
            ax.set_ylim(top=9)

        plt.show()
        # fig.savefig(f"rate-plot-size-{size}-{interval}.pdf")


    for s in df_agg[df_agg["timestamp"] == "2025-09-15T15:58:30-03:00"][
        "size"
    ].unique():
        plot_rate_size(s)
    return


if __name__ == "__main__":
    app.run()
