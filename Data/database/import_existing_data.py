"""
Import Existing Data into SSP Database
=======================================
This script imports your existing data from:
1. Notion export (CSV)
2. Analysis Pipeline results (CSV)
3. Manual data entry based on your Notion screenshot

Run this script to populate the database with all your existing data.
"""

import sys
from pathlib import Path

import pandas as pd

from ssp_database import SSPDatabase

DATA_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_DIR))

from ssp_config import load_config, get_group_ids

# =============================================================================
# DATA FROM YOUR NOTION DATABASE (based on screenshot)
# =============================================================================

# =============================================================================
# MASTER DATA FROM NOTION DATABASE (Updated: January 2026)
# =============================================================================
# Format: (Name, Weight_kg, Internal_ID, Status, Type, Tear_Date, Op_Date, Extract_Date, Test_Date, Method)

NOTION_DATA = [
    # =========================================================================
    # MASTER DATA - Updated from Notion CSV export (January 2026)
    # =========================================================================
    # Format: (Name, Weight_kg, Internal_ID, Status, Type, Tear_Date, Op_Date, Extract_Date, Test_Date, Method)
    
    # -------------------------------------------------------------------------
    # B-SERIES: Original cohort (2022)
    # -------------------------------------------------------------------------
    # B1 - TFL group
    ("B1 - non op", 4.72, "B/FL-B01", "Extracted", "Biomechan", "2022-06-09", "2022-07-21", "2022-12-05", "2022-12-06", "NON"),
    ("B1 - operated", 4.72, "B/FL-B01", "Extracted", "Biomechan", "2022-06-09", "2022-07-21", "2022-12-05", "2022-12-08", "TFL"),
    
    # B5 - MSC group
    ("B5 - non operated", 4.5, "B/MSC-H02", "Extracted", "Biomechan", "2022-06-14", "2022-07-26", "2022-12-06", "2022-12-08", "NON"),
    ("B5 - operated", 4.5, "B/MSC-H02", "Extracted", "Biomechan", "2022-06-14", "2022-07-26", "2022-12-06", "2022-12-08", "MSC"),
    
    # B6 - MSC group (only non-operated for biomechanics)
    ("B6 - non operated", 5.2, "B/MSC-H03", "Extracted", "Biomechan", "2022-06-14", "2022-07-26", "2022-12-13", "2022-12-17", "NON"),
    
    # B7 - MSC group
    ("B7 - non operated", 4.28, "B/MSC-B01", "Extracted", "Biomechan", "2022-06-16", "2022-07-28", "2022-12-13", "2022-12-17", "NON"),
    ("B7 - operated", 4.28, "B/MSC-B01", "Extracted", "Biomechan", "2022-06-16", "2022-07-28", "2022-12-13", "2022-12-17", "MSC"),
    
    # B9 - MSC group
    ("B9 - non operated", 4.36, "B/MSC-B03", "Extracted", "Biomechan", "2022-06-16", "2022-07-28", "2022-12-13", "2022-12-17", "NON"),
    ("B9 - operated", 4.36, "B/MSC-B03", "Extracted", "Biomechan", "2022-06-16", "2022-07-28", "2022-12-13", "2022-12-17", "MSC"),
    
    # B10 - TFL group (includes fractured sample)
    ("B10 - non operated", 4.4, "B/FL-H01", "Extracted", "Biomechan", "2022-06-21", "2022-08-02", "2022-12-05", "2022-12-07", "NON"),
    ("B10 - op - fractured", 4.4, "B/FL-H01", "Extracted", "Biomechan", "2022-06-21", "2022-08-02", "2022-12-05", "2022-12-08", "TFL"),
    ("B10 - operated", 4.4, "B/FL-H01", "Extracted", "Biomechan", "2022-06-21", "2022-08-02", "2022-12-05", "2022-12-08", "TFL"),
    
    # B11 - TFL group
    ("B11 - non operated", 4.0, "B/FL-H02", "Extracted", "Biomechan", "2022-06-21", "2022-08-02", "2022-12-06", "2022-12-08", "NON"),
    ("B11 - operated", 4.0, "B/FL-H02", "Extracted", "Biomechan", "2022-06-21", "2022-08-02", "2022-12-06", "2022-12-08", "TFL"),
    
    # -------------------------------------------------------------------------
    # C-SERIES: Pilot/additional tests (2024)
    # -------------------------------------------------------------------------
    ("C1 - non operated", None, None, "Extracted", "Biomechan", None, None, "2024-10-24", "2024-10-26", "NON"),
    ("C1 - operated", None, None, "Extracted", "Biomechan", None, None, "2024-10-24", "2024-10-27", "TFL"),
    ("C2 - non operated", None, None, "Extracted", "Biomechan", None, None, "2024-10-24", "2024-10-26", "NON"),
    ("C2 - operated", None, None, "Extracted", "Biomechan", None, None, "2024-10-24", "2024-10-27", "TFL"),
    
    # -------------------------------------------------------------------------
    # D-SERIES: Main experimental cohort (2025) - WITH WEIGHTS FROM NOTION
    # -------------------------------------------------------------------------
    # D1-D8: TFL group
    ("D1 - non operated", 4.9, None, "Extracted", "Biomechan", None, None, None, "2025-03-17", "NON"),
    ("D1 - operated", 4.9, None, "Extracted", "Biomechan", None, None, None, "2025-03-17", "TFL"),
    ("D2 - non operated", 4.8, None, "Extracted", "Biomechan", None, None, None, "2025-03-17", "NON"),
    ("D2 - operated", 4.8, None, "Extracted", "Biomechan", None, None, None, "2025-03-17", "TFL"),
    ("D3 - non operated", 4.5, None, "Extracted", "Biomechan", None, None, None, "2025-03-17", "NON"),
    ("D3 - operated", 4.5, None, "Extracted", "Biomechan", None, None, None, "2025-03-17", "TFL"),
    ("D4 - non operated", 5.25, None, "Extracted", "Biomechan", None, None, None, "2025-03-18", "NON"),
    ("D4 - operated", 5.25, None, "Extracted", "Biomechan", None, None, None, "2025-03-18", "TFL"),
    ("D5 - non operated", 5.04, None, "Extracted", "Biomechan", None, None, None, "2025-03-18", "NON"),
    ("D5 - operated", 5.04, None, "Extracted", "Biomechan", None, None, None, "2025-03-18", "TFL"),
    ("D6 - non operated", 4.9, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D6 - operated", 4.9, None, "Extracted", "Biomechan", None, None, None, "2025-03-19", "TFL"),
    ("D7 - non operated", 4.3, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D7 - operated", 4.3, None, "Extracted", "Biomechan", None, None, None, "2025-03-19", "TFL"),
    ("D8 - non operated", 4.5, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D8 - operated", 4.5, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "TFL"),
    
    # D9-D15: MSC group
    ("D9 - non operated", 4.9, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D9 - operated", 4.9, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "MSC"),
    ("D10 - non operated", 5.14, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D10 - operated", 5.14, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "MSC"),
    ("D11 - non operated", 5.5, None, "Extracted", "Biomechan", None, None, None, "2025-03-19", "NON"),
    ("D11 - operated", 5.5, None, "Extracted", "Biomechan", None, None, None, "2025-03-19", "MSC"),
    ("D12 - non operated", 4.8, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D12 - operated", 4.8, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "MSC"),
    ("D13 - non operated", 5.35, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D13 - operated", 5.35, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "MSC"),
    ("D14 - non operated", 5.2, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D14 - operated", 5.2, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "MSC"),
    ("D15 - non operated", 5.1, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "NON"),
    ("D15 - operated", 5.1, None, "Extracted", "Biomechan", None, None, None, "2025-03-20", "MSC"),
]

# =============================================================================
# GROUP ASSIGNMENTS - For OPERATED samples only (non-operated are always NON)
# =============================================================================
# Group assignments are loaded from Data/config.json to keep a single source
# of truth across the pipeline.

CONFIG, _, _ = load_config()
TFL_IDS, MSC_IDS = get_group_ids(CONFIG)
GROUP_ASSIGNMENTS = {subject_id: "TFL" for subject_id in TFL_IDS}
GROUP_ASSIGNMENTS.update({subject_id: "MSC" for subject_id in MSC_IDS})


def import_notion_data(db: SSPDatabase):
    """Import data from the Notion database (hardcoded from screenshot)."""
    print("\n" + "="*60)
    print("Importing Notion data...")
    print("="*60)
    
    subjects_added = set()
    samples_added = 0
    
    for row in NOTION_DATA:
        name, weight, internal_id, status, test_type, tear_date, op_date, extract_date, test_date, method = row
        
        # Parse name to get subject_id and condition
        parts = name.split(' - ')
        subject_id = parts[0].strip()
        condition_str = parts[1].strip() if len(parts) > 1 else None
        
        # Add subject (only once per subject_id)
        if subject_id not in subjects_added:
            db.add_subject(
                subject_id=subject_id,
                internal_id=internal_id,
                weight_kg=weight,
                status=status
            )
            subjects_added.add(subject_id)
            print(f"  + Subject: {subject_id} (Weight: {weight} kg, ID: {internal_id})")
        
        # Determine condition and treatment group
        if condition_str:
            if 'oper' in condition_str.lower() and 'non' not in condition_str.lower():
                condition = 'operated'
                sample_suffix = 'OPER'
                # Operated samples use the Method from Notion or GROUP_ASSIGNMENTS
                treatment_group = GROUP_ASSIGNMENTS.get(subject_id, method if method else 'TFL')
            else:
                condition = 'non_operated'
                sample_suffix = 'NO'
                treatment_group = 'NON'  # Non-operated are always control
            
            sample_id = f"{subject_id}_{sample_suffix}"
            
            # Handle special cases like "B10 - op - fractured"
            if 'fractured' in condition_str.lower():
                sample_id = f"{subject_id}_OPER_FRACTURED"
            
            # Add sample
            if db.add_sample(
                sample_id=sample_id,
                subject_id=subject_id,
                condition=condition,
                treatment_group=treatment_group,
                extraction_date=extract_date
            ):
                samples_added += 1
                print(f"    - Sample: {sample_id} ({treatment_group})")
            
            # Add procedures
            if tear_date:
                db.add_procedure(subject_id, 'tear_creation', tear_date)
            if op_date:
                db.add_procedure(subject_id, 'reconstruction', op_date)
    
    print(f"\n  Total: {len(subjects_added)} subjects, {samples_added} samples imported")


def import_analysis_results(db: SSPDatabase):
    """Import results from the Analysis Pipeline CSV."""
    print("\n" + "="*60)
    print("Importing Analysis Pipeline results...")
    print("="*60)
    
    results_csv = Path(__file__).parent.parent / "Results" / "Experiment_Master_Log_Detailed.csv"
    
    if not results_csv.exists():
        print(f"  ⚠ Results file not found: {results_csv}")
        print("  Skipping results import.")
        return
    
    df = pd.read_csv(results_csv)
    results_added = 0
    
    for _, row in df.iterrows():
        filename = row['Filename']
        sample_id_raw = row['SampleID']
        subgroup = row['Subgroup']
        
        # Determine condition from filename
        if '_NO' in filename:
            condition = 'non_operated'
            sample_id = f"{sample_id_raw}_NO"
        else:
            condition = 'operated'
            sample_id = f"{sample_id_raw}_OPER"
        
        # Ensure subject exists
        db.add_subject(subject_id=sample_id_raw)
        
        # Ensure sample exists with correct group assignment
        # Override with GROUP_ASSIGNMENTS if available
        treatment_group = subgroup
        if condition == 'operated' and sample_id_raw in GROUP_ASSIGNMENTS:
            treatment_group = GROUP_ASSIGNMENTS[sample_id_raw]
        elif condition == 'non_operated':
            treatment_group = 'NON'
        
        db.add_sample(
            sample_id=sample_id,
            subject_id=sample_id_raw,
            condition=condition,
            treatment_group=treatment_group
        )
        
        # Extract test date from filename
        parts = filename.split('_')
        test_date = parts[1] if len(parts) >= 2 else None
        
        # Add test record
        test_id = db.add_test(
            sample_id=sample_id,
            test_date=test_date,
            data_filename=filename,
            data_filepath=str(Path(__file__).parent.parent / "Selected_data" / filename)
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
            analysis_version='Analysis_Pipeline_v1'
        )
        results_added += 1
        print(f"  + {sample_id}: MaxLoad={row['MaxLoad_N']:.1f}N, Stiffness={row['Stiffness_N_mm']:.1f}N/mm")
    
    print(f"\n  Total: {results_added} results imported")


def verify_group_assignments(db: SSPDatabase):
    """Verify and display group assignments for review."""
    print("\n" + "="*60)
    print("Group Assignments Verification")
    print("="*60)
    
    # Query all samples with their groups
    query = """
    SELECT s.sample_id, s.subject_id, s.condition, s.treatment_group, 
           sub.internal_id, sub.weight_kg
    FROM samples s
    JOIN subjects sub ON s.subject_id = sub.subject_id
    ORDER BY s.subject_id, s.condition
    """
    df = db.execute_query(query)
    
    print("\nAll samples by group:\n")
    for group in ['NON', 'TFL', 'MSC']:
        group_df = df[df['treatment_group'] == group]
        print(f"  {group} ({len(group_df)} samples):")
        for _, row in group_df.iterrows():
            print(f"    - {row['sample_id']} ({row['internal_id']}, {row['weight_kg']} kg)")
        print()
    
    # Show any potential issues
    print("\n⚠ Potential issues to verify:")
    
    # Check for samples without test results
    query_no_results = """
    SELECT s.sample_id, s.treatment_group 
    FROM samples s
    LEFT JOIN results r ON s.sample_id = r.sample_id
    WHERE r.result_id IS NULL
    """
    no_results = db.execute_query(query_no_results)
    if len(no_results) > 0:
        print(f"  - {len(no_results)} samples without test results:")
        for _, row in no_results.iterrows():
            print(f"      {row['sample_id']} ({row['treatment_group']})")


def main():
    """Main import script."""
    print("\n" + "="*60)
    print("SSP BIOMECHANICS DATABASE - DATA IMPORT")
    print("="*60)
    
    # Initialize database
    db_path = Path(__file__).parent / "ssp_study.db"
    
    # Remove existing database to start fresh (comment out to append)
    if db_path.exists():
        print(f"\n⚠ Existing database found: {db_path}")
        response = input("  Delete and recreate? (y/n): ").strip().lower()
        if response == 'y':
            db_path.unlink()
            print("  Deleted existing database.")
        else:
            print("  Keeping existing database (will append data).")
    
    db = SSPDatabase(str(db_path))
    
    # Import data
    import_notion_data(db)
    import_analysis_results(db)
    verify_group_assignments(db)
    
    # Summary
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)
    
    counts = db.get_table_counts()
    for table, count in counts.items():
        print(f"  {table}: {count} records")
    
    print("\n  Group Statistics:")
    stats = db.get_group_statistics()
    print(stats.to_string(index=False))
    
    # Export to CSV for verification
    exports = db.export_to_csv()
    print(f"\n  Exported tables to: {Path(exports['subjects']).parent}")
    
    db.close()
    print(f"\n✅ Database created: {db_path}")
    print("   You can now use this database in your analysis pipeline!")


if __name__ == "__main__":
    main()
