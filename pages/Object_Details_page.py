import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import time
from streamlit.components.v1 import html
from utils.top_bar import display_top_bar
from utils.tag_stats import get_job_counts, render_job_stats_section
from utils.job_display import render_job_row
from utils.job_form import render_add_job_section, init_job_session_state
from utils.auth import get_user_info
from utils.Select_options_function import get_department_options
from utils.job_table_display import render_job_table








# --- Database path ---
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

st.set_page_config(page_title="Object Details", layout="wide")

from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()

# --- Helper: Safe DB read ---
def _read_query(sql, params=None, retries=3, delay=1.0):
    db_uri = f"file:{DB_PATH}?mode=ro"
    for _ in range(retries):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
                df = pd.read_sql_query(sql, conn, params=params or [], index_col=None)
                return df
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise e
    return pd.DataFrame()




def get_object_info(tag: str):
    """Fetch full specification of an object from 'objects' table."""
    if not tag:
        return None
    try:
        db_uri = f"file:{DB_PATH}?mode=ro"
        with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Object_Desc, Criticality_Desc, Category_Desc, Object_Note,
                       MIHLevel_Desc, Unit_Code, Object_Type, Train,
                       Father_Tag, Long_Tag, Registered, Modified
                FROM objects
                WHERE Object_Tag = ?
                LIMIT 1
            """, (tag,))
            row = cursor.fetchone()
            if row:
                keys = [
                    "Description", "Criticality", "Category", "Note",
                    "MIH Level", "Unit", "Type", "Train",
                    "Father Tag", "Long Tag", "Registered", "Modified"
                ]
                return dict(zip(keys, row))
    except Exception as e:
        st.error(f"Error fetching object info: {e}")
    return None

# --- Fetch all Object_Tags from database for selectbox ---
def get_all_object_tags():
    """Return a sorted list of all Object_Tag values from the objects table."""
    try:
        db_uri = f"file:{DB_PATH}?mode=ro"
        with sqlite3.connect(db_uri, uri=True, timeout=2) as conn:
            df = pd.read_sql_query("SELECT DISTINCT Object_Tag FROM objects ORDER BY Object_Tag ASC", conn)
            return df["Object_Tag"].dropna().astype(str).tolist()
    except Exception as e:
        st.error(f"Error loading tags: {e}")
        return []


# -------------------------------
# Maintenance department logic
# -------------------------------
MAINT_DEPTS = [
    "CBM",
    "Electrical",
    "Fix",
    "Inspection",
    "Instrument",
    "Rotary",
    "Service S",
    "HVAC"
]


init_job_session_state()
# --- Main page ----------------------------------------------------------------------------------------------------------
def main():
    # --- Read user info from query params ---
    username = st.query_params.get("username", "Unknown")
    name = st.query_params.get("name", "")
    department = st.query_params.get("department", "")

    # --- Optional tag passed from previous page ---
    tag_from_link = st.query_params.get("tag", "").strip().upper()

    display_top_bar(name, department)

    # search bar for tag
    all_tags = get_all_object_tags()

    # --- Determine default tag from URL (if valid) ---
    default_tag = tag_from_link if tag_from_link in all_tags else ""

    # --- Add an empty option at the top ---
    tag_options = [""] + all_tags

    # --- Selectbox for Object Tag ---
    tag_input = st.selectbox(
        "Select Object Tag:",
        options=tag_options,
        index=tag_options.index(default_tag) if default_tag in tag_options else 0,
        format_func=lambda x: "" if x == "" else x,
    )

    # --- Determine active tag ---
    active_tag = tag_input.strip().upper() if tag_input else ""
    # - -- Dynamically update browser tab title ---
    if active_tag:
        html(
            f"""
            <script>
            window.parent.document.title = "{active_tag}";
            </script>
            """,
            height=0,
        )

    # --- Retrieve object info if tag selected ---
    obj_info = get_object_info(active_tag)

    # --- Display 3-column layout ---
    col1, col2, col3 = st.columns([1, 1, 1])

    father_tag = obj_info.get("Father Tag") if obj_info else None
    unit_tag = obj_info.get("Unit") if obj_info else None
    train_tag = obj_info.get("Train") if obj_info else None

    # Adjust father tag display if father == unit
    if father_tag and unit_tag and father_tag == unit_tag:
        father_display = active_tag  # use the object tag itself
    else:
        father_display = father_tag or "-"

    with col1:
        st.markdown(f"""
            <div style="
                background:#fff;
                color:#003366;
                padding:12px 18px;
                border-radius:10px;
                font-size:20px;
                font-weight:bold;
                border:2px solid #173F5F;
                box-shadow:0 3px 10px rgba(0,0,0,0.10);
                margin-bottom:15px;
                text-align:center;
            ">
                Object Tag:<br>
                <span style='color:#800000; font-weight:700;'>{active_tag or '-'}</span>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        box_style = """
            background:#fff;
            color:#003366;
            padding:12px 18px;
            border-radius:10px;
            font-size:20px;
            font-weight:bold;
            border:2px solid #20639B;
            box-shadow:0 3px 10px rgba(0,0,0,0.10);
            margin-bottom:15px;
            text-align:center;
        """

        if father_display and father_display != "-":
            father_url = (
                f"/father_page?"
                f"username={username}&name={name}&department={department}&father_tag={father_display}&tag={active_tag}"
            )
            st.markdown(f"""
                <div style="{box_style}">
                    Father Tag:<br>
                    <a href="{father_url}" target="_self" style="
                        color:#005500;
                        font-weight:700;
                        text-decoration:none;
                    ">
                        {father_display}
                    </a>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="{box_style}">
                    Father Tag:<br>
                    <span style='color:#999; font-weight:700;'>-</span>
                </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div style="
                background:#fff;
                color:#003366;
                padding:12px 18px;
                border-radius:10px;
                font-size:20px;
                font-weight:bold;
                border:2px solid #3CAEA3;
                box-shadow:0 3px 10px rgba(0,0,0,0.10);
                margin-bottom:15px;
                text-align:center;
            ">
                Unit & Train:<br>
                <span style='color:#000066; font-weight:700;'>{unit_tag or '-'} – {train_tag or '-'}</span>
            </div>
        """, unsafe_allow_html=True)



    if not tag_input:
        st.info("Please enter an Object Tag to view its details.")
        return
    
    # --- Job counts for tag, father, and unit-train ---
    if obj_info:
        stats = get_job_counts(
            tag=active_tag,
            father_tag=obj_info.get("Father Tag"),
            long_tag=obj_info.get("Long Tag"),
            unit=obj_info.get("Unit"),
            train=obj_info.get("Train")
        )

        render_job_stats_section(active_tag, obj_info, stats)


    # --- Show Object Specifications in an Expander ---
    user_info = get_user_info(username)
    is_admin = bool(user_info and user_info.get("is_admin", 0))

    from utils.object_sections_info_expander import render_object_info_section, render_route_section
    from utils.tag_active_jobs_info import render_active_jobs_info_line


    if obj_info is not None:
        render_object_info_section(active_tag, obj_info, username, is_admin)
    else:
        st.info("⚠️ Object information not found in database.")


    # --- Show Note in a separate markdown box if it exists ---
    note_text = obj_info.get("Note", "")

    if note_text and str(note_text).strip() not in ["", "None", "null"]:
        st.markdown(
            f"""
            <div style="
                background-color:#fff8e1;
                border-left:5px solid #ffb300;
                padding:12px 15px;
                margin:10px 0 20px 0;
                border-radius:6px;
                color:#5a4500;
                font-size:14px;
            ">
                <b>📝 Additional Notes:</b><br>
                {note_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_active_jobs_info_line(active_tag)


    # --- Routes info section ---
    render_route_section(active_tag, username=username, name=name, department=department)


    st.markdown("""<hr style="border:none; border-top:2px solid darkgreen; margin:10px 0;">""",
                unsafe_allow_html=True)
    



    #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
    # --- Query DB for the selected tag ---
    query = """
        SELECT job_indx, date, department, wo_number, status, actual_start, job_type,
            performed_action, job_description, keywords, registered_by, route,
            anomaly, action_list
        FROM job_reports
        WHERE Object_Tag = ?
        ORDER BY date DESC, rowid DESC
    """


    df = _read_query(query, [active_tag])


    # --- Prepare and clean data ---
    df.rename(columns={
        "job_indx": "Index",
        "date": "Date",
        "department": "Department",
        "wo_number": "WO/PPM",
        "status": "Status",
        "actual_start": "Actual Start",
        "job_type": "Type",
        "performed_action": "Performed Job",
        "job_description": "Description",
        "keywords": "Keywords",
        "registered_by": "Registered By",
        "route": "Route"
    }, inplace=True)


    # --- Convert date column ---
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date", ascending=False).reset_index(drop=True)

    # --- Calculate elapsed days BEFORE filtering ---
    df["Elapsed days"] = df["Date"].diff(-1).dt.days
    df["Elapsed days"] = (
        df["Elapsed days"].abs()
        .astype("Int64")
        .fillna(pd.NA)
        .apply(lambda x: int(x) if pd.notna(x) else "-")
    )

    # --- Default: Show only last 15 records (no filters applied yet) ---
    #default_df = df.head(15).copy()


    # ================================
    # 🔹 FILTER SECTION
    # ================================
    with st.expander("🔍 Filter Job Records", expanded=False):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            date_from = st.date_input("From Date", value=None)
        with col2:
            date_to = st.date_input("To Date", value=None)
        with col3:
            job_type = st.selectbox("Job Type", options=["All", "PM", "CM"], index=0)

        # --- Department options ---
        department_options = get_department_options()



        department_options = get_department_options()
        if department and department not in department_options:
            department_options.append(department)

        col4, col5, col6 = st.columns([1, 1, 3])

        with col4:
            wo_filter = st.text_input("WO/PPM Filter (contains)", "")

        with col5:
            department_filter = st.selectbox(
                "Department",
                options=["All"] + department_options,
                index=(["All"] + department_options).index(department)
                if department in department_options else 0
            )
        with col6:
            keyword_filter = st.text_input("Keyword or Description Contains", "")


        apply_filter = st.button("Apply Filters")


    # --- Apply filters ---
    filtered_df = df.copy()

    if apply_filter:
        if date_from:
            filtered_df = filtered_df[filtered_df["Date"] >= pd.Timestamp(date_from)]
        if date_to:
            filtered_df = filtered_df[filtered_df["Date"] <= pd.Timestamp(date_to)]
        if job_type != "All":
            filtered_df = filtered_df[filtered_df["Type"].str.upper() == job_type]
        if wo_filter.strip():
            filtered_df = filtered_df[
                filtered_df["WO/PPM"].astype(str).str.contains(wo_filter.strip(), case=False, na=False)
            ]
        if department_filter != "All":
            filtered_df = filtered_df[
                filtered_df["Department"].astype(str).str.upper() == department_filter.strip().upper()
            ]
        if keyword_filter.strip():
            keyword_filter = keyword_filter.strip()
            mask = (
                filtered_df["Keywords"].astype(str).str.contains(keyword_filter, case=False, na=False)
                | filtered_df["Description"].astype(str).str.contains(keyword_filter, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        # ✅ Save filtered data
        st.session_state["filtered_df"] = filtered_df.copy()
        st.session_state["filters_applied"] = True

    elif st.session_state.get("filters_applied", False):
        filtered_df = st.session_state["filtered_df"]
    else:

        # Maintenance → filter by their department
        # Others → do NOT filter by department
        if department in MAINT_DEPTS:
            filtered_df = df[df["Department"].astype(str).str.upper() == department.strip().upper()]
        else:
            filtered_df = df.copy()  # Non-maintenance → all records


        # Show only the most recent 15 records
        filtered_df = filtered_df.head(15).copy()




    # ================================
    # 📤 Export Section (button on page)
    # ================================
    col_space, col_middle, col_link = st.columns([2, 5, 1])
    with col_link:
        st.markdown("""<hr style="border:none; border-top:0.5px ; margin:5px 0;">""", unsafe_allow_html=True)
        export_clicked = st.button(
            "📤 Export as CSV",
            key="export_link",
            help="Export filtered data to CSV"
        )

    if export_clicked:
        st.session_state["open_export_dialog"] = True

    # --- Open export dialog if triggered ---
    if st.session_state.get("open_export_dialog", False):
        from utils.export_tools import export_filtered_csv_dialog
        export_filtered_csv_dialog(
            job_ids=filtered_df["Index"].dropna().astype(int).tolist(),
            tag=active_tag,
            date_from=date_from,
            date_to=date_to,
            job_type=job_type,
            wo_filter=wo_filter,
            keyword_filter=keyword_filter,
        )

        # reset flag after closing
        st.session_state["open_export_dialog"] = False

    with col_middle:
        pass
    with col_space:

        if active_tag:
            st.session_state.job_temp["Object_Tag"] = active_tag

        render_add_job_section(user_department=department, user_name=username)
        
    # ---------------------------------------------------------
    if df.empty:
        st.warning(f"No job records found for tag **{active_tag}**.")
        return

    # ================================
    # 🔹 DATA DISPLAY Table
    # ================================



    render_job_table(filtered_df)



    st.markdown("""<hr style="border:none; border-top:2px solid darkgreen; margin:10px 0;">""",
                unsafe_allow_html=True)

    # ================================
    # 🧾 Add or View a Job Record
    # ================================
    with st.expander("🧾 Add or View a Job Record", expanded=False):

        col7, col8 = st.columns([1, 1])
        selected_job = None  # store selected job for editing

        # --- LEFT SIDE: View a specific job record ---
        with col7:
            job_input = st.text_input(
                "Enter a Job Index to view full job details:",
                placeholder="Type job index (e.g. 1023)..."
            )

            if job_input.strip():
                try:
                    job_id = int(job_input.strip())
                    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=3) as conn:
                        conn.execute("PRAGMA busy_timeout = 4000")
                        df_job = pd.read_sql_query(
                            """
                            SELECT job_indx, date, Object_Tag, job_description, keywords, department,
                                wo_number, permit_number, status, action_list, job_type, employee,
                                performed_action, route, registered_by, registered_date, anomaly, actual_start
                            FROM job_reports
                            WHERE job_indx = ?
                            LIMIT 1
                            """,
                            conn,
                            params=[job_id],
                        )

                    if df_job.empty:
                        st.warning(f"No record found for job index **{job_id}**.")
                    else:
                        selected_job = df_job.iloc[0].to_dict()
                        job_tag = str(selected_job.get("Object_Tag", "")).strip().upper()

                        if job_tag != active_tag.upper():
                            st.warning(
                                f"⚠️ Job index **{job_id}** belongs to **{job_tag}**, "
                                f"not to the current tag **{active_tag}**."
                            )
                            selected_job = None
                        else:
                            render_job_row(selected_job)

                            # ✏️ Edit / 🗑️ Delete buttons (permission-based)
                            col10, col11 = st.columns([0.37, 0.63])
                            user_info = get_user_info(username) or {}
                            is_admin = bool(user_info.get("is_admin", 0))
                            registered_by = str(selected_job.get("registered_by", "")).strip()
                            registered_date = selected_job.get("registered_date", "")
                            current_user = user_info.get("username", "").lower()

                            # --- Extract original registration info ---
                            if " | " in registered_by:
                                first_registered_by = registered_by.split(" | ")[0].strip()
                            else:
                                first_registered_by = registered_by.strip()

                            if " | " in registered_date:
                                first_registered_date = registered_date.split(" | ")[0].strip()
                            else:
                                first_registered_date = registered_date.strip()

                            # --- Parse registration date ---
                            from datetime import datetime

                            within_7_days = False
                            try:
                                if first_registered_date:
                                    reg_date = datetime.strptime(first_registered_date.split()[0], "%Y-%m-%d").date()
                                    within_7_days = (datetime.today().date() - reg_date).days <= 7
                            except Exception:
                                pass

                            same_user = current_user in first_registered_by.lower()
                            edit_enabled = is_admin or (same_user and within_7_days)

                            # --- Column 10: Delete button ---
                            with col10:
                                delete_clicked = False

                                if edit_enabled:
                                    st.session_state.setdefault("edit_mode", False)

                                    # First delete button
                                    delete_clicked = st.button("🗑️ Remove this record", key="delete_job_btn")

                                    # If delete clicked → enable confirmation
                                    if delete_clicked:
                                        st.session_state.confirm_delete = True


                            # ==============================================================
                            # 🔥 Confirmation Block (MUST BE OUTSIDE col10 for Streamlit 1.45)
                            # ==============================================================

                            if st.session_state.get("confirm_delete", False):

                                st.warning("⚠️ Are you sure? This cannot be undone.")

                                # Now safe: columns at root level
                                col_del1, col_del2 = st.columns([1, 1])

                                # ----- YES: DELETE -----
                                with col_del1:
                                    if st.button("✅ Yes, delete", key="confirm_delete_btn"):
                                        try:
                                            with sqlite3.connect(DB_PATH) as conn:
                                                conn.execute("PRAGMA busy_timeout = 4000")
                                                conn.execute("DELETE FROM job_reports WHERE job_indx = ?", (job_id,))
                                                conn.commit()

                                            st.success(f"🗑️ Record #{job_id} deleted successfully.")
                                            time.sleep(1.5)
                                            st.session_state.confirm_delete = False
                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"Error deleting record: {e}")
                                            st.session_state.confirm_delete = False

                                # ----- CANCEL -----
                                with col_del2:
                                    if st.button("❌ Cancel", key="cancel_delete_btn"):
                                        st.session_state.confirm_delete = False
                                        st.info("Deletion cancelled.")


                            # --- Column 11: Edit button ---
                            with col11:
                                if edit_enabled:
                                    st.session_state.setdefault("edit_mode", False)

                                    if not st.session_state.edit_mode:
                                        if st.button("✏️ Edit this report", key="edit_job_btn"):
                                            st.session_state.edit_mode = True
                                            st.session_state.selected_job_for_edit = selected_job
                                    else:
                                        if st.button("❌ Cancel Edit", key="cancel_edit_btn"):
                                            st.session_state.edit_mode = False
                                            st.session_state.selected_job_for_edit = None
                                else:
                                    st.caption("🔒 Editing disabled (user not registered or older than 7 days)")

                except ValueError:
                    st.warning("Please enter a valid numeric job index.")
                except Exception as e:
                    st.error(f"Error fetching job details: {e}")

        # --- RIGHT SIDE: Edit form ---
        with col8:
            if st.session_state.get("edit_mode", False) and st.session_state.get("selected_job_for_edit"):
                from utils.job_edit_form import render_edit_job_form
                job = st.session_state["selected_job_for_edit"]
                render_edit_job_form(username, job)



    st.markdown("""<hr style="border:none; border-top:2px solid darkgreen; margin:10px 0;">""", unsafe_allow_html=True)


    # ================================
    # 📈 MONTHLY TREND OF PM & CM RECORDS
    # ================================
    # from utils.trend_charts import render_monthly_trends

    # st.markdown("""<hr style="border:none; border-top:2px solid darkgreen; margin:10px 0;">""",
    #             unsafe_allow_html=True)

    # with st.expander(f"📈 Extra Info: {active_tag}", expanded=False):
    #     if df.empty or "Date" not in df.columns:
    #         st.info("No valid data available to generate monthly trend.")
    #         return
    #     render_monthly_trends(df, active_tag)

    with st.expander(f"📈 Extra Info: {active_tag}", expanded=False):
        # 🔘 Button to trigger monthly trend rendering
        if st.button(f"Load the Data", key=f"load_trend_{active_tag}"):
            if df.empty or "Date" not in df.columns:
                st.info("No valid data available to generate monthly trend.")
            else:
                from utils.trend_charts import render_monthly_trends
                render_monthly_trends(df, active_tag)
        else:
            pass
    # ================================
    # 🧩 STANDBY COMPARISON SECTION
    # ================================
    with st.expander(f"Standby Comparison for {active_tag}", expanded=False):


        # 🔘 Button to trigger calculation
        if st.button(f"Load the data", key="load_standby"):

            from utils.standby_comparison import render_standby_comparison
            render_standby_comparison(active_tag)
        else:
            pass

    # ================================
    # 🧩 Other Trains COMPARISON SECTION
    # ================================
    with st.expander(f"Other Trains Comparison for {active_tag}", expanded=False):


        # 🔘 Button to trigger calculation
        if st.button(f"Load the data", key="load_other_trains"):

            from utils.other_trains_comparison import render_typical_trains_comparison
            render_typical_trains_comparison(active_tag)
        else:
            pass


    # ================================
    # ⚙️ MOTOR SPECIFICATION SECTION
    # ================================
    st.markdown("""<hr style="border:none; border-top:2px solid darkgreen; margin:10px 0;">""",
            unsafe_allow_html=True)
    
    if obj_info:
        object_type = (obj_info.get("Type") or "").strip().lower()

        if object_type == "motor":
            from utils.motor_specs import load_motor_spec, render_motor_spec_row
            with st.expander("📑 Motor Specification", expanded=False):

                spec_row = load_motor_spec(active_tag)

                if spec_row is None:
                    st.info(f"No motor specifications found for tag **{active_tag}**.")
                else:
                    render_motor_spec_row(spec_row)



        # ================================
        # 📁 FOLDER LOCATION SECTION
        # ================================
        if active_tag:

            from utils.folder_locations import render_folder_location_section
            render_folder_location_section(active_tag)
        


if __name__ == "__main__":
    main()
