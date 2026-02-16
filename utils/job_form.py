# utils/job_form.py
import streamlit as st
import datetime
import sqlite3
import time
import os
import pandas as pd
from pathlib import Path
from collections import Counter
import jdatetime  # for Persian date
from utils.job_display import render_job_row
from utils.failure_modes import get_failure_modes_by_type
from utils.Select_options_function import (
    get_department_options,
    get_status_options,
    get_performed_job_options
)




# --- Database ---
DB_PATH = Path(__file__).parent.parent / "data" / "daily_jobs.db"

# --- Helper: safe DB write ---
def _write_query(sql: str, params=None, max_attempts: int = 3, delay: float = 1.5):
    db_path = DB_PATH
    params = params or []
    for attempt in range(max_attempts):
        try:
            with sqlite3.connect(db_path, check_same_thread=False, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(sql, params)
                conn.commit()
            return True
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                raise
    return False

def get_recent_related_jobs(tag: str, department: str, limit: int = 2):
    """
    Fetch up to `limit` most recent unique jobs for a tag and department,
    prioritized by status order: ongoing → on hold → completed.
    If multiple jobs share the same WO or Permit number, only the latest one is kept.
    """
    db_uri = f"file:{DB_PATH}?mode=ro"
    try:
        with sqlite3.connect(db_uri, uri=True, timeout=3) as conn:
            conn.execute("PRAGMA busy_timeout = 4000")

            # --- Fetch all possible statuses at once for efficiency
            df = pd.read_sql_query(
                """
                SELECT job_indx, date, job_description, wo_number, permit_number,
                       performed_action, employee, keywords, status, department, actual_start
                FROM job_reports
                WHERE Object_Tag = ? AND department = ? AND lower(job_type) = 'cm'
                ORDER BY date DESC, rowid DESC
                """,
                conn,
                params=[tag, department],
            )

        if df.empty:
            return []

        # --- Clean up and normalize
        df["status"] = df["status"].str.lower().fillna("")
        df["wo_number"] = df["wo_number"].fillna("").astype(str)
        df["permit_number"] = df["permit_number"].fillna("").astype(str)

        # --- Drop duplicates based on WO or Permit (keep last one by date)
        df = df.sort_values(by=["date", "job_indx"], ascending=[False, False])
        df = df.drop_duplicates(subset=["wo_number", "permit_number"], keep="first")

        # --- Custom sort order: ongoing → on hold → completed → others
        status_order = {"ongoing": 0, "on hold": 1, "completed": 2}
        df["status_order"] = df["status"].map(status_order).fillna(99)
        df = df.sort_values(by=["status_order", "date"], ascending=[True, False])

        # --- Limit the final list
        df = df.head(limit)

        return df.to_dict("records")

    except Exception as e:
        st.error(f"⚠️ Error fetching related jobs: {e}")
        return []


def search_related_jobs(tag: str, department: str, keyword: str, limit: int = 5):
    """Search up to `limit` recent jobs by keyword for a tag and department."""
    db_uri = f"file:{DB_PATH}?mode=ro"
    try:
        with sqlite3.connect(db_uri, uri=True, timeout=3) as conn:
            df = pd.read_sql_query(
                f"""
                SELECT job_indx, date, job_description, wo_number, permit_number,
                       performed_action, employee, keywords, status, department
                FROM job_reports
                WHERE Object_Tag = ? AND department = ? AND lower(job_type) = 'cm'
                  AND (
                        wo_number LIKE ? OR
                        job_description LIKE ? OR
                        performed_action LIKE ? OR
                        keywords LIKE ?
                      )
                ORDER BY date DESC, rowid DESC
                LIMIT {limit}
                """,
                conn,
                params=[
                    tag,
                    department,
                    f"%{keyword}%",
                    f"%{keyword}%",
                    f"%{keyword}%",
                    f"%{keyword}%",
                ],
            )
            return df.to_dict("records") if not df.empty else []
    except Exception as e:
        st.error(f"⚠️ Error searching related jobs: {e}")
        return []




# --- Save job to DB ---
def save_job_to_db(job_data: dict):
    sql = """
        INSERT INTO job_reports 
        (date, Object_Tag, job_description, keywords, department, wo_number,
        permit_number, status, action_list, job_type, employee, performed_action,
        route, registered_by, registered_date, anomaly, actual_start)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        job_data.get("date"),
        job_data.get("Object_Tag"),
        job_data.get("job_description"),
        job_data.get("keywords"),
        job_data.get("department"),
        job_data.get("wo_number"),
        job_data.get("permit_number"),
        job_data.get("status"),
        job_data.get("action_list", 0),
        job_data.get("job_type"),
        job_data.get("employee"),
        job_data.get("performed_action"),
        job_data.get("route"),
        job_data.get("registered_by"),
        job_data.get("registered_date"),
        job_data.get("anomaly", 0),
        job_data.get("actual_start"),  # ✅ matches the extra placeholder
    )

    try:
        _write_query(sql, params)
        return True
    except sqlite3.OperationalError as e:
        st.error(f"⚠️ Database locked or write failed:\n\n{e}")
        return False
    except Exception as e:
        st.error(f"❌ Unexpected database error:\n\n{e}")
        return False



# fetch tags function    
def get_all_object_tags():
    """Fetch all Object_Tag values from the objects table."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Object_Tag FROM objects ORDER BY Object_Tag")
            tags = [row[0] for row in cursor.fetchall()]
        return tags
    except Exception as e:
        st.error(f"⚠️ Failed to fetch tags:\n{e}")
        return []
    

