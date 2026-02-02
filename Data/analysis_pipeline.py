"""
Core analysis pipeline for SSP biomechanics data.
=================================================

This module provides the core analysis functions for processing
biomechanical test data from the supraspinatus tear study.

Key functions:
- classify_sample: Parse filenames to determine sample groups
- find_best_stiffness: Find the stiffest linear region in load-displacement curves
- process_all_files: Batch process all data files
- run_pipeline: Execute the complete analysis pipeline
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from ssp_config import get_config_paths, get_group_ids
from utils import (
    classify_sample,
    safe_trapezoid,
    validate_raw_data,
    normalize_load_column,
)

# Configure module logger
logger = logging.getLogger(__name__)

# Re-export classify_sample for backward compatibility
__all__ = [
    "classify_sample",
    "find_best_stiffness",
    "process_all_files",
    "generate_statistics",
    "save_results",
    "create_plots",
    "run_pipeline",
]


def find_best_stiffness(
    x: np.ndarray,
    y: np.ndarray,
    window_size: int,
    r2_threshold: float
) -> Tuple[float, float, float, int, int]:
    """
    Scan the curve to find the stiffest linear region.
    
    Uses a sliding window approach to find the region with the highest
    stiffness (slope) while maintaining good linearity (R² above threshold).
    
    Args:
        x: Displacement values (mm)
        y: Load values (N)
        window_size: Number of points in the sliding window
        r2_threshold: Minimum R² value to consider a region as linear
        
    Returns:
        Tuple of (slope, intercept, r_squared, start_idx, end_idx)
        Returns (nan, nan, nan, 0, 0) if no valid region is found.
    """
    best_r2 = -np.inf
    best_slope = 0.0
    best_params: Tuple[float, float, float, int, int] = (np.nan, np.nan, np.nan, 0, 0)

    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    n_points = len(x)
    if n_points < window_size:
        logger.warning(
            f"Insufficient data points ({n_points}) for window size ({window_size})"
        )
        return best_params

    for i in range(n_points - window_size):
        x_win = x[i : i + window_size].reshape(-1, 1)
        y_win = y[i : i + window_size]

        model = LinearRegression().fit(x_win, y_win)
        y_pred = model.predict(x_win)

        r2 = r2_score(y_win, y_pred)
        slope = float(model.coef_[0])
        intercept = float(model.intercept_)

        # Prefer regions with R² above threshold and highest slope
        if r2 >= r2_threshold:
            if slope > best_slope:
                best_slope = slope
                best_params = (slope, intercept, r2, i, i + window_size)

        # Fallback: if no region meets threshold, use best R²
        if r2 > best_r2 and best_slope == 0:
            best_r2 = r2
            best_params = (slope, intercept, r2, i, i + window_size)

    return best_params


def process_all_files(
    data_dir: Path,
    tfl_ids: List[str],
    msc_ids: List[str],
    r2_threshold: float,
    window_fraction: float,
    min_window: int
) -> Optional[pd.DataFrame]:
    """
    Process all CSV files in the data folder.
    
    Args:
        data_dir: Path to directory containing CSV data files
        tfl_ids: List of subject IDs in the TFL treatment group
        msc_ids: List of subject IDs in the MSC treatment group
        r2_threshold: Minimum R² for linear region detection
        window_fraction: Fraction of data points for sliding window
        min_window: Minimum window size in data points
        
    Returns:
        DataFrame with analysis results, or None if processing fails.
    """
    logger.info("=" * 60)
    logger.info("SSP BIOMECHANICS ANALYSIS PIPELINE")
    logger.info("=" * 60)

    if not data_dir.exists():
        logger.error(f"Folder not found: {data_dir}")
        return None

    files = sorted([f for f in data_dir.iterdir() if f.suffix.lower() == ".csv"])
    data_records: List[Dict] = []

    logger.info(f"Processing {len(files)} files...")

    for file_path in files:
        filename = file_path.name
        try:
            s_id, cond, sub = classify_sample(filename, tfl_ids, msc_ids)

            if cond == "Unknown":
                logger.warning(f"Skipping {filename}: Could not determine NO/OPER.")
                continue

            df = pd.read_csv(file_path)
            
            # Validate data
            validation_errors = validate_raw_data(df)
            if validation_errors:
                logger.warning(f"Skipping {filename}: {'; '.join(validation_errors)}")
                continue
            
            # Normalize load column
            df = normalize_load_column(df)
            y_col = "LoadN"

            # Truncate at max load (failure point)
            max_idx = df[y_col].idxmax()
            df_trunc = df.iloc[: max_idx + 1].copy()
            x = df_trunc["Crossheadmm"].values
            y = df_trunc[y_col].values

            # Calculate energy (area under curve)
            energy_mJ = safe_trapezoid(y, x)

            # Find stiffness using sliding window
            window_span = max(min_window, int(len(x) * window_fraction))
            slope, intercept, r2, idx_start, idx_end = find_best_stiffness(
                x, y, window_span, r2_threshold
            )
            stiffness_N_mm = slope

            data_records.append({
                "Filename": filename,
                "SampleID": s_id,
                "Subgroup": sub,
                "MaxLoad_N": float(df[y_col].max()),
                "Stiffness_N_mm": stiffness_N_mm,
                "Energy_mJ": energy_mJ,
                "R2_Score": r2,
                "Linear_Start_Idx": idx_start,
                "Linear_End_Idx": idx_end
            })

            logger.info(
                f"[OK] {filename} -> {sub}: "
                f"MaxLoad={df[y_col].max():.1f}N, Stiffness={stiffness_N_mm:.1f}N/mm"
            )

        except pd.errors.EmptyDataError:
            logger.error(f"Empty data file: {filename}")
        except pd.errors.ParserError as e:
            logger.error(f"CSV parsing error in {filename}: {e}")
        except KeyError as e:
            logger.error(f"Missing column in {filename}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing {filename}: {e}", exc_info=True)

    metadata = pd.DataFrame(data_records)
    logger.info(f"Processed {len(metadata)} samples successfully.")

    return metadata


def generate_statistics(metadata: pd.DataFrame) -> pd.DataFrame:
    """
    Generate group statistics from the analysis results.
    
    Args:
        metadata: DataFrame with analysis results from process_all_files()
        
    Returns:
        DataFrame with summary statistics grouped by Subgroup.
    """
    logger.info("=" * 60)
    logger.info("GROUP STATISTICS")
    logger.info("=" * 60)

    def list_ids(series: pd.Series) -> str:
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

    logger.info("\n" + stats.to_string())

    return stats


def save_results(
    metadata: pd.DataFrame,
    stats: pd.DataFrame,
    results_dir: Path
) -> Tuple[Path, Path]:
    """
    Save analysis results to CSV files.
    
    Args:
        metadata: DataFrame with detailed sample results
        stats: DataFrame with group statistics
        results_dir: Directory to save output files
        
    Returns:
        Tuple of (detail_path, stats_path) for the saved files.
    """
    logger.info("=" * 60)
    logger.info("SAVING RESULTS")
    logger.info("=" * 60)

    results_dir.mkdir(parents=True, exist_ok=True)

    detail_path = results_dir / "Experiment_Master_Log_Detailed.csv"
    metadata.to_csv(detail_path, index=False)
    logger.info(f"Saved: {detail_path}")

    stats_path = results_dir / "Group_Statistics_Detailed.csv"
    stats.to_csv(stats_path)
    logger.info(f"Saved: {stats_path}")
    
    return detail_path, stats_path


def create_plots(metadata: pd.DataFrame, results_dir: Path) -> Path:
    """
    Create summary bar plots for each treatment group.
    
    Args:
        metadata: DataFrame with analysis results
        results_dir: Directory to save the plot
        
    Returns:
        Path to the saved plot file.
    """
    logger.info("=" * 60)
    logger.info("GENERATING PLOTS")
    logger.info("=" * 60)

    import matplotlib.pyplot as plt

    # Use a style that's available in most matplotlib versions
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        try:
            plt.style.use("seaborn-whitegrid")
        except OSError:
            logger.debug("Seaborn style not available, using default")
    
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
            std_val = stds[j] if not np.isnan(stds[j]) else 0
            axes[i].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + std_val + 5,
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

    logger.info(f"Saved: {plot_path}")
    return plot_path


def run_pipeline(config: Dict, data_root: Path) -> Optional[pd.DataFrame]:
    """
    Run the full analysis pipeline.
    
    This is the main entry point that orchestrates the entire analysis:
    1. Load configuration
    2. Process all data files
    3. Generate statistics
    4. Save results and create plots
    
    Args:
        config: Configuration dictionary (from config.json)
        data_root: Root directory for data files
        
    Returns:
        DataFrame with analysis results, or None if processing fails.
    """
    # Configure logging for pipeline run
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
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
        logger.error("No data processed. Check your data folder.")
        return None

    stats = generate_statistics(metadata)
    save_results(metadata, stats, results_dir)
    create_plots(metadata, results_dir)

    logger.info("=" * 60)
    logger.info("[OK] ANALYSIS COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Total samples processed: {len(metadata)}")
    logger.info(f"Results saved to: {results_dir}")
    logger.info("Files generated:")
    logger.info("  - Experiment_Master_Log_Detailed.csv")
    logger.info("  - Group_Statistics_Detailed.csv")
    logger.info("  - Combined_Group_Plots.png")
    
    return metadata
