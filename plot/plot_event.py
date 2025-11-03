import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

observable = "edep_dot"
df = pd.read_csv("micro_audit.csv")  # your dump
d = df[df["event"]==539].copy()

# Identify the daughter and its parent
child = d[d["trackID"]==4999].sort_values("step")
parent_id = int(child["parentID"].iloc[0])
mom = d[d["trackID"]==parent_id].sort_values("step")

# --- Panel A: XY with color=|EKin_dot| (log)
fig, ax = plt.subplots(1,2, figsize=(11,4.2), gridspec_kw={'wspace':0.25})

def scatter_xy(ax, g, title, xlim=None, ylim=None):
    c = np.clip(np.abs(g[observable].values), 1e-100, None)
    c# = g["edep_dot"].values
    #print(c)
    sc = ax.scatter(g["gX"], g["gY"], c=c, s=12, cmap="viridis")
    #print(g["vx"], pd.Series(np.concatenate((g["gX"].diff()[1:], np.array([0.])))))
    ax.quiver(g["gX"], g["gY"], 
            pd.Series(np.concatenate((g["gX"].diff()[1:], np.array([0.])))), 
            pd.Series(np.concatenate((g["gY"].diff()[1:], np.array([0.])))), 
            angles='xy', scale_units='xy', scale=1, width=0.008, alpha=0.3
            )
    ax.set_aspect('equal', 'box')
    ax.set_title(title)
    ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]")
    ax.set_aspect('auto')
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:   
        ax.set_ylim(ylim)
    return sc

sc1 = scatter_xy(ax[0], mom,   f"Parent track {parent_id}", )
sc2 = scatter_xy(ax[1], child, f"Daughter track 1596", (359.95,360.07), (-36.5,-36.44))

# vertical lines for x-boundaries (edit to your geometry)
#for a in ax:
#    for xb in [0,50,100,150,200]:  # example
#        a.axvline(xb, color='k', ls=':', lw=0.7)
ax[0].axvline(360, color='grey', ls='--')
ax[1].axvline(360, color='grey', ls='--')
cb = fig.colorbar(sc1, ax=ax[0], shrink=0.85, label=observable)
cb = fig.colorbar(sc2, ax=ax[1], shrink=0.85, label=observable)
plt.tight_layout(); 
plt.savefig(f"fig_event539_xy_{observable}_dot.png", dpi=150)

# --- Panel B: per-step series
fig, ax = plt.subplots(2,1, figsize=(10,6), sharex=True)

for g, lab in [(mom, "parent"), (child, "daughter")]:
    ax[0].plot(g["step"], g["EKin_dot"], label=f"{lab} EKin_dot", alpha=0.8)
    ax[1].plot(g["step"], g["edep_dot"], label=f"{lab} edep_dot", alpha=0.8)

ax[0].set_yscale("symlog", linthresh=1e3); ax[1].set_yscale("symlog", linthresh=1e3)
ax[0].set_ylabel("EKin_dot"); ax[1].set_ylabel("edep_dot")
ax[1].set_xlabel("step index"); ax[0].legend(); ax[1].legend()
plt.tight_layout(); 
plt.savefig("fig_event539_step_series.png", dpi=150)