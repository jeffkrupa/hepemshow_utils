import numpy as np
import matplotlib.pyplot as plt
import glob
import os
import mplhep as hep
import tqdm
from matplotlib.colors import LogNorm

PLOT_DENSITY = True          # turn on density rendering
DENSITY_BINS = (220, 220)    # (x_bins, y_bins)
DENSITY_SIGMA = 2.0          # gaussian smoothing in *bin* units (try 1.5–3)
OVERLAY_RAW = True          # optionally still draw each trajectory

plt.style.use(hep.style.CMS)

# common constants
ROOT = "../optimizerun1_f0p05_moreepochs"
START = (25000.0, 5.0)
TARGET = (10000.0, 2.3)
MAX_EPOCHS = 150
SHOW_LANDSCAPE = True
SHOW_SEEDS = False
XMIN, XMAX = 5000.0, 30000.0
YMIN, YMAX = 1.,    7.

# find all training runs
#bases = sorted(glob.glob(os.path.join(ROOT, "seed_offset*")))
bases = sorted(
    os.path.join(ROOT, f"seed_offset{i}")
    for i in range(0, 100)
    if os.path.exists(os.path.join(ROOT, f"seed_offset{i}"))
)
fig, ax = plt.subplots(figsize=(15,10))

# pick a colormap with enough distinct colors
cmap = plt.get_cmap("tab20")

all_E = []
all_A = []

def plot_median_with_band(ax, trajs, n_bins=200, qlo=5, qhi=95,
                          path_kwargs=None, band_kwargs=None):
    """
    At fixed energy bins, measure the spread in absorber thickness across
    all trajectories.  Each trajectory is linearly interpolated onto the
    common energy grid so every trajectory contributes to every bin it spans.
    """
    if path_kwargs is None:
        path_kwargs = dict(color="black", lw=2.0, label="median trajectory")
    if band_kwargs is None:
        band_kwargs = dict(color="black", alpha=0.15, label=f"{qlo}–{qhi}% band")

    # Determine common energy range
    e_min = min(min(E) for E, A in trajs)
    e_max = max(max(E) for E, A in trajs)
    e_grid = np.linspace(e_min, e_max, n_bins)

    # For each trajectory, interpolate A as a function of epoch-parameterized E
    A_at_grid = []
    for E_raw, A_raw in trajs:
        E_arr = np.asarray(E_raw, dtype=float)
        A_arr = np.asarray(A_raw, dtype=float)
        if E_arr.size < 2:
            continue
        # fine-sample by epoch index, then interp onto energy grid
        t = np.arange(E_arr.size, dtype=float)
        t_fine = np.linspace(0, t[-1], 2000)
        E_fine = np.interp(t_fine, t, E_arr)
        A_fine = np.interp(t_fine, t, A_arr)
        # E generally decreases (25000 -> target), flip for np.interp
        if E_fine[0] > E_fine[-1]:
            A_interp = np.interp(e_grid, E_fine[::-1], A_fine[::-1])
        else:
            A_interp = np.interp(e_grid, E_fine, A_fine)
        A_at_grid.append(A_interp)

    if len(A_at_grid) < 2:
        return

    A_stack = np.vstack(A_at_grid)  # (n_trajs, n_bins)
    A_med = np.nanmedian(A_stack, axis=0)
    A_lo = np.nanpercentile(A_stack, qlo, axis=0)
    A_hi = np.nanpercentile(A_stack, qhi, axis=0)

    ax.plot(e_grid, A_med, **path_kwargs)
    ax.fill_between(e_grid, A_lo, A_hi, **band_kwargs)


