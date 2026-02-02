import sys
from pathlib import Path

import numpy as np
import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"
sys.path.insert(0, str(DATA_DIR))

from analysis_pipeline import classify_sample, find_best_stiffness
from ssp_config import load_config, get_group_ids


def _get_group_ids():
    config, _, _ = load_config()
    return get_group_ids(config)


def test_classify_sample_oper_tfl():
    tfl_ids, msc_ids = _get_group_ids()
    sample_id, condition, subgroup = classify_sample(
        "SSP_2025-03-20_D1_OPER.csv",
        tfl_ids,
        msc_ids
    )
    assert sample_id == "D1"
    assert condition == "OPER"
    assert subgroup == "TFL"


def test_classify_sample_oper_msc():
    tfl_ids, msc_ids = _get_group_ids()
    sample_id, condition, subgroup = classify_sample(
        "SSP_2025-03-20_D9_OPER.csv",
        tfl_ids,
        msc_ids
    )
    assert sample_id == "D9"
    assert condition == "OPER"
    assert subgroup == "MSC"


def test_classify_sample_non_operated():
    tfl_ids, msc_ids = _get_group_ids()
    sample_id, condition, subgroup = classify_sample(
        "SSP_2022-12-08_B5_NO.csv",
        tfl_ids,
        msc_ids
    )
    assert sample_id == "B5"
    assert condition == "NO"
    assert subgroup == "NON"


def test_find_best_stiffness_linear():
    x = np.arange(0, 10, dtype=float)
    y = 2.0 * x
    slope, intercept, r2, start_idx, end_idx = find_best_stiffness(
        x, y, window_size=5, r2_threshold=0.99
    )
    assert slope == pytest.approx(2.0, rel=1e-3)
    assert r2 == pytest.approx(1.0, rel=1e-6)
