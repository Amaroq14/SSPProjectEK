"""
Utilities for the SSP Streamlit app.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from ssp_config import get_config_paths, load_config


@st.cache_data(show_spinner=False)
def load_app_config() -> Tuple[Dict, Path, Dict[str, Path]]:
    config, data_root, _ = load_config()
    paths = get_config_paths(config, data_root)
    return config, data_root, paths


@st.cache_data(show_spinner=False)
def load_results_csv(results_path: Path) -> pd.DataFrame:
    if not results_path.exists():
        return pd.DataFrame()
    return pd.read_csv(results_path)


def parse_filename(filename: str) -> Tuple[Optional[str], str]:
    condition = "Unknown"
    if "_NO" in filename:
        condition = "NO"
    elif "_OPER" in filename:
        condition = "OPER"

    subject_id = None
    for part in filename.replace(".csv", "").split("_"):
        if part.startswith(("B", "C", "D")) and len(part) <= 3:
            subject_id = part
            break

    return subject_id, condition


def build_sample_id(filename: str) -> Optional[str]:
    subject_id, condition = parse_filename(filename)
    if not subject_id or condition == "Unknown":
        return None
    suffix = "NO" if condition == "NO" else "OPER"
    return f"{subject_id}_{suffix}"


def get_metadata_for_sample(db_path: Path, sample_id: str) -> Dict:
    query = "SELECT * FROM v_sample_details WHERE sample_id = ?"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(query, (sample_id,)).fetchone()
        return dict(row) if row else {}


def load_raw_curve(file_path: Path) -> Optional[pd.DataFrame]:
    if not file_path.exists():
        return None
    df = pd.read_csv(file_path)
    if "LoadN" not in df.columns and "LoadkN" in df.columns:
        df["LoadN"] = df["LoadkN"] * 1000
    return df


def compute_manual_stiffness(
    x: np.ndarray,
    y: np.ndarray,
    indices: List[int]
) -> Optional[Dict[str, float]]:
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
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "manual_stiffness.csv"
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    record_with_time = {"timestamp_utc": timestamp, **record}

    if output_path.exists():
        df = pd.read_csv(output_path)
        if "filename" in record_with_time:
            df = df[df["filename"] != record_with_time["filename"]]
        df = pd.concat([df, pd.DataFrame([record_with_time])], ignore_index=True)
    else:
        df = pd.DataFrame([record_with_time])

    df.to_csv(output_path, index=False)
    return output_path


def ensure_manual_results_table(db_path: Path) -> None:
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
    with sqlite3.connect(db_path) as conn:
        conn.execute(create_sql)
        conn.commit()


def save_manual_result_db(db_path: Path, record: Dict) -> None:
    ensure_manual_results_table(db_path)
    insert_sql = """
    INSERT INTO manual_results
    (sample_id, data_filename, reviewer, session_id, selection_start_idx,
     selection_end_idx, manual_stiffness_N_mm, manual_r2, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute(insert_sql, (
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


def load_manual_results_csv(results_dir: Path) -> pd.DataFrame:
    output_path = results_dir / "manual_stiffness.csv"
    if not output_path.exists():
        return pd.DataFrame()
    return pd.read_csv(output_path)
