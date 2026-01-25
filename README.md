# SSP Project
Comparative evaluation of surgical methods in the treatment of chronic irreparable supraspinatus tears.

Biomechanics analysis pipeline and database for the supraspinatus tear surgical comparison study.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Convert B-series (optional)
```bash
cd Data
python convert_b_series.py
```

### 3. Run Analysis
```bash
cd Data
python run_analysis.py
```

### 4. Update Database
```bash
cd Data/database
python update_results.py
```

### 5. Launch Interactive App
```bash
streamlit run Data/app.py
```

Manual stiffness selections are stored in:
- `Data/Results/manual_stiffness.csv`
- Database table `manual_results` in `Data/database/ssp_study.db`

## Configuration

All paths and group assignments live in `Data/config.json`.

Key fields:
- `data_paths.selected_data_dir`: input CSVs
- `data_paths.results_dir`: analysis outputs
- `groups.TFL_IDS` / `groups.MSC_IDS`: subgroup assignments

## Project Layout

```
Data/
├── config.json                 # Central config (paths + group IDs)
├── analysis_pipeline.py        # Canonical analysis logic
├── run_analysis.py             # Entry point script
├── convert_b_series.py         # Convert legacy B-series TXT files
├── app.py                      # Interactive Streamlit UI
├── app_utils.py                # App helper utilities
├── Selected_data/              # Input CSVs
├── Results/                    # Output results + plots
└── database/                   # SQLite DB + scripts
```

## Tests

```bash
pytest
```
