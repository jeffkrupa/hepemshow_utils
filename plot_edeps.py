import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import mplhep as hep

plt.style.use(hep.style.ROOT)

def plot_edeps(
    samples,
    n_samples_per_file=1000,
    nlayers=50,
    x=None,
    title=None,
    figsize=(15, 8),
    alpha_lines=0.9,
    capsize=2.0,
    lw=1.6,
    ms=3.5,
    grid=True,
    suffix=None,
    # NEW: variance scaling options
    plot_variance_scaling=True,
    file_counts=(10, 100, 1000),
    scaling_figsize=(15, 8),
    nmaxfiles=100,
):
    """
    Plot energy deposit (mean) and its derivative (mean) with standard-error bars.
    Optionally also plot sqrt(variance)/N_total as a function of layer for growing dataset sizes.

    Parameters
    ----------
    samples : list[(path,label) or dict]
        Each item is either (filepath_or_dir, label) or {'path':..., 'label':...}.
        To plot a finite-difference estimate, supply a dict with 'path' pointing to
        a directory that contains paired *_plus / *_minus files and specify 'epsilon'
        (optionally 'label'). Example:
            {'path': 'outputs/finite_diff...', 'epsilon': 0.005, 'label': 'FD eps=5e-3'}
        If 'path' is a directory, all files in that directory are loaded and averaged for the
        main plot. For the variance-scaling figure, subsets of the directory files are used.
        Each file must be a text file with shape (N_layers, 4) columns:
            [ mean_E, var_E, mean_dE, var_dE ]
    n_samples_per_file : float or int
        Number of generated samples per file (used to convert variances).
    nlayers : int
        Expected number of layers (rows).
    plot_variance_scaling : bool
        If True, also produce a second figure showing sqrt(variance)/N_total vs layer for
        several dataset sizes (file_counts) for any directory sample.
    file_counts : iterable[int]
        The “k files” sizes to plot (e.g., 10, 100, 1000).
    """
    # Normalize input sample spec
    norm = []
    for s in samples:
        if isinstance(s, dict):
            if "path_plus" in s or "path_minus" in s:
                if "path_plus" not in s or "path_minus" not in s or "epsilon" not in s:
                    raise ValueError("Finite-diff explicit spec requires 'path_plus', 'path_minus', and 'epsilon'.")
                path_plus = Path(s["path_plus"])
                path_minus = Path(s["path_minus"])
                epsilon = float(s["epsilon"])
                label = s.get("label", path_plus.name or path_minus.name)
                norm.append({
                    "type": "finite_diff_explicit",
                    "path_plus": path_plus,
                    "path_minus": path_minus,
                    "epsilon": epsilon,
                    "label": label,
                })
            else:
                if "path" not in s:
                    raise ValueError("Sample dict must include 'path'.")
                path = Path(s["path"])
                epsilon = s.get("epsilon", None)
                if epsilon is not None:
                    label = s.get("label", path.name)
                    norm.append({
                        "type": "finite_diff",
                        "path": path,
                        "epsilon": float(epsilon),
                        "label": label,
                    })
                else:
                    label = s.get("label", path.name)
                    norm.append({
                        "type": "single",
                        "path": path,
                        "label": label,
                    })
        else:
            path, label = s
            path = Path(path)
            norm.append({
                "type": "single",
                "path": path,
                "label": label,
            })

    def _load_file(path):
        arr = np.loadtxt(path)
        if arr.ndim != 2 or arr.shape[1] != 4:
            raise ValueError(f"{path} must have shape (N, 4); got {arr.shape}")
        return arr

    def _ensure_paths_exist(*paths):
        for p in paths:
            if p and not p.exists():
                raise FileNotFoundError(f"Expected file or directory not found: {p}")

    def _load_finite_diff_from_pairs(pairs, epsilon):
        arrays = []
        for pair in pairs:
            arr_plus = _load_file(pair["plus"])
            arr_minus = _load_file(pair["minus"])
            if arr_plus.shape != arr_minus.shape:
                raise ValueError(f"Mismatched shapes for {pair['plus']} and {pair['minus']}")
            arr_fd = np.empty_like(arr_plus)
            arr_fd[:, 0] = 0.5 * (arr_plus[:, 0] + arr_minus[:, 0])
            arr_fd[:, 1] = 0.25 * (arr_plus[:, 1] + arr_minus[:, 1])
            arr_fd[:, 2] = (arr_plus[:, 0] - arr_minus[:, 0]) / (2.0 * epsilon)
            arr_fd[:, 3] = (arr_plus[:, 1] + arr_minus[:, 1]) / (4.0 * epsilon * epsilon)
            arrays.append(arr_fd)
        if not arrays:
            raise ValueError("No valid plus/minus pairs found for finite-difference dataset.")
        return arrays

    # Load all datasets (for the main SE plots)
    loaded = []
    dir_cache = {}  # cache directory -> list of arrays to avoid re-reading for scaling
    for spec in norm:
        label = spec["label"]
        stype = spec["type"]
        if stype == "single":
            path = spec["path"]
            _ensure_paths_exist(path)
            n_samples = 0
            if path.is_dir():
                files = sorted(path.glob("*"))[:nmaxfiles]
                arrays = []
                for f in files:
                    arr = _load_file(f)
                    arrays.append(arr)
                if not arrays:
                    raise ValueError(f"No valid files found in directory {path}")
                arr_avg = np.mean(arrays, axis=0)
                n_samples = float(n_samples_per_file) * len(arrays)
                loaded.append((path, label, arr_avg, n_samples))
                dir_cache[path] = arrays
                print(f"Averaging files in directory: {path} -> {len(arrays)} files")
            else:
                arr = _load_file(path)
                loaded.append((path, label, arr, n_samples))
        elif stype in {"finite_diff", "finite_diff_explicit"}:
            epsilon = spec["epsilon"]
            if stype == "finite_diff":
                base = spec["path"]
                _ensure_paths_exist(base)
                if not base.is_dir():
                    raise ValueError(f"Finite-diff path must be a directory: {base}")
                files = sorted(base.glob("*"))
                pair_map = {}
                for f in files:
                    name = f.name
                    if name.endswith("_plus"):
                        core = name[:-5]
                        pair_map.setdefault(core, {})["plus"] = f
                    elif name.endswith("_minus"):
                        core = name[:-6]
                        pair_map.setdefault(core, {})["minus"] = f
                cores = sorted(core for core, pair in pair_map.items() if "plus" in pair and "minus" in pair)
                if not cores:
                    raise ValueError(f"No plus/minus file pairs found in {base}")
                if nmaxfiles is not None:
                    cores = cores[:nmaxfiles]
                pairs = [{"plus": pair_map[core]["plus"], "minus": pair_map[core]["minus"]} for core in cores]
                arrays = _load_finite_diff_from_pairs(pairs, epsilon)
                arr_avg = np.mean(arrays, axis=0)
                n_samples = float(n_samples_per_file) * len(arrays)
                loaded.append((base, label, arr_avg, n_samples))
                dir_cache[base] = arrays
                print(f"Finite-diff directory {base}: {len(arrays)} paired files (epsilon={epsilon})")
            else:
                path_plus = spec["path_plus"]
                path_minus = spec["path_minus"]
                _ensure_paths_exist(path_plus, path_minus)
                pairs = [{"plus": path_plus, "minus": path_minus}]
                arrays = _load_finite_diff_from_pairs(pairs, epsilon)
                arr_avg = arrays[0]
                n_samples = float(n_samples_per_file)
                loaded.append((path_plus.parent, label, arr_avg, n_samples))
                dir_cache[path_plus.parent] = arrays
                print(f"Finite-diff explicit files: {path_plus}, {path_minus} (epsilon={epsilon})")
        else:
            raise ValueError(f"Unhandled sample type: {stype}")

    # X axis
    n_rows = nlayers
    if x is None:
        xvals = np.arange(1, n_rows + 1)
    else:
        xvals = np.asarray(x)
        if xvals.shape[0] != n_rows:
            raise ValueError(f"x has length {xvals.shape[0]} but files have {n_rows} rows")

    # ===== Main figure: means with SE bars =====
    fig, (axL, axR) = plt.subplots(1, 2, figsize=figsize, sharex=True)

    # Left: mean energy deposit with SE
    for _, label, arr, n_samples in loaded:
        mean_E = arr[:, 0]
        var_E  = arr[:, 1]
        # Standard error of the mean: sqrt(var / N_total)
        se_E   = np.sqrt(var_E / float(n_samples)) if n_samples > 0 else np.nan

        axL.errorbar(
            xvals, mean_E,
            yerr=se_E,
            fmt='o-', ms=ms, lw=lw, capsize=capsize,
            alpha=alpha_lines, label=label + f" (N={n_samples:.2e})",
        )

    axL.set_xlabel("Layer")
    axL.set_ylabel("Mean energy deposit")
    if grid: axL.grid(True, linestyle='--', alpha=0.4)
    axL.legend(loc="best", fontsize=14)

    # Right: mean derivative with SE
    for _, label, arr, n_samples in loaded:
        mean_dE = arr[:, 2]
        var_dE  = arr[:, 3]
        se_dE   = np.sqrt(var_dE / float(n_samples)) if n_samples > 0 else np.nan

        axR.errorbar(
            xvals, mean_dE,
            yerr=se_dE,
            fmt='o-', ms=ms, lw=lw, capsize=capsize,
            alpha=alpha_lines, label=label,
        )
        
    axR.set_xlabel("Layer")
    axR.set_ylabel("Mean energy deposit derivative")
    if grid: axR.grid(True, linestyle='--', alpha=0.4)

    if title:
        fig.suptitle(title, y=1.02, fontsize=16)
    #axR.set_ylim(-1000,1000)
    plt.tight_layout()
    plt.savefig(f"edeps_and_derivatives{'' if suffix is None else '_'+str(suffix)}.png", dpi=300)

    # ===== Optional: variance scaling figure sqrt(var)/N_total vs layer =====
    scaling_fig = None
    if plot_variance_scaling:
        scaling_fig, (axS1, axS2) = plt.subplots(1, 2, figsize=scaling_figsize, sharex=True)
        #axS1.set_title(r"$\sqrt{\mathrm{var}(E)}/N_{\mathrm{total}}$ vs layer")
        #axS2.set_title(r"$\sqrt{\mathrm{var}(dE)}/N_{\mathrm{total}}$ vs layer")

        for spec in norm:
            if spec["type"] not in {"single", "finite_diff"}:
                # We require a directory to build k-file subsets
                continue
            path = spec["path"] if spec["type"] == "single" else spec["path"]
            arrays = dir_cache.get(path)
            if arrays is None:
                continue
            n_files_available = len(arrays)
            if n_files_available == 0:
                continue

            # stack for easy slicing: (n_files, nlayers, 4)
            stack = np.stack(arrays, axis=0)

            for k in file_counts:
                k_eff = min(k, n_files_available)
                subset = stack[:k_eff]  # (k_eff, nlayers, 4)

                # average variances across the k files (per layer)
                varE_mean  = np.mean(subset[:, :, 1], axis=0)  # (nlayers,)
                vardE_mean = np.mean(subset[:, :, 3], axis=0)

                N_total = float(n_samples_per_file) * k_eff

                # Requested curve: sqrt(variance)/N_total
                curve_E  = np.sqrt(varE_mean)#  / N_total)
                curve_dE = np.sqrt(vardE_mean)# / N_total)

                lblE = f" N={N_total:.1e}"
                lblD = f" N={N_total:.1e}"

                axS1.plot(xvals, curve_E, '-o', ms=ms, lw=lw, alpha=alpha_lines, label=lblE)
                axS2.plot(xvals, curve_dE, '-o', ms=ms, lw=lw, alpha=alpha_lines, label=lblD)

        axS1.set_xlabel("Layer")
        axS1.set_ylabel(r"$\sqrt{\mathrm{var}(E)/N_{\mathrm{total}}}$")
        if grid: axS1.grid(True, linestyle='--', alpha=0.4)
        axS1.legend(loc="best", fontsize=14)

        axS2.set_xlabel("Layer")
        axS2.set_ylabel(r"$\sqrt{\mathrm{var}(dE)/N_{\mathrm{total}}}$")
        if grid: axS2.grid(True, linestyle='--', alpha=0.4)
        axS2.legend(loc="best", fontsize=14)

        plt.tight_layout()
        plt.savefig(f"variance_scaling{'' if suffix is None else '_'+str(suffix)}.png", dpi=300)

    return fig, (axL, axR), scaling_fig


