"""
SSP Interactive Analysis App (Streamlit)
"""

from pathlib import Path
from uuid import uuid4
import sys

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "Data"
sys.path.insert(0, str(DATA_DIR))

from app_utils import (  # noqa: E402
    build_sample_id,
    compute_manual_stiffness,
    get_metadata_for_sample,
    load_app_config,
    load_manual_results_csv,
    load_raw_curve,
    load_results_csv,
    parse_filename,
    save_manual_result,
    save_manual_result_db
)


st.set_page_config(page_title="SSP Analysis", layout="wide")

config, data_root, paths = load_app_config()
results_df = load_results_csv(paths["results_csv"])
selected_data_dir = paths["selected_data_dir"]
results_dir = paths["results_dir"]
db_path = paths["database_path"]

st.title("SSP Biomechanics Interactive Analysis")

if results_df.empty:
    st.error("Results file not found. Run the analysis pipeline first.")
    st.stop()

if not db_path.exists():
    st.warning("Database not found. Metadata panel will be empty until a database is provided.")

st.sidebar.header("Filters")
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid4())
reviewer_name = st.sidebar.text_input("Reviewer name", value="")
session_id = st.sidebar.text_input("Session ID", value=st.session_state["session_id"])
subject_options = ["All"] + sorted(results_df["SampleID"].dropna().unique().tolist())
group_options = ["All"] + sorted(results_df["Subgroup"].dropna().unique().tolist())
condition_options = ["All", "NO", "OPER"]

subject_filter = st.sidebar.selectbox("Subject", subject_options, index=0)
group_filter = st.sidebar.selectbox("Group", group_options, index=0)
condition_filter = st.sidebar.selectbox("Condition", condition_options, index=0)

filtered_df = results_df.copy()
if subject_filter != "All":
    filtered_df = filtered_df[filtered_df["SampleID"] == subject_filter]
if group_filter != "All":
    filtered_df = filtered_df[filtered_df["Subgroup"] == group_filter]
if condition_filter != "All":
    if condition_filter == "NO":
        filtered_df = filtered_df[filtered_df["Filename"].str.contains("_NO", na=False)]
    else:
        filtered_df = filtered_df[filtered_df["Filename"].str.contains("_OPER", na=False)]

st.sidebar.markdown(f"**Samples matched:** {len(filtered_df)}")

sample_files = filtered_df["Filename"].dropna().tolist()
selected_file = st.selectbox("Select sample file", sample_files)

subject_id, condition = parse_filename(selected_file)
sample_id = build_sample_id(selected_file)

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Sample Metadata")
    if sample_id:
        metadata = get_metadata_for_sample(db_path, sample_id)
        if metadata:
            st.json(metadata)
        else:
            st.info("No metadata found in database for this sample.")
    else:
        st.info("Could not parse sample ID from filename.")

with col_right:
    st.subheader("Automated Results")
    row = results_df[results_df["Filename"] == selected_file].iloc[0]
    st.metric("Max Load (N)", f"{row['MaxLoad_N']:.2f}")
    st.metric("Stiffness (N/mm)", f"{row['Stiffness_N_mm']:.2f}")
    st.metric("Energy (mJ)", f"{row['Energy_mJ']:.2f}")
    st.metric("Linear Region R²", f"{row['R2_Score']:.4f}")

st.subheader("Load vs Displacement (manual linear region selection)")
st.caption("Drag to select a range on the plot (box select).")

raw_path = selected_data_dir / selected_file
raw_df = load_raw_curve(raw_path)

if raw_df is None:
    st.error(f"Raw file not found: {raw_path}")
    st.stop()

if "Crossheadmm" not in raw_df.columns or "LoadN" not in raw_df.columns:
    st.error("Raw data missing required columns: Crossheadmm, LoadN.")
    st.stop()

x = raw_df["Crossheadmm"].to_numpy()
y = raw_df["LoadN"].to_numpy()

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        marker=dict(size=3),
        name="Load"
    )
)
fig.update_layout(
    xaxis_title="Displacement (mm)",
    yaxis_title="Load (N)",
    dragmode="select",
    height=500
)

selected_points = plotly_events(
    fig,
    select_event=True,
    click_event=False,
    hover_event=False,
    key="selection"
)

selected_indices = [p["pointIndex"] for p in selected_points] if selected_points else []

manual_result = None
if selected_indices:
    manual_result = compute_manual_stiffness(x, y, selected_indices)

st.subheader("Manual Stiffness")
if manual_result:
    st.write(
        f"Selection: index {manual_result['start_idx']} to {manual_result['end_idx']} "
        f"({len(set(selected_indices))} points)"
    )
    st.metric("Manual Stiffness (N/mm)", f"{manual_result['slope']:.2f}")
    st.metric("Manual R²", f"{manual_result['r2']:.4f}")

    if st.button("Save manual stiffness result"):
        record = {
            "filename": selected_file,
            "sample_id": sample_id or "",
            "subject_id": subject_id or "",
            "condition": condition,
            "subgroup": row["Subgroup"],
            "reviewer": reviewer_name.strip() or None,
            "session_id": session_id.strip() or None,
            "selection_start_idx": manual_result["start_idx"],
            "selection_end_idx": manual_result["end_idx"],
            "manual_stiffness_N_mm": manual_result["slope"],
            "manual_r2": manual_result["r2"]
        }
        output_path = save_manual_result(results_dir, record)
        save_manual_result_db(db_path, record)
        st.success(f"Saved to {output_path}")
else:
    st.info("Select points on the plot to compute manual stiffness.")

st.subheader("Manual Stiffness History")
manual_df = load_manual_results_csv(results_dir)
if manual_df.empty:
    st.info("No manual stiffness results saved yet.")
else:
    st.dataframe(manual_df, use_container_width=True)

st.subheader("Export Manual Selections")
if manual_df.empty:
    st.caption("No data to export yet.")
else:
    export_df = manual_df.copy()
    if reviewer_name.strip():
        export_df = export_df[export_df["reviewer"] == reviewer_name.strip()]
    if session_id.strip():
        export_df = export_df[export_df["session_id"] == session_id.strip()]
    export_csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download manual selections (CSV)",
        data=export_csv,
        file_name="manual_stiffness_export.csv",
        mime="text/csv"
    )

st.subheader("Group Summary")
summary = results_df.groupby("Subgroup").agg(
    MaxLoad=("MaxLoad_N", "mean"),
    MaxLoad_Std=("MaxLoad_N", "std"),
    Stiffness=("Stiffness_N_mm", "mean"),
    Stiffness_Std=("Stiffness_N_mm", "std"),
    Energy=("Energy_mJ", "mean"),
    Energy_Std=("Energy_mJ", "std")
).reset_index()

summary_fig = go.Figure()
summary_fig.add_trace(go.Bar(
    x=summary["Subgroup"],
    y=summary["MaxLoad"],
    name="Max Load",
    error_y=dict(type="data", array=summary["MaxLoad_Std"].fillna(0))
))
summary_fig.add_trace(go.Bar(
    x=summary["Subgroup"],
    y=summary["Stiffness"],
    name="Stiffness",
    error_y=dict(type="data", array=summary["Stiffness_Std"].fillna(0))
))
summary_fig.add_trace(go.Bar(
    x=summary["Subgroup"],
    y=summary["Energy"],
    name="Energy",
    error_y=dict(type="data", array=summary["Energy_Std"].fillna(0))
))
summary_fig.update_layout(
    barmode="group",
    xaxis_title="Group",
    yaxis_title="Mean Value",
    height=400
)
st.plotly_chart(summary_fig, use_container_width=True)
