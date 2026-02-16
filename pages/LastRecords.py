import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import time
from datetime import datetime
import streamlit.components.v1 as components
from utils.top_bar import display_top_bar
from utils.Select_options_function import get_department_options


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"
st.set_page_config(page_title="Route Details", layout="wide")

from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()


def qp_first(key: str, default: str = "Unknown") -> str:
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

def _read_query(sql, params=None, retries=3, delay=1.0):
    db_uri = f"file:{DB_PATH}?mode=ro"
    for _ in range(retries):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
                df = pd.read_sql_query(sql, conn, params=params if params else [], index_col=None)
                return df
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise e
    return pd.DataFrame()

def fetch_last_job(tag: str, job_type_filter: str = "All", dept_filter: str = "All", max_attempts: int = 3, delay: float = 1.0):
    for attempt in range(max_attempts):
        try:
            db_uri = f"file:{DB_PATH}?mode=ro"
            with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
                sql = """
                    SELECT date, job_description, department, wo_number, status, job_type, performed_action
                    FROM job_reports
                    WHERE Object_Tag = ?
                """
                params = [tag]
                if job_type_filter != "All":
                    sql += " AND UPPER(job_type) = ?"
                    params.append(job_type_filter.upper())
                if dept_filter != "All":
                    sql += " AND department = ?"
                    params.append(dept_filter)
                sql += " ORDER BY date DESC, rowid DESC LIMIT 1"

                cursor = conn.cursor()
                cursor.execute(sql, tuple(params))
                row = cursor.fetchone()
                if row:
                    return {
                        "date": row[0],
                        "description": row[1],
                        "department": row[2],
                        "wo_number": row[3],
                        "status": row[4],
                        "job_type": row[5],
                        "performed_action": row[6],
                    }
                return None
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                st.error(f"DB error for tag {tag}: {e}")
                break
        except Exception as e:
            st.error(f"Unexpected error for tag {tag}: {e}")
            break
    return None

def style_job_type_html(val):
    if val is None:
        return ""
    v = str(val).strip().upper()
    if v == "PM":
        return f"<span style='color:#006400; font-weight:600;'>{val}</span>"
    elif v == "CM":
        return f"<span style='color:#8B0000; font-weight:600;'>{val}</span>"
    return val


def highlight_latest_date(date_str, date_dt, latest_date):
    if pd.isna(date_dt):
        return date_str
    if date_dt == latest_date:
        return f"<span class='latest-date'>{date_str}</span>"
    return date_str

def style_wo_html(val):
    if pd.isna(val) or val == "":
        return ""
    try:
        val = int(val)
        return f"<span class='wo-number'>{val:06d}</span>"
    except Exception:
        return str(val)


