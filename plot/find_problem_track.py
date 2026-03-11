import argparse
import os

import numpy as np
import pandas as pd


def _metric_column(metric):
    if metric == "max_abs_edep_dot":
        return "edep_dot"
    if metric == "max_abs_stepLength_dot":
        return "stepLength_dot"
    if metric == "max_abs_EKin_dot":
        return "EKin_dot"
    if metric == "var_edep_dot":
        return "edep_dot"
    raise ValueError("unknown metric")


def _update_max(metric_series, max_map):
    for key, val in metric_series.items():
        prev = max_map.get(key)
        if prev is None or val > prev:
            max_map[key] = val


def _compute_track_scores(path, metric, chunksize):
    col = _metric_column(metric)
    usecols = ["event", "trackID", col]
    max_map = {}
    sum_map = {}
    sumsq_map = {}
    count_map = {}

    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize):
        chunk = chunk.dropna(subset=["event", "trackID", col])
        if len(chunk) == 0:
            continue
        if metric.startswith("max_abs"):
            chunk["_abs"] = chunk[col].abs()
            g = chunk.groupby(["event", "trackID"])["_abs"].max()
            _update_max(g, max_map)
        elif metric == "var_edep_dot":
            g_sum = chunk.groupby(["event", "trackID"])[col].sum()
            chunk["_sq"] = chunk[col] * chunk[col]
            g_sumsq = chunk.groupby(["event", "trackID"])["_sq"].sum()
            g_count = chunk.groupby(["event", "trackID"])[col].size()
            for key, val in g_sum.items():
                sum_map[key] = sum_map.get(key, 0.0) + val
            for key, val in g_sumsq.items():
                sumsq_map[key] = sumsq_map.get(key, 0.0) + val
            for key, val in g_count.items():
                count_map[key] = count_map.get(key, 0) + int(val)
        else:
            raise ValueError("unknown metric")

    if metric.startswith("max_abs"):
        rows = [
            {"event": k[0], "trackID": k[1], "score": v}
            for k, v in max_map.items()
        ]
        return pd.DataFrame(rows)

    rows = []
    for key, count in count_map.items():
        if count == 0:
            continue
        s = sum_map.get(key, 0.0)
        ss = sumsq_map.get(key, 0.0)
        var = ss / count - (s / count) ** 2
        rows.append({"event": key[0], "trackID": key[1], "score": var})
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Find track with largest derivative metric in micro_audit CSV."
    )
    parser.add_argument("csv", help="Path to micro_audit CSV file.")
    parser.add_argument(
        "--metric",
        default="max_abs_edep_dot",
        choices=[
            "max_abs_edep_dot",
            "max_abs_stepLength_dot",
            "max_abs_EKin_dot",
            "var_edep_dot",
        ],
        help="Metric used to rank tracks.",
    )
    parser.add_argument("--top", type=int, default=10, help="Top N tracks to show.")
    parser.add_argument(
        "--chunksize",
        type=int,
        default=200000,
        help="CSV chunk size for streaming.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional CSV output path for full ranking.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        raise SystemExit(f"missing file: {args.csv}")

    df = _compute_track_scores(args.csv, args.metric, args.chunksize)
    if len(df) == 0:
        raise SystemExit("no rows found")

    df = df.sort_values("score", ascending=False)
    print(df.head(args.top).to_string(index=False))
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
