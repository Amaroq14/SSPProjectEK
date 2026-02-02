# SSP Biomechanics Analysis Pipeline

## Comparative Evaluation of Surgical Methods in the Treatment of Chronic Irreparable Supraspinatus Tears: A Biomechanical Study

**Authors:** E. Koumantou, C. J. Feroussis, E. D. Pasiou, S. K. Kourkoulis

**Affiliations:**
- National Technical University of Athens, Laboratory of Biomechanics and Biomedical Physics
- National and Kapodistrian University of Athens, School of Medicine

---

## Overview

This Jupyter notebook implements the biomechanical analysis pipeline for evaluating surgical repair methods of chronic supraspinatus tendon tears in a rabbit model. The study compares three groups:

| Group | Description | Treatment |
|-------|-------------|-----------|
| **NON** | Non-operated control | Intact contralateral shoulder |
| **TFL** | TFL Allograft | Tensor fascia lata reconstruction |
| **MSC** | TFL + Stem Cells | TFL allograft with bone marrow mesenchymal stem cells |

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
4. Select region with highest slope where R² ≥ 0.99
5. If no region meets R² threshold, use region with best R²

---

## Results

### Group Statistics Summary

| Group | n | Max Load (N) | Stiffness (N/mm) | Energy (mJ) |
|-------|---|--------------|------------------|-------------|
| **NON** | 23 | 418.17 ± 145.11 | 176.36 ± 87.73 | 843.63 ± 382.59 |
| **TFL** | 13 | 108.47 ± 46.85 | 29.94 ± 16.55 | 523.41 ± 620.15 |
| **MSC** | 10 | 154.59 ± 19.16 | 43.68 ± 11.34 | 670.55 ± 351.80 |

*Values shown as Mean ± Standard Deviation*

### Key Findings

1. **Non-operated controls (NON)** showed the highest mechanical properties, as expected for intact tissue

2. **MSC group showed improved outcomes vs TFL-only:**
   - Max Load: 43% higher (154.59 vs 108.47 N)
   - Stiffness: 46% higher (43.68 vs 29.94 N/mm)
   - Energy: 28% higher (670.55 vs 523.41 mJ)

3. **Both operated groups significantly weaker than controls:**
   - TFL: 26% of control max load
   - MSC: 37% of control max load

---

## Sample Breakdown

### NON Group (23 samples)
Non-operated contralateral shoulders serving as internal controls.

| Subject | Max Load (N) | Stiffness (N/mm) | Energy (mJ) |
|---------|--------------|------------------|-------------|
| B10 | 483.05 | 243.67 | 642.79 |
| B11 | 395.07 | 213.80 | 430.70 |
| B5 | 341.85 | 148.06 | 660.87 |
| B6 | 594.00 | 300.06 | 900.69 |
| B7 | 653.00 | 304.17 | 1157.26 |
| B9 | 499.00 | 348.31 | 759.62 |
| C1 | 458.37 | 137.25 | 921.32 |
| C2 | 354.41 | 64.14 | 1170.66 |
| D1 | 287.74 | 79.28 | 636.53 |
| D2 | 277.05 | 44.80 | 1059.28 |
| D3 | 214.83 | 79.88 | 456.85 |
| D4 | 404.61 | 172.01 | 763.34 |
| D5 | 518.49 | 190.89 | 922.75 |
| D6 | 710.48 | 291.00 | 1389.90 |
| D7 | 255.44 | 124.58 | 415.10 |
| D8 | 602.32 | 241.68 | 1378.63 |
| D9 | 337.29 | 215.34 | 341.20 |
| D10 | 300.36 | 165.50 | 555.08 |
| D11 | 322.32 | 138.13 | 435.52 |
| D12 | 414.82 | 145.66 | 828.99 |
| D13 | 300.04 | 92.28 | 703.37 |
| D14 | 253.24 | 60.16 | 1941.08 |
| D15 | 640.14 | 255.56 | 931.98 |

