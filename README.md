# SSP Biomechanics Analysis Pipeline

## Comparative Evaluation of Surgical Methods in the Treatment of Chronic Irreparable Supraspinatus Tears: A Biomechanical Study

**Authors:** E. Koumantou, C. J. Feroussis, E. D. Pasiou, S. K. Kourkoulis

**Affiliations:**
- National Technical University of Athens, Laboratory of Biomechanics and Biomedical Physics
- National and Kapodistrian University of Athens, School of Medicine

---

## Project Structure

```
2_SSP_Project/
├── Analysis_Pipeline.ipynb   # Self-contained analysis notebook (run this)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .gitignore
│
├── Selected_data/            # Pipeline input: 46 curated CSVs (B, C, D series)
├── Results/                  # Pipeline output: plots & summary CSVs
│
├── CADs/                     # 3D models of the testing apparatus
├── Photos/                   # Experiment photos organised by date
│
├── Raw_Data/                 # Archival raw data
│   ├── InitialData/          #   Original B-series .txt files & C/D-series CSVs
│   ├── Ferousis-Koumantou_MTS/  # Raw MTS machine output by date
│   ├── Initial_Data.pdf
│   └── Selected_Data.pdf
│
└── MATLAB/                   # Legacy MATLAB analysis files
    ├── Analysis_Pipeline.m
    ├── SSP_Pipeline.mlx
    ├── Thesis_code.mlx
    └── SSP_Project/          # MATLAB project with scripts & resources
```

---

## Overview

This Jupyter notebook implements the biomechanical analysis pipeline for evaluating surgical repair methods of chronic supraspinatus tendon tears in a rabbit model. The study compares three groups:

| Group | Description | Treatment |
|-------|-------------|-----------|
| **NON** | Non-operated control | Intact contralateral shoulder |
| **TFL** | TFL Allograft | Tensor fascia lata reconstruction |
| **MSC** | TFL + Stem Cells | TFL allograft with bone marrow mesenchymal stem cells |

The entire analysis -- configuration, data loading, computation, statistics, and plotting -- is contained in a **single self-contained notebook** (`Analysis_Pipeline.ipynb`). No additional Python files are required.

---

## Methods

### Biomechanical Testing
- **Test type:** Uniaxial tension to failure
- **Loading rate:** 1 mm/min
- **Machine:** MTS testing system

### Metrics Calculated

| Metric | Description | Unit |
|--------|-------------|------|
| **Max Load** | Ultimate failure load | N |
| **Stiffness** | Slope of the stiffest linear region | N/mm |
| **Energy** | Area under load-displacement curve (work to failure) | mJ |

### Stiffness Calculation Algorithm
1. Truncate curve at maximum load (failure point)
2. Apply sliding window (10% of data points, minimum 5 points)
3. Fit linear regression in each window
4. Select region with highest slope where R² >= 0.99
5. If no region meets R² threshold, use region with best R²

---

## Sample Assignments

### TFL Group (11 specimens)
B1, B10, B11, D1, D2, D3, D4, D5, D6, D7, D8

### MSC Group (13 specimens)
B5, B6, B7, B9, C1, C2, D9, D10, D11, D12, D13, D14, D15

Each specimen has both a **NO** (non-operated contralateral) and an **OPER** (operated) data file, giving 46 CSVs total.

### Sample Exclusion

Individual samples can be excluded from the analysis by editing the `EXCLUDED_SAMPLES` list at the top of the notebook:

```python
# Exclude specific samples:
EXCLUDED_SAMPLES = ['B1', 'D15']

# Include all samples (default):
EXCLUDED_SAMPLES = []
```

---

## How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Notebook
```bash
jupyter notebook Analysis_Pipeline.ipynb
```

Or open in JupyterLab / VS Code / Cursor and run all cells sequentially.

### 3. Output
Results are saved to the `Results/` folder (created automatically):
- `Experiment_Master_Log_Detailed.csv` -- All sample data
- `Group_Statistics_Detailed.csv` -- Summary statistics
- `Combined_Group_Plots.png` -- Group comparison bar charts
- `Plot_NON.png`, `Plot_TFL.png`, `Plot_MSC.png` -- Individual load-displacement curves

---

## Notebook Structure

| Cell | Content |
|------|---------|
| 1 | Title and abstract |
| 2 | Setup description |
| 3 | Imports, configuration, sample selection, and all core functions |
| 4 | Classification function demonstration |
| 5 | Run analysis pipeline |
| 6 | Generate and display statistics |
| 7 | Group comparison bar charts |
| 8 | Individual load-displacement curves by group |
| 9 | Interactive Plotly visualisations |
| 10 | Stiffness visualisation for all subjects |

---

## Conclusion

The biomechanical analysis demonstrates that MSC-enhanced TFL grafts show improved mechanical properties compared to TFL-only grafts, suggesting that bone marrow mesenchymal stem cells may contribute to enhanced tendon healing. However, both operated groups remain significantly weaker than intact controls, indicating that complete restoration of native tissue properties is not achieved with either method.

---

## License

This project is for academic research purposes.

## Contact

For questions about this analysis, please contact the authors.
