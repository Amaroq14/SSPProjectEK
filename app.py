"""
Streamlit entrypoint wrapper.
Runs the app located in Data/app.py for Streamlit Cloud.
"""

from pathlib import Path
import runpy

APP_PATH = Path(__file__).resolve().parent / "Data" / "app.py"
runpy.run_path(str(APP_PATH), run_name="__main__")
