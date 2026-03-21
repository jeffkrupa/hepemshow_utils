import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
import re
import mplhep as hep
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.ticker import MaxNLocator, FuncFormatter
from matplotlib.patches import Rectangle

plt.style.use(hep.style.ROOT)
plt.style.use("style.mplstyle")

def plot_edeps(
    samples,
    n_samples_per_file=1000,
    nlayers=50,
    x=None,
    title=None,
    figsize=(15, 8),
    alpha_lines=0.9,
    capsize=3.0,
    lw=3.5,
    ms=3.5,
    grid=False,
    suffix=None,
    default_deriv_target="a",
    # NEW: variance scaling options
    plot_variance_scaling=True,
    file_counts=(10, 100, 1000),
    scaling_figsize=(15, 8),
    nmaxfiles=100,
    seed_range=None,
    inset_unprotected=None,
    inset_loc="upper right",
    inset_size=("37%", "37%"),
):
    """
    Plot energy deposit (mean) and its derivative (mean) with standard-error bars.
    Optionally also plot sqrt(variance)/N_total as a function of layer for growing dataset sizes.

    Parameters
    ----------
    samples : list[(path,label) or dict]
        Each item is either (filepath_or_dir, label) or {'path':..., 'label':...}.
        To override which derivative the dataset represents, set key 'deriv_target' to
        'a' (absorber thickness, default) or 'energy' (primary energy).  To plot a
        finite-difference estimate, supply a dict with 'path' pointing to a directory
        that contains paired *_plus / *_minus files and specify 'epsilon' (optionally
        'label' and 'deriv_target'). Example:
            {'path': 'outputs/finite_diff...', 'epsilon': 0.005, 'label': 'FD eps=5e-3', 'deriv_target': 'energy'}
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
    inset_unprotected : str or dict or None
        Optional dataset to plot in an inset on the derivative panel.
        Accepts a filepath/dir or dict with keys {'path', 'label'}.
        Files must follow the same (N,4) format.
    inset_loc : str
        Location for the inset axes (matplotlib legend-style locations).
    inset_size : tuple(str,str)
        Size of the inset axes, e.g. ("40%", "40%").
    """
    # Normalize input sample spec
    norm = []
    inset_from_samples = None
    inset_skip_paths = set()
    inset_skip_labels = set()
    for s in samples:
        if isinstance(s, dict):
            deriv_target = s.get("deriv_target", default_deriv_target)
            if s.get("inset_unprotected", False) and inset_from_samples is None:
                inset_from_samples = s
                inset_skip_paths.add(Path(s["path"]))
                inset_skip_labels.add(s.get("label", "Unprotected"))
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
                    "deriv_target": deriv_target,
                })
            else:
                if "path" not in s:
                    raise ValueError("Sample dict must include 'path'.")
                path = Path(s["path"])
                epsilon = s.get("epsilon", None)
                label = s.get("label", path.name)
                if epsilon is not None:
                    norm.append({
                        "type": "finite_diff",
                        "path": path,
                        "epsilon": float(epsilon),
                        "label": label,
                        "deriv_target": deriv_target,
                    })
                else:
                    norm.append({
                        "type": "single",
                        "path": path,
                        "label": label,
                        "deriv_target": deriv_target,
                    })
        else:
            path, label = s
            path = Path(path)
            norm.append({
                "type": "single",
                "path": path,
                "label": label,
                "deriv_target": default_deriv_target,
            })

    # Parse seed_range (e.g. "3000-3999") into (lo, hi) inclusive
    _seed_lo, _seed_hi = None, None
    if seed_range is not None:
        parts = seed_range.split("-")
        if len(parts) != 2:
            raise ValueError(f"seed_range must be 'lo-hi', got '{seed_range}'")
        _seed_lo, _seed_hi = int(parts[0]), int(parts[1])

    _seed_re = re.compile(r'_(\d+)$')

    def _filter_by_seed(files):
        """Filter file list by seed_range. Extract seed from trailing _NNN in filename stem."""
        if _seed_lo is None:
            return list(files)[:nmaxfiles]
        out = []
        for f in files:
            m = _seed_re.search(f.stem)
            if m is None:
                continue
            s = int(m.group(1))
            if _seed_lo <= s <= _seed_hi:
                out.append(f)
        return sorted(out)

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
        deriv_target = spec.get("deriv_target", default_deriv_target)
        if stype == "single":
            path = spec["path"]
            _ensure_paths_exist(path)
            n_samples = 0.0
            if path.is_dir():
                files = _filter_by_seed(path.glob("*"))
                arrays = []
                for f in files:
                    #if "_4645" in f.name or "_643" in f.name or "_577" in f.name:  # known bad seeds with NaNs
                    #    print(f"Skipping file with known bad seed: {f}")
                    #    continue
                    arr = _load_file(f)
                    arrays.append(arr)
                if not arrays:
                    raise ValueError(f"No valid files found in directory {path}")
                arr_avg = np.mean(arrays, axis=0)
                n_samples = float(n_samples_per_file) * len(arrays)
                loaded.append({
                    "path": path,
                    "label": label,
                    "array": arr_avg,
                    "n_samples": n_samples,
                    "deriv_target": deriv_target,
                })
                dir_cache[path] = arrays
                print(f"Averaging files in directory: {path} -> {len(arrays)} files")
            else:
                arr = _load_file(path)
                loaded.append({
                    "path": path,
                    "label": label,
                    "array": arr,
                    "n_samples": n_samples,
                    "deriv_target": deriv_target,
                })
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
                pairs = [{"plus": pair_map[core]["plus"], "minus": pair_map[core]["minus"]} for core in cores]
                arrays = _load_finite_diff_from_pairs(pairs, epsilon)
                arr_avg = np.mean(arrays, axis=0)
                n_samples = float(n_samples_per_file) * len(arrays)
                loaded.append({
                    "path": base,
                    "label": label,
                    "array": arr_avg,
                    "n_samples": n_samples,
                    "deriv_target": deriv_target,
                })
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
                base = path_plus.parent
                loaded.append({
                    "path": base,
                    "label": label,
                    "array": arr_avg,
                    "n_samples": n_samples,
                    "deriv_target": deriv_target,
                })
                dir_cache[base] = arrays
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
    axR.tick_params(top=False, right=False, labeltop=False, labelright=False)

    # Left: mean energy deposit with SE
    for entry in loaded:
        if entry["path"] in inset_skip_paths or entry["label"] in inset_skip_labels:
            continue

        label = entry["label"]
        arr = entry["array"]
        n_samples = entry["n_samples"]
        mean_E = arr[:, 0]
        var_E  = arr[:, 1]
        # Standard error of the mean: sqrt(var / N_total)
        se_E   = np.sqrt(var_E / float(n_samples)) if n_samples > 0 else np.nan

        count_suffix = f" (N={n_samples:.2e})" if n_samples > 0 else ""
        axL.errorbar(
            xvals, mean_E,
            yerr=se_E,
            fmt='o-', #ms=ms, lw=lw, capsize=capsize,
            alpha=alpha_lines, label=label #+ count_suffix,
        )

    axL.set_xlabel("Layer", fontsize=24)
    axL.set_ylabel("energy deposit per layer  $\overline{\mathit{E}_{\mathrm{dep}}}$ [MeV]", fontsize=24)
    if grid: axL.grid(True, linestyle='--', alpha=0.4)
    #axL.legend(loc="best", fontsize=14)

    target_axis_map = {
        "a": r"$\partial \overline{\mathit{E}_{\mathrm{dep}}} / \partial \mathit{\alpha}$ [MeV mm$^{-1}$]", 
        "energy": r"$\partial \overline{\mathit{E}_{\mathrm{dep}}} / \partial \mathit{E}_{\mathrm{beam}}$ [dimensionless]",
    }
    unique_targets = sorted({entry["deriv_target"] for entry in loaded})
    target = unique_targets[0]
    axis_label = f"{target_axis_map.get(target, target)}"

    # Right: mean derivative with SE
    for entry in loaded:
        if entry["path"] in inset_skip_paths or entry["label"] in inset_skip_labels:
            continue
        label = entry["label"]
        arr = entry["array"]
        n_samples = entry["n_samples"]
        target = entry["deriv_target"]
        mean_dE = arr[:, 2]
        var_dE  = arr[:, 3]
        se_dE   = np.sqrt(var_dE / float(n_samples)) if n_samples > 0 else np.nan

        count_suffix = f" (N={n_samples:.2e})" if n_samples > 0 else ""
        axR.errorbar(
            xvals, mean_dE,
            yerr=se_dE,
            fmt='o-', #ms=ms, lw=lw, capsize=capsize,
            alpha=alpha_lines, label=label# + count_suffix,
        )
        
    axR.set_xlabel("Layer")
    axR.set_ylabel(axis_label)
    if grid: axR.grid(True, linestyle='--', alpha=0.4)
    y_min, y_max = axR.get_ylim()
    y_pad = 0.4 * (y_max - y_min)
    axR.set_ylim(y_min, y_max + y_pad)
    #axR.set_yscale("symlog")

    if inset_unprotected is None and inset_from_samples is not None:
        inset_unprotected = {
            "path": inset_from_samples["path"],
            "label": inset_from_samples.get("label", "Unprotected"),
        }

    if inset_unprotected is not None:
        if isinstance(inset_unprotected, dict):
            inset_path = Path(inset_unprotected["path"])
            inset_label = inset_unprotected.get("label", inset_path.name)
        else:
            inset_path = Path(inset_unprotected)
            inset_label = inset_path.name
        _ensure_paths_exist(inset_path)
        if inset_path.is_dir():
            files = _filter_by_seed(inset_path.glob("*"))
            arrays = [_load_file(f) for f in files]
            if not arrays:
                raise ValueError(f"No valid files found in directory {inset_path}")
            inset_arr = np.mean(arrays, axis=0)
            inset_samples = float(n_samples_per_file) * len(arrays)
        else:
            inset_arr = _load_file(inset_path)
            inset_samples = 0.0
        inset_mean = inset_arr[:, 2]
        inset_var = inset_arr[:, 3]
        inset_se = np.sqrt(inset_var / float(inset_samples)) if inset_samples > 0 else np.nan

        ax_inset = inset_axes(axR, width=inset_size[0], height=inset_size[1], loc="upper right", borderpad=0.0)
        ax_inset.set_facecolor("white")
        ax_inset.patch.set_alpha(1.0)
        ax_inset.patch.set_zorder(10)   # ensure the patch is above axR artists
        ax_inset.set_zorder(11)         # inset contents above its patch
        ax_inset.errorbar(
            xvals, inset_mean,
            yerr=inset_se,
            fmt='o-',
            alpha=alpha_lines,
            color="grey",
            markersize=3,
            linewidth=1.5,
            label=inset_label,
        )
        ax_inset.text(0.45, 0.9, "AD (no stopgrad)", transform=ax_inset.transAxes,
                      ha="center", va="top", fontsize=15, color="black")
        #axR.errorbar([], [], yerr=[], fmt='o-', color="grey", label=f"{inset_label}")
        ax_inset.grid(False)
        #ax_inset.set_xlabel("Layer", fontsize=10)
        #ax_inset.set_ylabel(axis_label, fontsize=10)
        ax_inset.tick_params(axis="both", labelsize=14)
        ax_inset.xaxis.set_major_locator(MaxNLocator(nbins=2))
        ax_inset.yaxis.set_major_locator(MaxNLocator(nbins=2))
        def _sci_tick(v, _pos):
            if v == 0:
                return "0"
            exp = int(np.floor(np.log10(abs(v))))
            coeff = v / (10 ** exp)
            return rf"{coeff:.1f}×10$^{{{exp}}}$"
        #ax_inset.yaxis.set_major_formatter(FuncFormatter(_sci_tick))
        if target == "a":
            ax_inset.set_yticks([-2.5e12, 0, 2.5e12])
        elif target == "energy":
            ax_inset.set_yticks([-1.5e8, 0, 1.5e8])
        ax_inset.minorticks_off()
        ax_inset.yaxis.set_minor_locator(plt.NullLocator())
        #ax_inset.xaxis.set_minor_locator(plt.NullLocator())
        ax_inset.tick_params(left=False, right=False, bottom=True, top=False)
        ax_inset.tick_params(axis="x", which="both",
                     bottom=True, labelbottom=True,
                     top=False, labeltop=False)
        ax_inset.xaxis.set_major_locator(MaxNLocator(nbins=3))   # e.g. 0, 20–30, 40–50 depending on range
        # label them exactly how you want (bold, large)
        if target == "a":
            ax_inset.set_yticklabels(
                [r"$\mathbf{-10^{12}}$", r"$\mathbf{0}$", r"$\mathbf{10^{12}}$"],
                fontsize=18,  # bump as desired
            )
        elif target == "energy":
            ax_inset.set_yticklabels(
                [r"$\mathbf{-10^{8}}$", r"$\mathbf{0}$", r"$\mathbf{10^{8}}$"],
                fontsize=18,  # bump as desired
            )

        # make sure no offset text shows up
        ax_inset.yaxis.offsetText.set_visible(False)
        ax_inset.yaxis.offsetText.set_visible(False)

    axR.legend(loc="upper left", )#fontsize=14)

    if title:
        fig.suptitle(title, y=1.02, fontsize=16)
    #axR.set_ylim(-1000,1000)
    plt.tight_layout()
    plt.savefig(f"edeps_and_derivatives{'' if suffix is None else '_'+str(suffix)}.png", dpi=300)
    plt.savefig(f"edeps_and_derivatives{'' if suffix is None else '_'+str(suffix)}.pdf", dpi=300)

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

                axS1.plot(xvals, curve_E, '-o', #ms=ms, lw=lw,
                          alpha=alpha_lines, label=lblE
                )
                axS2.plot(xvals, curve_dE, '-o', #ms=ms, lw=lw, 
                          alpha=alpha_lines, label=lblD
                )

        axS1.set_xlabel("Layer")
        axS1.set_ylabel(r"$\sqrt{\mathrm{var}(E)/N_{\mathrm{total}}}$")
        if grid: axS1.grid(True, linestyle='--', alpha=0.4)
        axS1.legend(loc="best", )#fontsize=14)

        axS2.set_xlabel("Layer")
        axS2.set_ylabel(r"$\sqrt{\mathrm{var}(dE)/N_{\mathrm{total}}}$")
        if grid: axS2.grid(True, linestyle='--', alpha=0.4)
        axS2.legend(loc="best", )#fontsize=14)

        plt.tight_layout()
        plt.savefig(f"variance_scaling{'' if suffix is None else '_'+str(suffix)}.png", dpi=300)
        plt.savefig(f"variance_scaling{'' if suffix is None else '_'+str(suffix)}.pdf", dpi=300)

    return fig, (axL, axR), scaling_fig


