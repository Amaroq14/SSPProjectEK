"""
SSP Biomechanics Study Database Manager
========================================
A SQLite-based database for managing experimental data from the
supraspinatus tear surgical comparison study.

Usage:
    from ssp_database import SSPDatabase
    
    db = SSPDatabase()  # Creates/connects to database
    db.add_subject('D1', weight_kg=4.5, internal_id='B/FL-H01')
    db.add_sample('D1_OPER', subject_id='D1', condition='operated', treatment_group='TFL')
    
    # Query results
    results = db.get_group_results('MSC')
    stats = db.get_group_statistics()
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class SSPDatabase:
    """Database manager for SSP biomechanics study data."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Defaults to 'ssp_study.db' 
                     in the same directory as this script.
        """
        if db_path is None:
            db_dir = Path(__file__).parent
            db_path = db_dir / "ssp_study.db"
        
        self.db_path = Path(db_path)
        self.conn = None
        self._connect()
        self._initialize_schema()
        self._initialize_treatment_groups()
    
    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
    
    def _initialize_schema(self):
        """Create tables if they don't exist."""
        schema_path = self.db_path.parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                self.conn.executescript(f.read())
        self.conn.commit()
    
    def _initialize_treatment_groups(self) -> None:
        """Insert default treatment group definitions."""
        groups = [
            ('NON', 'Intact/Control', 'Non-operated contralateral shoulder serving as internal control', None, False),
            ('TFL', 'TFL Allograft', 'Tensor fascia lata allograft reconstruction without stem cells', 'TFL', False),
            ('MSC', 'TFL + MSC', 'Tensor fascia lata allograft with bone marrow mesenchymal stem cells', 'TFL', True),
        ]
        for group in groups:
            try:
                self.conn.execute("""
                    INSERT OR IGNORE INTO treatment_groups 
                    (group_id, group_name, description, graft_type, has_stem_cells)
                    VALUES (?, ?, ?, ?, ?)
                """, group)
            except sqlite3.IntegrityError:
                # Group already exists, ignore
                pass
            except sqlite3.Error as e:
                logger.warning(f"Failed to insert treatment group {group[0]}: {e}")
        self.conn.commit()
    
    # =========================================================================
    # SUBJECT MANAGEMENT
    # =========================================================================
    
    def add_subject(self, subject_id: str, internal_id: str = None, 
                    weight_kg: float = None, status: str = None,
                    sex: str = 'Male', species: str = 'Rabbit',
                    age_weeks: int = None, strain: str = None,
                    notes: str = None) -> bool:
        """
        Add a new subject (animal) to the database.
        
        Args:
            subject_id: Unique identifier (e.g., 'B1', 'D5')
            internal_id: Lab internal ID (e.g., 'B/FL-B01', 'B/MSC-H02')
            weight_kg: Body weight in kilograms
            status: Subject status ('Extracted', 'Dead', 'Test')
            sex: Sex of the animal
            species: Species name
            age_weeks: Age at experiment start
            strain: Animal strain/breed
            notes: Additional notes
            
        Returns:
            True if successful, False if subject already exists
        """
        try:
            self.conn.execute("""
                INSERT INTO subjects 
                (subject_id, internal_id, weight_kg, status, sex, species, age_weeks, strain, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (subject_id, internal_id, weight_kg, status, sex, species, age_weeks, strain, notes))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Subject {subject_id} already exists. Use update_subject() to modify.")
            return False
    
    def update_subject(self, subject_id: str, **kwargs) -> bool:
        """Update an existing subject's information."""
        valid_fields = ['internal_id', 'weight_kg', 'status', 'sex', 'species', 
                        'age_weeks', 'strain', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [subject_id]
        
        self.conn.execute(f"""
            UPDATE subjects SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE subject_id = ?
        """, values)
        self.conn.commit()
        return self.conn.total_changes > 0
    
    def get_subject(self, subject_id: str) -> Optional[Dict]:
        """Get subject information by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM subjects WHERE subject_id = ?", (subject_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_subjects(self) -> pd.DataFrame:
        """Get all subjects as a DataFrame."""
        return pd.read_sql_query("SELECT * FROM subjects", self.conn)
    
    # =========================================================================
    # SAMPLE MANAGEMENT
    # =========================================================================
    
    def add_sample(self, sample_id: str, subject_id: str, condition: str,
                   treatment_group: str, shoulder: str = None,
                   extraction_date: Union[str, date] = None,
                   storage_method: str = None, notes: str = None) -> bool:
        """
        Add a new sample (test specimen) to the database.
        
        Args:
            sample_id: Unique sample identifier (e.g., 'B1_OPER', 'D5_NO')
            subject_id: Parent subject ID (e.g., 'B1', 'D5')
            condition: 'operated' or 'non_operated'
            treatment_group: 'NON', 'TFL', or 'MSC'
            shoulder: 'left' or 'right'
            extraction_date: Date tissue was extracted
            storage_method: How sample was stored
            notes: Additional notes
            
        Returns:
            True if successful
        """
        # Normalize condition
        if condition.upper() in ['OPER', 'OPERATED', 'OP']:
            condition = 'operated'
        elif condition.upper() in ['NO', 'NON', 'NON_OPERATED', 'NON-OPERATED']:
            condition = 'non_operated'
        
        try:
            self.conn.execute("""
                INSERT INTO samples 
                (sample_id, subject_id, condition, treatment_group, shoulder, 
                 extraction_date, storage_method, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sample_id, subject_id, condition, treatment_group, shoulder,
                  extraction_date, storage_method, notes))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"Error adding sample {sample_id}: {e}")
            return False
    
    def get_sample(self, sample_id: str) -> Optional[Dict]:
        """Get sample information by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM v_sample_details WHERE sample_id = ?", (sample_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_samples_by_group(self, treatment_group: str) -> pd.DataFrame:
        """Get all samples in a treatment group."""
        return pd.read_sql_query(
            "SELECT * FROM v_sample_details WHERE treatment_group = ?",
            self.conn, params=(treatment_group,))
    
    # =========================================================================
    # PROCEDURE MANAGEMENT
    # =========================================================================
    
    def add_procedure(self, subject_id: str, procedure_type: str,
                      procedure_date: Union[str, date] = None,
                      surgeon: str = None, notes: str = None) -> int:
        """
        Add a procedure record for a subject.
        
        Args:
            subject_id: Subject ID
            procedure_type: 'tear_creation', 'reconstruction', 'extraction'
            procedure_date: Date of procedure
            surgeon: Name of surgeon/researcher
            notes: Procedure notes
            
        Returns:
            Procedure ID
        """
        cursor = self.conn.execute("""
            INSERT INTO procedures (subject_id, procedure_type, procedure_date, surgeon, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (subject_id, procedure_type, procedure_date, surgeon, notes))
        self.conn.commit()
        return cursor.lastrowid
    
    # =========================================================================
    # BIOMECHANICAL TEST MANAGEMENT
    # =========================================================================
    
    def add_test(self, sample_id: str, test_date: Union[str, date],
                 data_filename: str, data_filepath: str = None,
                 crosshead_speed_mm_min: float = 1.0,
                 preload_N: float = None, gauge_length_mm: float = None,
                 temperature_C: float = None, operator: str = None,
                 test_run_number: int = 1, is_valid: bool = True,
                 failure_mode: str = None, notes: str = None,
                 machine: str = 'MTS', test_type: str = 'uniaxial_tension') -> int:
        """
        Add a biomechanical test record.
        
        Returns:
            Test ID
        """
        cursor = self.conn.execute("""
            INSERT INTO biomechanical_tests 
            (sample_id, test_date, test_type, machine, crosshead_speed_mm_min,
             preload_N, gauge_length_mm, temperature_C, data_filename, data_filepath,
             operator, test_run_number, is_valid, failure_mode, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sample_id, test_date, test_type, machine, crosshead_speed_mm_min,
              preload_N, gauge_length_mm, temperature_C, data_filename, data_filepath,
              operator, test_run_number, is_valid, failure_mode, notes))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_test(self, test_id: int) -> Optional[Dict]:
        """Get test information by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM biomechanical_tests WHERE test_id = ?", (test_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # =========================================================================
    # RESULTS MANAGEMENT
    # =========================================================================
    
    def add_result(self, test_id: int, sample_id: str,
                   max_load_N: float, stiffness_N_mm: float,
                   energy_to_failure_mJ: float = None,
                   displacement_at_failure_mm: float = None,
                   linear_region_start_idx: int = None,
                   linear_region_end_idx: int = None,
                   linear_region_r2: float = None,
                   stiffness_method: str = 'sliding_window',
                   analysis_version: str = None,
                   notes: str = None) -> int:
        """
        Add calculated results for a test.
        
        Returns:
            Result ID
        """
        cursor = self.conn.execute("""
            INSERT INTO results 
            (test_id, sample_id, max_load_N, stiffness_N_mm, energy_to_failure_mJ,
             displacement_at_failure_mm, linear_region_start_idx, linear_region_end_idx,
             linear_region_r2, stiffness_method, analysis_version, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_id, sample_id, max_load_N, stiffness_N_mm, energy_to_failure_mJ,
              displacement_at_failure_mm, linear_region_start_idx, linear_region_end_idx,
              linear_region_r2, stiffness_method, analysis_version, notes))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_results(self, sample_id: str = None, treatment_group: str = None) -> pd.DataFrame:
        """
        Get results, optionally filtered by sample or group.
        
        Args:
            sample_id: Filter by specific sample
            treatment_group: Filter by treatment group ('NON', 'TFL', 'MSC')
            
        Returns:
            DataFrame with results
        """
        query = "SELECT * FROM v_full_results WHERE 1=1"
        params = []
        
        if sample_id:
            query += " AND sample_id = ?"
            params.append(sample_id)
        if treatment_group:
            query += " AND treatment_group = ?"
            params.append(treatment_group)
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_group_statistics(self) -> pd.DataFrame:
        """Get summary statistics by treatment group."""
        return pd.read_sql_query("SELECT * FROM v_group_statistics", self.conn)

    # =========================================================================
    # MANUAL RESULTS MANAGEMENT
    # =========================================================================

    def add_manual_result(
        self,
        sample_id: str,
        data_filename: str,
        selection_start_idx: int,
        selection_end_idx: int,
        manual_stiffness_N_mm: float,
        manual_r2: float = None,
        reviewer: str = None,
        session_id: str = None,
        notes: str = None
    ) -> int:
        """
        Add a manual stiffness result from user-selected linear region.
        Returns: manual_result_id
        """
        cursor = self.conn.execute("""
            INSERT INTO manual_results
            (sample_id, data_filename, reviewer, session_id, selection_start_idx,
             selection_end_idx, manual_stiffness_N_mm, manual_r2, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sample_id, data_filename, reviewer, session_id, selection_start_idx,
              selection_end_idx, manual_stiffness_N_mm, manual_r2, notes))
        self.conn.commit()
        return cursor.lastrowid

    def get_manual_results(
        self,
        sample_id: str = None,
        reviewer: str = None,
        session_id: str = None
    ) -> pd.DataFrame:
        """Get manual results filtered by sample/reviewer/session."""
        query = "SELECT * FROM manual_results WHERE 1=1"
        params = []
        if sample_id:
            query += " AND sample_id = ?"
            params.append(sample_id)
        if reviewer:
            query += " AND reviewer = ?"
            params.append(reviewer)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        return pd.read_sql_query(query, self.conn, params=params)
    
    # =========================================================================
    # BULK IMPORT METHODS
    # =========================================================================
    
    def import_from_notion_csv(self, csv_path: str) -> int:
        """
        Import subjects from a Notion export CSV.
        
        Expected columns: Name, Weight, ID, Status, Type, Tear Date, 
                         Operation Date, Extraction Date, Date tested, Method
        
        Returns:
            Number of records imported
        """
        df = pd.read_csv(csv_path)
        count = 0
        
        for _, row in df.iterrows():
            # Parse the Name column to get subject_id and condition
            name = str(row.get('Name', ''))
            
            # Extract subject ID (e.g., 'B1' from 'B1 - non operated')
            parts = name.split(' - ')
            subject_id = parts[0].strip() if parts else name
            condition = parts[1].strip() if len(parts) > 1 else None
            
            # Add subject if not exists
            self.add_subject(
                subject_id=subject_id,
                internal_id=row.get('ID'),
                weight_kg=row.get('Weight ...') or row.get('Weight'),
                status=row.get('Status')
            )
            
            # Determine treatment group from Method column
            method = str(row.get('Method', '')).upper()
            if 'MSC' in method:
                treatment_group = 'MSC'
            elif 'TFL' in method:
                treatment_group = 'TFL'
            else:
                treatment_group = 'NON'
            
            # Create sample_id
            if condition:
                if 'oper' in condition.lower() and 'non' not in condition.lower():
                    sample_id = f"{subject_id}_OPER"
                    cond = 'operated'
                else:
                    sample_id = f"{subject_id}_NO"
                    cond = 'non_operated'
                    treatment_group = 'NON'  # Non-operated are always NON group
                
                # Add sample
                self.add_sample(
                    sample_id=sample_id,
                    subject_id=subject_id,
                    condition=cond,
                    treatment_group=treatment_group,
                    extraction_date=row.get('Extraction Date')
                )
                
                # Add procedures
                if pd.notna(row.get('Tear Date')):
                    self.add_procedure(subject_id, 'tear_creation', row.get('Tear Date'))
                if pd.notna(row.get('Operation Date')):
                    self.add_procedure(subject_id, 'reconstruction', row.get('Operation Date'))
                
                count += 1
        
        return count
    
    def import_from_analysis_results(self, csv_path: str) -> int:
        """
        Import results from the Analysis_Pipeline output CSV.
        
        Expected columns: Filename, SampleID, Subgroup, MaxLoad_N, Stiffness_N_mm,
                         Energy_mJ, R2_Score, Linear_Start_Idx, Linear_End_Idx
        
        Returns:
            Number of results imported
        """
        df = pd.read_csv(csv_path)
        count = 0
        
        for _, row in df.iterrows():
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
            self.add_subject(subject_id=sample_id_raw)
            
            # Ensure sample exists
            self.add_sample(
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
            test_id = self.add_test(
                sample_id=sample_id,
                test_date=test_date,
                data_filename=filename
            )
            
            # Add results
            self.add_result(
                test_id=test_id,
                sample_id=sample_id,
                max_load_N=row['MaxLoad_N'],
                stiffness_N_mm=row['Stiffness_N_mm'],
                energy_to_failure_mJ=row.get('Energy_mJ'),
                linear_region_start_idx=row.get('Linear_Start_Idx'),
                linear_region_end_idx=row.get('Linear_End_Idx'),
                linear_region_r2=row.get('R2_Score'),
                stiffness_method='sliding_window'
            )
            count += 1
        
        return count
    
    # =========================================================================
    # EXPORT METHODS
    # =========================================================================
    
    def export_to_csv(self, output_dir: str = None) -> Dict[str, str]:
        """
        Export all tables to CSV files.
        
        Returns:
            Dictionary of table names to file paths
        """
        if output_dir is None:
            output_dir = self.db_path.parent / "exports"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        tables = ['subjects', 'samples', 'procedures', 'biomechanical_tests', 'results', 'manual_results']
        exports = {}
        
        for table in tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", self.conn)
            filepath = output_dir / f"{table}.csv"
            df.to_csv(filepath, index=False)
            exports[table] = str(filepath)
        
        # Also export the full results view
        df = pd.read_sql_query("SELECT * FROM v_full_results", self.conn)
        filepath = output_dir / "full_results.csv"
        df.to_csv(filepath, index=False)
        exports['full_results'] = str(filepath)
        
        return exports
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute a custom SQL query and return results as DataFrame."""
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        tables = ['subjects', 'samples', 'procedures', 'biomechanical_tests', 'results', 'manual_results']
        counts = {}
        for table in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        return counts
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_database(db_path: str = None) -> SSPDatabase:
    """Create a new database and return the manager."""
    return SSPDatabase(db_path)


def quick_import_notion(notion_csv: str, db_path: str = None) -> SSPDatabase:
    """Quick import from Notion CSV export."""
    db = SSPDatabase(db_path)
    count = db.import_from_notion_csv(notion_csv)
    print(f"Imported {count} records from Notion export")
    return db


def quick_import_results(results_csv: str, db_path: str = None) -> SSPDatabase:
    """Quick import from Analysis_Pipeline results CSV."""
    db = SSPDatabase(db_path)
    count = db.import_from_analysis_results(results_csv)
    print(f"Imported {count} results from analysis output")
    return db


# =============================================================================
# MAIN - Demo/Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SSP Biomechanics Database - Demo")
    print("=" * 60)
    
    # Create database
    db = SSPDatabase()
    
    # Add some example data
    print("\n1. Adding example subjects...")
    db.add_subject('B1', internal_id='B/FL-B01', weight_kg=4.72, status='Extracted')
    db.add_subject('B5', internal_id='B/MSC-H02', weight_kg=4.5, status='Extracted')
    db.add_subject('D1', internal_id='B/FL-H01', weight_kg=4.4, status='Extracted')
    
    print("\n2. Adding example samples...")
    db.add_sample('B1_NO', 'B1', 'non_operated', 'NON', extraction_date='2022-12-05')
    db.add_sample('B1_OPER', 'B1', 'operated', 'TFL', extraction_date='2022-12-05')
    db.add_sample('B5_NO', 'B5', 'non_operated', 'NON', extraction_date='2022-12-06')
    db.add_sample('B5_OPER', 'B5', 'operated', 'MSC', extraction_date='2022-12-06')
    
    print("\n3. Adding example test and results...")
    test_id = db.add_test('B1_OPER', '2022-12-06', 'SSP_2022-12-06_B1_OPER.csv')
    db.add_result(test_id, 'B1_OPER', max_load_N=180.27, stiffness_N_mm=57.35, 
                  energy_to_failure_mJ=549.78, linear_region_r2=0.999)
    
    print("\n4. Database summary:")
    counts = db.get_table_counts()
    for table, count in counts.items():
        print(f"   {table}: {count} records")
    
    print("\n5. All subjects:")
    print(db.get_all_subjects())
    
    print("\n6. Group statistics:")
    print(db.get_group_statistics())
    
    db.close()
    print("\n✅ Demo complete! Database saved to:", db.db_path)
