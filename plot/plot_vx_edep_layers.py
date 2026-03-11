import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import mplhep as hep

plt.style.use(hep.style.ROOT)
plt.style.use("style.mplstyle")

#import matplotlib as mpl
#mpl.rcParams["text.usetex"] = True

def main():
    parser = argparse.ArgumentParser(description="Plot edep fraction vs vx for all layers.")
    parser.add_argument("csv", help="Path to vx_edep_hist.csv")
    parser.add_argument("--output", default="vx_edep_layers.png", help="Output image filename")
    parser.add_argument("--use-frac", action="store_true", help="Plot edep_frac instead of edep")
    parser.add_argument("--logy", action="store_true", help="Log scale y-axis")
    parser.add_argument("--show-variance", action="store_true", help="Plot ±1σ bands using variance")
    parser.add_argument("--sem", action="store_true", help="Use standard error (sqrt(var / n_events))")
    args = parser.parse_args()

    path = Path(args.csv)
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")

    df = pd.read_csv(path)
    if not {"layer", "bin", "vx_low", "vx_high"}.issubset(df.columns):
        raise SystemExit("CSV must contain: layer, bin, vx_low, vx_high")

    if args.use_frac:
        if "mean_frac" in df.columns:
            ycol = "mean_frac"
            vcol = "var_frac"
        else:
            ycol = "edep_frac"
            vcol = None
    else:
        if "mean_edep" in df.columns:
            ycol = "mean_edep"
            vcol = "var_edep"
        else:
            ycol = "edep"
            vcol = None
    if ycol not in df.columns:
        raise SystemExit(f"CSV missing column: {ycol}")

    df["vx_center"] = 0.5 * (df["vx_low"] + df["vx_high"])
    layers = sorted(df["layer"].unique())
    n_layers = len(layers)
    cmap = plt.get_cmap("RdYlGn_r")

    fig, ax = plt.subplots()#figsize=(10, 6))
    for idx, layer in enumerate(layers):
        color = cmap(idx / max(n_layers - 1, 1))
        sub = df[df["layer"] == layer].sort_values("vx_center")
        ax.plot(sub["vx_center"], sub[ycol], color=color, alpha=0.6, lw=1.5)
        if args.show_variance and vcol and vcol in sub.columns:
            sigma = np.sqrt(sub[vcol].values)
            if args.sem and "n_events" in sub.columns:
                n = np.maximum(sub["n_events"].values, 1.0)
                sigma = sigma / np.sqrt(n)
            y = sub[ycol].values
            ax.fill_between(
                sub["vx_center"],
                y - sigma,
                y + sigma,
                color=color,
                alpha=0.15,
                linewidth=0,
            )

    ax.set_ylim(1e-3,1.) if args.logy else ax.set_ylim(0, None)
    ax.set_xlabel(r"Particle track direction $\mathit{v}_{\mathrm{x}}$")
    ax.set_ylabel(r"$\mathit{E}_{\mathrm{dep}}$ fraction" if args.use_frac else "Edep")
    if args.logy:
        ax.set_yscale("log")

    
    # Direction annotations
    y_annot = 0.1
    ax.annotate(
        "Backwards tracks",
        xy=(0.05, y_annot),
        xytext=(0.1, y_annot),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", lw=1.5, color="grey"),
        fontsize=15,
        color="grey",
        ha="left",
        va="center",
    )
    ax.annotate(
        "Forward tracks",
        xy=(0.95, y_annot),
        xytext=(0.9, y_annot),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", lw=1.5, color="grey"),
        fontsize=15,
        color="grey",
        ha="right",
        va="center",
    )

    # Legend handles for layer 0 and last
    ax.plot([], [], color=cmap(0.0), label=f"Layer {layers[0] + 1}")
    ax.plot([], [], color=cmap(1.0), label=f"Layer {layers[-1] + 1}")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(args.output, dpi=300)
    plt.savefig(args.output.replace("png","pdf"), dpi=300)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
