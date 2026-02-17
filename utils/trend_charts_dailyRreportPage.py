# utils/chart_module.py
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 1) SHARED DATA LOADER
# ============================================================
def load_job_data(days_back=365):
    """
    Loads job_reports + objects table (unit) with ONE optimized JOIN.
    Returns fully processed dataframe:
        • date (datetime)
        • month (YYYY-MM)
        • month_order (datetime for sorting)
        • job_type
        • department
        • unit
    """

    DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

    date_to = datetime.today().date()
    date_from = date_to - timedelta(days=days_back)

    query = """
        SELECT 
            r.date,
            r.job_type,
            r.department,
            r.Object_Tag,
            o.Unit_Code AS unit,
            o.Object_Type
        FROM job_reports r
        LEFT JOIN objects o
            ON r.Object_Tag = o.Object_Tag
        WHERE r.date BETWEEN ? AND ?
    """

    db_uri = f"file:{DB_PATH}?mode=ro"

    with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
        df = pd.read_sql_query(query, conn, params=[str(date_from), str(date_to)])

    # date & month
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["month_order"] = df["date"].dt.to_period("M").apply(lambda p: p.start_time)

    df["unit"] = df["unit"].fillna("Unknown").astype(str)

    return df



# ============================================================
# 2) PM/CM TREND CHARTS (1 YEAR OVERVIEW)
# ============================================================
def trend_chart_object_page():
    import streamlit as st
    import plotly.express as px

    df = load_job_data(365)

    if df.empty:
        st.warning("⚠️ No records for last 12 months.")
        return

    # ------------------------------------------------------------
    # MONTH ORDER HANDLING
    # ------------------------------------------------------------
    month_order_df = (
        df[["month_order", "month"]]
        .drop_duplicates()
        .sort_values("month_order")
    )
    month_label_list = month_order_df["month"].tolist()

    # ------------------------------------------------------------
    # SEPARATE PM AND CM FIRST
    # ------------------------------------------------------------
    df_pm = df[df["job_type"].str.upper() == "PM"]
    df_cm = df[df["job_type"].str.upper() == "CM"]

    # ------------------------------------------------------------
    # PM / CM COUNT PER DEPARTMENT
    # ------------------------------------------------------------
    pm_grouped = df_pm.groupby(["month", "department"]).size().reset_index(name="Count")
    cm_grouped = df_cm.groupby(["month", "department"]).size().reset_index(name="Count")

    # ------------------------------------------------------------
    # TOP 7 UNITS BASED ON PM AND CM SEPARATELY
    # ------------------------------------------------------------
    top_units_pm = df_pm["unit"].value_counts().head(10).index.tolist()
    top_units_cm = df_cm["unit"].value_counts().head(10).index.tolist()

    # st.info({"Top Units PM": top_units_pm})
    # st.info({"Top Units CM": top_units_cm})

    # ------------------------------------------------------------
    # GROUP UNITS: Top 12 + Others
    # ------------------------------------------------------------

    # PM
    df_pm_units = df_pm.copy()
    df_pm_units["unit_grouped"] = df_pm_units["unit"].where(
        df_pm_units["unit"].isin(top_units_pm),
        "Others"
    )

    pm_unit = (
        df_pm_units.groupby(["month", "unit_grouped"])
        .size()
        .reset_index(name="Count")
        .rename(columns={"unit_grouped": "unit"})
    )

    # CM
    df_cm_units = df_cm.copy()
    df_cm_units["unit_grouped"] = df_cm_units["unit"].where(
        df_cm_units["unit"].isin(top_units_cm),
        "Others"
    )

    cm_unit = (
        df_cm_units.groupby(["month", "unit_grouped"])
        .size()
        .reset_index(name="Count")
        .rename(columns={"unit_grouped": "unit"})
    )

    # ============================================================
    # DISPLAY CHARTS — PM & CM by DEPARTMENT
    # ============================================================

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 PM Trend — Stacked by Department**")
        fig_pm = px.bar(pm_grouped, x="month", y="Count",
                        color="department", barmode="stack")
        fig_pm.update_xaxes(categoryorder="array", categoryarray=month_label_list)
        st.plotly_chart(fig_pm, use_container_width=True)

    with col2:
        st.markdown("**📊 CM Trend — Stacked by Department**")
        fig_cm = px.bar(cm_grouped, x="month", y="Count",
                        color="department", barmode="stack")
        fig_cm.update_xaxes(categoryorder="array", categoryarray=month_label_list)
        st.plotly_chart(fig_cm, use_container_width=True)

    st.markdown("""
    <hr style='border:none; border-top:4px solid #8B0000; margin:25px 0; width:100%;'>
    """, unsafe_allow_html=True)

    # ============================================================
    # DISPLAY CHARTS — PM & CM by TOP UNITS
    # ============================================================

    # Configurable Top-N
    top_n = st.slider("Select number of Top Units", 3, 15, 10)

    # Recompute top units dynamically
    top_units_pm = df_pm["unit"].value_counts().head(top_n).index.tolist()
    top_units_cm = df_cm["unit"].value_counts().head(top_n).index.tolist()

    # -------------------------
    # PM: Group Top-N + Others
    # -------------------------
    df_pm_units = df_pm.copy()
    df_pm_units["unit_grouped"] = df_pm_units["unit"].where(
        df_pm_units["unit"].isin(top_units_pm),
        "Others"
    )

    pm_unit = (
        df_pm_units.groupby(["month", "unit_grouped"])
        .size()
        .reset_index(name="Count")
        .rename(columns={"unit_grouped": "unit"})
    )

    # -------------------------
    # CM: Group Top-N + Others
    # -------------------------
    df_cm_units = df_cm.copy()
    df_cm_units["unit_grouped"] = df_cm_units["unit"].where(
        df_cm_units["unit"].isin(top_units_cm),
        "Others"
    )

    cm_unit = (
        df_cm_units.groupby(["month", "unit_grouped"])
        .size()
        .reset_index(name="Count")
        .rename(columns={"unit_grouped": "unit"})
    )

    # Ordering: Others always last
    unit_order_pm = top_units_pm + ["Others"]
    unit_order_cm = top_units_cm + ["Others"]

    colU1, colU2 = st.columns(2)

    # -------------------------
    # PM Chart
    # -------------------------
    with colU1:
        st.markdown(f"**📊 PM Trend — Top {top_n} Units + Others**")

        fig_pm_unit = px.bar(
            pm_unit,
            x="month",
            y="Count",
            color="unit",
            barmode="stack",
            category_orders={"unit": unit_order_pm}
        )

        fig_pm_unit.update_xaxes(
            categoryorder="array",
            categoryarray=month_label_list
        )

        # Style "Others"
        fig_pm_unit.update_traces(
            selector=dict(name="Others"),
            marker_color="lightgray"
        )

        st.plotly_chart(fig_pm_unit, use_container_width=True)

    # -------------------------
    # CM Chart
    # -------------------------
    with colU2:
        st.markdown(f"**📊 CM Trend — Top {top_n} Units + Others**")

        fig_cm_unit = px.bar(
            cm_unit,
            x="month",
            y="Count",
            color="unit",
            barmode="stack",
            category_orders={"unit": unit_order_cm}
        )

        fig_cm_unit.update_xaxes(
            categoryorder="array",
            categoryarray=month_label_list
        )

        # Style "Others"
        fig_cm_unit.update_traces(
            selector=dict(name="Others"),
            marker_color="lightgray"
        )

        st.plotly_chart(fig_cm_unit, use_container_width=True)



