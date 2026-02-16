import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import datetime
import os
from utils.job_form import save_job_to_db
import time
import streamlit.components.v1 as components
from utils.Select_options_function import (
    get_department_options,
    get_status_options,
    get_performed_job_options
)



DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


def get_last_job_info(tag: str, max_attempts: int = 3, delay: float = 1.0):
    """Safely fetch the most recent job entry for a given tag."""
    for attempt in range(max_attempts):
        try:
            db_uri = f"file:{DB_PATH}?mode=ro"
            with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT date, job_description, department, wo_number, status, job_type, performed_action
                    FROM job_reports
                    WHERE Object_Tag = ?
                    ORDER BY date DESC, rowid DESC
                    LIMIT 1
                """, (tag,))
                result = cursor.fetchone()

            if result:
                return {
                    "date": result[0],
                    "description": result[1],
                    "department": result[2],
                    "wo_number": result[3],
                    "status": result[4],
                    "job_type": result[5],
                    "performed_action": result[6],
                }

            return None

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                st.error(f"Database error for tag {tag}: {e}")
                break
        except Exception as e:
            st.error(f"Unexpected error while reading database: {e}")
            break
    return None


def add_daily_jobs_form(tags: list, username: str, name: str, department: str, route: str):
    """Display a form to add daily jobs for a route, with each tag showing last job as a table."""
    if not tags:
        st.warning("⚠️ No tags provided for this route.")
        return

    # --- Style ---
    st.markdown("""
    <style>
    .job-info-box {
        background-color: #f0f8ff;
        border: 1px solid #cce0ff;
        border-radius: 12px;
        padding: 20px 25px;
        margin-bottom: 20px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.08);
        line-height: 1.6;
    }
    textarea {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Segoe UI', 'Tahoma', 'Verdana', sans-serif;
        unicode-bidi: plaintext !important;
    }
    div[data-testid="stColumn"] {
        padding-left: -0.5rem !important;
        padding-right: 0rem !important;
        margin-left: -0.5rem !important;
        margin-right: 0rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- General Job Info ---
    col1, col2, col3,col4 = st.columns(4)
    with col1:
        job_date = st.date_input("Date", value=datetime.date.today())
        wo_number = st.text_input("PPM Number")

    with col2:
        actual_start_date = st.date_input("Actual Start",value=job_date, help="By default this will match the Job Date, but you may change it if the job actually started earlier")
        permit_number = st.text_input("Permit Number")

    with col3:
        job_type = "PM"
        # --- Status and Performed Job dropdowns (with defaults) ---
        status_options = [""] + get_status_options()  
        performed_job_options = [""] + get_performed_job_options()  

        # Set defaults
        default_status = "Completed"
        default_performed_action = "Checked"

        status = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(default_status) if default_status in status_options else 0,
        )

        performed_action = st.selectbox(
            "Performed Action",
            options=performed_job_options,
            index=performed_job_options.index(default_performed_action) if default_performed_action in performed_job_options else 0,
        )
    with col4:
        all_departments = get_department_options()
        default_index = all_departments.index(department) if department in all_departments else 0
        dept = st.selectbox("Department", options=all_departments, index=default_index)
        employee = st.text_input("Employees (comma separated)", placeholder="مثال: اصغر فرهادی، سیدرضا میرکریمی")


    st.markdown("---")

    # --- Tag-specific Inputs ---
    tag_data = {}
    for tag in tags:
        # --- Fetch last job info ---
        last_job = get_last_job_info(tag)




        # --- After table: Split layout ---
        col1, col2 = st.columns([1, 6])
        with col1:
            # Inject custom CSS for purple bold checkbox labels
            st.markdown("""
            <style>
            /* Style checkbox labels */
            div[data-testid="stCheckbox"] label p {
                color: #4B0082 !important;   /* dark purple */
                font-weight: 700 !important; /* bold text */
                font-size: 15px !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # Checkbox itself
            tag_data[tag + "_checked"] = st.checkbox(f"{tag}", key=f"chk_{tag}")

        with col2:
            tag_data[tag] = st.text_area(
                "Job description:",
                key=f"desc_{tag}",
                height=68,
                placeholder="توضیحات فعالیت انجام‌شده..."
            )

        # --- Show last job info (full-width table) ---
        col5, col6 = st.columns([1, 6])
        with col5:
            st.markdown(
            "<p style='text-align:right; font-size:14px; margin-bottom:4px;'>Last Record:</p>",
            unsafe_allow_html=True
            )
        with col6:
            if last_job:
                # Determine text color (only text, borders stay black)
                if last_job["job_type"] == "CM":
                    text_color = "#b30000"  # dark red
                else:
                    text_color = "#006400"  # dark green

                # Create DataFrame
                df = pd.DataFrame([{
                    "Date": last_job["date"],
                    "Department": last_job["department"],
                    "Type": last_job["job_type"],
                    "WO/PPM": last_job["wo_number"],
                    "Status": last_job["status"],
                    "Action": last_job["performed_action"],
                    "Description": f"<div style='direction:rtl;text-align:left;font-family:Segoe UI,Tahoma,Verdana,sans-serif;"

                                f"white-space:pre-wrap; word-wrap:break-word; max-height:200px; overflow:auto;'>"
                                f"{last_job['description'].replace(chr(10), '<br>')}</div>"
                }])

                # Black-bordered simple table
                # Black-bordered simple table with fixed column widths
                html_table = f"""
                <style>
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    table-layout: fixed;        /* ✅ Fixes column widths */
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    font-size: 13px;
                    margin-top: 5px;
                    margin-bottom: 10px;
                    border: 2px solid black;
                    border-radius: 6px;
                }}
                th, td {{
                    padding: 6px;
                    text-align: center;
                    border: 1px solid black;
                    background-color: #fff;
                    color: {text_color};
                    overflow-wrap: break-word;   /* ✅ Wraps text if too long */
                    word-wrap: break-word;
                }}
                th {{
                    background-color: #f9f9f9;
                    color: black;
                    font-weight: 600;
                }}
                td:last-child {{
                    text-align: left;
                    direction: rtl;
                }}

                /* ✅ Set fixed widths per column */
                th:nth-child(1), td:nth-child(1) {{ width: 8%; }}  /* Date */
                th:nth-child(2), td:nth-child(2) {{ width: 8%; }}  /* Department */
                th:nth-child(3), td:nth-child(3) {{ width: 8%; }}  /* Type */
                th:nth-child(4), td:nth-child(4) {{ width: 8%; }}  /* WO/PPM */
                th:nth-child(5), td:nth-child(5) {{ width: 8%; }}  /* Status */
                th:nth-child(6), td:nth-child(6) {{ width: 8%; }}  /* Action */
                th:nth-child(7), td:nth-child(7) {{ width: 52%; }}  /* Description */
                tr:hover td {{
                    background-color: #f5f5f5;
                }}
                </style>
                """ + df.to_html(index=False, escape=False)

                components.html(html_table, height=95, scrolling=False)


            else:
                pass


        st.markdown("""<hr style="border:none; border-top:2px solid darkgreen; margin:10px 0;">""",
                    unsafe_allow_html=True)
        



    pc_user = os.getlogin()
    registered_by = f"{username} ({pc_user})"

    # --- Submit Button ---
    # --- Count selected jobs ---
    checked_jobs = sum(1 for tag in tags if tag_data.get(tag + "_checked", False))

    # --- Initialize session flag ---
    if "confirm_submit" not in st.session_state:
        st.session_state.confirm_submit = False

    # --- When user clicks Submit ---
    # --- Count selected jobs ---
    checked_jobs = sum(1 for tag in tags if tag_data.get(tag + "_checked", False))

    # --- Initialize session flag ---
    if "confirm_submit" not in st.session_state:
        st.session_state.confirm_submit = False

    # --- Show confirmation dialog when user clicks Submit ---
    if st.button("Submit Jobs"):
        if checked_jobs == 0:
            st.warning("⚠️ Please select at least one job before submitting.")
        elif not status.strip():
            st.warning("⚠️ Please select a Status before submitting.")    
        elif not wo_number.strip():
            st.error("⚠️ You should fill the PPM number before submitting.")
        else:
            st.session_state.confirm_submit = True  # trigger dialog

    # --- Define dialog popup ---
    @st.dialog("⚠️ Confirm Submission")
    def confirm_submission_dialog():
        formatted_date = job_date.strftime("%d-%m-%Y")
        wo_display = wo_number.strip() if wo_number.strip() else "—"

        st.markdown(f"""
        <div style='text-align:center; font-size:16px;'>
            <p>
                {username}; You are about to submit 
                <b style='color:#b30000;'>{checked_jobs}</b> job(s).
            </p>
            <p><b>{formatted_date} </b>
                (<b style='color:darkgreen;'>PPM: {wo_display}</b>)</p>
            <p>Are you sure you want to continue?</p>
        </div>
        """, unsafe_allow_html=True)


        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("✅ Yes, submit now"):
                inserted_count = 0
                for tag in tags:
                    checkbox = tag_data.get(tag + "_checked", False)
                    desc = tag_data.get(tag, "").strip()

                    if checkbox or desc:
                        if checkbox and not desc:
                            desc_text = f"{desc}"
                        elif not checkbox and desc:
                            desc_text = f"Off - {desc}"
                        else:
                            desc_text = f"{desc}"

                        row = {
                            "date": job_date.isoformat(),
                            "Object_Tag": tag,
                            "job_description": desc_text,
                            "keywords": "",
                            "department": dept,
                            "wo_number": wo_number,
                            "permit_number": permit_number,
                            "status": status,
                            "action_list": False,
                            "job_type": job_type,
                            "employee": employee,
                            "performed_action": performed_action,
                            "route": route,
                            "registered_by": registered_by,
                            "registered_date": datetime.date.today().isoformat(),
                            "actual_start": actual_start_date.isoformat() if actual_start_date else None
                        }

                        if save_job_to_db(row):
                            inserted_count += 1

                st.success(f"✅ {inserted_count} job(s) added successfully!")
                st.session_state.confirm_submit = False
                st.rerun()

        with col_cancel:
            if st.button("❌ Cancel"):
                st.session_state.confirm_submit = False
                st.rerun()

    # --- Open dialog ---
    if st.session_state.confirm_submit:
        confirm_submission_dialog()