@st.cache_data(ttl=600)
def get_object_info(tag: str):
    """Fetch Father Tag, Unit, Train, and Object Type from objects table."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT Father_Tag, Unit_Code, Train, Object_Type FROM objects WHERE Object_Tag = ?",
            (tag,)
        )
        row = cur.fetchone()
        conn.close()

        if row:
            return {
                "Father_Tag": row[0],
                "Unit": row[1],
                "Train": row[2],
                "Object_Type": row[3],
            }
    except Exception as e:
        st.error(f"⚠️ Error reading object info: {e}")

    return {"Father_Tag": "-", "Unit": "-", "Train": "-", "Object_Type": "-"}


#@st.cache_data(ttl=600)  # cache for 10 minutes
def get_top_keywords_for_tag(tag: str, top_n: int = 5):
    """
    Fetch the most used keywords for a given Object_Tag from job_reports.
    Returns a list of top_n keywords in lowercase.
    """
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT keywords FROM job_reports WHERE Object_Tag = ? ORDER BY job_indx DESC LIMIT 75", (tag,))
        #st.info(tag)
        rows = cur.fetchall()
        #st.info(rows)
        conn.close()

        # Flatten and normalize keywords
        all_keywords = []
        for r in rows:
            if r[0]:
                all_keywords.extend([k.strip().lower() for k in r[0].split(",") if k.strip()])

        # Count frequency
        counter = Counter(all_keywords)
        top_keywords = [k for k, _ in counter.most_common(top_n)]
        return top_keywords

    except Exception as e:
        st.warning(f"⚠️ Could not fetch keyword suggestions: {e}")
        return []

# --- Session-state initialization helper ---
def init_job_session_state():
    if "job_wizard_step" not in st.session_state:
        st.session_state.job_wizard_step = 1
    if "job_temp" not in st.session_state:
        st.session_state.job_temp = {}
    if "job_error" not in st.session_state:
        st.session_state.job_error = ""
    if "last_submitted_job" not in st.session_state:
        st.session_state.last_submitted_job = None
    if "open_job_dialog" not in st.session_state:
        st.session_state.open_job_dialog = False

# --- Dialog control ---
def open_job_dialog():
    init_job_session_state()
    st.session_state.open_job_dialog = True
    st.session_state.job_wizard_step = 1
    st.session_state.job_temp = {}
    st.session_state.job_error = ""

def close_job_dialog(clear_temp=True):
    init_job_session_state()
    st.session_state.open_job_dialog = False
    st.session_state.job_wizard_step = 1
    st.session_state.job_error = ""
    if clear_temp:
        st.session_state.job_temp = {}

# --- Initial form ---
def render_initial_job_form():
    """Ask user for date and Object Tag first, with selectbox and empty default."""
    init_job_session_state()
    submitted = False

    with st.form("initial_job_form"):
        today = datetime.date.today()
        date = st.date_input("Select Date", value=today)

        # --- Fetch tags from objects table ---
        # --- Fetch tags from objects table ---
        tags = get_all_object_tags()
        tags_with_empty = [""] + tags  # add empty option at the top

        # ✅ Get default tag from session (set by main page)
        default_tag = st.session_state.job_temp.get("Object_Tag", "")
        default_index = tags_with_empty.index(default_tag) if default_tag in tags_with_empty else 0

        if default_tag:
            object_tag = default_tag
            st.markdown(
                f"Selected Tag: <span style='color:darkred; font-weight:bold;'>{object_tag}</span>",
                unsafe_allow_html=True
            )

        else:
            object_tag = st.selectbox("Object Tag", options=tags_with_empty, index=0)



        submit_btn = st.form_submit_button("Continue")

        if submit_btn:
            if not object_tag:
                st.error("⚠️ .لطفاً تگ تجهیز را وارد کنید")
            else:
                # Save initial data in session state
                st.session_state.job_temp = {
                    "date": date.isoformat(),
                    "Object_Tag": object_tag.upper(),
                    "job_type": "CM"
                }
                st.session_state.open_job_dialog = True
                submitted = True  # mark that we submitted

    return submitted



# --- Add Job Section ---
def render_add_job_section(user_department=None, user_name=None):
    init_job_session_state()

    # Store user's department in session so job_dialog can access it
    if user_department:
        st.session_state["user_department"] = user_department
    if user_name:
        st.session_state["username"] = user_name

    # --- Always show the "Add New Job" button ---
    # --- Custom red-shadow style for the Add button ---
    st.markdown("""
        <style>
        div[data-testid="stButton"] > button.add-cm-job-btn {
            background-color: #b30000 !important;   /* dark red */
            color: white !important;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            box-shadow: 0px 0px 12px rgba(255, 0, 0, 0.6);  /* red glow */
            transition: all 0.2s ease-in-out;
        }
        div[data-testid="stButton"] > button.add-cm-job-btn:hover {
            background-color: #cc0000 !important;
            box-shadow: 0px 0px 20px rgba(255, 0, 0, 0.8);
            transform: scale(1.03);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Add button with custom class ---
    add_clicked = st.button("➕ **Add** New **CM** Job", key="add_cm_job", type="primary")
    st.markdown(
        "<script>document.querySelector('button[kind=\"primary\"]')?.classList.add('add-cm-job-btn');</script>",
        unsafe_allow_html=True
    )

    if add_clicked:
        current_tag = st.session_state.job_temp.get("Object_Tag", "")
        st.session_state.show_job_form = True
        st.session_state.job_error = ""
        st.session_state.job_wizard_step = 1
        st.session_state.open_job_dialog = False
        st.session_state.job_temp = {"Object_Tag": current_tag} if current_tag else {}


    # --- Show initial date + tag form only if button clicked ---
    if st.session_state.get("show_job_form", False):
        submitted = render_initial_job_form()
        if submitted:
            st.session_state.show_job_form = False  # hide initial form after submitting
            job_dialog()

    # --- If wizard already open (Step 1-3), show dialog ---
    elif st.session_state.open_job_dialog:
        job_dialog()

    # --- Show last submitted job ---

    if st.session_state.last_submitted_job and st.session_state.get("show_last_job", False):
        job = st.session_state.last_submitted_job
        render_job_row(job)

        import urllib.parse

        tag = job.get("Object_Tag", "")
        username = st.session_state.get("username", "")
        name = st.session_state.get("user_name", "")
        department = st.session_state.get("user_department", "")

        if tag:
            base_params = {
                "tag": tag,
                "username": username,
                "name": name,
                "department": department,
            }

            url = f"/Object_Details_page?{urllib.parse.urlencode(base_params, quote_via=urllib.parse.quote)}"

            st.markdown(
                f"""
                <div style='margin-top:1em; text-align:center;'>
                    <a href='{url}' target='_blank'
                    style='color:#1E40AF; font-weight:600; text-decoration:none; font-size:15px;'>
                    🔗 Open Object Details to view or edit this record: <b>{tag}</b>
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

        

# --- Job Wizard Dialog ---
@st.dialog("Add Job Report")
def job_dialog():
    init_job_session_state()
    step = st.session_state.job_wizard_step
    object_tag = st.session_state.job_temp.get("Object_Tag", "")
    selected_date = st.session_state.job_temp.get("date", "")

    # Styled header
    st.markdown(
        f"""
        <div style="font-size:16px; font-weight:bold;">
            Step {step} / 3 |
            <span style="color:darkred;">{object_tag}</span> | 
            <span style="color:darkgreen;">{selected_date}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # --- Step 1 ---
    if step == 1:
        with st.form("job_step1"):
            selected_date = st.session_state.job_temp.get("date")
            object_tag = st.session_state.job_temp.get("Object_Tag")
            user_department = st.session_state.get("user_department", None)
            info = get_object_info(object_tag)

            # ---- Header display ----
            try:
                greg_date = datetime.date.fromisoformat(selected_date)
                persian_date = jdatetime.date.fromgregorian(date=greg_date).strftime("%Y/%m/%d")
                weekday = greg_date.strftime("%A")
            except:
                persian_date, weekday = "-", "-"

            st.markdown(f"""
            <div style="padding:1em; border:1px solid #ccc; border-radius:10px; background-color:#f9f9fb;">
            📅 <b>Date:</b> {selected_date} | {weekday} | {persian_date}<br>
            🏷️ <b>Object Tag:</b> {object_tag}<br>
            🧩 <b>Father Tag:</b> {info['Father_Tag']} | <b>Unit:</b> {info['Unit']} | <b>Train:</b> {info['Train']}
            </div>
            """, unsafe_allow_html=True)


            # ---- SHOW ONGOING JOBS ----
            selected_record = None

            st.markdown("### 🟢 Ongoing / Recent Jobs for This Equipment")

            if user_department:
                ongoing_jobs = get_recent_related_jobs(object_tag, user_department, limit=2)

                if ongoing_jobs:
                    for i, rec in enumerate(ongoing_jobs, start=1):

                        with st.expander(
                            f"Job #{rec['job_indx']} — {rec['status'].capitalize()} — {rec['date']} — W.O.: {rec.get('wo_number','-')}"
                        ):
                            st.markdown(f"""
                            <div style="background:#f5faff;border-left:4px solid #0072B2;
                                        padding:10px 15px;border-radius:8px;font-size:13px;">
                                WO: {rec.get('wo_number','-')} | Permit: {rec.get('permit_number','-')}<br>
                                Employee(s): {rec.get('employee','-')}<br>
                                Performed Action: {rec.get('performed_action','-')}<br>
                                Description: <i>{rec.get('job_description','-')}</i><br>
                                Actual Start: <i>{rec.get('actual_start','-')}</i>
                            </div>
                            """, unsafe_allow_html=True)

                            if st.checkbox(f"Continue from this job", key=f"use_prev_{i}"):
                                selected_record = rec
                else:
                    st.info("No recent jobs found for this tag & department.")

            else:
                st.info("Department not detected — cannot search for ongoing jobs.")


            st.markdown("""
            <div style="
                font-family: 'Vazirmatn', sans-serif;
                font-size:14px;
                direction: rtl;
                text-align: right;
                margin-top:10px;
                margin-bottom:10px;
            ">
            اگر این گزارش ادامه یک گزارش قبلی است لطفا آن را از لیست بالا انتخاب کنید<br>
            <span style="font-size:12px; color:gray; direction:ltr; text-align:left;">
            If this report is a continuation of a previous (ongoing) report, please select it
            </span>
            </div>
            <hr style="margin-top:5px; margin-bottom:5px;">
            """, unsafe_allow_html=True)

            # ---- BUTTONS ----
            col1, col2 = st.columns([2, 1])
            with col1:
                next_btn = st.form_submit_button("➡️ Next")
            with col2:
                cancel_btn = st.form_submit_button("❌ Cancel")

            if cancel_btn:
                close_job_dialog()
                st.rerun()

            if next_btn:
                if selected_record:
                    # continuation job
                    st.session_state.job_temp.update({
                        "wo_number": selected_record.get("wo_number", ""),
                        "permit_number": selected_record.get("permit_number", ""),
                        "performed_action": selected_record.get("performed_action", ""),
                        "employee": selected_record.get("employee", ""),
                        "keywords": selected_record.get("keywords", ""),
                        "department": selected_record.get("department", ""),
                        "actual_start": selected_record.get("actual_start") or selected_record.get("date"),
                    })
                    st.success(f"✔ Continuing from Job #{selected_record['job_indx']}")
                else:
                    # new job
                    st.session_state.job_temp["actual_start"] = selected_date

                st.session_state.job_wizard_step = 2
                st.rerun()

    # --- Step 2 ---
    elif step == 2:
        with st.form("job_step2"):
            # --- Fetch department options from the function ---
            all_departments = get_department_options()  # use as-is
            user_department = st.session_state.get("user_department", None)

            # --- Determine default index ---
            current_department = st.session_state.job_temp.get("department", "")
            default_department = user_department if user_department in all_departments else current_department
            default_index = all_departments.index(default_department) if default_department in all_departments else 0

            # --- Department selectbox ---
            department = st.selectbox(
                "Department",
                options=all_departments,
                index=default_index,
                key="department_select"
            )

            # --- Other inputs (W.O. and Permit side by side) ---
            col_wo, col_permit = st.columns([1, 1])
            with col_wo:
                wo_number = st.text_input(
                    "W.O. Number",
                    value=st.session_state.job_temp.get("wo_number", "")
                )
            with col_permit:
                permit_number = st.text_input(
                    "Permit Number",
                    value=st.session_state.job_temp.get("permit_number", "")
                )


            # ---- Keywords ----
            st.markdown(
                '<hr style="border:none; border-top:1px solid #ccc; margin-top:0.2em; margin-bottom:0.2em;" />',
                unsafe_allow_html=True
            )

            # --- Detect object type and load failure modes ---
            object_tag = st.session_state.job_temp.get("Object_Tag", "")
            object_info = get_object_info(object_tag)
            object_type = (object_info.get("Object_Type") or "").strip()
            failure_mode_options = get_failure_modes_by_type(object_type)

            # --- 🔹 Load previous keywords if any ---
            prev_keywords = st.session_state.job_temp.get("keywords", "")
            prev_keywords_list = [kw.strip() for kw in prev_keywords.split(",") if kw.strip()] if prev_keywords else ["", "", ""]

            # ensure we always have three placeholders
            while len(prev_keywords_list) < 3:
                prev_keywords_list.append("")

            st.markdown(f"🧩 {object_type} Keywords:")
            col_kw1, col_kw2 = st.columns(2)

            # --- If failure modes exist, use dropdowns ---
            if failure_mode_options:
                with col_kw1:
                    kw1 = st.selectbox(
                        "➊ Failure Mode",
                        options=[""] + failure_mode_options,
                        index=(
                            [""] + failure_mode_options
                        ).index(prev_keywords_list[0]) if prev_keywords_list[0] in failure_mode_options else 0,
                        key="failure_mode_select_1",
                    )
                with col_kw2:
                    kw2 = st.selectbox(
                        "➋ Failure Mode",
                        options=[""] + failure_mode_options,
                        index=(
                            [""] + failure_mode_options
                        ).index(prev_keywords_list[1]) if prev_keywords_list[1] in failure_mode_options else 0,
                        key="failure_mode_select_2",
                    )

                kw3 = st.text_input(
                    "➌ Failure Mode (manual entry)",
                    value=prev_keywords_list[2],
                    key="failure_mode_manual",
                )

            else:
                # --- Otherwise: 3 manual text fields ---
                with col_kw1:
                    kw1 = st.text_input("➊ Failure Mode", value=prev_keywords_list[0])
                with col_kw2:
                    kw2 = st.text_input("➋ Failure Mode", value=prev_keywords_list[1])
                kw3 = st.text_input("➌ Failure Mode", value=prev_keywords_list[2])

            # --- Combine into comma-separated list ---
            keywords_list = [kw.strip().lower() for kw in [kw1, kw2, kw3] if kw.strip()]
            keywords = ", ".join(keywords_list)
            


            # --- Fetch suggested keywords from job history ---
            object_tag = st.session_state.job_temp.get("Object_Tag", "")
            suggested_keywords = get_top_keywords_for_tag(object_tag, top_n=5)

            # --- Display suggestions below input ---
            if suggested_keywords:
                st.markdown(
                    f"""
                    <div style='color:#555; font-size:0.9em; margin-bottom:0.5em;'>
                        Most used keywords for <b style="color:darkred;">{object_tag}</b>:<br>
                        <div style="text-align:center; color:darkgreen; font-size:0.9em; margin-top:0.3em;">
                            {' | '.join(suggested_keywords)}
                        </div>
                        <hr style="border:none; border-top:1px solid #ccc; margin-top:0.2em; margin-bottom:0.2em;" />
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style='color:#999; font-size:0.9em; margin-bottom:0.5em;'>
                        No keyword history found for <b>{object_tag}</b>.
                    </div>
                    <hr style="border:none; border-top:1px solid #ccc; margin-top:0.2em; margin-bottom:0.2em;" />
                    """,
                    unsafe_allow_html=True
                )

            # --- Checkbox below ---
            col_a, col_b = st.columns(2)
            with col_a:
                action_list = st.checkbox("Action List?", value=bool(st.session_state.job_temp.get("action_list", False)))
            with col_b:
                anomaly = st.checkbox("Anomaly?", value=bool(st.session_state.job_temp.get("anomaly", False)))


            # --- Add a visual gap before buttons ---
            st.markdown("<div style='margin-top:1.5em;'></div>", unsafe_allow_html=True)

            # --- Buttons in one line ---
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                next_btn = st.form_submit_button("➡️ Next", use_container_width=True)
            with col2:
                prev_btn = st.form_submit_button("⬅️ Previous", use_container_width=True)
            with col3:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

            # --- Handle button actions ---
            if cancel_btn:
                close_job_dialog()
                st.rerun()

            if prev_btn:
                st.session_state.job_wizard_step = 1
                st.rerun()

            if next_btn:

                # ----------------------------------------------
                # Add new failure modes ONLY when going Next
                # ----------------------------------------------

                from utils.failure_modes import append_failure_mode

                # Case A: object type already has predefined failure modes
                if failure_mode_options:
                    # Only kw3 is manual, add if typed
                    if kw3.strip():
                        append_failure_mode(object_type, kw3.strip())

                # Case B: no failure modes exist → all inputs are manual
                else:
                    for manual_kw in [kw1, kw2, kw3]:
                        if manual_kw.strip():
                            append_failure_mode(object_type, manual_kw.strip())


                # ✅ Validation before proceeding
                    # ✅ Save form data to session
                st.session_state.job_temp.update({
                    "department": department.strip(),
                    "wo_number": wo_number.strip(), # type: ignore
                    "permit_number": permit_number.strip(),  # type: ignore
                    "keywords": keywords.strip(),
                    "action_list": int(action_list),
                    "anomaly": int(anomaly), 
                })
                st.session_state.job_wizard_step = 3
                st.session_state.job_error = ""
                st.rerun()

    # --- Step 3 ---
    else:
        with st.form("job_step3"):
            st.markdown("""
            <style>
            textarea[aria-label="Job Description"] {
                direction: rtl;       /* keep Persian right-aligned */
                text-align: right;    /* align text to right */
                unicode-bidi: plaintext; /* let English remain LTR */
            }
            </style>
            """, unsafe_allow_html=True)
            
            job_description = st.text_area(
                "Job Description",
                value=st.session_state.job_temp.get("job_description", "")
            )
            #job_description = st.text_area("Job Description", value=st.session_state.job_temp.get("job_description", ""))
 
            # --- Status and Performed Action side by side ---
            col_status, col_action = st.columns(2)

            with col_status:
                status_options = [""] + get_status_options()
                status = st.selectbox(
                    "Status",
                    options=status_options,
                    index=0,
                    key="status_select"
                )

            with col_action:
                performed_action_options = [""] + get_performed_job_options()
                default_performed_action = st.session_state.job_temp.get("performed_action", "")
                default_index = (
                    performed_action_options.index(default_performed_action)
                    if default_performed_action in performed_action_options
                    else 0
                )

                performed_action = st.selectbox(
                    "Performed Job",
                    options=performed_action_options,
                    index=default_index,
                    key="performed_action_select",
                    help=("Adjust (includes: Balance, Align, Calibrate, Correct);  Check (includes: Inspect, Test);  Service (includes: Clean, Paint, Grease)"
                    )
                )


            employee_input = st.text_input(
                "Employees (comma separated)", 
                value=st.session_state.job_temp.get("employee", ""),
                placeholder="مثال: اصغر فرهادی، سیدرضا میرکریمی"
            )
            # Clean and normalize spacing
            employee = ", ".join([e.strip() for e in employee_input.split(",") if e.strip()]) # type: ignore

            route = ""
            #registered_by = st.text_input("Registered By", value=st.session_state.job_temp.get("registered_by", ""))

            # --- Add spacing before buttons ---
            st.markdown("<div style='margin-top:1.5em;'></div>", unsafe_allow_html=True)

            # --- Buttons in one line ---
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)
            with col2:
                prev_btn = st.form_submit_button("⬅️ Previous", use_container_width=True)
            with col3:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

            # --- Button actions ---
            if cancel_btn:
                close_job_dialog()
                st.rerun()

            if prev_btn:
                st.session_state.job_wizard_step = 2
                st.rerun()

            if submit_btn:
                if not job_description.strip():  # type: ignore
                    st.session_state.job_error = "⚠️ Please enter the job description."
                elif not status.strip():
                    st.session_state.job_error = "⚠️ Please select a job status before submitting."
                elif not performed_action.strip():
                    st.session_state.job_error = "⚠️ Please select the performed job before submitting."
                else:
                    page_user = st.session_state.get("username", "unknown")  # from page
                    pc_user = os.getlogin()  # local Windows username
                    registered_by = f"{page_user} ({pc_user})"
                    registered_date = datetime.date.today().isoformat()

                    st.session_state.job_temp.update({
                        "job_description": job_description.strip(),  # type: ignore
                        "keywords": st.session_state.job_temp.get("keywords", ""),
                        "employee": employee.strip(),
                        "status": status.strip(),
                        "performed_action": performed_action.strip(),
                        "route": route.strip(),
                        "registered_by": registered_by.strip(),
                        "registered_date": registered_date,
                    })

                    ok = save_job_to_db(st.session_state.job_temp)
                    if ok:
                        st.session_state.last_submitted_job = st.session_state.job_temp.copy()
                        st.success("✅ گزارش با موفقیت ذخیره شد!")
                        close_job_dialog()
                        st.rerun()

    # --- Show error if any ---
    if st.session_state.job_error:
        st.error(st.session_state.job_error)
