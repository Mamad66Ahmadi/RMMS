import pandas as pd
from pathlib import Path
import streamlit as st


def load_motor_spec(tag: str):
    """
    Load Motor Specification.xlsx and return the row where ITEM == tag.
    Returns a Pandas Series or None.
    """
    try:
        data_path = Path(__file__).resolve().parents[1] / "data" / "Motor Specification.xlsx"

        if not data_path.exists():
            st.warning("⚠️ Motor Specification.xlsx not found in /data")
            return None

        df = pd.read_excel(data_path)

        # Normalize column names
        df.columns = [col.strip().upper() for col in df.columns]

        if "ITEM" not in df.columns:
            st.warning("⚠️ Sheet does not contain 'ITEM' column.")
            return None

        df["ITEM"] = df["ITEM"].astype(str).str.strip().str.upper()

        tag_normalized = str(tag).strip().upper()
        matched = df[df["ITEM"] == tag_normalized]

        if matched.empty:
            return None

        return matched.iloc[0]  # return first matching row as Series

    except Exception as e:
        st.error(f"Error reading Motor Specification.xlsx: {e}")
        return None



def render_motor_spec_row(row):
    """
    Display the motor specification row as a DataFrame (single row table).
    """

    # Convert Series → DataFrame
    df = row.to_frame().T

    # Fix column names (strip + capitalize)
    df.columns = [str(col).strip() for col in df.columns]


    st.dataframe(df, use_container_width=True)
