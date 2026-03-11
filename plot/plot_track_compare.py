import argparse
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm, Normalize
from matplotlib.ticker import NullFormatter, SymmetricalLogLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
import mplhep as hep
from matplotlib.patches import FancyArrowPatch
from matplotlib.ticker import MaxNLocator

plt.style.use(hep.style.ROOT)
plt.style.use("style.mplstyle")

LABELS = {
    "edep_dot": r"$\mathit{E}_{\mathrm{dep}}$ derivative ($\left|\partial \mathit{E}_{\mathrm{dep}} / \partial \mathit{\alpha}\right|$) [MeV mm$^{-1}$]",
    "EKin_dot": r"Kinetic energy derivative ($\partial E_{kin} / \partial \alpha$)",
    "stepLength_dot": r"Step length derivative ($\partial L / \partial \alpha$)",
}

def _load_track(path, event, track_id, axis, observable):
    cols = [
        "event",
        "trackID",
        "step",
        "gX",
        "gY",
        "gZ",
        "gX_pre",
        "gY_pre",
        "gZ_pre",
        "onBoundary",
        "is_stopgrad",
        observable,
    ]
    cols = [c for c in cols if c != observable] + [observable]
    df = pd.read_csv(path, usecols=lambda c: c in cols)
    df = df[(df["event"] == event) & (df["trackID"] == track_id)].copy()
    if len(df) == 0:
        raise ValueError(f"no rows for event={event}, trackID={track_id} in {path}")
    df = df.sort_values("step").reset_index(drop=True)
    if "gX" not in df.columns:
        df["gX"] = df["gX_pre"]
    if "gY" not in df.columns:
        df["gY"] = df["gY_pre"]
    if "gZ" not in df.columns:
        df["gZ"] = df["gZ_pre"]
    xcol, ycol = ("gX", "gY") if axis == "xy" else ("gX", "gZ")
    return df, xcol, ycol


def _make_segments(df, xcol, ycol):
    pts = np.column_stack([df[xcol].values, df[ycol].values])
    if len(pts) < 2:
        return np.empty((0, 2, 2))
    return np.stack([pts[:-1], pts[1:]], axis=1)


def _auto_pick_track(path, metric):
    col = "edep_dot" if metric == "max_abs_edep_dot" else "stepLength_dot"
    usecols = ["event", "trackID", col]
    best_score = None
    best_key = None
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=200000):
        chunk = chunk.dropna(subset=["event", "trackID", col])
        if len(chunk) == 0:
            continue
        chunk["_abs"] = chunk[col].abs()
        g = chunk.groupby(["event", "trackID"])["_abs"].max()
        for key, val in g.items():
            if best_score is None or val > best_score:
                best_score = val
                best_key = key
    if best_key is None:
        raise ValueError("no rows found for auto-pick")
    return best_key[0], best_key[1]


def _apply_style():
    here = os.path.dirname(os.path.abspath(__file__))
    style_path = os.path.join(here, "style.mplstyle")
    if os.path.exists(style_path):
        plt.style.use(style_path)


def _boundary_lines(xmin, xmax, base, offset):
    if xmin > xmax:
        xmin, xmax = xmax, xmin
    start = int(np.floor((xmin - offset) / base)) - 1
    end = int(np.ceil((xmax - offset) / base)) + 1
    lines = []
    for n in range(start, end + 1):
        for x in (base * n, base * n + offset):
            if xmin <= x <= xmax:
                lines.append(x)
    return sorted(lines)


def _add_arrows(ax, df, xcol, ycol, step_stride):
    if len(df) < 2:
        return
    dx = df[xcol].diff().values
    dy = df[ycol].diff().values
    xs = df[xcol].values
    ys = df[ycol].values
    step_len = np.hypot(dx, dy)
    finite = np.isfinite(step_len)
    if not np.any(finite):
        return
    med = np.nanmedian(step_len[finite])
    min_len = 0.001 * med
    max_len = 2.0 * med
    xspan = np.nanmax(xs) - np.nanmin(xs)
    yspan = np.nanmax(ys) - np.nanmin(ys)
    head_w = 0.04 * max(xspan, yspan)
    head_l = 0.04 * max(xspan, yspan)
    for i in range(1, len(step_len), step_stride):
        arrow_len = step_len[i]
        if step_len[i] < 0.05:
            continue
        ux = dx[i] / step_len[i]
        uy = dy[i] / step_len[i]
        center_x = xs[i]
        center_y = ys[i]
        start_x = center_x - dx[i]*1.5 #* 0.5
        start_y = center_y - dy[i]*1.5 #* 0.5
        arrow = FancyArrowPatch(
            (start_x, start_y),
            (start_x + ux * arrow_len, start_y + uy * arrow_len),
            arrowstyle="-|>",
            mutation_scale=22.0,
            linewidth=0.0,
            facecolor="black",
            edgecolor="none",
            alpha=0.6,
            zorder=5,
        )
        ax.add_patch(arrow)