def main():
    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")
    display_top_bar(name, department)

    raw_val = st.query_params.get("route", None)


    if isinstance(raw_val, list):
        route_code = raw_val[0].strip().upper()
    elif isinstance(raw_val, str):
        route_code = raw_val.strip().upper()
    else:
        st.error("❌ No route specified in URL.")
        return

    st.markdown(f"""
        <div style="
            background:#fff;color:#003366;padding:10px 18px;border-radius:10px;
            font-size:20px;font-weight:700;border:1.5px solid #0066CC;
            box-shadow:0 2px 6px rgba(0,0,0,0.1);margin-bottom:10px;">
            🛠️ Route Details — <span style="background:#e6f0ff;padding:3px 8px;
            border-radius:6px;font-weight:600;color:#003366;">{route_code}</span>
        </div>
    """, unsafe_allow_html=True)

    tags_df = _read_query("SELECT Object_Tag FROM routes WHERE PMRoute_Code = ?", [route_code])

    if tags_df.empty:
        st.info(f"No tags found for route '{route_code}'.")
        return
    

    tags = tags_df["Object_Tag"].dropna().tolist()

    # =====================================================
    # 🧭 Filters
    # =====================================================
    col1, col2 = st.columns(2)
    with col1:
        dept_options = ["All"] + get_department_options()
        selected_dept = st.selectbox("Department", dept_options, index=0)
    with col2:
        job_type_options = ["All", "PM", "CM"]
        selected_job_type = st.selectbox("Job Type", job_type_options, index=0)

    # =====================================================
    # 🧮 Query Data
    # =====================================================
    records = []
    for tag in tags:
        last_job = fetch_last_job(tag, job_type_filter=selected_job_type, dept_filter=selected_dept)
        if last_job:
            records.append({
                "Date": last_job["date"],
                "Tag": tag,
                "Type": last_job["job_type"],
                "WO No": last_job.get("wo_number", ""),
                "Department": last_job["department"],
                "Description": str(last_job["description"]).replace("\n", "<br>")
            })
        else:
            records.append({"Date": "", "Tag": tag, "Type": "", "Department": "", "Description": "", "WO No": ""})

    df = pd.DataFrame(records)
    df["WO No"] = df["WO No"].apply(style_wo_html)

    df["Type"] = df["Type"].apply(style_job_type_html)


    # --- Parse dates safely ---
    df["_Date_dt"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

    latest_date = df["_Date_dt"].max()


    df["Date"] = [
        highlight_latest_date(d, dt, latest_date)
        for d, dt in zip(df["Date"], df["_Date_dt"])
    ]



    df.drop(columns=["_Date_dt"], inplace=True)

    # =====================================================
    # 🖨️ Print Mode Toggle
    # =====================================================
    st.markdown("<hr style='border:0;height:1px;background-color:green;margin:4px 0;'>", unsafe_allow_html=True)
    print_mode = st.session_state.get("print_mode", False)

    colA, colB = st.columns([6, 1])
    with colB:
        if not print_mode:
            if st.button("🖨️ Print Table", use_container_width=True):
                st.session_state["print_mode"] = True
                st.rerun()
        else:
            if st.button("↩️ Exit Print Mode", use_container_width=True):
                st.session_state["print_mode"] = False
                st.rerun()

    # =====================================================
    # 📄 Normal View or Print View
    # =====================================================
    today_str = datetime.today().strftime("%d/%m/%Y")


    if not print_mode:


        # --- Normal Mode ---
        components.html(
            """
            <style>
            table {
                width:100%;
                table-layout: fixed;
                border-collapse: separate;
                border-spacing:0;
                border:1px solid #ddd;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size:12px;
                border-radius:8px;
                overflow:hidden;
            }
            th {
                background-color:#adc35c;
                color:#333;
                font-weight:650;
                text-align:center !important;
                padding:10px 8px;
                border-bottom:1px solid #ddd;
                font-size:13px;
                line-height:1.4;
            }
            td {
                padding:10px 8px;
                text-align:center;
                border-bottom:1px solid #eee;
                vertical-align:middle;
                background-color:#fff;
                font-size:12px;
                line-height:1.5;
            }
            .latest-date {
                color: #1b5e20;
                font-weight: 700;
                background-color: #e8f5e9;
                padding: 2px 6px;
                border-radius: 6px;
            }

            tr:hover td { background-color:#fff; }
            th:nth-child(1), td:nth-child(1) { width:7%; }   /* Date */
            th:nth-child(2), td:nth-child(2) { width:8%; }   /* Tag */
            th:nth-child(3), td:nth-child(3) { width:5%; }   /* Type */
            th:nth-child(4), td:nth-child(4) { width:5%; }   /* ppm */
            th:nth-child(5), td:nth-child(5) { width:8%; }   /* Department */
            th:nth-child(6), td:nth-child(6) {
                width:65%;
                text-align:left !important;
                direction: rtl;
                word-wrap:break-word;
                white-space:normal;
            }
            th, td { border-right:1px solid #f0f0f0; }
            th:last-child, td:last-child { border-right:none; }
            </style>
            """ + df.to_html(index=False, escape=False),
            height=900,
            scrolling=True
        )
    else:


        html_code = f"""
        <script>
            window.onload = function() {{ window.print(); }}
        </script>
        <style>
        table {{
            width:100%;
            table-layout: fixed;
            border-collapse: separate;
            border-spacing:0;
            border:1px solid #ddd;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size:12px;
            border-radius:8px;
            overflow:hidden;
        }}
        th {{
            background-color:#adc35c40;
            color:#333;
            font-weight:650;
            text-align:center !important;
            padding:10px 8px;
            border-bottom:1px solid #ddd;
            font-size:13px;
            line-height:1.4;
        }}
        td {{
            padding:10px 8px;
            text-align:center;
            border-bottom:1px solid #eee;
            vertical-align:middle;
            background-color:#fff;
            font-size:12px;
            line-height:1.5;
        }}
        tr:hover td {{ background-color:#fff; }}

        th:nth-child(1), td:nth-child(1) {{ width:8%; }}
        th:nth-child(2), td:nth-child(2) {{ width:8%; }}
        th:nth-child(3), td:nth-child(3) {{ width:5%; }}
        th:nth-child(4), td:nth-child(4) {{ width:5%; }}   /* ppm */

        th:nth-child(5), td:nth-child(5) {{ width:8%; }}
        th:nth-child(6), td:nth-child(6) {{
            width:65%;
            text-align:left !important;
            direction: rtl;
            word-wrap:break-word;
            white-space:normal;
        }}
        th, td {{ border-right:1px solid #f0f0f0; }}
        th:last-child, td:last-child {{ border-right:none; }}
        @page {{ size:A4 landscape; margin:10mm; }}
        @media print {{
            html, body {{
                width:297mm;
                height:210mm;
                -webkit-print-color-adjust:exact !important;
                print-color-adjust:exact !important;
            }}
            .stApp header, .stApp footer, .stSidebar, [data-testid="stToolbar"] {{
                display:none !important;
            }}
        }}
        </style>
        <div class="route-header" style="
            text-align:center;
            font-size:16px;
            font-weight:650;
            color:#003366;
            margin-bottom:10px;
        ">
            Route Report — 
            <span style="color:#2e7d32;">{route_code}</span>
            &nbsp;—&nbsp;
            <span style="font-size:14px; color:#444;">{today_str}</span>
        </div>
        """ + df.to_html(index=False, escape=False)

        components.html(html_code, height=900, scrolling=True)



if __name__ == "__main__":
    main()
