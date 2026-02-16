import streamlit as st
import pandas as pd
import sqlite3
import time
import urllib.parse
from pathlib import Path


# --- Shared Database Path ---
def _get_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


# --- Helper: Safe Read Query ---
def _read_query(sql: str, params=None) -> pd.DataFrame:
    db_path = _get_db_path()
    db_uri = f"file:{db_path}?mode=ro"
    for attempt in range(3):
        try:
            with sqlite3.connect(db_uri, uri=True, check_same_thread=False, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                return pd.read_sql_query(sql, conn, params=params or [])
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < 2:
                time.sleep(1.5)
            else:
                raise
    return pd.DataFrame()


# --- Main Function ---
def show_route_search(username, name, department):
    st.subheader("🔍 Search for a Route")

    # --- Prepare encoded query parameters for links ---
    query_params = {
        "username": username,
        "name": name,
        "department": department
    }
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)

    # --- Input form ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        route_code = st.text_input("Route Code (partial):").strip()
    with col2:
        job_desc = st.text_input("Job Description (partial):").strip()
    with col3:
        unit = st.text_input("Unit (e.g., 106, TRT1):").strip()
    with col4:
        tag = st.text_input("Tag (e.g., 104-K-101A):").strip()

    if st.button("🔎 Search Routes"):
        # --- Build WHERE clause ---
        where_clauses, params = [], []
        if route_code:
            where_clauses.append("PMRoute_Code LIKE ?")
            params.append(f"%{route_code}%")
        if job_desc:
            where_clauses.append("PMRoute_Desc LIKE ?")
            params.append(f"%{job_desc}%")
        if unit:
            where_clauses.append("PMRoute_Code LIKE ?")
            params.append(f"%{unit}%")
        if tag:
            where_clauses.append("Object_Tag LIKE ?")
            params.append(f"%{tag}%")

        if not where_clauses:
            st.warning("Enter at least one search criterion.")
            return

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT Route_ID, PMRoute_Code, PMRoute_Desc, Object_Tag, StandardJob_Desc
            FROM routes
            WHERE {where_sql}
            ORDER BY PMRoute_Code
            LIMIT 300
        """

        try:
            df = _read_query(query, params)
            df = df.drop_duplicates(subset=["PMRoute_Code"]).reset_index(drop=True)
        except Exception as e:
            st.error(f"Database read error: {e}")
            return

        if df.empty:
            st.info("No matching routes found.")
            return

        st.success(f"✅ Found {len(df)} matching routes (distinct PMRoute_Code)")

        # --- Display Table (Prettified + Clickable Route Code) ---
        display_df = df[["PMRoute_Code", "PMRoute_Desc", "StandardJob_Desc"]].copy()
        display_df.columns = ["Route Code", "Route Description", "Route Standard Job"]

        # Create clickable links (open route_details_page in new tab)
        def make_link(code):
            url = f"/route_details_page?{encoded_params}&route={urllib.parse.quote(str(code))}"
            return f'<a href="{url}" target="_blank" style="color:#0072E3; text-decoration:none; font-weight:600;">{code}</a>'

        display_df["Route Code"] = display_df["Route Code"].apply(make_link)

        # --- Custom CSS styling ---
        st.markdown("""
        <style>
        .pretty-table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 10px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .pretty-table th {
            background-color: #2C3E50;
            color: white;
            text-align: left;
            padding: 10px;
            font-size: 15px;
        }
        .pretty-table td {
            background-color: #f9f9f9;
            padding: 8px 10px;
            border-bottom: 1px solid #ddd;
            font-size: 14px;
        }
        .pretty-table tr:hover td {
            background-color: #f0f8ff;
        }
        .pretty-table a:hover {
            text-decoration: underline;
        }
        </style>
        """, unsafe_allow_html=True)

        # --- Render HTML table ---
        html_table = display_df.to_html(escape=False, index=False, classes="pretty-table")
        st.markdown(html_table, unsafe_allow_html=True)

        # --- Instruction text below table ---
        st.markdown("""
        <div style='margin-top: 15px; font-size: 15px; color: #444; text-align: center; font-weight: bold;'>
        Click on the Route that you want to add data.<br>
        بر روی مسیری که میخواهید داده وارد کنید کلیک کنید
        </div>
        """, unsafe_allow_html=True)