def _add_stopgrad_marks(ax, df, xcol, ycol):
    if "is_stopgrad" not in df.columns:
        return
    marks = np.where(df["is_stopgrad"].values == 1)[0].tolist()
    if not marks:
        return
    xs = df[xcol].values
    ys = df[ycol].values
    xspan = np.nanmax(xs) - np.nanmin(xs)
    yspan = np.nanmax(ys) - np.nanmin(ys)
    seg_len = 0.06 * max(xspan, yspan)

    for idx in marks:
        if idx <= 0 or idx >= len(df):
            print("Skipping mark at index", idx)
            continue
        dx = xs[idx] - xs[idx - 1]
        dy = ys[idx] - ys[idx - 1]
        norm = np.hypot(dx, dy)
        if norm == 0:
            print("[norm] Skipping mark at index", idx)
            continue
        ux = -dy / norm
        uy = dx / norm
        x0 = xs[idx] - ux * seg_len * 0.5
        x1 = xs[idx] + ux * seg_len * 0.5
        y0 = ys[idx] - uy * seg_len * 0.5
        y1 = ys[idx] + uy * seg_len * 0.5
        print("Adding marks")
        ax.plot([x0, x1], [y0, y1], color="red", lw=25.0, alpha=0.9, zorder=6)
        return

