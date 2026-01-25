"""
SSP Database - Verification and Update Tool
============================================
Use this script to:
1. View all subjects and samples
2. Verify group assignments
3. Update metadata for specific samples
4. Add new samples

Run interactively or use the functions directly.
"""

from ssp_database import SSPDatabase
from pathlib import Path
import pandas as pd

# Initialize database
DB_PATH = Path(__file__).parent / "ssp_study.db"


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def view_all_subjects(db: SSPDatabase) -> pd.DataFrame:
    """Display all subjects with their metadata."""
    print_header("ALL SUBJECTS")
    
    df = db.get_all_subjects()
    if df.empty:
        print("  No subjects in database. Run import_existing_data.py first.")
        return df
    
    # Select key columns for display
    cols = ['subject_id', 'internal_id', 'weight_kg', 'status']
    display_df = df[cols].copy()
    display_df = display_df.sort_values('subject_id')
    
    print(display_df.to_string(index=False))
    print(f"\n  Total: {len(df)} subjects")
    return df


def view_all_samples(db: SSPDatabase) -> pd.DataFrame:
    """Display all samples with their group assignments."""
    print_header("ALL SAMPLES BY GROUP")
    
    query = """
    SELECT s.sample_id, s.subject_id, s.condition, s.treatment_group,
           sub.internal_id, sub.weight_kg, sub.status
    FROM samples s
    JOIN subjects sub ON s.subject_id = sub.subject_id
    ORDER BY s.treatment_group, s.subject_id, s.condition
    """
    df = db.execute_query(query)
    
    if df.empty:
        print("  No samples in database.")
        return df
    
    for group in ['NON', 'TFL', 'MSC']:
        group_df = df[df['treatment_group'] == group]
        print(f"\n  {group} GROUP ({len(group_df)} samples)")
        print("  " + "-" * 50)
        for _, row in group_df.iterrows():
            weight = f"{row['weight_kg']:.2f}kg" if pd.notna(row['weight_kg']) else "---"
            internal = row['internal_id'] if pd.notna(row['internal_id']) else "---"
            print(f"    {row['sample_id']:<20} | {internal:<12} | {weight:<8} | {row['status']}")
    
    return df


def view_results_summary(db: SSPDatabase) -> pd.DataFrame:
    """Display results summary by sample."""
    print_header("RESULTS SUMMARY")
    
    df = db.get_results()
    if df.empty:
        print("  No results in database.")
        return df
    
    # Group by treatment group
    for group in ['NON', 'TFL', 'MSC']:
        group_df = df[df['treatment_group'] == group]
        if group_df.empty:
            continue
        
        print(f"\n  {group} GROUP (n={len(group_df)})")
        print("  " + "-" * 60)
        print(f"  {'Sample':<15} {'MaxLoad(N)':<12} {'Stiffness(N/mm)':<18} {'Energy(mJ)':<12}")
        print("  " + "-" * 60)
        
        for _, row in group_df.iterrows():
            max_load = f"{row['max_load_N']:.1f}" if pd.notna(row['max_load_N']) else "---"
            stiff = f"{row['stiffness_N_mm']:.1f}" if pd.notna(row['stiffness_N_mm']) else "---"
            energy = f"{row['energy_to_failure_mJ']:.1f}" if pd.notna(row['energy_to_failure_mJ']) else "---"
            print(f"    {row['sample_id']:<15} {max_load:<12} {stiff:<18} {energy:<12}")
        
        # Group stats
        print("  " + "-" * 60)
        print(f"    Mean:          {group_df['max_load_N'].mean():.1f}          "
              f"{group_df['stiffness_N_mm'].mean():.1f}               "
              f"{group_df['energy_to_failure_mJ'].mean():.1f}")
        print(f"    SD:            {group_df['max_load_N'].std():.1f}          "
              f"{group_df['stiffness_N_mm'].std():.1f}               "
              f"{group_df['energy_to_failure_mJ'].std():.1f}")
    
    return df


