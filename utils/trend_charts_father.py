# utils/family_charts.py
import pandas as pd
import sqlite3
from pathlib import Path
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


# -----------------------------------------------------------
# 🔍 Load 1-year CM/PM + department
# -----------------------------------------------------------
def load_family_year_data(family_tags, days_back=365):
    date_to = datetime.today().date()
    date_from = date_to - timedelta(days=days_back)

    placeholders = ",".join(["?"] * len(family_tags))
    params = family_tags + [str(date_from), str(date_to)]

    query = f"""
        SELECT Object_Tag, job_type, department
        FROM job_reports
        WHERE Object_Tag IN ({placeholders})
        AND date BETWEEN ? AND ?
    """

    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            df = pd.read_sql_query(query, conn, params=params)
    except:
        return pd.DataFrame()

    df["job_type"] = df["job_type"].astype(str).str.upper()
    df["department"] = df["department"].astype(str).fillna("Unknown")
    return df


# -----------------------------------------------------------
# 📊 Render Family Charts (CM/PM) stacked by department
# -----------------------------------------------------------
def render_family_cm_pm_charts(family_tags):
    df = load_family_year_data(family_tags)

    if df.empty:
        st.warning("No CM/PM records found for the last 12 months.")
        return

    # Aggregate PM & CM counts grouped by department
    df_grouped = (
        df.groupby(["Object_Tag", "job_type", "department"])
        .size()
        .reset_index(name="Count")
    )

    # Determine top 7 tags by total activity
    total_counts = (
        df_grouped.groupby("Object_Tag")["Count"].sum().sort_values(ascending=False)
    )
    top7_tags = total_counts.head(7).index.tolist()

    df_grouped = df_grouped[df_grouped["Object_Tag"].isin(top7_tags)]

    # Split into PM and CM parts
    df_pm = df_grouped[df_grouped["job_type"] == "PM"]
    df_cm = df_grouped[df_grouped["job_type"] == "CM"]

    col1, col2 = st.columns(2)

    # ========== PM CHART (STACKED BY DEPARTMENT) ==========
    with col1:
        st.markdown("🟢 PM Counts (Last 12 Months, Stacked by Department)")
        if df_pm.empty:
            st.info("No PM records for this family.")
        else:
            fig_pm = px.bar(
                df_pm,
                x="Object_Tag",
                y="Count",
                color="department",
                barmode="stack",
                text="Count",
            )
            fig_pm.update_traces(textposition="outside")
            fig_pm.update_layout(legend_title_text="Department")
            st.plotly_chart(fig_pm, use_container_width=True)

    # ========== CM CHART (STACKED BY DEPARTMENT) ==========
    with col2:
        st.markdown("🟠 CM Counts (Last 12 Months, Stacked by Department)")
        if df_cm.empty:
            st.info("No CM records for this family.")
        else:
            fig_cm = px.bar(
                df_cm,
                x="Object_Tag",
                y="Count",
                color="department",
                barmode="stack",
                text="Count",
            )
            fig_cm.update_traces(textposition="outside")
            fig_cm.update_layout(legend_title_text="Department")
            st.plotly_chart(fig_cm, use_container_width=True)