def _decode_token(token):
    return float(token.replace("p", "."))


def _encode_token(token):
    return str(token).replace(".", "p").replace("-", "m")


def _discover_afn_scan_runs(outputs_dir):
    pattern = re.compile(r"_nmf(?P<a>[^_]+)_ruf(?P<f>[^_]+)_cre(?P<n>[^_]+)$")
    groups = {}
    for run_dir in sorted(outputs_dir.glob("ad_a2p3_E10000_thr0p1_gst1_bbs1_x2_nmf*_ruf*_cre*")):
        if not run_dir.is_dir():
            continue
        if not any(run_dir.glob("edeps_*")):
            continue
        match = pattern.search(run_dir.name)
        if match is None:
            continue
        a_tok = match.group("a")
        f_tok = match.group("f")
        n_tok = match.group("n")
        groups.setdefault(a_tok, []).append((run_dir, f_tok, n_tok))

    for a_tok, entries in groups.items():
        entries.sort(key=lambda item: (_decode_token(item[1]), _decode_token(item[2])))
    return groups


if __name__ == "__main__":
    outputs_dir = Path("../jobs/outputs")
    finite_diff_path = Path(
        "../../../../../hepemshow_reproductionattempt1/hepemshow/build/hepemshow_utils/jobs/outputs/finite_diff_a2.3_eps0.005"
    )
    '''
    afn_groups = _discover_afn_scan_runs(outputs_dir)
    if not afn_groups:
        raise FileNotFoundError(
            f"No 3x3x3 scan directories found under {outputs_dir} "
            "(expected names like ..._nmf*_ruf*_cre*)."
        )

    for a_tok in sorted(afn_groups, key=_decode_token):
        samples = [{"path": finite_diff_path, "label": "Finite diff", "epsilon": 0.005}]
        for run_dir, f_tok, n_tok in afn_groups[a_tok]:
            samples.append(
                {
                    "path": run_dir,
                    "label": f"AD (F={f_tok}, N={n_tok})",
                    "deriv_target": "a",
                }
            )

        suffix = f"scan_A{_encode_token(a_tok)}"
        print(f"Plotting A={a_tok} with {len(afn_groups[a_tok])} AD runs -> suffix '{suffix}'")
        plot_edeps(
            samples,
            n_samples_per_file=1e4,
            nlayers=50,
            nmaxfiles=1000,
            suffix=suffix,
            plot_variance_scaling=False,
            file_counts=(10, 100, 1000, 3500),
        )
    '''

    samples = [
        
        { #MAIN ABS ONE
            "path": "/fs/ddn/sdf/group/atlas/d/jkrupa/hepemshow_reproductionattempt1/hepemshow/build/hepemshow_utils/jobs/outputs/finite_diff_a2.3_eps0.005", 
            "label": "Finite diff", 
            "epsilon": 0.005
        },
        { 
            'path': Path('../jobs/outputs/ad_a2p3_E10000_thr0p0_gst1_bbs1_x2_gmc1000_cre0p001_copysign_fix'),
            'label': 'AD (f=0.0, cre1e-3, gmc1000)',
            'deriv_target': 'a',
        },
        { 
            'path': Path('../jobs/outputs/ad_a2p3_E10000_thr0p2_gst1_bbs1_x2_gmc1000_cre1e-3_copysign_fix'),
            'label': 'AD (f=0.2, cre1e-3, gmc1000)',
            'deriv_target': 'a',
        },

        #{ #MAIN ENERGY ONE
        #    "path": "/fs/ddn/sdf/group/atlas/d/jkrupa/hepemshow_reproductionattempt1/hepemshow/build/hepemshow_utils/jobs/outputs/finite_diff_energy_E10000_eps50/", 
        #    "label": "Finite diff", 
        #    "epsilon": 50
        #},

        #{
        #    'path': Path('../jobs/outputs/ad_energy_E10000_thr0p2_gst1_bbs1_x2_copysign_fix'),
        #    'label': 'AD (f=0.2)',
        #    'deriv_target': 'energy',
        #},
        #{
        #    'path': Path('../jobs/outputs/ad_a2p3_E10000_thr0p05_gst1_bbs1_x2_copysign_fix'),
        #    'label': 'AD (f=0.05)',
        #    'deriv_target': 'a',
        #},
        #{
        #    'path': Path('../jobs/outputs/ad_a2p3_E10000_thr0p2_gst1_bbs1_x2_copysign_fix'),
        #    'label': 'AD (f=0.2)',
        #    'deriv_target': 'a',
        #},

        #{
        #    'path': Path('../jobs/outputs/ad_energy_E10000_thr0p2_gst1_bbs1_x2_copysign_fix'),
        #    'label': 'AD (f=0.2)',
        #    'deriv_target': 'a',
        #},


        #{
        #    'path': Path('../jobs/outputs/ad_a2p3_E10000_thr0p1_gst1_bbs1_x2_nmf10_gnmf10_copysign_fix'),
        #    'label': 'AD (with numia regularization)',
        #    'deriv_target': 'a',
        #},
        #{
        #    'path': Path('../jobs/outputs/ad_a2p3_E10000_thr0p1_gst1_bbs1_ffs1_x2_nmf1p0_gnmf1p0_gpef0p01_bdf0p01_ruf0p01_cre0p01_ucf0p1_ute0p01_usf0p01_udf1e-6'),
        #    'label': 'AD (regularize DTO+denoms)',
        #    'deriv_target': 'a',
        #},
    ]
    plot_edeps(
        samples,
        n_samples_per_file=2e4,
        nlayers=50,
        nmaxfiles=5000,
        seed_range="1-1000", 
        suffix='baseline',
        plot_variance_scaling=False,
        file_counts=(10, 100, 1000, 3500),
    )
