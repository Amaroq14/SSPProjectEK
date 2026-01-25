"""
Core analysis pipeline for SSP biomechanics data.
"""

from pathlib import Path
from typing import Dict, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from ssp_config import get_config_paths, get_group_ids


def classify_sample(filename: str, tfl_ids: list, msc_ids: list) -> Tuple[str, str, str]:
    """
    Parse filename to find Sample ID, Condition (NO/OPER), and Subgroup.
    """
    parts = filename.replace(".csv", "").split("_")

    condition = "Unknown"
    if "NO" in parts:
        condition = "NO"
    elif "OPER" in parts:
        condition = "OPER"

    sample_id = "Unknown"
    subgroup = "Unassigned"

    if condition == "NO":
        subgroup = "NON"

    for part in parts:
        if part in tfl_ids:
            sample_id = part
            if condition == "OPER":
                subgroup = "TFL"
            break
        if part in msc_ids:
            sample_id = part
            if condition == "OPER":
                subgroup = "MSC"
            break

    if sample_id == "Unknown":
        for part in parts:
            if part.startswith(("B", "C", "D")) and len(part) <= 3:
                sample_id = part
                break

    return sample_id, condition, subgroup


def find_best_stiffness(
    x: np.ndarray,
    y: np.ndarray,
    window_size: int,
    r2_threshold: float
) -> Tuple[float, float, float, int, int]:
    """
    Scan the curve to find the stiffest linear region.
    Returns: slope, intercept, r_squared, start_idx, end_idx
    """
    best_r2 = -np.inf
    best_slope = 0
    best_params = (np.nan, np.nan, np.nan, 0, 0)

    x = np.array(x)
    y = np.array(y)

    n_points = len(x)
    if n_points < window_size:
        return best_params

    for i in range(n_points - window_size):
        x_win = x[i : i + window_size].reshape(-1, 1)
        y_win = y[i : i + window_size]

        model = LinearRegression().fit(x_win, y_win)
        y_pred = model.predict(x_win)

        r2 = r2_score(y_win, y_pred)
        slope = model.coef_[0]

        if r2 >= r2_threshold:
            if slope > best_slope:
                best_slope = slope
                best_params = (slope, model.intercept_, r2, i, i + window_size)

        if r2 > best_r2 and best_slope == 0:
            best_r2 = r2
            best_params = (slope, model.intercept_, r2, i, i + window_size)

    return best_params


def process_all_files(
    data_dir: Path,
    tfl_ids: list,
    msc_ids: list,
    r2_threshold: float,
    window_fraction: float,
    min_window: int
) -> Optional[pd.DataFrame]:
    """Process all CSV files in the data folder."""
    print("\n" + "=" * 60)
    print("SSP BIOMECHANICS ANALYSIS PIPELINE")
    print("=" * 60)

    if not data_dir.exists():
        print(f"\n[X] Error: Folder not found: {data_dir}")
        return None

    files = sorted([f for f in data_dir.iterdir() if f.suffix.lower() == ".csv"])
    data_records = []

    print(f"\nProcessing {len(files)} files...\n")

    for file_path in files:
        filename = file_path.name
        try:
            s_id, cond, sub = classify_sample(filename, tfl_ids, msc_ids)

            if cond == "Unknown":
                print(f"  [!] Skipping {filename}: Could not determine NO/OPER.")
                continue

            df = pd.read_csv(file_path)

            if "LoadN" in df.columns:
                y_col = "LoadN"
            elif "LoadkN" in df.columns:
                df["LoadN"] = df["LoadkN"] * 1000
                y_col = "LoadN"
            else:
                print(f"  [!] Skipping {filename}: No load column found.")
                continue

            max_idx = df[y_col].idxmax()
            df_trunc = df.iloc[: max_idx + 1].copy()
            x = df_trunc["Crossheadmm"].values
            y = df_trunc[y_col].values

            energy_mJ = np.trapz(y, x)

            window_span = max(min_window, int(len(x) * window_fraction))
            slope, intercept, r2, idx_start, idx_end = find_best_stiffness(
                x, y, window_span, r2_threshold
            )
            stiffness_N_mm = slope

            data_records.append({
                "Filename": filename,
                "SampleID": s_id,
                "Subgroup": sub,
                "MaxLoad_N": df[y_col].max(),
                "Stiffness_N_mm": stiffness_N_mm,
                "Energy_mJ": energy_mJ,
                "R2_Score": r2,
                "Linear_Start_Idx": idx_start,
                "Linear_End_Idx": idx_end
            })

            print(
                f"  [OK] {filename} -> {sub}: "
                f"MaxLoad={df[y_col].max():.1f}N, Stiffness={stiffness_N_mm:.1f}N/mm"
            )

        except Exception as e:
            print(f"  [X] Error processing {filename}: {e}")

    metadata = pd.DataFrame(data_records)
    print(f"\n  Processed {len(metadata)} samples successfully.")

    return metadata


