"""
Convert B-Series Data to CSV Format
====================================
This script converts the B-series TXT files from SSP_Project/Raw_Data/
to CSV format matching the D-series data in Data/Selected_data/

The original files are NOT modified - this only creates new CSV copies.

Usage:
    cd Data
    python convert_b_series.py
"""

import os
import re
from pathlib import Path
from datetime import datetime

from ssp_config import load_config, get_config_paths

# Paths from config
CONFIG, DATA_ROOT, _ = load_config()
PATHS = get_config_paths(CONFIG, DATA_ROOT)
B_SERIES_SOURCE = PATHS["raw_b_series_dir"]
OUTPUT_DIR = PATHS["selected_data_dir"]

# Mapping of test dates from the B-series files (DD-Mon-YY format to YYYY-MM-DD)
MONTH_MAP = {
    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
}


def parse_date(date_str):
    """Convert DD-Mon-YY to YYYY-MM-DD format."""
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            day = parts[0].zfill(2)
            month = MONTH_MAP.get(parts[1], '12')
            year = '20' + parts[2] if len(parts[2]) == 2 else parts[2]
            return f"{year}-{month}-{day}"
    except:
        pass
    return "2022-12-08"  # Default fallback


def convert_b_series_file(input_path, output_dir):
    """
    Convert a single B-series TXT file to CSV format.
    
    Args:
        input_path: Path to the B-series TXT file
        output_dir: Directory to save the CSV file
    
    Returns:
        Output filename if successful, None if failed
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            print(f"  [!] Skipping {input_path.name}: Too few lines")
            return None
        
        # Parse header info from line 1 and 2
        sample_line = lines[0].strip()  # e.g., "Sample:	B1 operated"
        header_line = lines[1].strip()
        first_data_line = lines[2].strip()
        
        # Extract sample info
        sample_match = re.search(r'Sample:\s*(\w+)\s*(.*)', sample_line)
        if sample_match:
            sample_id = sample_match.group(1)  # e.g., "B1"
            condition_raw = sample_match.group(2).strip()  # e.g., "operated" or "non operated"
        else:
            print(f"  [!] Skipping {input_path.name}: Could not parse sample line")
            return None
        
        # Determine condition code
        if 'non' in condition_raw.lower():
            condition_code = 'NO'
        else:
            condition_code = 'OPER'
        
        # Parse first data line to get test date
        first_data_parts = first_data_line.split('\t')
        test_date = "2022-12-08"  # Default
        
        # Find the test date (usually in position 3)
        for part in first_data_parts:
            if re.match(r'\d{2}-\w{3}-\d{2}', part):
                test_date = parse_date(part)
                break
        
        # Find displacement and load columns (last two non-empty columns in header)
        header_parts = header_line.split('\t')
        disp_col_idx = None
        load_col_idx = None
        
        for i, col in enumerate(header_parts):
            if 'displacement' in col.lower():
                disp_col_idx = i
            elif 'load' in col.lower():
                load_col_idx = i
        
        if disp_col_idx is None or load_col_idx is None:
            # Fall back to last two columns
            disp_col_idx = len(header_parts) - 2
            load_col_idx = len(header_parts) - 1
        
        # Extract data points
        data_points = []
        
        for line in lines[2:]:  # Skip header lines
            parts = line.strip().split('\t')
            
            # Find displacement and load values
            # They're usually in the last two non-empty columns
            values = [p.strip() for p in parts if p.strip()]
            
            if len(values) >= 2:
                try:
                    # Try to get displacement and load from the expected columns
                    if len(parts) > max(disp_col_idx, load_col_idx):
                        disp = parts[disp_col_idx].strip()
                        load = parts[load_col_idx].strip()
                    else:
                        # Fallback: use last two values
                        disp = values[-2]
                        load = values[-1]
                    
                    # Convert to float to validate
                    disp_val = float(disp)
                    load_val = float(load)
                    data_points.append((disp_val, load_val))
                except (ValueError, IndexError):
                    continue
        
        if len(data_points) < 10:
            print(f"  [!] Skipping {input_path.name}: Only {len(data_points)} data points found")
            return None
        
        # Generate output filename: SSP_YYYY-MM-DD_SampleID_Condition.csv
        output_filename = f"SSP_{test_date}_{sample_id}_{condition_code}.csv"
        output_path = output_dir / output_filename
        
        # Check if file already exists
        if output_path.exists():
            print(f"  [!] File exists, skipping: {output_filename}")
            return None
        
        # Write CSV file
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header matching D-series format
            f.write("Crossheadmm,LoadN,Timesec\n")
            
            # Write data points with synthetic time (assuming ~10 Hz sampling)
            time_step = 0.1  # 100ms between points
            for i, (disp, load) in enumerate(data_points):
                time_sec = i * time_step
                f.write(f"{disp},{load},{time_sec:.3f}\n")
        
        return output_filename
        
    except Exception as e:
        print(f"  [X] Error converting {input_path.name}: {e}")
        return None


def main():
    """Main conversion function."""
    print("=" * 60)
    print("B-SERIES DATA CONVERSION")
    print("=" * 60)
    print(f"\nSource: {B_SERIES_SOURCE}")
    print(f"Output: {OUTPUT_DIR}")
    
    # Check source directory exists
    if not B_SERIES_SOURCE.exists():
        print(f"\n[X] Source directory not found: {B_SERIES_SOURCE}")
        return
    
    # Create output directory if needed
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all B-series sample files
    b_files = list(B_SERIES_SOURCE.glob("Sample_B*.txt"))
    
    if not b_files:
        print(f"\n[X] No B-series files found in {B_SERIES_SOURCE}")
        return
    
    print(f"\nFound {len(b_files)} B-series files to convert:\n")
    
    converted = []
    skipped = []
    
    for filepath in sorted(b_files):
        print(f"  Converting: {filepath.name}")
        result = convert_b_series_file(filepath, OUTPUT_DIR)
        
        if result:
            converted.append(result)
            print(f"    -> {result}")
        else:
            skipped.append(filepath.name)
    
    # Summary
    print("\n" + "=" * 60)
    print("CONVERSION SUMMARY")
    print("=" * 60)
    print(f"\n  [OK] Converted: {len(converted)} files")
    print(f"  [!] Skipped:   {len(skipped)} files")
    
    if converted:
        print(f"\n  New CSV files saved to: {OUTPUT_DIR}")
        print("\n  Converted files:")
        for f in converted:
            print(f"    - {f}")
    
    if skipped:
        print("\n  Skipped files:")
        for f in skipped:
            print(f"    - {f}")
    
    print("\n[OK] Done! You can now run the Analysis Pipeline to process all data.")


if __name__ == "__main__":
    main()
