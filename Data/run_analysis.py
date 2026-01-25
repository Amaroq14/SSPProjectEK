"""
SSP Biomechanics Analysis Pipeline - Standalone Script
=======================================================
Processes all samples (B, C, D series) and generates results.

Usage:
    cd Data
    python run_analysis.py
"""

from ssp_config import load_config
from analysis_pipeline import run_pipeline


def main():
    """Main analysis pipeline."""
    config, data_root, _ = load_config()
    run_pipeline(config, data_root)


if __name__ == "__main__":
    main()
