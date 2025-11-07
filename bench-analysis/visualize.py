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

    import pandas as pd
    import scienceplots
    import matplotlib.pyplot as plt
    import marimo as mo
    from pandas import DataFrame
    return DataFrame, glob, json, mo, pd, plt, re


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


    df = get_all_results()
    return (df,)


@app.cell
def _(df):
    # Derive metrics
    def fix(row):
        try:
            # creates new column 'rate_bps' with the integer value of 'rate'
            # most of the rows have a 'rate' like 123456bps, a minority have 'rate' like 100%, the later is converted to None
            return int(row.rate.removesuffix("bps"))
        except ValueError:
            return None


    df["rate_bps"] = df.apply(fix, axis=1)
    df.loc[df["stage"].isna() & (df["iteration"] == 0), "stage"] = "warmup"
    df.loc[df["stage"].isna() & (df["iteration"] != 0), "stage"] = "search"
    df["repetitions"] = df["repetitions"].fillna(0).astype(int)
    df["rate_gbps"] = df["rate_bps"] / 1000**3
    df["actual_duration_s"] = df["actual_duration_ms"] / 1000
    # older measurements doesn't have a 'stage', so they have the value None in this column.
    # 'stage' where added when we added the repetition stage, before that the first iteration were the warmup measure
    # and subsequent ones were searching
    df["pps_out"] = df["stats.total.opackets"] / df["actual_duration_s"]
    df["mpps_out"] = df["pps_out"] / 1000000
    df["pps"] = df["stats.total.ipackets"] / df["actual_duration_s"]
    # older measurements doesn't have the repetitions number, so we should set them to zero
    df["mpps"] = df["pps"] / 1000000
    df["actual_rate_bps_out"] = (
        df["stats.total.obytes"] * 8 / df["actual_duration_s"]
    )
    df["actual_rate_gbps_out"] = df["actual_rate_bps_out"] / 1000**3
    df["actual_rate_bps"] = df["stats.total.ibytes"] * 8 / df["actual_duration_s"]
    df["actual_rate_gbps"] = df["actual_rate_bps"] / 1000**3
    df["actual_rate_gbps_from_pps"] = df["mpps"] * df["size"]
    df["gap"] = df["actual_rate_bps_out"] / df["rate_bps"] * 100
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
    return (df_latency,)


@app.cell
def _(df):
    df_aggregated = (
        df[(df["stage"] == "repeat")]
        .groupby(["timestamp", "tag", "size"])[
            [
                "pgid.latency.0.latency.jitter",
                "pgid.latency.0.latency.average",
                "mpps",
            ]
        ]
        .agg(["mean", "std"])
        .reset_index()
    )
    return (df_aggregated,)


@app.cell
def _(df_aggregated, timestamp):
    df_aggregated[df_aggregated["timestamp"] == timestamp.value]
    return


@app.cell
def _(df_latency):
    df_latency
    return


@app.cell
def _(df_aggregated, plt, timestamp):
    plt.rcdefaults()
    plt.style.use(["science", "ieee", "grid", "notebook"])


    df_selected = df_aggregated[df_aggregated["timestamp"] == timestamp.value]

    fig, ax = plt.subplots()

    for utag in df_selected["tag"].unique():
        df_selectedd = df_selected[df_selected["tag"] == utag]

        ax.plot(df_selectedd["size"], df_selectedd["mpps"], label=utag)


    plt.show()
    return


if __name__ == "__main__":
    app.run()