def generate_statistics(metadata: pd.DataFrame) -> pd.DataFrame:
    """Generate group statistics."""
    print("\n" + "=" * 60)
    print("GROUP STATISTICS")
    print("=" * 60)

    def list_ids(series):
        return ", ".join(sorted(series.unique()))

    stats = metadata.groupby("Subgroup").agg(
        MaxLoad_Mean=("MaxLoad_N", "mean"),
        MaxLoad_Std=("MaxLoad_N", "std"),
        Stiffness_Mean=("Stiffness_N_mm", "mean"),
        Stiffness_Std=("Stiffness_N_mm", "std"),
        Energy_Mean=("Energy_mJ", "mean"),
        Energy_Std=("Energy_mJ", "std"),
        Count=("SampleID", "count"),
        Sample_List=("SampleID", list_ids)
    ).round(2)

    print("\n")
    print(stats.to_string())

    return stats


def save_results(metadata: pd.DataFrame, stats: pd.DataFrame, results_dir: Path) -> None:
    """Save results to CSV files."""
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    results_dir.mkdir(parents=True, exist_ok=True)

    detail_path = results_dir / "Experiment_Master_Log_Detailed.csv"
    metadata.to_csv(detail_path, index=False)
    print(f"\n  Saved: {detail_path}")

    stats_path = results_dir / "Group_Statistics_Detailed.csv"
    stats.to_csv(stats_path)
    print(f"  Saved: {stats_path}")


def create_plots(metadata: pd.DataFrame, results_dir: Path) -> None:
    """Create summary plots."""
    print("\n" + "=" * 60)
    print("GENERATING PLOTS")
    print("=" * 60)

    import matplotlib.pyplot as plt

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams["figure.figsize"] = [10, 6]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    groups = ["NON", "TFL", "MSC"]
    colors = ["#2ecc71", "#3498db", "#e74c3c"]

    for i, metric in enumerate(["MaxLoad_N", "Stiffness_N_mm", "Energy_mJ"]):
        means = [metadata[metadata["Subgroup"] == g][metric].mean() for g in groups]
        stds = [metadata[metadata["Subgroup"] == g][metric].std() for g in groups]
        counts = [len(metadata[metadata["Subgroup"] == g]) for g in groups]

        bars = axes[i].bar(groups, means, color=colors, alpha=0.8, edgecolor="black")
        axes[i].errorbar(groups, means, yerr=stds, fmt="none", color="black", capsize=5)

        for j, bar in enumerate(bars):
            axes[i].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + stds[j] + 5,
                f"n={counts[j]}",
                ha="center",
                va="bottom",
                fontsize=10
            )

        titles = {
            "MaxLoad_N": "Max Load (N)",
            "Stiffness_N_mm": "Stiffness (N/mm)",
            "Energy_mJ": "Energy (mJ)"
        }
        axes[i].set_title(titles[metric], fontsize=14, fontweight="bold")
        axes[i].set_ylabel(titles[metric])
        axes[i].set_xlabel("Treatment Group")

    plt.tight_layout()

    plot_path = results_dir / "Combined_Group_Plots.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"\n  Saved: {plot_path}")


def run_pipeline(config: Dict, data_root: Path) -> None:
    """Run the full analysis pipeline."""
    paths = get_config_paths(config, data_root)
    data_dir = paths["selected_data_dir"]
    results_dir = paths["results_dir"]

    tfl_ids, msc_ids = get_group_ids(config)

    analysis_cfg = config.get("analysis", {})
    r2_threshold = float(analysis_cfg.get("stiffness_r2_threshold", 0.99))
    window_fraction = float(analysis_cfg.get("stiffness_window_fraction", 0.1))
    min_window = int(analysis_cfg.get("stiffness_min_window", 5))

    metadata = process_all_files(
        data_dir=data_dir,
        tfl_ids=tfl_ids,
        msc_ids=msc_ids,
        r2_threshold=r2_threshold,
        window_fraction=window_fraction,
        min_window=min_window
    )

    if metadata is None or len(metadata) == 0:
        print("\n[X] No data processed. Check your data folder.")
        return

    stats = generate_statistics(metadata)
    save_results(metadata, stats, results_dir)
    create_plots(metadata, results_dir)

    print("\n" + "=" * 60)
    print("[OK] ANALYSIS COMPLETE!")
    print("=" * 60)
    print(f"\n  Total samples processed: {len(metadata)}")
    print(f"  Results saved to: {results_dir}")
    print("\n  Files generated:")
    print("    - Experiment_Master_Log_Detailed.csv")
    print("    - Group_Statistics_Detailed.csv")
    print("    - Combined_Group_Plots.png")
