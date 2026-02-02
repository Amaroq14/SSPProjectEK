"""
SSP Shared Utilities
====================
Common utilities shared across the SSP analysis pipeline.

This module consolidates parsing logic and validation functions
to ensure consistency across all components.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# FILENAME PARSING
# =============================================================================

def parse_filename(filename: str) -> Tuple[Optional[str], str]:
    """
    Parse an SSP data filename to extract subject ID and condition.
    
    Args:
        filename: The filename to parse (e.g., 'SSP_2025-03-17_D1_NO.csv')
        
    Returns:
        Tuple of (subject_id, condition) where:
        - subject_id: e.g., 'D1', 'B5', 'C2' or None if not found
        - condition: 'NO', 'OPER', or 'Unknown'
    
    Example:
        >>> parse_filename('SSP_2025-03-17_D1_NO.csv')
        ('D1', 'NO')
        >>> parse_filename('SSP_2022-12-08_B5_OPER.csv')
        ('B5', 'OPER')
    """
    # Determine condition
    condition = "Unknown"
    if "_NO" in filename or "_NO." in filename:
        condition = "NO"
    elif "_OPER" in filename:
        condition = "OPER"
    
    # Extract subject ID (B1, C2, D15, etc.)
    subject_id = None
    parts = filename.replace(".csv", "").split("_")
    for part in parts:
        # Match pattern: Letter followed by 1-2 digits
        if re.match(r'^[BCD]\d{1,2}$', part):
            subject_id = part
            break
    
    return subject_id, condition


def build_sample_id(filename: str) -> Optional[str]:
    """
    Build a sample ID from a filename.
    
    Args:
        filename: The filename to parse
        
    Returns:
        Sample ID in format 'SubjectID_Condition' (e.g., 'D1_NO', 'B5_OPER')
        or None if parsing fails.
    
    Example:
        >>> build_sample_id('SSP_2025-03-17_D1_NO.csv')
        'D1_NO'
    """
    subject_id, condition = parse_filename(filename)
    if not subject_id or condition == "Unknown":
        return None
    return f"{subject_id}_{condition}"


def classify_sample(
    filename: str,
    tfl_ids: List[str],
    msc_ids: List[str]
) -> Tuple[str, str, str]:
    """
    Parse filename to find Sample ID, Condition (NO/OPER), and Subgroup.
    
    Args:
        filename: The data filename
        tfl_ids: List of subject IDs in the TFL group
        msc_ids: List of subject IDs in the MSC group
        
    Returns:
        Tuple of (sample_id, condition, subgroup) where:
        - sample_id: Subject identifier (e.g., 'D1', 'B5')
        - condition: 'NO', 'OPER', or 'Unknown'
        - subgroup: 'NON', 'TFL', 'MSC', or 'Unassigned'
    """
    subject_id, condition = parse_filename(filename)
    
    if subject_id is None:
        subject_id = "Unknown"
    
    subgroup = "Unassigned"
    
    # Non-operated samples are always in the NON (control) group
    if condition == "NO":
        subgroup = "NON"
    elif condition == "OPER":
        # Determine treatment group based on subject ID
        if subject_id in tfl_ids:
            subgroup = "TFL"
        elif subject_id in msc_ids:
            subgroup = "MSC"
    
    return subject_id, condition, subgroup


def extract_test_date(filename: str) -> Optional[str]:
    """
    Extract the test date from an SSP filename.
    
    Args:
        filename: The filename (e.g., 'SSP_2025-03-17_D1_NO.csv')
        
    Returns:
        Date string in YYYY-MM-DD format, or None if not found.
    
    Example:
        >>> extract_test_date('SSP_2025-03-17_D1_NO.csv')
        '2025-03-17'
    """
    parts = filename.split('_')
    if len(parts) >= 2:
        # Check if second part matches date pattern
        date_candidate = parts[1]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_candidate):
            return date_candidate
    return None


# =============================================================================
# DATA VALIDATION
# =============================================================================

def validate_raw_data(df: pd.DataFrame) -> List[str]:
    """
    Validate that a raw data DataFrame has required columns and valid values.
    
    Args:
        df: DataFrame loaded from a raw data CSV file
        
    Returns:
        List of error messages. Empty list if validation passes.
    
    Example:
        >>> df = pd.read_csv('data.csv')
        >>> errors = validate_raw_data(df)
        >>> if errors:
        ...     print("Validation failed:", errors)
    """
    errors = []
    
    # Check for required columns
    required_cols = ['Crossheadmm', 'LoadN']
    for col in required_cols:
        if col not in df.columns:
            # Check for alternative column names
            if col == 'LoadN' and 'LoadkN' in df.columns:
                continue  # LoadkN is acceptable
            errors.append(f"Missing required column: {col}")
    
    if errors:
        return errors  # Can't validate further without required columns
    
    # Check for empty data
    if len(df) == 0:
        errors.append("Data file is empty")
        return errors
    
    # Check for valid displacement values
    if 'Crossheadmm' in df.columns:
        if df['Crossheadmm'].isna().all():
            errors.append("All displacement values are missing")
        elif (df['Crossheadmm'] < 0).any():
            errors.append("Negative displacement values detected")
    
    # Check for valid load values
    load_col = 'LoadN' if 'LoadN' in df.columns else 'LoadkN'
    if load_col in df.columns:
        if df[load_col].isna().all():
            errors.append("All load values are missing")
    
    # Check for minimum data points
    min_points = 10
    if len(df) < min_points:
        errors.append(f"Insufficient data points: {len(df)} < {min_points}")
    
    return errors


def normalize_load_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure DataFrame has LoadN column in Newtons.
    
    If LoadkN exists, converts to LoadN. Returns a copy of the DataFrame.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with LoadN column
    """
    df = df.copy()
    if 'LoadN' not in df.columns and 'LoadkN' in df.columns:
        df['LoadN'] = df['LoadkN'] * 1000
        logger.debug("Converted LoadkN to LoadN")
    return df


# =============================================================================
# NUMERICAL UTILITIES
# =============================================================================

def safe_trapezoid(y: np.ndarray, x: np.ndarray) -> float:
    """
    Compute the area under a curve using the trapezoidal rule.
    
    This is a compatibility wrapper that works with both NumPy 1.x and 2.x.
    
    Args:
        y: Array of y values (e.g., load)
        x: Array of x values (e.g., displacement)
        
    Returns:
        The integral (area under the curve)
    """
    # np.trapz is available in all NumPy versions
    # np.trapezoid was added in NumPy 2.0
    return float(np.trapz(y, x))


def compute_linear_fit(
    x: np.ndarray,
    y: np.ndarray
) -> Tuple[float, float, float]:
    """
    Compute linear regression fit for x, y data.
    
    Args:
        x: Independent variable array
        y: Dependent variable array
        
    Returns:
        Tuple of (slope, intercept, r_squared)
    """
    if len(x) < 2:
        return 0.0, 0.0, 0.0
    
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs[0], coeffs[1]
    
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    
    return float(slope), float(intercept), float(r_squared)
