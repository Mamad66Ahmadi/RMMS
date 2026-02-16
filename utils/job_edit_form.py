import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from utils.Select_options_function import (   # ✅ import your helper functions
    get_department_options,
    get_status_options,
    get_performed_job_options,
)

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


def render_edit_job_form(username: str, job: dict):
    """Render the edit form for a single job record."""

    with st.form("edit_job_form", clear_on_submit=False):
        col_left, col_right = st.columns(2)

        # ==============================
        # LEFT COLUMN
        # ==============================
        with col_left:

            new_date = st.date_input(
                "Date",
                value=pd.to_datetime(job.get("date")).date()
            )


            # 🔹 Department dropdown
            department_options = get_department_options()
            dept_value = job.get("department", "")
            if dept_value not in department_options and dept_value:
                department_options.insert(0, dept_value)
            new_department = st.selectbox("Department", options=department_options, index=department_options.index(dept_value) if dept_value in department_options else 0)

            new_wo = st.text_input("W.O. Number", value=job.get("wo_number", ""))
            new_permit = st.text_input("Permit Number", value=job.get("permit_number", ""))

            # 🔹 Status dropdown
            status_options = get_status_options()
            status_value = str(job.get("status", "")).capitalize()
            if status_value not in status_options and status_value:
                status_options.insert(0, status_value)
            new_status = st.selectbox("Status", options=status_options, index=status_options.index(status_value) if status_value in status_options else 0)

            st.markdown("<hr style='margin:8px 0; border-top:2px solid #ccc;'>", unsafe_allow_html=True)
            # with col_chk2:
            action_default = bool(job.get("action_list", False))
            action_checked = st.checkbox("Action List", value=action_default)

        # ==============================
        # RIGHT COLUMN
        # ==============================
        with col_right:
            new_act_date = st.date_input(
                "Actual Start",
                value=pd.to_datetime(job.get("actual_start")).date()
                    if job.get("actual_start")
                    else datetime.today().date(),
                key="actual_start_edit"
            )

            # 🔹 Performed Job dropdown
            performed_options = get_performed_job_options()
            performed_value = str(job.get("performed_action", "")).capitalize()
            if performed_value not in performed_options and performed_value:
                performed_options.insert(0, performed_value)
            new_performed = st.selectbox("Performed Action", options=performed_options, index=performed_options.index(performed_value) if performed_value in performed_options else 0)

            new_employee = st.text_input("Employees", value=job.get("employee", ""))
            new_keywords = st.text_input("Keywords", value=job.get("keywords", ""))
            new_route = st.text_input("Route", value=job.get("route", ""),disabled=True)

            # 🔹 Divider line
            st.markdown("<hr style='margin:8px 0; border-top:2px solid #ccc;'>", unsafe_allow_html=True)

            # col_chk1, col_chk2 = st.columns(2)
            # with col_chk1:
            anomaly_default = bool(job.get("anomaly", False))
            anomaly_checked = st.checkbox("Anomaly", value=anomaly_default)


        # ==============================
        # DESCRIPTION BOX
        # ==============================
        desc_value = st.text_area(
            "Job Description",
            value=job.get("job_description", ""),
            height=150,
            key="desc_box",
        )




        # ==============================
        # FORM BUTTONS
        # ==============================
        st.markdown("<hr style='margin:5px 0; border-top:1.4px solid #ccc;'>", unsafe_allow_html=True)
        col_submit, col_cancel = st.columns([1, 1])

        with col_submit:
            submit_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)
        with col_cancel:
            cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)

        # Cancel logic
        if cancel_edit:
            st.session_state.edit_mode = False
            st.session_state.selected_job_for_edit = None
            st.rerun()

        # Save logic
        if submit_edit:
            try:
                page_user = username
                pc_user = os.getlogin()
                now_date = datetime.today().date().isoformat()

                # Add modifier info
                modifier_line = f"{page_user} ({pc_user}) (modifier)"
                date_line = f"{now_date} (modified)"
                old_reg_by = str(job.get("registered_by", "")).strip()
                old_reg_date = str(job.get("registered_date", "")).strip()

                if old_reg_by and not old_reg_by.endswith(" | "):
                    old_reg_by += " | "
                if old_reg_date and not old_reg_date.endswith(" | "):
                    old_reg_date += " | "

                new_registered_by = old_reg_by + modifier_line
                new_registered_date = old_reg_date + date_line

                # --- Update record ---
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        """
                            UPDATE job_reports
                            SET date=?, actual_start=?, department=?, wo_number=?, permit_number=?, 
                                status=?, performed_action=?, employee=?, keywords=?, 
                                route=?, job_description=?, 
                                anomaly=?, action_list=?, 
                                registered_by=?, registered_date=?
                            WHERE job_indx=?;
                        """,
                        (
                            new_date.isoformat(),
                            new_act_date.isoformat(), 
                            new_department.strip(),
                            new_wo.strip(),
                            new_permit.strip(),
                            new_status.strip(),
                            new_performed.strip(),
                            new_employee.strip(),
                            new_keywords.strip(),
                            new_route.strip(),
                            desc_value.strip(),
                            int(anomaly_checked),    # anomaly is TEXT, so store as "True"/"False"
                            int(action_checked),     # action_list is BOOLEAN, store 0/1
                            new_registered_by,
                            new_registered_date,
                            job["job_indx"],
                        ),
                    )
                    conn.commit()


                st.success("✅ Job record updated successfully!")
                st.session_state.edit_mode = False
                st.session_state.selected_job_for_edit = None
                st.rerun()

            except Exception as e:
                st.error(f"Error updating record: {e}")
