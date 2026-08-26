import numpy as np
import matplotlib.pyplot as plt
import glob
import os
import mplhep as hep
plt.style.use(hep.style.CMS)
# 1) Point to your single run
base = "test1/seed_offset0"

# 2) Find and sort all opt-* subdirectories by their epoch number
opt_dirs = sorted(
    glob.glob(os.path.join(base, "opt-*")),
    key=lambda d: int(os.path.basename(d).split("-")[-1])
)

# 3) Load each arr.npz in order and collect (energy, thickness)
energies = []
thicknesses = []
target = 10000, 2.3
for d in opt_dirs[:150]:
    npz = os.path.join(d, "forward", "arr.npz")
    if not os.path.isfile(npz):
        print(f"Warning: {npz} does not exist, skipping")
        continue
    data = np.load(npz)
    energies.append(float(data["beam_energy"]))
    thicknesses.append(float(data["absorber_thickness"]))

print(energies, thicknesses)

# 4) Plot the trajectory as individual segments
fig, ax = plt.subplots(figsize=(10,10))

# draw arrows for each step
for i in range(1, len(energies)):
    ax.annotate(
        "", 
        xy=(energies[i],   thicknesses[i]), 
        xytext=(energies[i-1], thicknesses[i-1]),
        arrowprops=dict(arrowstyle='-', lw=2, alpha=0.7)
    )

# mark start and end
ax.scatter(energies[0], thicknesses[0], color="green", s=50, label="start")
ax.scatter(energies[-1], thicknesses[-1], color="red",   s=50, label="end")
ax.plot(
    target[0], target[1],
    marker="D",
    markersize=15,
    linestyle="",
    markerfacecolor="none",       # no fill
    markeredgecolor="purple",     # outline color
    markeredgewidth=1.5,          # edge line width
    label="target"
)
ax.set_xlabel("Primary energy [GeV]")
ax.set_ylabel("Absorber thickness [mm]")
#ax.set_title("Step-by-step training trajectory for seed_offset1")
ax.set_xlim(8000, 24000)
ax.set_ylim(1., 6)
ax.legend()
plt.tight_layout()
plt.savefig(base+"/trajectory_plot.png")