"""
Configuration loader for SSP analysis tools.
"""

import json
from pathlib import Path
from typing import Dict, Tuple

DEFAULT_CONFIG_FILENAME = "config.json"


def get_data_root() -> Path:
    """Return the Data directory path."""
    return Path(__file__).resolve().parent


def load_config(config_path: str = None) -> Tuple[Dict, Path, Path]:
    """
    Load config file and return (config, data_root, config_path).
    """
    data_root = get_data_root()
    resolved_path = Path(config_path) if config_path else data_root / DEFAULT_CONFIG_FILENAME
    with open(resolved_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config, data_root, resolved_path


def resolve_path(path_str: str, base_dir: Path) -> Path:
    """Resolve a config path relative to base_dir."""
    return (base_dir / path_str).resolve()


def get_config_paths(config: Dict, base_dir: Path) -> Dict[str, Path]:
    """Return resolved paths from config."""
    paths = config.get("data_paths", {})
    return {key: resolve_path(value, base_dir) for key, value in paths.items()}


def get_group_ids(config: Dict) -> Tuple[list, list]:
    """Return (TFL_IDS, MSC_IDS) from config."""
    groups = config.get("groups", {})
    return groups.get("TFL_IDS", []), groups.get("MSC_IDS", [])