def check_missing_data(db: SSPDatabase):
    """Identify samples with missing data."""
    print_header("DATA COMPLETENESS CHECK")
    
    # Subjects without weight
    query = "SELECT subject_id, internal_id FROM subjects WHERE weight_kg IS NULL"
    missing_weight = db.execute_query(query)
    if not missing_weight.empty:
        print("\n  Subjects missing WEIGHT:")
        for _, row in missing_weight.iterrows():
            print(f"    - {row['subject_id']} ({row['internal_id']})")
    
    # Subjects without internal_id
    query = "SELECT subject_id FROM subjects WHERE internal_id IS NULL"
    missing_id = db.execute_query(query)
    if not missing_id.empty:
        print("\n  Subjects missing INTERNAL ID:")
        for _, row in missing_id.iterrows():
            print(f"    - {row['subject_id']}")
    
    # Samples without test results
    query = """
    SELECT s.sample_id, s.treatment_group, sub.status
    FROM samples s
    JOIN subjects sub ON s.subject_id = sub.subject_id
    LEFT JOIN results r ON s.sample_id = r.sample_id
    WHERE r.result_id IS NULL AND sub.status = 'Extracted'
    """
    no_results = db.execute_query(query)
    if not no_results.empty:
        print("\n  Extracted samples WITHOUT TEST RESULTS:")
        for _, row in no_results.iterrows():
            print(f"    - {row['sample_id']} ({row['treatment_group']})")
    
    if missing_weight.empty and missing_id.empty and no_results.empty:
        print("\n  All data complete!")


def update_subject_weight(db: SSPDatabase, subject_id: str, weight_kg: float):
    """Update a subject's weight."""
    success = db.update_subject(subject_id, weight_kg=weight_kg)
    if success:
        print(f"  Updated {subject_id} weight to {weight_kg} kg")
    else:
        print(f"  Failed to update {subject_id}")


def update_subject_internal_id(db: SSPDatabase, subject_id: str, internal_id: str):
    """Update a subject's internal ID."""
    success = db.update_subject(subject_id, internal_id=internal_id)
    if success:
        print(f"  Updated {subject_id} internal_id to {internal_id}")
    else:
        print(f"  Failed to update {subject_id}")


def batch_update_from_dict(db: SSPDatabase, updates: dict):
    """
    Batch update subjects from a dictionary.
    
    Args:
        updates: Dict of {subject_id: {field: value, ...}}
    
    Example:
        updates = {
            'D1': {'weight_kg': 4.2, 'internal_id': 'B/FL-D01'},
            'D2': {'weight_kg': 4.5, 'internal_id': 'B/FL-D02'},
        }
        batch_update_from_dict(db, updates)
    """
    print_header("BATCH UPDATE")
    
    for subject_id, fields in updates.items():
        success = db.update_subject(subject_id, **fields)
        if success:
            print(f"  Updated {subject_id}: {fields}")
        else:
            print(f"  Failed to update {subject_id}")


def export_for_review(db: SSPDatabase, output_file: str = None):
    """Export all data to CSV for review in Excel/Notion."""
    print_header("EXPORT FOR REVIEW")
    
    if output_file is None:
        output_file = Path(__file__).parent / "data_review.csv"
    
    query = """
    SELECT 
        sub.subject_id,
        sub.internal_id,
        sub.weight_kg,
        sub.status as subject_status,
        s.sample_id,
        s.condition,
        s.treatment_group,
        s.extraction_date,
        bt.test_date,
        bt.data_filename,
        r.max_load_N,
        r.stiffness_N_mm,
        r.energy_to_failure_mJ,
        r.linear_region_r2
    FROM subjects sub
    LEFT JOIN samples s ON sub.subject_id = s.subject_id
    LEFT JOIN biomechanical_tests bt ON s.sample_id = bt.sample_id
    LEFT JOIN results r ON bt.test_id = r.test_id
    ORDER BY sub.subject_id, s.condition
    """
    
    df = db.execute_query(query)
    df.to_csv(output_file, index=False)
    print(f"  Exported to: {output_file}")
    print(f"  Total rows: {len(df)}")
    return output_file