trajs = [] 
for idx, base in tqdm.tqdm(enumerate(bases)):

    # collect the first MAX_EPOCHS epochs for this run
    epoch_files = sorted(glob.glob(os.path.join(base, "epoch_*.npz")),
                         key=lambda f: int(os.path.basename(f).split("_")[1].split(".")[0]))
    epoch_files = epoch_files[:MAX_EPOCHS]
    if not epoch_files:
        continue

    # load the trajectory
    energies = [START[0]]
    thicknesses = [START[1]]
    for f in epoch_files:
        try:
            data = np.load(f)
            energies.append(float(data["beam_energy"]))
            thicknesses.append(float(data["absorber_thickness"]))
        except:
            print(f"[warn] Could not load data from {f}, skipping epoch")
            continue

    all_E.extend(energies[1:])
    all_A.extend(thicknesses[1:])
    trajs.append( (energies, thicknesses) )


    # plot line + markers
    color = cmap(idx % cmap.N)
    if OVERLAY_RAW:

        ax.plot(
            energies, thicknesses,
            marker="x", markersize=0,
            linestyle="-", linewidth=0.4,
            color="grey", alpha=0.7,
            #label=os.path.basename(base)
        )

    # only plot endpoint if within frame
    e_end = energies[-1]
    a_end = thicknesses[-1]
    if XMIN <= e_end <= XMAX and YMIN <= a_end <= YMAX:
        ax.scatter(
            e_end, a_end,
            marker="x", color="red", s=20, zorder=4
        )
        seed_label = os.path.basename(base).replace("seed_offset", "")
        if SHOW_SEEDS:
            ax.text(
                e_end, a_end,
                seed_label,
                color="red",
                fontsize=12,
                ha="left",
                va="bottom",
                zorder=5
            )
    else:
        print(f"[warn] Endpoint of {base} ({e_end:.1f}, {a_end:.3f}) "
              f"outside plot bounds, skipping marker.")
    #if idx > 20:
    #    print("[info] Limiting to first 20 trajectories for overlay.")
    #    break

# draw common start and target

#fig, ax = plt.subplots(figsize=(10, 6))
plot_median_with_band(ax, trajs, n_bins=250, qlo=5, qhi=95, 
    path_kwargs=dict(color="blue", lw=2.5, label="median trajectory"), 
    band_kwargs=dict(color="blue", alpha=0.25, label=r"5–95% band")
)
#ax.set_xlabel("Primary energy [GeV]")
#ax.set_ylabel("Absorber thickness [mm]")
#ax.legend(frameon=False)
#plt.savefig(ROOT+"/median_trajectory.png")
#plt.savefig(ROOT+"/median_trajectory.pdf")


ax.scatter(*START,  color="green",  s=80, label="start", zorder=5)
ax.scatter([], [],  marker="x", color="red", s=20, label="endpoint")
ax.set_xlabel("Primary energy [GeV]")
ax.set_ylabel("Absorber thickness [mm]")
ax.set_xlim(XMIN, XMAX)
ax.set_ylim(YMIN, YMAX)


# if your Matplotlib version doesn’t accept framealpha in legend(),
# you can do it afterward:

ax.plot(
    TARGET[0], TARGET[1],
    marker="D",
    markersize=12,
    linestyle="",
    markerfacecolor="none",       # no fill
    markeredgecolor="purple",     # outline color
    markeredgewidth=1.5,          # edge line width
    label="target",
    zorder=10,          # <-- add this
)

leg = ax.legend(
    ncol=1,
    #fontsize="medium",      # or "xx-small"
    loc="lower right",
    frameon=True,            # draw the legend box
    facecolor="white",       # fill box white
    edgecolor="black",       # optional: give it a border
    framealpha=0.6,           # make the box semi-transparent
    #fontsize=18,
)
leg.get_frame().set_alpha(0.6)

if SHOW_LANDSCAPE:
    y = np.linspace(1.0,7,50)
    x = np.linspace(5000,30000,50)
    a = np.loadtxt("landscape.dat")
    ax.contour(x,y,a.T,levels=100)
    #ax.colorbar()
    

plt.tight_layout()
plt.savefig(ROOT+"/all_trajectories.png")
plt.savefig(ROOT+"/all_trajectories.pdf")

#plt.show()
