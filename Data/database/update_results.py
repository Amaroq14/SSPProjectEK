"""
Update Database with Analysis Results
=====================================
This script imports the latest analysis results into the SSP database.

Usage:
    cd Data/database
    python update_results.py
"""

import sys
import os
from pathlib import Path

# Add Data and database directories to path for imports
DATA_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_DIR))
sys.path.insert(0, str(Path(__file__).parent))

from ssp_database import SSPDatabase
from ssp_config import load_config, get_config_paths
import pandas as pd

def main():
    print("=" * 60)
    print("UPDATING DATABASE WITH ANALYSIS RESULTS")
    print("=" * 60)
    
    # Paths
    config, data_root, _ = load_config()
    paths = get_config_paths(config, data_root)
    db_path = paths["database_path"]
    results_path = paths["results_csv"]
    
    print(f"\nDatabase: {db_path}")
    print(f"Results:  {results_path}")
    
    # Check results file exists
    if not results_path.exists():
        print(f"\n[X] Results file not found: {results_path}")
        print("    Run 'python run_analysis.py' first to generate results.")
        return
    
    # Read results
    results_df = pd.read_csv(results_path)
    print(f"\nFound {len(results_df)} results to import.")
    
    # Connect to database
    db = SSPDatabase(str(db_path))
    
    # Show current state
    counts_before = db.get_table_counts()
    print(f"\nCurrent database state:")
    for table, count in counts_before.items():
        print(f"  {table}: {count} records")
    
    # Clear existing results and tests to avoid duplicates
    print("\nClearing existing test results...")
    db.conn.execute("DELETE FROM results")
    db.conn.execute("DELETE FROM biomechanical_tests")
    db.conn.commit()
    
    # Import new results
    print("\nImporting new results...")
    
    imported = 0
    errors = 0
    
    for _, row in results_df.iterrows():
        try:
            filename = row['Filename']
            sample_id_raw = row['SampleID']
            subgroup = row['Subgroup']
            
            # Determine condition from filename
            if '_NO' in filename or '_NO.' in filename:
                condition = 'non_operated'
                sample_id = f"{sample_id_raw}_NO"
            else:
                condition = 'operated'
                sample_id = f"{sample_id_raw}_OPER"
            
            # Ensure subject exists
            existing_subject = db.get_subject(sample_id_raw)
            if not existing_subject:
                db.add_subject(subject_id=sample_id_raw)
            
            # Ensure sample exists
            existing_sample = db.get_sample(sample_id)
            if not existing_sample:
                db.add_sample(
                    sample_id=sample_id,
                    subject_id=sample_id_raw,
                    condition=condition,
                    treatment_group=subgroup
                )
            
            # Extract test date from filename (SSP_YYYY-MM-DD_...)
            test_date = None
            parts = filename.split('_')
            if len(parts) >= 2:
                test_date = parts[1]  # e.g., '2024-10-26'
            
            # Add test record
            test_id = db.add_test(
                sample_id=sample_id,
                test_date=test_date,
                data_filename=filename
            )
            
            # Add results
            db.add_result(
                test_id=test_id,
                sample_id=sample_id,
                max_load_N=row['MaxLoad_N'],
                stiffness_N_mm=row['Stiffness_N_mm'],
                energy_to_failure_mJ=row.get('Energy_mJ'),
                linear_region_start_idx=int(row.get('Linear_Start_Idx', 0)),
                linear_region_end_idx=int(row.get('Linear_End_Idx', 0)),
                linear_region_r2=row.get('R2_Score'),
                stiffness_method='sliding_window',
                analysis_version='run_analysis.py v1.0'
            )
            
            imported += 1
            print(f"  [OK] {sample_id}: MaxLoad={row['MaxLoad_N']:.1f}N")
            
        except Exception as e:
            errors += 1
            print(f"  [X] Error importing {row.get('Filename', 'unknown')}: {e}")
    
    # Show final state
    counts_after = db.get_table_counts()
    print(f"\n" + "=" * 60)
    print("UPDATE COMPLETE")
    print("=" * 60)
    print(f"\n  Imported: {imported} results")
    print(f"  Errors:   {errors}")
    
    print(f"\nFinal database state:")
    for table, count in counts_after.items():
        print(f"  {table}: {count} records")
    
    # Show group statistics
    print("\nGroup Statistics from Database:")
    print("-" * 60)
    try:
        stats = db.get_group_statistics()
        if len(stats) > 0:
            print(stats.to_string())
        else:
            print("  No statistics available (view may not exist)")
    except Exception as e:
        print(f"  Could not fetch statistics: {e}")
    
    db.close()
    print(f"\n[OK] Database updated: {db_path}")


if __name__ == "__main__":
    main()
