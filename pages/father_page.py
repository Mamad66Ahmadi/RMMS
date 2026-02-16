import streamlit as st
import pandas as pd
import sqlite3
import time
import urllib.parse
from pathlib import Path
from streamlit.components.v1 import html

# --- Internal utilities ---
from utils.top_bar import display_top_bar
from utils.job_form import init_job_session_state
from utils.job_table_display import render_family_job_table
from utils.Select_options_function import get_department_options

# =====================================================
# 📘 CONFIG & CONSTANTS
# =====================================================
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"
st.set_page_config(page_title="Father Tag Details", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #27AE5F15; }
</style>
""", unsafe_allow_html=True)

from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()


# =====================================================
# 🔹 DATABASE UTILITIES
# =====================================================
def _read_query(sql: str, params=None, retries: int = 3, delay: float = 1.0) -> pd.DataFrame:
    """Safe read-only SQLite query with retry logic."""
    db_uri = f"file:{DB_PATH}?mode=ro"
    for _ in range(retries):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=3) as conn:
                df = pd.read_sql_query(sql, conn, params=params or [], index_col=None)
                return df.loc[:, ~df.columns.duplicated()]
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise
    return pd.DataFrame()

def get_all_father_tags() -> list:
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            df = pd.read_sql_query(
                "SELECT DISTINCT Father_Tag FROM objects WHERE Father_Tag IS NOT NULL ORDER BY Father_Tag ASC;", conn)
        return df["Father_Tag"].dropna().astype(str).tolist()
    except Exception as e:
        st.error(f"Error loading father tags: {e}")
        return []

def get_family_tags(father_tag: str) -> pd.DataFrame:
    """Return Object_Tag and Object_Type for all related family members."""
    if not father_tag:
        return pd.DataFrame(columns=["Object_Tag", "Object_Type"])
    query = """
        SELECT Object_Tag, Object_Type
        FROM objects
        WHERE Long_Tag LIKE ? OR Long_Tag LIKE ? OR Object_Tag = ?
        ORDER BY Object_Type, Object_Tag;
    """
    pattern = f"%/{father_tag}/%"
    pattern2 = f"{father_tag}/%"

    
    df = _read_query(query, [pattern, pattern2, father_tag])
    if df.empty:
        return pd.DataFrame(columns=["Object_Tag", "Object_Type"])
    df["Object_Tag"] = df["Object_Tag"].astype(str)
    df["Object_Type"] = df["Object_Type"].fillna("Unknown").astype(str)
    return df

# =====================================================
# 🧩 MAIN PAGE
# =====================================================
def main():
    username = st.query_params.get("username", "Unknown")
    name = st.query_params.get("name", "")
    department = st.query_params.get("department", "")
    father_tag = st.query_params.get("father_tag", "").strip().upper()

    display_top_bar(name, department)
    init_job_session_state()

    # --- Father Tag Selection ---
    all_fathers = get_all_father_tags()
    selected_father = st.selectbox(
        "Select Father Tag:",
        [""] + all_fathers,
        index=([""] + all_fathers).index(father_tag) if father_tag in all_fathers else 0
    )
    if not selected_father:
        st.info("👈 Please select a Father Tag to view related data.")
        return

    html(f"<script>window.parent.document.title = '{selected_father} (Father Tag Details)';</script>", height=0)

    # --- Family Tags ---
    df_fam = get_family_tags(selected_father)
    if df_fam.empty:
        st.warning(f"No related tags found for father tag: {selected_father}")
        return
    family_tags = df_fam["Object_Tag"].tolist()

    # =====================================================
    # 🔍 Filter Section (session-persistent)
    # =====================================================


    MAINT_DEPTS = [
        "CBM", "Electrical", "Fix", "Inspection",
        "Instrument", "Rotary", "Service S", "HVAC"
    ]

    default_department = department if department in MAINT_DEPTS else "All"

    default_filters = {
        "date_from": None,
        "date_to": None,
        "job_type": "All",
        "wo_filter": "",
        "permit_filter": "",
        "department_filter": default_department,   # ← FIXED HERE
        "keyword_filter": "",
    }


    for k, v in default_filters.items():
        st.session_state.setdefault(k, v)

    with st.expander("🔍 Filter Family Job Records", expanded=False):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            date_from = st.date_input("From Date", value=st.session_state.date_from)
        with col2:
            date_to = st.date_input("To Date", value=st.session_state.date_to)
        with col3:
            job_type = st.selectbox("Job Type", ["All", "PM", "CM"],
                                    index=["All", "PM", "CM"].index(st.session_state.job_type))

        col4, col5, col6 = st.columns([1, 1, 3])
        with col4:
            wo_filter = st.text_input("WO/PPM (contains)", st.session_state.wo_filter)
        with col5:
            raw_depts = get_department_options()
            dept_opts = sorted(set(raw_depts))
            if department and department not in dept_opts:
                dept_opts.insert(0, department)
            department_filter = st.selectbox(
                "Department",
                ["All"] + dept_opts,
                index=(["All"] + dept_opts).index(st.session_state.department_filter)
                if st.session_state.department_filter in dept_opts else 0
            )
        with col6:
            keyword_filter = st.text_input("Keyword/Description", st.session_state.keyword_filter)

        col_btn = st.columns([1, 7])[0]
        with col_btn:
            apply_filter = st.button("Apply Filters", use_container_width=True)

        if apply_filter:
            st.session_state.date_from = date_from
            st.session_state.date_to = date_to
            st.session_state.job_type = job_type
            st.session_state.wo_filter = wo_filter
            st.session_state.department_filter = department_filter
            st.session_state.keyword_filter = keyword_filter

    # =====================================================
    # 🧮 Query Logic
    # =====================================================
    placeholders = ",".join(["?"] * len(family_tags))
    base_query = f"""
        SELECT job_indx, date, Object_Tag, department, job_type, wo_number,
               permit_number, performed_action, job_description, keywords,
               status, action_list, anomaly, route, actual_start,
               registered_by, registered_date
        FROM job_reports
        WHERE Object_Tag IN ({placeholders})
    """
    params = family_tags

    if st.session_state.date_from:
        base_query += " AND date >= ?"
        params.append(str(st.session_state.date_from))
    if st.session_state.date_to:
        base_query += " AND date <= ?"
        params.append(str(st.session_state.date_to))
    if st.session_state.job_type != "All":
        base_query += " AND UPPER(job_type) = ?"
        params.append(st.session_state.job_type.upper())
    if st.session_state.wo_filter.strip():
        base_query += " AND wo_number LIKE ?"
        params.append(f"%{st.session_state.wo_filter.strip()}%")
    if st.session_state.department_filter != "All":
        base_query += " AND UPPER(department) = ?"
        params.append(st.session_state.department_filter.upper())
    if st.session_state.keyword_filter.strip():
        base_query += " AND (keywords LIKE ? OR job_description LIKE ?)"
        kw = f"%{st.session_state.keyword_filter.strip()}%"
        params.extend([kw, kw])

    base_query += " ORDER BY date DESC, job_indx DESC"

    # =====================================================
    # 🧠 Intelligent Limit Logic
    # =====================================================
    filters_active = any([
        st.session_state.date_from,
        st.session_state.date_to,
        st.session_state.job_type != "All",
        st.session_state.wo_filter.strip(),
        st.session_state.keyword_filter.strip(),
        (st.session_state.department_filter != (department if department else "All"))
    ])

    limit = 15 if not filters_active else 100

    # --- Count total before applying limit (for info display)
    count_query = f"SELECT COUNT(*) AS total FROM ({base_query})"
    total_df = _read_query(count_query, params)
    total_records = int(total_df['total'][0]) if not total_df.empty else 0

    base_query += f" LIMIT {limit}"
    df = _read_query(base_query, params)

    if total_records > limit:
        st.info(f"Showing **{limit}** most recent records out of **{total_records}** total matches.")
    else:
        st.info(f"Showing **{total_records}** most recent records out of **{total_records}** total matches.")

    if df.empty:
        st.info("No records found for this family.")
        return


    # =====================================================
    # 📤 Export + Add Job + Display
    # =====================================================
    col_space, col_mid, col_export = st.columns([2, 5, 1])
    with col_export:
        export_clicked = st.button("📤 Export as CSV", key="export_family_csv")

    if export_clicked:
        from utils.export_tools import export_filtered_csv_dialog
        export_filtered_csv_dialog(
            job_ids=df,
            tag=selected_father,
            date_from=st.session_state.date_from,
            date_to=st.session_state.date_to,
            job_type=st.session_state.job_type,
            wo_filter=st.session_state.wo_filter,
            keyword_filter=st.session_state.keyword_filter,
        )

    with col_space:
        tag_param = st.query_params.get("tag", "").strip().upper()
        if tag_param:
            object_url = (
                f"/Object_Details_page?"
                f"username={username}&name={name}&department={department}&tag={tag_param}"
            )

            st.markdown(
                f"""
                <div style='text-align:left; margin-top:8px;'>
                    <a href="{object_url}" target="_self" style="
                        background-color:#1b4d89;
                        color:white;
                        padding:8px 18px;
                        text-decoration:none;
                        border-radius:8px;
                        font-weight:600;
                        box-shadow:0 2px 6px rgba(0,0,0,0.25);
                    ">
                    Back to Tag: {tag_param}
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            pass
    # =====================================================
    # 🧾 Render Job Table
    # =====================================================
    render_family_job_table(df)


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

                        # ✅ Check if job_tag belongs to the family tags
                        if job_tag not in [t.upper() for t in family_tags]:
                            st.warning(
                                f"⚠️ Job index **{job_id}** belongs to **{job_tag}**, "
                                f"which is **not part of the current family ({selected_father})**."
                            )
                            selected_job = None
                        else:
                            from utils.job_display import render_job_row
                            from utils.auth import get_user_info


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
                                    delete_clicked = st.button("🗑️ Remove this record", key="delete_job_btn")

                                    if delete_clicked or st.session_state.get("confirm_delete", False):
                                        st.session_state.confirm_delete = True
                                        st.warning("⚠️ Are you sure you want to permanently delete this record? This action **cannot be undone.**")

                                        col_del1, col_del2 = st.columns([1, 1])
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

    # =====================================================
    # 📋 Family Members Expander (restored)
    # =====================================================
    with st.expander(f"📋 Family Members of {selected_father} ({len(df_fam)})", expanded=False):
        grouped = df_fam.groupby("Object_Type")
        base_params = {"username": username, "name": name, "department": department}
        for obj_type, group in grouped:
            st.markdown(
                f"<div style='margin-top:10px; margin-bottom:5px; font-weight:650; "
                f"color:#11224E; font-size:15px;'>{obj_type} ({len(group)}):</div>",
                unsafe_allow_html=True)
            tag_links = []
            for tag in sorted(group["Object_Tag"].tolist()):
                params = {**base_params, "tag": tag}
                link = f"/Object_Details_page?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
                tag_links.append(
                    f"<a href='{link}' target='_blank' style='color:#000; text-decoration:none; font-weight:450;'>{tag}</a>")
            st.markdown(
                f"<div style='font-size:15px; color:#000; line-height:1.6; "
                f"margin-bottom:10px;'>{', '.join(tag_links)}</div>",
                unsafe_allow_html=True)


    # =====================================================
    # 📊 Family CM/PM Trend Charts (New Section)
    # =====================================================


    with st.expander("📊 Family CM/PM Charts (1-Year Overview)", expanded=False):

        if st.button("Load the Data"):
            from utils.trend_charts_father import render_family_cm_pm_charts

            st.markdown(
                f"""
                <div style='
                    margin-top:10px; 
                    font-size:20px; 
                    color:#a6282e;
                    font-weight:600;
                '>
                    📊 Activity Distribution for Family Members of <span style='font-weight:700;'>{selected_father}</span>
                    <br>
                    <span style='font-size:16px; color:#5a1b1e;'>
                        (Last 12 Months)
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("---")
            render_family_cm_pm_charts(family_tags)


# =====================================================
# ▶️ ENTRY POINT
# =====================================================
if __name__ == "__main__":
    main()
