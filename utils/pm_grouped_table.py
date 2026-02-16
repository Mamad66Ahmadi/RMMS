# utils/pm_grouped_table.py

from pathlib import Path
from datetime import date as _date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.filter_section import _read_query
import urllib.parse
import jdatetime


def gregorian_to_persian(d):
    if pd.isna(d):
        return ""
    try:
        j = jdatetime.date.fromgregorian(
            year=d.year, month=d.month, day=d.day
        )
        return j.strftime("%Y/%m/%d")
    except Exception:
        return ""

# ======================================================
# DB reader
# ======================================================
def read_pm_jobs(db_path: Path, department: str | None = None) -> pd.DataFrame:
    sql = """
    SELECT
        job_indx,
        date,
        route,
        wo_number,
        status,
        performed_action,
        department,
        Object_Tag,
        actual_start
    FROM job_reports
    WHERE UPPER(job_type) = 'PM'
    """

    # Add department filter only if it's not "All" or None
    if department and department != "All":
        sql += f" AND department = '{department}'"

    # Order by date descending and limit to 1000 rows
    sql += " ORDER BY date DESC LIMIT 1000"

    return _read_query(db_path, sql)



# ======================================================
# Cleaning
# ======================================================
def clean_pm_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["Date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["Route"] = df["route"].fillna("-")
    df["Actual_Start"] = pd.to_datetime(df["actual_start"], errors="coerce")  # NEW

    return df

# ======================================================
def make_route_link(route_code: str, query_params: dict | None = None) -> str:
    if not route_code or route_code == "-":
        return "-"

    params = (query_params or {}).copy()
    params["route"] = route_code

    encoded = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"/route_details_page?{encoded}"

    return (
        f"<a href='{url}' target='_blank' "
        f"style='color:#0072E3; text-decoration:none; font-weight:600;'>"
        f"{route_code}</a>"
    )

# ========================================
# Grouping + feature engineering
# ========================================
def group_pm_jobs(df_pm: pd.DataFrame, query_params: dict | None = None) -> pd.DataFrame:
    if df_pm.empty:
        return pd.DataFrame()

    grouped = (
        df_pm.groupby(["Date", "Route"], as_index=False)
        .agg({
            "wo_number": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
            "department": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
            "Object_Tag": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
            "performed_action": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
            "Actual_Start": "min",
        })
    )

    grouped["Object Tags"] = grouped["Object_Tag"].apply(
        lambda x: (
            f"<span title='{x}'>{len(x.split(','))} tags</span>"
            if isinstance(x, str) and x.strip()
            else "-"
        )
    )

    today = _date.today()
    grouped["Day"] = pd.to_datetime(grouped["Date"]).dt.day_name()
    grouped["Date_Display"] = grouped["Date"].apply(
        lambda d: (
            f"<span title='{gregorian_to_persian(d)}'>{d}</span>"
            if pd.notna(d)
            else "-"
        )
    )

    grouped["Actual Start_Display"] = grouped["Actual_Start"].apply(
        lambda d: (
            f"<span title='{gregorian_to_persian(d.date())}'>{d.date()}</span>"
            if pd.notna(d)
            else "-"
        )
    )

    grouped["Performed Action"] = grouped["performed_action"]
    grouped["Route ID"] = grouped["Route"].apply(
        lambda r: make_route_link(r, query_params)
    )
    grouped["PPM No."] = grouped["wo_number"]
    grouped["Department"] = grouped["department"]
    grouped["Days Ago"] = grouped["Date"].apply(
        lambda d: (today - d).days if pd.notna(d) else "-"
    )

    # ---- Column order ----
    grouped = grouped[[
        "Route ID",
        "Date_Display",
        "Day",
        "Days Ago",
        "Object Tags",
        "PPM No.",
        "Department",
        "Performed Action",
        "Actual Start_Display",
    ]]

    grouped = grouped.rename(columns={
        "Date_Display": "Date",
        "Actual Start_Display": "Actual Start",
    })

    # ---- Remove duplicates, keep latest per Route ID ----
    # Sort by Date descending to ensure the latest comes first
    grouped = grouped.sort_values("Date", ascending=False)
    grouped = grouped.drop_duplicates(subset="Route ID", keep="first")

    return grouped.reset_index(drop=True)


# ======================================================
# HTML renderer
# ======================================================
def render_grouped_pm_table(df: pd.DataFrame):
    if df.empty:
        st.info("No PM jobs found.")
        return

    html = """
    <style>
    table {
        width:100%;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
        border:1px solid #ddd;
        font-family:'Segoe UI', Tahoma;
        font-size:13px;
        border-radius:8px;
        overflow:hidden;
    }
    th {
        background:#00493a;
        color:#fff;
        padding:10px;
        font-size:14px;
        text-align:center;
    }
    td {
        padding:10px;
        text-align:center;
        border-bottom:1px solid #eee;
        background:#fff;
    }
    tr:hover td { background:#f1f1f1; }

    th:nth-child(1), td:nth-child(1) { width:18%; }
    th:nth-child(2), td:nth-child(2) { width:18%; }
    th:nth-child(3), td:nth-child(3) { width:10%; }
    th:nth-child(4), td:nth-child(4) { width:7%; }
    th:nth-child(4), td:nth-child(4) { width:10%; }  
    th:nth-child(5), td:nth-child(5) { width:10%; } 
    th:nth-child(6), td:nth-child(6) { width:10%; }
    th:nth-child(7), td:nth-child(7) { width:10%; }
    th:nth-child(8), td:nth-child(8) { width:18%; }
    th:nth-child(9), td:nth-child(9) { width:15%; }

    </style>
    """ + df.to_html(index=False, escape=False)

    height = min(800, 220 + len(df) * 38)
    components.html(html, height=height, scrolling=True)


# ======================================================
# One-call helper (optional but recommended)
# ======================================================

def show_grouped_pm_table(db_path: Path, query_params: dict | None = None):
    from utils.Select_options_function import get_department_options

    query_params = query_params or {}

    # Get department from query_params, fallback to "All"
    user_department_from_query = query_params.get("department", "All")

    # List of department options, default includes "All"
    departments = ["All"] + get_department_options()

    # Ensure department exists in options
    default_department = user_department_from_query if user_department_from_query in departments else "All"

    selected_department = st.selectbox(
        "Select Department",
        departments,
        index=departments.index(default_department)
    )

    # Fetch only the relevant department data from DB
    df_raw = read_pm_jobs(db_path, selected_department)
    df_clean = clean_pm_df(df_raw)

    # Group and render
    df_grouped = group_pm_jobs(df_clean, query_params)
    render_grouped_pm_table(df_grouped)
