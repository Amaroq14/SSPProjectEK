# SSP Biomechanics Study Database

A SQLite database system for managing experimental data from the supraspinatus tear surgical comparison study.

## Quick Start

### 1. Install Dependencies
```bash
pip install pandas numpy matplotlib scikit-learn
```

### 2. Initialize Database with Your Data
```bash
cd Data/database
python import_existing_data.py
```

This will:
- Create the database (`ssp_study.db`)
- Import your Notion data (subjects, samples, procedures)
- Import your Analysis Pipeline results
- Export verification CSVs

### 3. Verify and Update Data
```bash
python verify_and_update.py
```

Interactive tool to:
- View all subjects and samples by group
- Check for missing data (weights, IDs, results)
- Update individual records
- Export data for review in Excel/Notion

### 4. Update Results from Analysis
```bash
cd Data/database
python update_results.py
```

### 5. Use in Your Analysis

```python
from ssp_database import SSPDatabase

# Connect to database
db = SSPDatabase()

# Query results
results = db.get_results(treatment_group='MSC')
print(results)

# Get group statistics
stats = db.get_group_statistics()
print(stats)

# Custom SQL query
df = db.execute_query("""
    SELECT sample_id, max_load_N, stiffness_N_mm 
    FROM v_full_results 
    WHERE treatment_group = 'TFL'
""")
```

---

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `subjects` | Animal/specimen information (ID, weight, status) |
| `treatment_groups` | Group definitions (NON, TFL, MSC) |
| `procedures` | Surgical procedures timeline |
| `samples` | Test specimens (operated vs non-operated) |
| `biomechanical_tests` | Test session metadata |
| `results` | Calculated biomechanical properties |
| `manual_results` | User-selected manual stiffness results |

### Key Views

| View | Description |
|------|-------------|
| `v_sample_details` | Samples with subject info joined |
| `v_full_results` | Complete results with all metadata |
| `v_group_statistics` | Summary statistics by group |

---

## Common Operations

### Add a New Subject
```python
db.add_subject(
    subject_id='D17',
    internal_id='B/MSC-H10',
    weight_kg=4.2,
    status='Extracted'
)
```

### Add a New Sample
```python
db.add_sample(
    sample_id='D17_OPER',
    subject_id='D17',
    condition='operated',
    treatment_group='MSC',
    extraction_date='2025-01-20'
)
```

### Add Test Results
```python
# Add test metadata
test_id = db.add_test(
    sample_id='D17_OPER',
    test_date='2025-01-22',
    data_filename='SSP_2025-01-22_D17_OPER.csv'
)

# Add calculated results
db.add_result(
    test_id=test_id,
    sample_id='D17_OPER',
    max_load_N=165.5,
    stiffness_N_mm=52.3,
    energy_to_failure_mJ=720.5,
    linear_region_r2=0.998
)
```

### Query Results by Group
```python
# Get all MSC results
msc_results = db.get_results(treatment_group='MSC')

# Get specific sample
sample_results = db.get_results(sample_id='D17_OPER')

# Get statistics
stats = db.get_group_statistics()
```

### Export Data
```python
# Export all tables to CSV
exports = db.export_to_csv('path/to/output')
```

---

## Integration with Analysis Pipeline

The canonical pipeline is `Data/run_analysis.py`. After running it, use:

```bash
cd Data/database
python update_results.py
```

---

## Group Assignments

Group assignments live in `Data/config.json` under `groups`.
Update that file and re-run `python run_analysis.py`.

---

## File Structure

```
Data/
├── config.json                 # Central config (paths + group IDs)
├── analysis_pipeline.py        # Canonical analysis logic
├── run_analysis.py             # Entry point script
├── database/
│   ├── schema.sql              # Database schema definition
│   ├── ssp_database.py         # Python database manager class
│   ├── import_existing_data.py # Import script (edit NOTION_DATA here)
│   ├── update_results.py       # Load analysis results into DB
│   ├── verify_and_update.py    # Interactive verification/update tool
│   ├── ssp_study.db            # SQLite database (created after import)
│   ├── README.md               # This file
│   └── exports/                # CSV exports (created after import)
│       ├── subjects.csv
│       ├── samples.csv
│       ├── results.csv
│       ├── full_results.csv
│       ├── data_review.csv     # Full export for verification
│       └── notion_import.csv   # Format for Notion re-import
├── Selected_data/              # Raw CSV data files
├── Results/                    # Analysis outputs
└── Analysis_Pipeline.ipynb     # Legacy notebook (reference only)
```

---

## Backup & Sharing

The database is a single file (`ssp_study.db`). To backup or share:

```bash
# Backup
cp ssp_study.db ssp_study_backup_2025-01-25.db

# The file can be opened with any SQLite viewer:
# - DB Browser for SQLite (free, cross-platform)
# - DBeaver (free, cross-platform)
# - SQLiteStudio (free, cross-platform)
```

---

## Troubleshooting

### "Subject already exists" error
The database enforces unique IDs. Use `update_subject()` to modify:
```python
db.update_subject('B1', weight_kg=4.8, status='Completed')
```

### Missing foreign key
Ensure you add subjects before samples, and samples before results:
```python
db.add_subject('D17', ...)  # First
db.add_sample('D17_OPER', subject_id='D17', ...)  # Second
test_id = db.add_test(sample_id='D17_OPER', ...)  # Third
db.add_result(test_id=test_id, sample_id='D17_OPER', ...)  # Fourth
```

### Re-import everything
Delete the database file and run import again:
```bash
rm ssp_study.db
python import_existing_data.py
```
