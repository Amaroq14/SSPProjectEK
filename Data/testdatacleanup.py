import os
import pandas as pd

# --- CONFIGURATION ---
ROOT_DIR = 'Ferousis-Koumantou_MTS'
OUTPUT_DIR = 'Clean_raw_data'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"📂 Output folder ready: {OUTPUT_DIR}\n")

files_converted = 0

def find_header_row(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if "Crosshead" in line and "Load" in line:
                return i
    return None

for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
    if OUTPUT_DIR in dirpath: continue

    for filename in filenames:
        if filename.endswith(".txt"):
            source_path = os.path.join(dirpath, filename)
            try:
                # 1. GENERATE FILE NAME
                run_folder = os.path.basename(dirpath)
                sample_folder = os.path.basename(os.path.dirname(dirpath))
                date_folder = os.path.basename(os.path.dirname(os.path.dirname(dirpath)))
                
                if not date_folder.startswith("20"):
                    new_filename = f"SSP_{sample_folder}_{run_folder}.csv"
                else:
                    new_filename = f"SSP_{date_folder}_{sample_folder}.csv"

                dest_path = os.path.join(OUTPUT_DIR, new_filename)
                if os.path.exists(dest_path):
                    unique_suffix = f"_{run_folder.split(' ')[0:3]}".replace(" ", "")
                    new_filename = f"SSP_{date_folder}_{sample_folder}_{unique_suffix}.csv"
                    dest_path = os.path.join(OUTPUT_DIR, new_filename)

                # 2. READ & DETECT UNITS
                start_index = find_header_row(source_path)
                if start_index is not None:
                    # Read as text to check units
                    df = pd.read_csv(source_path, sep='\t', skiprows=start_index, dtype=str)
                    df.columns = df.columns.str.strip()
                    
                    if 'Crosshead' in df.columns and 'Load' in df.columns:
                        first_row_load = str(df.iloc[0]['Load'])
                        
                        # LOGIC: Convert kN -> N
                        convert_kN_to_N = False
                        if 'kN' in first_row_load:
                            convert_kN_to_N = True
                        
                        # Prepare Columns (Renaming LoadkN -> LoadN)
                        cols = ['Crosshead', 'Load']
                        new_headers = ['Crossheadmm', 'LoadN']
                        if 'Time' in df.columns:
                            cols.append('Time')
                            new_headers.append('Timesec')

                        df_final = df[cols].copy()
                        df_final.columns = new_headers
                        
                        # Drop unit row
                        if any(c.isalpha() for c in str(df_final.iloc[0]['Crossheadmm'])):
                            df_final = df_final.iloc[1:]

                        # Clean Numbers
                        for col in new_headers:
                            df_final[col] = df_final[col].str.replace(',', '.', regex=False)
                            df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
                        
                        # APPLY MATH
                        if convert_kN_to_N:
                            df_final['LoadN'] = df_final['LoadN'] * 1000
                            print(f"   ℹ️  Converted {filename} from kN to N")
                        
                        # Absolute value
                        df_final['LoadN'] = df_final['LoadN'].abs()
                        df_final['Crossheadmm'] = df_final['Crossheadmm'].abs()

                        df_final.to_csv(dest_path, index=False)
                        print(f"✅ Cleaned: {new_filename}")
                        files_converted += 1
            except Exception as e:
                print(f"❌ Error: {e}")

print(f"\nCompleted! {files_converted} files converted to Newtons.")