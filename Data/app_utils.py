"""
Utilities for the SSP Streamlit app.
=====================================

This module provides helper functions for the interactive Streamlit application,
including data loading, metadata lookup, and manual stiffness calculations.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from ssp_config import get_config_paths, load_config
from utils import parse_filename, build_sample_id, normalize_load_column

# Configure module logger
logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "load_app_config",
    "load_results_csv",
    "parse_filename",
    "build_sample_id",
    "get_metadata_for_sample",
    "load_raw_curve",
    "compute_manual_stiffness",
    "save_manual_result",
    "save_manual_result_db",
    "load_manual_results_csv",
]


@st.cache_data(show_spinner=False)
def load_app_config() -> Tuple[Dict, Path, Dict[str, Path]]:
    """Load application configuration from config.json."""
    config, data_root, _ = load_config()
    paths = get_config_paths(config, data_root)
    return config, data_root, paths


@st.cache_data(show_spinner=False)
def load_results_csv(results_path: Path) -> pd.DataFrame:
    """Load analysis results from CSV file."""
    if not results_path.exists():
        logger.warning(f"Results file not found: {results_path}")
        return pd.DataFrame()
    return pd.read_csv(results_path)


def get_metadata_for_sample(db_path: Path, sample_id: str) -> Dict:
    """
    Retrieve sample metadata from the database.
    
    Args:
        db_path: Path to the SQLite database
        sample_id: Sample identifier (e.g., 'D1_NO')
        
    Returns:
        Dictionary with sample metadata, or empty dict if not found.
    """
    if not db_path.exists():
        logger.debug(f"Database not found: {db_path}")
        return {}
    
    query = "SELECT * FROM v_sample_details WHERE sample_id = ?"
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, (sample_id,)).fetchone()
            return dict(row) if row else {}
    except sqlite3.OperationalError as e:
        logger.warning(f"Database query failed: {e}")
        return {}


def load_raw_curve(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Load raw load-displacement curve data from CSV.
    
    Args:
        file_path: Path to the CSV data file
        
    Returns:
        DataFrame with normalized columns, or None if file not found.
    """
    if not file_path.exists():
        logger.warning(f"Raw data file not found: {file_path}")
        return None
    
    try:
        df = pd.read_csv(file_path)
        return normalize_load_column(df)
    except pd.errors.EmptyDataError:
        logger.error(f"Empty data file: {file_path}")
        return None
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        return None


def compute_manual_stiffness(
    x: np.ndarray,
    y: np.ndarray,
    indices: List[int]
) -> Optional[Dict[str, float]]:
    """
    Compute stiffness from user-selected data points.
    
    Args:
        x: Full displacement array
        y: Full load array
        indices: List of selected point indices
        
    Returns:
        Dictionary with slope, intercept, r2, start_idx, end_idx
        or None if insufficient points selected.
    """
    if len(indices) < 2:
        return None
    
    idx = sorted(set(indices))
    x_sel = x[idx]
    y_sel = y[idx]
    
    if len(x_sel) < 2:
        return None

    slope, intercept = np.polyfit(x_sel, y_sel, 1)
    y_pred = slope * x_sel + intercept
    ss_res = np.sum((y_sel - y_pred) ** 2)
    ss_tot = np.sum((y_sel - np.mean(y_sel)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r2),
        "start_idx": int(min(idx)),
        "end_idx": int(max(idx))
    }


def save_manual_result(results_dir: Path, record: Dict) -> Path:
    """
    Save a manual stiffness result to CSV.
    
    Args:
        results_dir: Directory to save results
        record: Dictionary with result data
        
    Returns:
        Path to the saved CSV file.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "manual_stiffness.csv"
    
    # Use timezone-aware UTC timestamp
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record_with_time = {"timestamp_utc": timestamp, **record}

    if output_path.exists():
        df = pd.read_csv(output_path)
        if "filename" in record_with_time:
            df = df[df["filename"] != record_with_time["filename"]]
        df = pd.concat([df, pd.DataFrame([record_with_time])], ignore_index=True)
    else:
        df = pd.DataFrame([record_with_time])

    df.to_csv(output_path, index=False)
    logger.info(f"Saved manual result to {output_path}")
    return output_path


def ensure_manual_results_table(db_path: Path) -> None:
    """
    Ensure the manual_results table exists in the database.
    
    Args:
        db_path: Path to the SQLite database
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS manual_results (
        manual_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_id TEXT NOT NULL,
        data_filename TEXT NOT NULL,
        reviewer TEXT,
        session_id TEXT,
        selection_start_idx INTEGER NOT NULL,
        selection_end_idx INTEGER NOT NULL,
        manual_stiffness_N_mm REAL NOT NULL,
        manual_r2 REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
    );
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(create_sql)
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to create manual_results table: {e}")
        raise


def save_manual_result_db(db_path: Path, record: Dict) -> Optional[int]:
    """
    Save a manual stiffness result to the database.
    
    Args:
        db_path: Path to the SQLite database
        record: Dictionary with result data
        
    Returns:
        The ID of the inserted row, or None if insertion failed.
    """
    ensure_manual_results_table(db_path)
    insert_sql = """
    INSERT INTO manual_results
    (sample_id, data_filename, reviewer, session_id, selection_start_idx,
     selection_end_idx, manual_stiffness_N_mm, manual_r2, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(insert_sql, (
                record.get("sample_id"),
                record.get("filename"),
                record.get("reviewer"),
                record.get("session_id"),
                record.get("selection_start_idx"),
                record.get("selection_end_idx"),
                record.get("manual_stiffness_N_mm"),
                record.get("manual_r2"),
                record.get("notes")
            ))
            conn.commit()
            logger.info(f"Saved manual result to database (id={cursor.lastrowid})")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Failed to save manual result to database: {e}")
        return None


def load_manual_results_csv(results_dir: Path) -> pd.DataFrame:
    """
    Load manual stiffness results from CSV.
    
    Args:
        results_dir: Directory containing the results
        
    Returns:
        DataFrame with manual results, or empty DataFrame if file not found.
    """
    output_path = results_dir / "manual_stiffness.csv"
    if not output_path.exists():
        return pd.DataFrame()
    return pd.read_csv(output_path)
