import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import datetime
import os
from utils.job_form import save_job_to_db
import time
from utils.Select_options_function import (
    get_department_options,
    get_status_options,
    get_performed_job_options
)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

# ======================================================================================
# 🔹 Fetch jobs for a given PPM number for only the tags in this route
# ======================================================================================
def get_ppm_jobs_for_route(ppm_number: str, tags: list, max_attempts=3, delay=1.0):
    if not ppm_number or not tags:
        return {}, {}

    placeholders = ",".join(["?"] * len(tags))
    # params: wo_number + tags + job_type
    params = [ppm_number] + tags + ["PM"]

    for _ in range(max_attempts):
        try:
            db_uri = f"file:{DB_PATH}?mode=ro"
            with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
                query = f"""
                    SELECT job_indx, date, Object_Tag, job_description, department,
                           wo_number, permit_number, status, job_type, employee,
                           performed_action, route, registered_by, registered_date
                    FROM job_reports
                    WHERE wo_number = ?
                      AND Object_Tag IN ({placeholders})
                      AND job_type = ?
                    ORDER BY date DESC, rowid DESC
                """
                df = pd.read_sql_query(query, conn, params=params)  # type: ignore[arg-type]


            if df.empty:
                return {}, {}

            jobs_by_tag = {}
            for _, row in df.iterrows():
                tag = row["Object_Tag"]
                if tag not in jobs_by_tag:
                    jobs_by_tag[tag] = row.to_dict()

            first = next(iter(jobs_by_tag.values()))
            global_info = {
                "date": first["date"],
                "department": first["department"],
                "wo_number": first["wo_number"],
                "permit_number": first["permit_number"],
                "status": first["status"],
                "job_type": first["job_type"],
                "employee": first["employee"],
                "performed_action": first["performed_action"],
                "route": first["route"],
                "registered_by": first["registered_by"],
                "registered_date": first["registered_date"],
            }

            return jobs_by_tag, global_info

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
                continue
            st.error(f"Database error: {e}")
            return {}, {}
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return {}, {}

    return {}, {}


# ======================================================================================
# 🔹 Update job in DB
# ======================================================================================
def update_job_in_db(job_indx, row, max_attempts=3, delay=1.5):
    for attempt in range(max_attempts):
        try:
            with sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("""
                    UPDATE job_reports
                    SET date=?, actual_start=?, Object_Tag=?, job_description=?, keywords=?, department=?,
                    wo_number=?, permit_number=?, status=?, action_list=?, job_type=?,
                    employee=?, performed_action=?, route=?, registered_by=?, registered_date=?
                    WHERE job_indx=?
                """, (
                    row["date"], row["actual_start"], row["Object_Tag"], row["job_description"], row["keywords"],
                    row["department"], row["wo_number"], row["permit_number"], row["status"],
                    int(bool(row["action_list"])), row["job_type"], row["employee"],
                    row["performed_action"], row["route"], row["registered_by"],
                    row["registered_date"], job_indx
                ))
                conn.commit()
            return True

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_attempts - 1:
                time.sleep(delay)
                continue
            st.error(f"Database error updating job {job_indx}: {e}")
            return False
        except Exception as e:
            st.error(f"Unexpected error updating job {job_indx}: {e}")
            return False

    return False

def delete_job_by_indx(job_indx: int):
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM job_reports WHERE job_indx = ?", (job_indx,))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ Error deleting job {job_indx}: {e}")
        return False

