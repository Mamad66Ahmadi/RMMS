#other_trains_comparison.py

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

import re

from utils.standby_comparison import get_standby_variants   # ← USE YOUR FUNCTION

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


def get_typical_family(active_tag: str):
    """
    Build full typical family:
      - use get_standby_variants(active_tag)
      - find typical trains for active tag + each standby
      - stop when next train does NOT exist
      - return sorted unique list of real tags in objects table
    """

    # -----------------------------------------
    # Helper: extract parts needed for variants
    # -----------------------------------------
    def extract_train_info(tag: str):
        """
        Return (prefix, train_number, suffix, tail)
        prefix:   "104-KM-"
        train_number: "301"
        suffix:   "A"
        tail:     "-AM1A" or "" if nothing after train block
        """
        parts = tag.split("-")
        if len(parts) < 3:
            return None

        block = parts[2]  # e.g., "301A", "101B", "101AM1A"

        m = re.match(r"(\d{3})(.*)", block)
        if not m:
            return None

        number_block = m.group(1)      # "301"
        suffix = m.group(2)            # "A"
        prefix = "-".join(parts[:2]) + "-"
        tail = "-" + "-".join(parts[3:]) if len(parts) > 3 else ""

        return prefix, number_block, suffix, tail

    # -----------------------------------------
    # Load full prefix group from DB once
    # -----------------------------------------
    parts = active_tag.split("-")
    prefix_main = "-".join(parts[:2]) + "-"

    db_uri = f"file:{DB_PATH}?mode=ro"

    try:
        with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            df = pd.read_sql_query(
                "SELECT Object_Tag FROM objects WHERE Object_Tag LIKE ?",
                conn,
                params=[prefix_main + "%"],
            )
    except Exception:
        return []

    existing = set(df["Object_Tag"].astype(str).tolist())

    # -----------------------------------------
    # Collect standbys using your existing function
    # -----------------------------------------
    standbys = get_standby_variants(active_tag)

    # The set of tags we will return
    result = set()
    result.add(active_tag)
    result.update(standbys)

    # -----------------------------------------
    # Generate typical trains for a tag
    # -----------------------------------------
    def generate_typicals(tag):
        info = extract_train_info(tag)
        if not info:
            return []

        prefix, num_block, suffix, tail = info

        typicals = []
        miss_count = 0   # count consecutive missing trains

        # Check trains 1 through 6
        for t in range(1, 7):
            new_train_block = f"{t}{num_block[1:]}"
            candidate = f"{prefix}{new_train_block}{suffix}{tail}"

            if candidate in existing:
                typicals.append(candidate)
                miss_count = 0   # reset misses
            else:
                miss_count += 1
                if miss_count >= 2:  # stop after TWO consecutive failures
                    break

        return typicals


    # -----------------------------------------
    # Apply typical generation for active + standby
    # -----------------------------------------
    for t in [active_tag] + standbys:
        for variant in generate_typicals(t):
            result.add(variant)
    import streamlit as st
    st.write(result)
    return sorted(result)


# --------------------------------------------------------------##################################
#            Charts and stats 
# --------------------------------------------------------------#################################