# ============================================================
# 3) UNITS ↔ DEPARTMENTS (CM ONLY) — TIME RANGE SELECTABLE
# ============================================================
def unit_department_charts(days_back=365):
    import streamlit as st
    import plotly.express as px

    df = load_job_data(days_back)

    # CM-only
    df = df[df["job_type"].str.upper() == "CM"].copy()
    df = df[df["unit"] != "999"]  # remove placeholder
    df["Object_Type"] = df["Object_Type"].fillna("Unknown").astype(str)

    if df.empty:
        st.warning("⚠️ No CM records in this time range.")
        return

    # -------------------------
    # LEFT chart (ALL units)
    # -------------------------
    unit_dep_grouped = (
        df.groupby(["unit", "department"])
        .size()
        .reset_index(name="Count")
    )


    # -------------------------
    # RIGHT chart: Top 14 Units + Others
    # -------------------------
    top14_units = df["unit"].value_counts().head(9).index.tolist()

    df_right = df.copy()
    df_right["unit_grouped"] = df_right["unit"].where(
        df_right["unit"].isin(top14_units),
        "Others"
    )

    dep_unit_grouped = (
        df_right
        .groupby(["department", "unit_grouped"])
        .size()
        .reset_index(name="Count")
        .rename(columns={"unit_grouped": "unit"})
    )

    # Ordering
    dept_order = (
        dep_unit_grouped.groupby("department")["Count"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    unit_order = top14_units + ["Others"]


    colA, colB = st.columns(2)

    # Left chart: ALL units
    with colA:
        st.markdown("**Units per Department (CM Only – All Units)**")
        fig_unit_dep = px.bar(
            unit_dep_grouped,
            x="unit",
            y="Count",
            color="department",
            barmode="stack"
        )
        fig_unit_dep.update_xaxes(categoryorder="array", categoryarray=unit_order)
        st.plotly_chart(fig_unit_dep, use_container_width=True)

    # Right chart: TOP 14 units
    with colB:
        st.markdown("**Departments per Unit (CM Only – Top 14 Units + Others)**")

        fig_dep_unit = px.bar(
            dep_unit_grouped,
            x="department",
            y="Count",
            color="unit",
            barmode="stack",
            category_orders={
                "unit": unit_order,
                "department": dept_order
            }
        )

        # Style "Others"
        fig_dep_unit.update_traces(
            selector=dict(name="Others"),
            marker_color="lightgray"
        )

        st.plotly_chart(fig_dep_unit, use_container_width=True)


    # ============================================================
    # 🔹 CM REPORT DISTRIBUTION BY OBJECT TYPE
    # ============================================================

    st.markdown("""
    <hr style='border:none; border-top:4px solid #00493a; margin:30px 0; width:100%;'>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 CM Report Distribution by Object Type")

    # CM only
    df_cm = df[df["job_type"].str.upper() == "CM"].copy()

    # Clean object types
    df_cm = df_cm[df_cm["Object_Type"].notna()]
    df_cm["Object_Type"] = df_cm["Object_Type"].str.strip()
    df_cm = df_cm[df_cm["Object_Type"] != ""]



    colLl, colRr = st.columns(2)
    with colLl:

        # --------------------------------------------
        # Department selector (LEFT chart only)
        # --------------------------------------------
        dept_options = sorted(df_cm["department"].dropna().unique().tolist())
        dept_options = ["All"] + dept_options

        selected_dept = st.selectbox(
            "Filter CM Reports by Department",
            options=dept_options,
            index=0,
            key="cm_unit_object_type_dept"
        )

    with colRr:
        pass


    colL, colR = st.columns(2)



    # ------------------------------------------------------------
    # LEFT: Units vs CM Count (Stacked by Object Type)
    # ------------------------------------------------------------
    with colL:
        st.markdown("**CM Reports per Unit (stacked by Object Type)**")


        df_left = df_cm.copy()

        if selected_dept != "All":
            df_left = df_left[df_left["department"] == selected_dept]

        unit_type_grouped = (
            df_left
            .groupby(["unit", "Object_Type"])
            .size()
            .reset_index(name="Count")
        )

        fig_unit_type = px.bar(
            unit_type_grouped,
            x="unit",
            y="Count",
            color="Object_Type",
        )

        fig_unit_type.update_layout(
            barmode="stack",
            xaxis_title="Unit",
            yaxis_title="CM Report Count",
            legend_title="Object Type",
        )

        st.plotly_chart(fig_unit_type, use_container_width=True)

    # ------------------------------------------------------------
    # RIGHT: Departments vs CM Count (Stacked by Object Type)
    # ------------------------------------------------------------
    with colR:
        st.markdown("**CM Reports per Department (stacked by Object Type)**")


        dep_type_grouped = (
            df_cm
            .groupby(["department", "Object_Type"])
            .size()
            .reset_index(name="Count")
        )

        fig_dep_type = px.bar(
            dep_type_grouped,
            x="department",
            y="Count",
            color="Object_Type",
        )


        fig_dep_type.update_layout(
            barmode="stack",
            xaxis_title="Department",
            yaxis_title="CM Report Count",
            legend_title="Object Type",
        )

        st.plotly_chart(fig_dep_type, use_container_width=True)
