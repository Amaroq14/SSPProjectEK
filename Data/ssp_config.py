"""
Configuration loader for SSP analysis tools.
=============================================

Provides functions to load and parse the central configuration file (config.json)
that controls paths, group assignments, and analysis parameters.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILENAME = "config.json"


def get_data_root() -> Path:
    """
    Return the Data directory path.
    
    Returns:
        Path to the Data directory (where this module is located).
    """
    return Path(__file__).resolve().parent


def load_config(config_path: Optional[Union[str, Path]] = None) -> Tuple[Dict[str, Any], Path, Path]:
    """
    Load configuration file and return parsed config with paths.
    
    Args:
        config_path: Optional path to config file. Defaults to config.json
                    in the Data directory.
    
    Returns:
        Tuple of (config_dict, data_root_path, config_file_path)
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    data_root = get_data_root()
    resolved_path = Path(config_path) if config_path else data_root / DEFAULT_CONFIG_FILENAME
    
    if not resolved_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {resolved_path}")
    
    with open(resolved_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    logger.debug(f"Loaded configuration from {resolved_path}")
    return config, data_root, resolved_path


def resolve_path(path_str: str, base_dir: Path) -> Path:
    """
    Resolve a config path relative to base_dir.
    
    Args:
        path_str: Relative path string from config
        base_dir: Base directory to resolve against
        
    Returns:
        Resolved absolute Path
    """
    return (base_dir / path_str).resolve()


def get_config_paths(config: Dict[str, Any], base_dir: Path) -> Dict[str, Path]:
    """
    Return resolved paths from config.
    
    Args:
        config: Configuration dictionary
        base_dir: Base directory to resolve relative paths against
        
    Returns:
        Dictionary mapping path names to resolved Path objects
    """
    paths = config.get("data_paths", {})
    return {key: resolve_path(value, base_dir) for key, value in paths.items()}


def get_group_ids(config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Return treatment group subject IDs from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (TFL_IDS, MSC_IDS) lists
    """
    groups = config.get("groups", {})
    return groups.get("TFL_IDS", []), groups.get("MSC_IDS", [])


def get_analysis_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return analysis parameters from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with analysis parameters:
        - stiffness_r2_threshold: float
        - stiffness_window_fraction: float
        - stiffness_min_window: int
    """
    analysis = config.get("analysis", {})
    return {
        "stiffness_r2_threshold": float(analysis.get("stiffness_r2_threshold", 0.99)),
        "stiffness_window_fraction": float(analysis.get("stiffness_window_fraction", 0.1)),
        "stiffness_min_window": int(analysis.get("stiffness_min_window", 5)),
    }
