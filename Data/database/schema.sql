-- ============================================================
-- SSP Biomechanics Study Database Schema
-- Comparative evaluation of surgical methods for supraspinatus tears
-- ============================================================

-- 1. SUBJECTS TABLE: Animal/specimen information
CREATE TABLE IF NOT EXISTS subjects (
    subject_id TEXT PRIMARY KEY,           -- e.g., 'B1', 'B5', 'C1', 'D1'
    internal_id TEXT,                       -- e.g., 'B/FL-B01', 'B/MSC-H02'
    weight_kg REAL,                         -- Body weight in kg
    sex TEXT DEFAULT 'Male',                -- Sex of the animal
    species TEXT DEFAULT 'Rabbit',          -- Species
    strain TEXT,                            -- Strain/breed if applicable
    age_weeks INTEGER,                      -- Age at start of experiment
    status TEXT,                            -- 'Extracted', 'Dead', 'Test', etc.
    notes TEXT,                             -- Any additional notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. EXPERIMENTAL GROUPS TABLE: Treatment group definitions
CREATE TABLE IF NOT EXISTS treatment_groups (
    group_id TEXT PRIMARY KEY,              -- 'NON', 'TFL', 'MSC'
    group_name TEXT NOT NULL,               -- Full name
    description TEXT,                       -- Detailed description
    graft_type TEXT,                        -- Type of graft used
    has_stem_cells BOOLEAN DEFAULT FALSE    -- Whether MSCs were added
);

-- 3. PROCEDURES TABLE: Surgical/experimental procedures timeline
CREATE TABLE IF NOT EXISTS procedures (
    procedure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    procedure_type TEXT NOT NULL,           -- 'tear_creation', 'reconstruction', 'extraction'
    procedure_date DATE,
    surgeon TEXT,                           -- Surgeon/researcher name
    anesthesia TEXT,                        -- Anesthesia protocol
    complications TEXT,                     -- Any complications noted
    notes TEXT,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

-- 4. SAMPLES TABLE: Individual test specimens (operated vs non-operated shoulder)
CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY,             -- e.g., 'B1_OPER', 'B1_NO', 'D5_NO'
    subject_id TEXT NOT NULL,
    shoulder TEXT,                          -- 'left' or 'right' (optional)
    condition TEXT NOT NULL,                -- 'operated' (OPER) or 'non_operated' (NO)
    treatment_group TEXT NOT NULL,          -- 'NON', 'TFL', or 'MSC'
    extraction_date DATE,
    storage_method TEXT,                    -- e.g., 'frozen_-20C', 'fresh'
    preservation_medium TEXT,               -- e.g., 'PBS', 'saline'
    notes TEXT,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
    FOREIGN KEY (treatment_group) REFERENCES treatment_groups(group_id)
);

-- 5. BIOMECHANICAL TESTS TABLE: Test session metadata
CREATE TABLE IF NOT EXISTS biomechanical_tests (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id TEXT NOT NULL,
    test_date DATE NOT NULL,
    test_type TEXT DEFAULT 'uniaxial_tension', -- Type of mechanical test
    machine TEXT DEFAULT 'MTS',              -- Testing machine
    load_cell_capacity_N REAL,              -- Load cell capacity
    crosshead_speed_mm_min REAL DEFAULT 1.0, -- Loading rate
    preload_N REAL,                         -- Preload applied
    gauge_length_mm REAL,                   -- Initial gauge length
    temperature_C REAL,                     -- Test temperature
    humidity_percent REAL,                  -- Ambient humidity
    data_filename TEXT,                     -- Raw data file name
    data_filepath TEXT,                     -- Full path to data file
    operator TEXT,                          -- Person running the test
    test_run_number INTEGER DEFAULT 1,      -- If multiple runs per sample
    is_valid BOOLEAN DEFAULT TRUE,          -- Whether test data is valid
    failure_mode TEXT,                      -- e.g., 'midsubstance', 'insertion', 'grip'
    notes TEXT,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
);

-- 6. RESULTS TABLE: Calculated biomechanical properties
CREATE TABLE IF NOT EXISTS results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    sample_id TEXT NOT NULL,
    
    -- Primary outcomes
    max_load_N REAL,                        -- Ultimate failure load (N)
    stiffness_N_mm REAL,                    -- Stiffness/slope (N/mm)
    energy_to_failure_mJ REAL,              -- Area under curve (mJ)
    displacement_at_failure_mm REAL,        -- Displacement at max load
    
    -- Stiffness calculation details
    linear_region_start_idx INTEGER,        -- Start index of linear region
    linear_region_end_idx INTEGER,          -- End index of linear region
    linear_region_r2 REAL,                  -- R² of linear fit
    stiffness_method TEXT,                  -- 'sliding_window', 'manual', '20-60%'
    
    -- Additional mechanical properties (optional)
    yield_load_N REAL,                      -- Yield point load
    yield_displacement_mm REAL,             -- Displacement at yield
    toe_region_length_mm REAL,              -- Length of toe region
    
    -- Normalized properties (if cross-section available)
    cross_section_area_mm2 REAL,            -- Cross-sectional area
    stress_at_failure_MPa REAL,             -- Ultimate stress
    strain_at_failure_percent REAL,         -- Ultimate strain
    elastic_modulus_MPa REAL,               -- Young's modulus
    
    -- Metadata
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_version TEXT,                  -- Version of analysis script
    notes TEXT,
    
    FOREIGN KEY (test_id) REFERENCES biomechanical_tests(test_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
);

-- 7. RAW DATA TABLE: Store actual measurement points (optional, for small datasets)
CREATE TABLE IF NOT EXISTS raw_data_points (
    point_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    time_sec REAL,
    displacement_mm REAL,
    load_N REAL,
    FOREIGN KEY (test_id) REFERENCES biomechanical_tests(test_id)
);

-- 8. MANUAL STIFFNESS RESULTS: User-selected linear regions
CREATE TABLE IF NOT EXISTS manual_results (
    manual_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id TEXT NOT NULL,
    data_filename TEXT NOT NULL,
    reviewer TEXT,
    session_id TEXT,
    selection_start_idx INTEGER NOT NULL,
    selection_end_idx INTEGER NOT NULL,
    manual_stiffness_N_mm REAL NOT NULL,
    manual_r2 REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
);

-- ============================================================
-- INDEXES for faster queries
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_samples_subject ON samples(subject_id);
CREATE INDEX IF NOT EXISTS idx_samples_group ON samples(treatment_group);
CREATE INDEX IF NOT EXISTS idx_tests_sample ON biomechanical_tests(sample_id);
CREATE INDEX IF NOT EXISTS idx_results_sample ON results(sample_id);
CREATE INDEX IF NOT EXISTS idx_results_test ON results(test_id);
CREATE INDEX IF NOT EXISTS idx_manual_results_sample ON manual_results(sample_id);
CREATE INDEX IF NOT EXISTS idx_manual_results_reviewer ON manual_results(reviewer);

-- ============================================================
-- VIEWS for easy data access
-- ============================================================

-- View: Complete sample information with subject details
CREATE VIEW IF NOT EXISTS v_sample_details AS
SELECT 
    s.sample_id,
    s.subject_id,
    sub.internal_id,
    sub.weight_kg,
    sub.status AS subject_status,
    s.condition,
    s.treatment_group,
    tg.group_name,
    tg.description AS group_description,
    s.extraction_date,
    s.shoulder,
    s.notes AS sample_notes
FROM samples s
JOIN subjects sub ON s.subject_id = sub.subject_id
JOIN treatment_groups tg ON s.treatment_group = tg.group_id;

-- View: Complete results with all metadata
CREATE VIEW IF NOT EXISTS v_full_results AS
SELECT 
    r.result_id,
    s.sample_id,
    s.subject_id,
    sub.internal_id,
    sub.weight_kg,
    s.condition,
    s.treatment_group,
    tg.group_name,
    bt.test_date,
    bt.data_filename,
    bt.failure_mode,
    r.max_load_N,
    r.stiffness_N_mm,
    r.energy_to_failure_mJ,
    r.displacement_at_failure_mm,
    r.linear_region_r2,
    bt.is_valid
FROM results r
JOIN biomechanical_tests bt ON r.test_id = bt.test_id
JOIN samples s ON r.sample_id = s.sample_id
JOIN subjects sub ON s.subject_id = sub.subject_id
JOIN treatment_groups tg ON s.treatment_group = tg.group_id
WHERE bt.is_valid = TRUE;

-- View: Group statistics summary
CREATE VIEW IF NOT EXISTS v_group_statistics AS
SELECT 
    treatment_group,
    COUNT(*) as n,
    ROUND(AVG(max_load_N), 2) as mean_max_load_N,
    ROUND(AVG(stiffness_N_mm), 2) as mean_stiffness_N_mm,
    ROUND(AVG(energy_to_failure_mJ), 2) as mean_energy_mJ
FROM v_full_results
GROUP BY treatment_group;