def render_typical_trains_comparison(active_tag: str):
    """
    Build two stacked bar charts (PM and CM) + summary statistics
    for all typical-family tags across the last 12 months.
    """

    # ===============================================
    # 1️⃣ Load all typical family tags
    # ===============================================
    tags = get_typical_family(active_tag)

    if not tags:
        st.info("⚠️ No typical family found for this tag.")
        return

    if len(tags) == 1 and tags[0] == active_tag:
        st.info("⚠️ No typical family exists for this tag.")
        return

    max_tags = 10

    # ===============================================
    # 2️⃣ Prepare date range (last 12 months)
    # ===============================================
    today = datetime.today().date()
    year_ago = today - timedelta(days=365)
    months = pd.date_range(start=year_ago, end=today, freq="MS").strftime("%Y-%m")

    # ===============================================
    # 3️⃣ Single DB query for ALL statistics
    # ===============================================
    db_uri = f"file:{DB_PATH}?mode=ro"

    try:
        with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")

            df = pd.read_sql_query(
                f"""
                SELECT Object_Tag, job_type, date
                FROM job_reports
                WHERE Object_Tag IN ({','.join(['?'] * len(tags))})
                AND date >= ?
                """,
                conn,
                params=tags + [year_ago.strftime("%Y-%m-%d")],
            )

    except Exception as e:
        st.error(f"Database error: {e}")
        return

    if df.empty:
        st.info("No job records found for these tags in the last year.")
        return

    # Preprocessing
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["job_type"] = df["job_type"].str.upper()

    # ===============================================
    # 4️⃣ Pivot tables (PM / CM monthly)
    # ===============================================
    pm_pivot = (
        df[df["job_type"] == "PM"]
        .groupby(["month", "Object_Tag"]).size()
        .unstack(fill_value=0)
        .reindex(months, fill_value=0)
    )

    cm_pivot = (
        df[df["job_type"] == "CM"]
        .groupby(["month", "Object_Tag"]).size()
        .unstack(fill_value=0)
        .reindex(months, fill_value=0)
    )

    valid_tags = set(pm_pivot.columns).union(cm_pivot.columns)

    if not valid_tags:
        st.info("No PM/CM records found in the last 12 months.")
        return

    # Rank by total count (PM+CM)
    total_counts = (
        df.groupby("Object_Tag")
        .size()
        .sort_values(ascending=False)
    )

    top_tags = total_counts.head(max_tags).index.tolist()
    # ===============================================
    # 5️⃣ Charts (show only if at least one tag has data)
    # ===============================================

    # --- CM Chart (only if any CM exists) ---
    if cm_pivot.sum().sum() > 0:      # <── checks if any CM count exists
        fig_cm = go.Figure()
        for tag in top_tags:
            if tag in cm_pivot.columns and cm_pivot[tag].sum() > 0:
                fig_cm.add_trace(go.Bar(x=months, y=cm_pivot[tag], name=tag))

        fig_cm.update_layout(
            title=f"CM Jobs per Month (Typical Family of {active_tag})",
            barmode="stack",
            xaxis_title="Month",
            yaxis_title="CM Count",
            height=400,
        )
    else:
        fig_cm = None


    # --- PM Chart (only if any PM exists) ---
    if pm_pivot.sum().sum() > 0:      # <── checks if any PM count exists
        fig_pm = go.Figure()
        for tag in top_tags:
            if tag in pm_pivot.columns and pm_pivot[tag].sum() > 0:
                fig_pm.add_trace(go.Bar(x=months, y=pm_pivot[tag], name=tag))

        fig_pm.update_layout(
            title=f"PM Jobs per Month (Typical Family of {active_tag})",
            barmode="stack",
            xaxis_title="Month",
            yaxis_title="PM Count",
            height=400,
        )
    else:
        fig_pm = None


    # ===============================================
    # Display charts dynamically
    # ===============================================
    col1, col2 = st.columns(2)

    with col1:
        if fig_cm:
            st.plotly_chart(fig_cm, use_container_width=True)
        else:
            st.markdown("No CM data.")

    with col2:
        if fig_pm:
            st.plotly_chart(fig_pm, use_container_width=True)
        else:
            st.markdown("No PM data.")

    # ===============================================
    # 6️⃣ Summary statistics (using SAME df)
    # ===============================================
    st.markdown("<hr style='border:none; border-top:2px solid #888;'>",
                unsafe_allow_html=True)

    summary_data = []
    for tag in top_tags:
        pm_total = pm_pivot[tag].sum() if tag in pm_pivot else 0
        cm_total = cm_pivot[tag].sum() if tag in cm_pivot else 0
        total = pm_total + cm_total
        pm_rate = (pm_total / total * 100) if total else 0
        summary_data.append((tag, pm_total, cm_total, total, round(pm_rate, 1)))

    df_summary = pd.DataFrame(summary_data,
                              columns=["Tag", "PM", "CM", "Total", "PM%"])

    total_all = df_summary["Total"].sum()
    highest_total = df_summary.loc[df_summary["Total"].idxmax()]
    highest_pm = df_summary.loc[df_summary["PM%"].idxmax()]
    highest_cm = df_summary.loc[df_summary["CM"].idxmax()]
    active_total = df_summary[df_summary["Tag"] == active_tag]["Total"].iloc[0]
    active_share = (active_total / total_all * 100) if total_all else 0

    # Coloring function
    def color_tag(tag):
        return "#830520" if tag == active_tag else "#117A65"

    # ==========================================================
    # 🟣 Active Tag Contribution
    # ==========================================================
    st.markdown(
        f"""
        🔹 <b span style='color:{color_tag(active_tag)};'>{active_tag}</span></b> 
        contributes <b style='color:#8E44AD;'>{round(active_share, 1)}%</b> of 
        the total <b style='color:#C62300;'>{total_all}</b> job records among its <b>Typical Family</b> (last 12 months).
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<hr style='border:none; border-top:1.5px solid #bbb; margin-top:5px; margin-bottom:5px;'>",
        unsafe_allow_html=True
    )

    # ==========================================================
    # 🔵 Highest Total Records
    # ==========================================================
    st.markdown(
        f"""
        🔹 <b style='color:#132440;'>
        <span style='color:{color_tag(highest_total['Tag'])};'>{highest_total['Tag']}</span></b> has the <b style='color:#1F618D;'>highest total job count </b> with <b style='color:#CB4335;'>{highest_total['Total']}</b> jobs in the last 12 months.
        """,
        unsafe_allow_html=True,
    )

    # ==========================================================
    # 🔴 Highest CM Count (if > 0)
    # ==========================================================
    if highest_cm["CM"] > 0:
        st.markdown(
            f"""
            🔹 <b style='color:#154360;'>
            <span style='color:{color_tag(highest_cm['Tag'])};'>{highest_cm['Tag']}</span></b> has the <b style='color:#CA6F1E;'>highest CM count</b> with <b style='color:#E67E22;'>{highest_cm['CM']}</b> corrective jobs.
            """,
            unsafe_allow_html=True,
        )

    # ==========================================================
    # 🟢 Highest PM Rate (if > 0)
    # ==========================================================
    if highest_pm["PM%"] > 0:
        st.markdown(
            f"""
            🔹 <b style='color:#154360;'>
            <span style='color:{color_tag(highest_pm['Tag'])};'>{highest_pm['Tag']}</span></b> has the <b style='color:#3B1C32;'>highest PM rate</b> of <b style='color:#3B1C32;'>{highest_pm['PM%']}%</b>.
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<span style='color:#555;'>(Note: these highest values may also be shared by other tags.)</span>",
        unsafe_allow_html=True
    )