plot_edeps(
    [
        #("outputs/absorberderivative_ekcut0.5", "fix + KE>=0.5 MeV"),
        #("outputs/absorberderivative_noekcut", "fix"),
        #("outputs/absorberderivative_killdescendents", "fix + kill descendents"),
        #("outputs/absorberderivative_killdescendents_threshold2_0p1", "fix + kill descedents + threshold2=-0.1"),
        #("outputs/absorberderivative_killdescendents_threshold2_m1p0", "fix + kill descedents + threshold2=-1"),
        #("outputs/ad_a2.3_kecut0p1", "fix + kill descedents + ek>0.1 MeV"),
        #("outputs/ad_a2.3_kecut0p3", "fix + kill descedents + ek>0.3 MeV"),
        ("outputs/ad_a2.3", "fix + kill descendents (next 80M events)"),
        ("outputs/ad_a2.3_thr0p05", "fix + kill descendents (threshold=0.05)"),
        ("outputs/ad_a2.3_thr0p2", "fix + kill descendents (threshold=0.2)"),
        {"path": "outputs/finite_diff_a2.3_eps0.005", "label": "finite diff eps=5e-3", "epsilon": 0.005},
        #{"path": "outputs/finite_diff_a2.3_eps0.0005", "label": "finite diff eps=5e-4", "epsilon": 0.0005},



    ],
    n_samples_per_file=2e4,
    nlayers=50,
    nmaxfiles=1000,
    #suffix="fix0p1",
    plot_variance_scaling=False,
    file_counts=(10, 100, 1000,3500),
)