### TFL Group (13 samples)
Tensor fascia lata allograft reconstruction without stem cells.

| Subject | Max Load (N) | Stiffness (N/mm) | Energy (mJ) |
|---------|--------------|------------------|-------------|
| B1 | 143.12 | 32.48 | 510.78 |
| B10 | 72.37 | 42.31 | 100.46 |
| B11 | 99.08 | 20.22 | 558.38 |
| C1 | 180.27 | 57.35 | 549.78 |
| C2 | 161.46 | 6.28 | 2520.54 |
| D1 | 130.11 | 49.16 | 291.96 |
| D2 | 27.31 | 5.77 | 405.91 |
| D3 | 43.37 | 14.08 | 125.26 |
| D4 | 69.70 | 16.95 | 284.15 |
| D5 | 85.44 | 37.21 | 165.06 |
| D6 | 153.07 | 46.19 | 425.04 |
| D7 | 116.14 | 34.47 | 369.46 |
| D8 | 128.72 | 26.69 | 497.58 |

### MSC Group (10 samples)
TFL allograft with bone marrow mesenchymal stem cells.

| Subject | Max Load (N) | Stiffness (N/mm) | Energy (mJ) |
|---------|--------------|------------------|-------------|
| B5 | 171.97 | 44.28 | 456.79 |
| B7 | 120.00 | 28.51 | 731.55 |
| B9 | 135.00 | 26.61 | 716.15 |
| D9 | 183.45 | 55.70 | 857.41 |
| D10 | 153.92 | 59.26 | 277.49 |
| D11 | 160.86 | 45.24 | 977.17 |
| D12 | 148.38 | 57.01 | 322.27 |
| D13 | 154.24 | 44.45 | 496.72 |
| D14 | 174.42 | 37.97 | 1428.73 |
| D15 | 143.71 | 37.74 | 441.20 |

---

## How to Run

### Prerequisites
```bash
pip install pandas numpy matplotlib scikit-learn plotly
```

### Required Files
The notebook imports from these modules (must be in the same directory):
- `ssp_config.py` - Configuration loader
- `utils.py` - Shared utilities
- `analysis_pipeline.py` - Core analysis functions
- `config.json` - Configuration file

### Running the Notebook
1. Open `Analysis_Pipeline.ipynb` in Jupyter Notebook/Lab
2. Run all cells sequentially
3. Results are saved to `Results/` folder

---

## Output Files

| File | Description |
|------|-------------|
| `Experiment_Master_Log_Detailed.csv` | All sample data with calculated metrics |
| `Group_Statistics_Detailed.csv` | Summary statistics by group |
| `Combined_Group_Plots.png` | Bar charts comparing groups |
| `Plot_NON.png` | Load-displacement curves for NON group |
| `Plot_TFL.png` | Load-displacement curves for TFL group |
| `Plot_MSC.png` | Load-displacement curves for MSC group |
| `Stiffness_Region_Examples.png` | Examples of linear region detection |

---

## Notebook Structure

| Cell | Content |
|------|---------|
| 1-2 | Title, abstract, setup description |
| 3-4 | Imports and configuration loading |
| 5 | Classification function demonstration |
| 6 | Run analysis pipeline |
| 7 | Generate and display statistics |
| 8 | Group comparison bar charts |
| 9 | Individual load-displacement curves by group |
| 10 | Interactive Plotly visualizations |
| 11 | Stiffness visualization for ALL subjects |

---

## Conclusion

The biomechanical analysis demonstrates that MSC-enhanced TFL grafts show improved mechanical properties compared to TFL-only grafts, suggesting that bone marrow mesenchymal stem cells may contribute to enhanced tendon healing. However, both operated groups remain significantly weaker than intact controls, indicating that complete restoration of native tissue properties is not achieved with either method.

---

## References

For the complete analysis pipeline and database tools, see the main project repository.

**Interactive Analysis:** Use the Streamlit app for manual stiffness selection:
```bash
streamlit run app.py
```