def main():
    parser = argparse.ArgumentParser(
        description="Plot side-by-side track steps for stopgrad vs no-stopgrad."
    )
    parser.add_argument("--nostop", required=True, help="No-stopgrad CSV path.")
    parser.add_argument("--stop", required=True, help="Stopgrad CSV path.")
    parser.add_argument("--event", type=int, default=None, help="Event ID.")
    parser.add_argument("--track-id", type=int, default=None, help="Track ID.")
    parser.add_argument(
        "--auto-track",
        action="store_true",
        help="Pick track with max abs edep_dot from the no-stop file.",
    )
    parser.add_argument(
        "--axis",
        default="xy",
        choices=["xy", "xz"],
        help="Plot axis choice.",
    )
    parser.add_argument(
        "--observable",
        default="edep_dot",
        help="Observable used for color and step series.",
    )
    parser.add_argument(
        "--abs",
        dest="abs_value",
        action="store_true",
        help="Use absolute value of observable for color scaling.",
    )
    parser.add_argument(
        "--color-scale",
        default="log",
        choices=["log", "linear"],
        help="Color normalization for top panels.",
    )
    parser.add_argument(
        "--boundary-x",
        type=float,
        action="append",
        default=[],
        help="Repeatable x positions for boundary lines.",
    )
    parser.add_argument(
        "--boundary-period",
        type=float,
        default=8.0,
        help="Boundary period for auto lines.",
    )
    parser.add_argument(
        "--boundary-offset",
        type=float,
        default=2.3,
        help="Boundary offset for auto lines (8n + offset).",
    )
    parser.add_argument(
        "--auto-boundaries",
        action="store_true",
        help="Draw boundary lines at n*period and n*period+offset.",
    )
    parser.add_argument(
        "--arrow-stride",
        type=int,
        default=4,
        help="Step stride for drawing direction arrows.",
    )
    parser.add_argument(
        "--output",
        default="track_compare.png",
        help="Output image filename.",
    )
    parser.add_argument(
        "--no-step-panel",
        action="store_true",
        help="Only plot event displays (no derivative vs step panels).",
    )
    args = parser.parse_args()

    if args.auto_track:
        event, track_id = _auto_pick_track(args.nostop, "max_abs_edep_dot")
    else:
        if args.event is None or args.track_id is None:
            raise SystemExit("Provide --event and --track-id or use --auto-track")
        event = args.event
        track_id = args.track_id

    _apply_style()

    d0, xcol, ycol = _load_track(args.nostop, event, track_id, args.axis, args.observable)
    d1, _xcol, _ycol = _load_track(args.stop, event, track_id, args.axis, args.observable)

    def drop_edge_tick(ax, side="right", tol=1e-10):
        ax.figure.canvas.draw()  # make sure ticks are finalized

        ticks = np.asarray(ax.get_xticks())
        lo, hi = ax.get_xlim()
        lo, hi = (lo, hi) if lo <= hi else (hi, lo)

        inside = ticks[(ticks >= lo - tol) & (ticks <= hi + tol)]
        if inside.size < 2:
            return

        drop = inside.max() if side == "right" else inside.min()
        keep = ticks[np.abs(ticks - drop) > tol]
        ax.set_xticks(keep)

    def make_norm(vals):
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            raise SystemExit("no finite observable values")
        if args.color_scale == "log":
            positive = vals[vals > 0]
            vmin = np.min(positive) if len(positive) else 1e-8
            vmax = np.max(positive) if len(positive) else 1.0
            return LogNorm(vmin=max(vmin, 1e-12), vmax=max(vmax, vmin * 10.0))
        vmin, vmax = float(np.min(vals)), float(np.max(vals))
        return Normalize(vmin=vmin, vmax=vmax)

    if args.no_step_panel:
        fig, axes = plt.subplots(
            1,
            2,
            figsize=(14, 7),
            sharex=False,
            sharey=True,
            gridspec_kw={"wspace": 0.0},
            #constrained_layout=True,
        )
        ax_event_no, ax_event_stop = axes
        ax_deriv_no = None
        ax_deriv_stop = None
    else:
        fig, axes = plt.subplots(
            2,
            2,
            figsize=(11, 8),
            sharex="col",
            gridspec_kw={"hspace": 0.0, "wspace": 0.28},
            #constrained_layout=True,
        )
        ax_event_no = axes[0, 0]
        ax_event_stop = axes[1, 0]
        ax_deriv_no = axes[0, 1]
        ax_deriv_stop = axes[1, 1]

    x_min = min(d0[xcol].min(), d1[xcol].min())
    x_max = max(d0[xcol].max(), d1[xcol].max())
    y_min = min(d0[ycol].min(), d1[ycol].min())
    y_max = max(d0[ycol].max(), d1[ycol].max())
    x_pad = 0.02 * (x_max - x_min) if x_max > x_min else 1.0
    y_pad = 0.02 * (y_max - y_min) if y_max > y_min else 1.0

    def plot_track(ax, df, title, show_xlabel, norm, inset_label):
        segments = _make_segments(df, xcol, ycol)
        vals = df[args.observable].values
        if args.abs_value:
            vals = np.abs(vals)
        if len(vals) > 1:
            vals = vals[:-1]
        lc = LineCollection(segments, array=vals, cmap="viridis", norm=norm, linewidths=2.0)
        ax.add_collection(lc)
        ax.scatter(df[xcol], df[ycol], s=8, color="black", alpha=0.2)
        if "onBoundary" in df.columns:
            onb = df["onBoundary"] == 1
            ax.scatter(df.loc[onb, xcol], df.loc[onb, ycol], s=12, color="white", edgecolor="black")
        ax.set_xlim(x_min - x_pad, x_max + x_pad)
        ax.set_ylim(y_min - y_pad, y_max + y_pad)
        for xb in args.boundary_x:
            ax.axvline(xb, color="black", lw=4.0, alpha=0.7, ls=":")
        if args.auto_boundaries:
            for xb in _boundary_lines(x_min, x_max, args.boundary_period, args.boundary_offset):
                ax.axvline(xb, color="black", lw=3.8, alpha=0.6, ls=":")
                ax.text(
                    xb + 0.02 * x_pad,
                    y_max - y_pad * 31,
                    r"boundary $x = b$",
                    rotation=90,
                    ha="right",
                    va="top",
                    fontsize=20,
                    color="black",
                    alpha=0.7,
                )

        if show_xlabel:
            ax.set_xlabel("x position [mm]")
        if not (args.no_step_panel and ax is ax_event_stop):
            ax.set_ylabel("y position [mm]" if args.axis == "xy" else "z position [mm]")
        else:
            ax.set_ylabel("")
        ax.set_title("")
        ax.set_aspect("auto")
        _add_arrows(ax, df, xcol, ycol, args.arrow_stride)
        #if inset_label == "Stop grad":
        #    _add_stopgrad_marks(ax, df, xcol, ycol)
        ax.text(
            0.4,
            0.95,
            inset_label,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=22,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
        )


        return lc

    vals0 = d0[args.observable].values
    vals1 = d1[args.observable].values
    if args.abs_value:
        vals0 = np.abs(vals0)
        vals1 = np.abs(vals1)
    norm = make_norm(np.concatenate([vals0, vals1]))

    lc0 = plot_track(ax_event_no, d0, "no stopgrad", show_xlabel=True, norm=norm, inset_label="Baseline")
    lc1 = plot_track(ax_event_stop, d1, "stopgrad", show_xlabel=True, norm=norm, inset_label="Stop grad")
    label = LABELS.get(args.observable, args.observable)
    if args.no_step_panel:
        divider = make_axes_locatable(ax_event_stop)
        cax = divider.append_axes("right", size="4%", pad=0.2)
        cbar = fig.colorbar(lc0, cax=cax, label=label)
        cbar.ax.set_ylabel(label)
    else:
        cbar = fig.colorbar(lc0, ax=[ax_event_no, ax_event_stop], label=label, pad=0.06)
        cbar.ax.set_ylabel(label)

    if not args.no_step_panel:
        ax_deriv_no.plot(d0["step"], d0[args.observable], lw=1.5)
        ax_deriv_stop.plot(d1["step"], d1[args.observable], lw=1.5)
        ax_deriv_no.set_title("")
        ax_deriv_stop.set_title("")
        ax_deriv_no.set_xlabel("")
        ax_deriv_stop.set_xlabel("step")
        ax_deriv_no.set_ylabel(label)
        ax_deriv_stop.set_ylabel(label)
        ax_deriv_no.set_yscale("symlog", linthresh=1e-3)
        ax_deriv_stop.set_yscale("symlog", linthresh=1e-3)
        #for ax in (ax_deriv_no, ax_deriv_stop):
        #    ax.yaxis.set_major_locator(SymmetricalLogLocator(base=10, linthresh=1e-3))
        #    ax.yaxis.set_minor_locator(SymmetricalLogLocator(base=10, linthresh=1e-3, subs=(0.1,)))
        #    ax.yaxis.set_minor_formatter(NullFormatter())
        #for ax in (ax_deriv_no, ax_deriv_stop):
        #    ax.yaxis.set_label_position("right")
        #    ax.yaxis.tick_right()
        step_max = max(d0["step"].max(), d1["step"].max())
        ax_deriv_no.set_xlim(0, step_max)
        ax_deriv_stop.set_xlim(0, step_max)
    else:
        #ax_event_no.tick_params(left=True, labelleft=True, right=False)
        #ax_event_no.yaxis.set_ticks_position("left")
        #ax_event_stop.tick_params(left=False, labelleft=False, right=False, labelright=False)
        #ax_event_stop.yaxis.set_ticks_position("none")
        #ax_event_stop.yaxis.set_ticks([])
        ax_event_no.spines["right"].set_visible(False)

    fig.tight_layout()
    if args.no_step_panel:
        fig.canvas.draw()
        ax_event_no.tick_params(axis="y", which="both", left=True, labelleft=True, right=False, labelright=False)
        ax_event_stop.tick_params(axis="y", which="both", left=False, labelleft=False, right=True, labelright=False)
        left_ticks = ax_event_no.get_xticks()
        right_ticks = ax_event_stop.get_xticks()
        #if len(left_ticks) > 1:
        #    ax_event_no.set_xticks(left_ticks[:-1])
        #    ax_event_no.set_xticklabels([f"{t:g}" for t in left_ticks[:-1]])
        #ax_event_stop.set_xlim(left_ticks[0],left_ticks[-1])
        ax_event_no.set_xticks(right_ticks[1:-1])
        #ax_event_no.set_xlim(ax_event_no.get_xlim()[0], ax_event_no.get_xlim()[1])     # drop rightmost

        #ax_event_no.xaxis.set_major_locator(MaxNLocator(prune="upper"))

        #ax_event_no.set_xticks(left_ticks[:-1])     # drop rightmost

        drop_edge_tick(ax_event_no,  side="right")  # drop boundary tick on left panel


        #ax_event_stop.set_xticks(right_ticks[1:])
        #ax_event_stop.set_xticklabels([f"{t:g}" for t in right_ticks[1:]])
        
    fig.savefig(args.output, dpi=150)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