def generate_notion_import_csv(db: SSPDatabase, output_file: str = None):
    """Generate a CSV that matches Notion's expected format for import."""
    print_header("GENERATE NOTION IMPORT CSV")
    
    if output_file is None:
        output_file = Path(__file__).parent / "notion_import.csv"
    
    query = """
    SELECT 
        CASE 
            WHEN s.condition = 'operated' THEN sub.subject_id || ' - operated'
            WHEN s.condition = 'non_operated' THEN sub.subject_id || ' - non operated'
            ELSE sub.subject_id
        END as Name,
        sub.weight_kg as "Weight (kg)",
        sub.internal_id as ID,
        sub.status as Status,
        CASE WHEN r.result_id IS NOT NULL THEN 'Biomechan' ELSE NULL END as Type,
        s.treatment_group as Method,
        bt.test_date as "Date tested",
        s.extraction_date as "Extraction Date",
        r.max_load_N as "Max Load (N)",
        r.stiffness_N_mm as "Stiffness (N/mm)",
        r.energy_to_failure_mJ as "Energy (mJ)"
    FROM subjects sub
    LEFT JOIN samples s ON sub.subject_id = s.subject_id
    LEFT JOIN biomechanical_tests bt ON s.sample_id = bt.sample_id
    LEFT JOIN results r ON bt.test_id = r.test_id
    ORDER BY sub.subject_id, s.condition DESC
    """
    
    df = db.execute_query(query)
    df.to_csv(output_file, index=False)
    print(f"  Exported to: {output_file}")
    return output_file


# =============================================================================
# INTERACTIVE MODE
# =============================================================================

def interactive_menu():
    """Run interactive verification and update menu."""
    print("\n" + "=" * 70)
    print("  SSP DATABASE - VERIFICATION & UPDATE TOOL")
    print("=" * 70)
    
    if not DB_PATH.exists():
        print(f"\n  Database not found at: {DB_PATH}")
        print("  Please run 'python import_existing_data.py' first.")
        return
    
    db = SSPDatabase(str(DB_PATH))
    
    while True:
        print("\n" + "-" * 40)
        print("  OPTIONS:")
        print("    1. View all subjects")
        print("    2. View all samples by group")
        print("    3. View results summary")
        print("    4. Check for missing data")
        print("    5. Export data for review (CSV)")
        print("    6. Generate Notion import CSV")
        print("    7. Update a subject's weight")
        print("    8. Update a subject's internal ID")
        print("    9. Run all checks")
        print("    0. Exit")
        print("-" * 40)
        
        choice = input("  Enter choice (0-9): ").strip()
        
        if choice == '1':
            view_all_subjects(db)
        elif choice == '2':
            view_all_samples(db)
        elif choice == '3':
            view_results_summary(db)
        elif choice == '4':
            check_missing_data(db)
        elif choice == '5':
            export_for_review(db)
        elif choice == '6':
            generate_notion_import_csv(db)
        elif choice == '7':
            subject = input("  Enter subject ID (e.g., D1): ").strip()
            weight = input("  Enter weight in kg: ").strip()
            try:
                update_subject_weight(db, subject, float(weight))
            except ValueError:
                print("  Invalid weight value.")
        elif choice == '8':
            subject = input("  Enter subject ID (e.g., D1): ").strip()
            internal = input("  Enter internal ID (e.g., B/FL-D01): ").strip()
            update_subject_internal_id(db, subject, internal)
        elif choice == '9':
            view_all_subjects(db)
            view_all_samples(db)
            view_results_summary(db)
            check_missing_data(db)
        elif choice == '0':
            print("\n  Goodbye!")
            break
        else:
            print("  Invalid choice. Please try again.")
    
    db.close()


# =============================================================================
# QUICK UPDATE TEMPLATE
# =============================================================================

def quick_update_template():
    """
    Template for batch updates. Edit the dictionary below and run this function.
    """
    db = SSPDatabase(str(DB_PATH))
    
    # =========================================================================
    # EDIT THIS DICTIONARY WITH YOUR UPDATES
    # =========================================================================
    updates = {
        # Example: 'D1': {'weight_kg': 4.2, 'internal_id': 'B/FL-D01'},
        # Add your updates here:
        
    }
    # =========================================================================
    
    if updates:
        batch_update_from_dict(db, updates)
    else:
        print("  No updates specified. Edit the 'updates' dictionary in this function.")
    
    db.close()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    interactive_menu()