# ======================================================================================
# 🔹 MAIN EDIT FORM — EXACTLY LIKE ADD FORM (Plus PPM Search)
# ======================================================================================
def edit_daily_jobs_form(tags: list, username: str, name: str, department: str, route: str):

    # ---------------------------------------------------
    # STYLE (identical to add form)
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # STATE
    # ---------------------------------------------------
    if "edit_ppm_data" not in st.session_state:
        st.session_state.edit_ppm_data = None
    if "confirm_edit_ppm" not in st.session_state:
        st.session_state.confirm_edit_ppm = False

    # ---------------------------------------------------
    # 🔍 SEARCH PPM (SECTION 1)
    # ---------------------------------------------------
    col_s0, col_s1, col_s2 = st.columns([5, 2, 5])
    with col_s0:
        pass
    with col_s1:
        ppm_input = st.text_input("**PPM Number to edit:**", key="edit_ppm_search")
        load_clicked = st.button("🔍 Load PPM")
    with col_s2:
        pass
        
    

    

    if load_clicked:
        ppm_str = ppm_input.strip()
        if not ppm_str:
            st.warning("⚠️ Enter a PPM number.")
            return

        jobs_by_tag, global_info = get_ppm_jobs_for_route(ppm_str, tags)

        if not jobs_by_tag:
            st.warning("⚠️ No PPM records found in this route.")
            st.session_state.edit_ppm_data = None
            return

        st.success(f"✅ Loaded {len(jobs_by_tag)} PPM records.")
        st.session_state.edit_ppm_data = {
            "ppm": ppm_str,
            "jobs_by_tag": jobs_by_tag,
            "global": global_info,
        }

    data = st.session_state.edit_ppm_data
    if not data:
        return  # don't show form yet

    jobs_by_tag = data["jobs_by_tag"]
    global_info = data["global"]


    # Determine if editing is allowed (7-day rule)
    edit_allowed = False


    from utils.auth import get_user_info   # if not already imported

    user_info = get_user_info(username) or {}
    is_admin = bool(user_info.get("is_admin", 0))
    current_user = user_info.get("username", "").lower()

    registered_by_raw = (global_info.get("registered_by") or "").strip()
    registered_date_raw = (global_info.get("registered_date") or "").strip()

    # Extract the first registered_by (before " | ")
    if " | " in registered_by_raw:
        first_registered_by = registered_by_raw.split(" | ")[0].strip()
    else:
        first_registered_by = registered_by_raw

    # Extract the first registered_date (before " | ")
    if " | " in registered_date_raw:
        first_registered_date = registered_date_raw.split(" | ")[0].strip()
    else:
        first_registered_date = registered_date_raw

    within_7_days = False
    try:
        if first_registered_date:
            reg_date = datetime.datetime.strptime(
                first_registered_date.split()[0], "%Y-%m-%d"
            ).date()
            within_7_days = (datetime.date.today() - reg_date).days <= 7
    except Exception:
        pass

    same_user = current_user in first_registered_by.lower()

    edit_enabled = is_admin or (same_user and within_7_days)

    # ---------------------------------------------------
    # SECTION 2 — GENERAL JOB INFO (IDENTICAL TO ADD FORM)
    # ---------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # --- Job Date ---
        default_date = datetime.date.today()
        if global_info.get("date"):
            try:
                default_date = datetime.date.fromisoformat(global_info["date"])
            except:
                pass

        job_date = st.date_input(
            "Date",
            value=default_date,
            key="edit_date"
        )

        wo_number = st.text_input(
            "PPM Number",
            value=data.get("ppm", ""),
            key="edit_wo_number"
        )

    with col2:
        # --- Actual Start (fixed) ---
        default_actual_start = default_date  # safe fallback

        if global_info.get("actual_start"):
            try:
                default_actual_start = datetime.date.fromisoformat(global_info["actual_start"])
            except:
                pass

        actual_start_date = st.date_input(
            "Actual Start",
            value=default_actual_start,
            help="Defaults to the Job Date, but you can change it if the job started earlier or later. "
                "به صورت پیش‌فرض برابر با تاریخ کار است، اما در صورت نیاز می‌توانید آن را تغییر دهید.",
            key="edit_actual_start"
        )

        permit_number = st.text_input(
            "Permit Number",
            value=global_info.get("permit_number") or "",
            key="edit_permit"
        )

    with col3:
        # --- Status & Performed Action ---
        status_options = [""] + get_status_options()
        performed_options = [""] + get_performed_job_options()

        default_status = global_info.get("status") or "Completed"
        default_perf = global_info.get("performed_action") or "Checked"

        status = st.selectbox(
            "Status",
            status_options,
            index=status_options.index(default_status) if default_status in status_options else 0,
            key="edit_status"
        )

        performed_action = st.selectbox(
            "Performed Action",
            performed_options,
            index=performed_options.index(default_perf) if default_perf in performed_options else 0,
            key="edit_perf"
        )

    with col4:
        # --- Department ---
        all_depts = get_department_options()
        dep_val = global_info.get("department") or department
        idx = all_depts.index(dep_val) if dep_val in all_depts else 0

        dept = st.selectbox("Department", all_depts, index=idx, key="edit_dept")

        # --- Employee(s) ---
        employee = st.text_input(
            "Employees (comma separated)",
            value=global_info.get("employee") or "",
            key="edit_employee"
        )

    st.markdown("---")

    # ---------------------------------------------------
    # SECTION 3 — TAG INPUTS (IDENTICAL LAYOUT TO ADD FORM)
    # ---------------------------------------------------
    edit_tag_data = {}

    # checkbox color identical
    st.markdown("""
    <style>
    div[data-testid="stCheckbox"] label p {
        color: #4B0082 !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    for tag in tags:

        existing = jobs_by_tag.get(tag)
        existing_desc = existing["job_description"] if existing else ""

        # same layout as add form
        col1_tag, col2_tag = st.columns([1, 6])

        with col1_tag:
            edit_tag_data[tag + "_checked"] = st.checkbox(
                f"{tag}",
                value=bool(existing),
                key=f"edit_chk_{tag}"
            )

        with col2_tag:
            edit_tag_data[tag] = st.text_area(
                "Job description:",
                value=existing_desc,
                key=f"edit_desc_{tag}",
                height=68,
                placeholder="توضیحات فعالیت انجام‌شده..."
            )

        # ---- Last record table (FULL MATCH TO ADD FORM) ----

        st.markdown("<hr style='border:none; border-top:2px solid darkgreen;'>",
                    unsafe_allow_html=True)

    # ---------------------------------------------------
    # SECTION 4 — SUBMIT & CONFIRMATION (IDENTICAL TO ADD)
    # ---------------------------------------------------
    pc_user = os.getlogin()
    registered_by = f"{username} ({pc_user})"

    checked_count = sum(
        1 for tag in tags if edit_tag_data.get(tag + "_checked", False)
    )

    # If editing allowed → show real button
    # ---- PERMISSION-BASED EDIT ACCESS ----
    if not edit_enabled:
        st.markdown("""
        <div style='color:#880000; background:#ffeaea; padding:12px;
                    border-radius:10px; border:2px solid #cc0000;
                    text-align:right; direction:rtl; font-weight:bold;'>
            ⛔ شما اجازه ویرایش این گزارش را ندارید.<br>
            تنها یک هفته بعد از وارد یک ریپورت فرصت دارید آن را حذف یا ویرایش کنید<br>
            بعد از این بازه زمانی، این کار تنها توسط ادمین امکان‌پذیر است.
        </div>
        """, unsafe_allow_html=True)

    else:
        if st.button("💾 Save Edited Jobs"):
            st.session_state.confirm_edit_ppm = True



    @st.dialog("⚠️ Confirm Editing")
    def edit_confirm_dialog():
        formatted_date = job_date.strftime("%d-%m-%Y")
        wo_display = wo_number or "—"

        st.markdown(f"""
            <div style='text-align:center; font-size:16px;'>
                <p>You are about to edit 
                    <b style='color:#b30000;'>{checked_count}</b> job(s).</p>
                <p><b>{formatted_date}</b> (PPM: <b>{wo_display}</b>)</p>
                <p>Are you sure?</p>
            </div>
        """, unsafe_allow_html=True)

        col_ok, col_cancel = st.columns(2)

        with col_ok:
            if st.button("✅ Yes, save changes"):
                updated = 0
                inserted = 0
                deleted = 0

                for tag in tags:
                    checked = edit_tag_data.get(tag + "_checked", False)
                    desc = (edit_tag_data.get(tag, "") or "").strip()

                    existing = jobs_by_tag.get(tag)

                    # -------------------------
                    # CASE 1: Existing record + now unchecked → DELETE
                    # -------------------------
                    if existing and not checked:
                        if delete_job_by_indx(existing["job_indx"]):
                            deleted += 1
                        continue  # Skip to next tag

                    # -------------------------
                    # CASE 2: Neither checked nor description → skip
                    # -------------------------
                    if not (checked or desc):
                        continue

                    # -------------------------
                    # CASE 3: Build description text
                    # -------------------------
                    if checked and not desc:
                        desc_text = desc
                    elif not checked and desc:
                        desc_text = f"Off - {desc}"
                    else:
                        desc_text = desc

                    # -------------------------
                    # Shared row for insert OR update
                    # -------------------------
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
                        "job_type": "PM",
                        "employee": employee,
                        "performed_action": performed_action,
                        "route": route,
                        "registered_by": registered_by,
                        "registered_date": datetime.date.today().isoformat(),
                        "actual_start": actual_start_date.isoformat(),

                    }

                    # -------------------------
                    # CASE 4: Existing + checked → UPDATE
                    # -------------------------
                    if existing:
                        if update_job_in_db(existing["job_indx"], row):
                            updated += 1

                    # -------------------------
                    # CASE 5: New + checked → INSERT
                    # -------------------------
                    else:
                        if save_job_to_db(row):
                            inserted += 1


                st.success(
                    f"✅ Edit complete — Updated: {updated}, Added: {inserted}, Deleted: {deleted}"
                )

                st.session_state.confirm_edit_ppm = False
                st.rerun()

        with col_cancel:
            if st.button("❌ Cancel"):
                st.session_state.confirm_edit_ppm = False
                st.rerun()


    if edit_enabled and st.session_state.confirm_edit_ppm:
        edit_confirm_dialog()
