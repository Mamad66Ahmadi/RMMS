import streamlit as st
from pathlib import Path
import pandas as pd


CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "Failure Modes.csv"


def get_failure_modes_by_type(object_type: str) -> list:
    """
    Reads 'Failure Modes.csv' from the data folder and returns
    a list of failure modes for the given object type (column name).

    If the object_type contains words like switch, transmitter, gauge...
    it automatically maps to the 'Sensor' column.
    """
    if not CSV_PATH.exists():
        return []

    try:
        df = pd.read_csv(CSV_PATH)
        available_columns = [c.strip() for c in df.columns]

        if not object_type:
            return []

        obj_type_lower = object_type.strip().lower()

        # Sensor keyword mapping
        sensor_keywords = [
            "switch", "element", "transmitter", "gauge", "indicator",
            "detector", "monitor", "phasor", "probe", "sensor"
        ]
        if any(word in obj_type_lower for word in sensor_keywords):
            object_type = "Sensor"

        # case-insensitive lookup
        matching_column = next(
            (col for col in available_columns if col.lower() == object_type.lower()),
            None
        )
        if not matching_column:
            return []

        modes = (
            df[matching_column]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

        modes = sorted(set([m for m in modes if m]))
        return modes

    except Exception as e:
        st.warning(f"⚠️ Error reading Failure Modes: {e}")
        return []


# ---------------------------------------------------------------------
# ✅ NEW FUNCTION
# ---------------------------------------------------------------------
def append_failure_mode(object_type: str, new_mode: str) -> bool:
    """
    Adds a new failure mode to the CSV for the given object_type.
    - Auto-maps sensors to 'Sensor'
    - Creates the CSV if missing
    - Creates a column if missing
    - Prevents duplicate values
    - Returns True if added, False otherwise
    """

    new_mode = new_mode.strip()
    if not object_type or not new_mode:
        return False

    # --- Normalize object type ---
    obj_type_lower = object_type.strip().lower()
    sensor_keywords = [
        "switch", "element", "transmitter", "gauge", "indicator",
        "detector", "monitor", "phasor", "probe", "sensor"
    ]
    if any(word in obj_type_lower for word in sensor_keywords):
        object_type = "Sensor"

    try:
        # --- Create CSV if it does not exist ---
        if not CSV_PATH.exists():
            df = pd.DataFrame({object_type: [new_mode]})
            df.to_csv(CSV_PATH, index=False)
            return True

        # --- Load existing CSV ---
        df = pd.read_csv(CSV_PATH)

        # Clean column names
        df.columns = [c.strip() for c in df.columns]

        # --- If column does NOT exist → create it ---
        if object_type not in df.columns:
            df[object_type] = None

        # --- Load current values ---
        current_modes = (
            df[object_type]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

        # --- Prevent duplicates ---
        if new_mode.lower() in [m.lower() for m in current_modes]:
            return False

        # --- Append new row (safe) ---
        df = pd.concat(
            [df, pd.DataFrame({object_type: [new_mode]})],
            ignore_index=True
        )

        # --- Save back ---
        df.to_csv(CSV_PATH, index=False)

        return True

    except Exception as e:
        st.warning(f"⚠️ Error updating Failure Modes CSV: {e}")
        return False
