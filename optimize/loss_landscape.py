import glob
import os
import re
import numpy as np
base="grid_out2/results/"
target_edeps = np.array([  6.44720956,  11.79173741,  20.02149913,  31.95206159,
        47.9909972 ,  66.91844529,  89.41778528, 113.90719478,
       140.82566728, 168.820834  , 195.85531888, 219.99708905,
       243.70740818, 268.87485451, 287.30212994, 302.01039517,
       316.04630012, 327.02940627, 334.06695477, 337.75965538,
       336.72465625, 333.73688956, 329.14702084, 323.78267712,
       314.71196688, 307.11630178, 294.93432329, 281.11202882,
       267.87407676, 255.33010566, 241.88277465, 229.58843553,
       216.80904855, 201.9387832 , 189.50195292, 174.88187943,
       164.32877834, 153.95496684, 141.50670561, 131.93556534,
       122.27717228, 113.81493825, 104.92110335,  98.25718919,
        89.15019442,  82.73998634,  76.57967363,  69.18894586,
        64.13626066,  54.4685019 ])

nE, nA = 50, 50
beam_energies = np.linspace(5000, 30000, nE)
absorber_thicknesses = np.linspace(1.0, 7.0,    nA)

land = np.zeros((nE,nA))
for fn in glob.glob(os.path.join(base, "edeps*")):
    name = os.path.splitext(os.path.basename(fn))[0]
    parts = name.split('_')
    # Expected filename pattern: edeps_E<energy>_A<thickness>_seed<idx>, with "p" standing for decimal points.
    if len(parts) < 4 or not parts[1].startswith("E") or not parts[2].startswith("A"):
        print(f"[skip] Unrecognized filename format: {fn}")
        continue
    try:
        e = float(parts[1][1:].replace('p', '.'))
        a = float(parts[2][1:].replace('p', '.'))
    except ValueError as exc:
        print(f"[skip] Could not parse E/A from {fn}: {exc}")
        continue
    i = int(np.argmin(np.abs(beam_energies - e)))
    j = int(np.argmin(np.abs(absorber_thicknesses - a)))
    try:
        edeps = np.loadtxt(fn)[:,0]
    except Exception as exc:
        print(f"[skip] Could not load {fn}: {exc}")
        continue
    land[i,j] = np.linalg.norm(edeps - target_edeps)**2
    print(f"file={name}, e={e}, a={a}, i={i}, j={j}, loss={land[i,j]:.3f}")
np.savetxt("landscape.dat", land)
