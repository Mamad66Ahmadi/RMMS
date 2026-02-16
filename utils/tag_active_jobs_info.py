# utils/tag_active_jobs_info.py

import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


def get_active_job_counts_by_department(tag: str):
    """
    For a given tag:
    - fetch ALL CM records
    - deduplicate by WO/Permit (keep latest)
    - count ongoing / on hold per department
    """
    db_uri = f"file:{DB_PATH}?mode=ro"

    try:
        with sqlite3.connect(db_uri, uri=True, timeout=3) as conn:
            df = pd.read_sql_query(
                """
                SELECT
                    job_indx,
                    date,
                    department,
                    status,
                    wo_number,
                    permit_number
                FROM job_reports
                WHERE Object_Tag = ?
                  AND lower(job_type) = 'cm'
                ORDER BY date DESC, rowid DESC
                """,
                conn,
                params=[tag],
            )

        if df.empty:
            return {}

        # -----------------------
        # Normalize
        # -----------------------
        df["status"] = df["status"].str.lower().fillna("")
        df["department"] = df["department"].fillna("Unknown")
        df["wo_number"] = df["wo_number"].fillna("").astype(str)
        df["permit_number"] = df["permit_number"].fillna("").astype(str)

        # -----------------------
        # Deduplicate by WO / Permit
        # -----------------------
        df = df.sort_values(by=["date", "job_indx"], ascending=[False, False])
        df = df.drop_duplicates(subset=["wo_number", "permit_number"], keep="first")

        # -----------------------
        # Filter active statuses
        # -----------------------
        df = df[df["status"].isin(["ongoing", "on hold"])]

        if df.empty:
            return {}

        # -----------------------
        # Count per department
        # -----------------------
        result = defaultdict(lambda: {"ongoing": 0, "on hold": 0})

        for _, row in df.iterrows():
            dept = row["department"]
            status = row["status"]
            result[dept][status] += 1

        return dict(result)

    except Exception as e:
        st.error(f"⚠️ Error calculating active job info: {e}")
        return {}


def render_active_jobs_info_line(tag: str):
    """
    Render human-readable info line below routes section
    """
    data = get_active_job_counts_by_department(tag)

    if not data:
        return

    lines = []
    for dept, counts in data.items():
        parts = []
        if counts["ongoing"]:
            parts.append(f"{counts['ongoing']} ongoing")
        if counts["on hold"]:
            parts.append(f"{counts['on hold']} on hold")

        if parts:
            lines.append(
                f"<b>{dept}</b>: " + " and ".join(parts)
            )

    if not lines:
        return

    html = f"""
    <div style="
        background:#f8f9fa;
        border-left:5px solid #ff9800;
        padding:10px 14px;
        margin:8px 0 12px 0;
        border-radius:6px;
        font-size:14px;
        color:#333;
    ">
        <b>📌 Active CM Reports for {tag}:</b><br>
        {"<br>".join(lines)}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
