# standby_comparison.py

import sqlite3
import pandas as pd
import streamlit as st
import time
from pathlib import Path

# --- Database path ---
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


# ==========================================================
# 🔹 Get sibling standby tags for the given tag
# ==========================================================
def get_standby_variants(active_tag: str):
    """Return a list of sibling standby tags (excluding the active one)."""
    if not active_tag or active_tag.count("-") != 2 or not active_tag[-1].isalpha():
        return []

    # Example: 113-P-116A → root = "113-P-116"
    root = active_tag[:-1]

    db_uri = f"file:{DB_PATH}?mode=ro"

    for attempt in range(3):  # Retry mechanism
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")

                tags = pd.read_sql_query(
                    "SELECT Object_Tag FROM objects WHERE Object_Tag LIKE ?",
                    conn,
                    params=[f"{root}%"],
                )["Object_Tag"].dropna().astype(str).tolist()

            tags = sorted(set(tags))
            return [t for t in tags if t != active_tag]

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 2:
                time.sleep(1.5)
            else:
                st.error(f"Database error while fetching standby variants: {e}")
                return []

    return []


# ==========================================================
# 🔹 Safe job count with PM, CM, and Total
# ==========================================================
def _safe_job_breakdown(tag: str, max_attempts: int = 3, delay: float = 1.5):
    """Return total, PM, CM counts for a tag with retry and safety."""
    db_uri = f"file:{DB_PATH}?mode=ro"

    for attempt in range(max_attempts):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")

                df = pd.read_sql_query(
                    """
                    SELECT 
                        SUM(CASE WHEN UPPER(job_type) = 'PM' THEN 1 ELSE 0 END) AS PM,
                        SUM(CASE WHEN UPPER(job_type) = 'CM' THEN 1 ELSE 0 END) AS CM,
                        COUNT(*) AS Total
                    FROM job_reports
                    WHERE Object_Tag = ?
                    """,
                    conn,
                    params=[tag],
                )

                row = df.iloc[0]
                pm = int(row["PM"] or 0)
                cm = int(row["CM"] or 0)
                total = int(row["Total"] or 0)
                return pm, cm, total

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                st.warning(f"Error fetching job breakdown for {tag}: {e}")
                return 0, 0, 0
        except Exception as e:
            st.warning(f"Unexpected error for {tag}: {e}")
            return 0, 0, 0

    return 0, 0, 0


# ==========================================================
# 🔹 Main Function: Render Standby Comparison Chart
# ==========================================================
def render_standby_comparison(active_tag: str):
    """Display a visual summary (no charts) comparing PM/CM job counts between standby tags."""
    standby_tags = get_standby_variants(active_tag)

    if not standby_tags:
        st.info("No standby units found for this tag.")
        return

    # --- Collect job counts safely
    job_data = []
    all_tags = [active_tag] + standby_tags

    for tag in all_tags:
        pm, cm, total = _safe_job_breakdown(tag)
        pm_percent = (pm / total * 100) if total > 0 else 0
        job_data.append((tag, pm, cm, total, round(pm_percent, 1)))

    # --- Convert to DataFrame
    df = pd.DataFrame(job_data, columns=["Tag", "PM", "CM", "Total", "PM %"])
    df = df.sort_values("Tag").reset_index(drop=True)

    # --- Calculate overall statistics
    total_all = df["Total"].sum()
    highest_total = df.loc[df["Total"].idxmax()]
    highest_pm = df.loc[df["PM %"].idxmax()]
    highest_cm = df.loc[df["CM"].idxmax()]

    # Active tag share among all records
    active_total = df.loc[df["Tag"] == active_tag, "Total"].iloc[0]
    active_share = (active_total / total_all * 100) if total_all > 0 else 0

    # --- Function for coloring active tag ---
    def color_tag(tag):
        return "#830520" if tag == active_tag else "#117A65"

    # --- 4️⃣ Active tag contribution ---
    st.markdown(
        f"""
        🔹 <b span style='color:{color_tag(active_tag)};'>{active_tag}</span></b> 
        contributes <b style='color:#8E44AD;'>{round(active_share, 1)}%</b> of 
        the total <b style='color:#C62300;'>{total_all}</b> job records among its standby group.
        """,
        unsafe_allow_html=True,
    )

    # --- Separator line (no gaps) ---
    st.markdown(
        "<hr style='border:none; border-top:1.5px solid #bbb; margin-top:0px; margin-bottom:0px;'>",
        unsafe_allow_html=True
    )

    # --- 1️⃣ Highest total records ---
    st.markdown(
        f"""
        🔹 <b style='color:#132440;'> 
        <span style='color:{color_tag(highest_total["Tag"])};'>{highest_total['Tag']}</span></b> 
        has the <b style='color:#1F618D;'>highest total job records</b> with 
        <b style='color:#CB4335;'>{highest_total['Total']}</b> entries.
        """,
        unsafe_allow_html=True,
    )

    # --- 3️⃣ Highest CM count (only show if > 0) ---
    if highest_cm["CM"] > 0:
        st.markdown(
            f"""
            🔹 <b style='color:#154360;'> 
            <span style='color:{color_tag(highest_cm["Tag"])};'>{highest_cm['Tag']}</span></b> 
            has the <b style='color:#CA6F1E;'>highest CM count</b> with 
            <b style='color:#E67E22;'>{highest_cm['CM']}</b> records.
            """,
            unsafe_allow_html=True,
        )

    # --- 2️⃣ Highest PM rate (only show if > 0) ---
    if highest_pm["PM %"] > 0:
        st.markdown(
            f"""
            🔹 <b style='color:#154360;'> 
            <span style='color:{color_tag(highest_pm["Tag"])};'>{highest_pm['Tag']}</span></b> 
            has the <b style='color:#3B1C32;'>highest PM rate</b> of 
            <b style='color:#3B1C32;'>{highest_pm['PM %']}%</b>.
            """,
            unsafe_allow_html=True,
        )
    st.markdown(
        "<span style='color:#555;'>(Note: these highest values may also be shared by other tags.)</span>",
        unsafe_allow_html=True
    )