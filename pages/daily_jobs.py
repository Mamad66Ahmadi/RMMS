import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import base64

# --- Internal modules ---
from utils.top_bar import display_top_bar
from utils.job_table_display import render_job_table_with_tag
from utils.job_form import render_add_job_section, init_job_session_state
from utils.auth import get_user_info
from utils.job_display import render_job_row
from utils.filter_section import render_filter_and_query


# ==========================================================
# 📘 Database Path
# ==========================================================
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

st.set_page_config(page_title="Recent Job Reports", layout="wide")

from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()

# ==========================================================
# Persian Font
# ==========================================================
font_path = Path(__file__).parent.parent / "fonts" / "Vazirmatn-Bold.woff2"
with open(font_path, "rb") as f:
    font_data = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
@font-face {{
    font-family: 'Vazirmatn';
    src: url(data:font/woff2;base64,{font_data}) format('woff2');
    font-weight: bold;
}}
.dialog-persian {{
    font-family: 'Vazirmatn', sans-serif;
    direction: rtl;
    text-align: right;
    color: #222;
    line-height: 1.9;
    font-size: 15px;
}}
.dialog-title {{
    font-family: 'Vazirmatn', sans-serif;
    text-align: right;
    color: #a80000;
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
}}
</style>
""", unsafe_allow_html=True)


# ==========================================================
# 🧾 Main
# ==========================================================
def main():
    username = st.query_params.get("username", "Unknown")
    name = st.query_params.get("name", "")
    department = st.query_params.get("department", "")

    display_top_bar(name, department)
    init_job_session_state()

    # ======================================================
    # 🔍 Filter Section + Query (NEW CLEAN FUNCTION)
    # ======================================================
    df, total_matches, date_from, date_to, job_type, wo_filter, keyword_filter = \
        render_filter_and_query(str(DB_PATH), username, department)

    # ======================================================
    # 🧮 Display Info
    # ======================================================
    try:
        df_dates = pd.to_datetime(df["date"], errors="coerce")
        actual_from = df_dates.min().date()
        actual_to = df_dates.max().date()
        shown = len(df)

    except:
        actual_from = date_from
        actual_to = date_to
        shown = len(df)

    if df.empty:
        st.info("No job records found in the selected range.")
        no_data = True
    else:

        if total_matches > 150:
            st.info(f"Showing **{shown}** most recent records out of **{total_matches}** total matches.")
        else:
            st.info(f"Showing **{shown}** records out of **{total_matches}**. "
                    f"(From **{actual_from}** to **{actual_to}**)")

        no_data = False

    # ==========================================================
    # 🔹 Add Father Tag + Family Count
    # ==========================================================
    if not df.empty:
        from utils.tag_father_stats import get_father_and_recent_count
        father_data = []
        for _, row in df.iterrows():
            tag = str(row["Object_Tag"]).strip()
            date_val = str(row["date"]).strip()
            father, count = get_father_and_recent_count(tag, date_val)
            father_data.append((row["job_indx"], father, count))

        father_df = pd.DataFrame(
            father_data,
            columns=["job_indx", "Father Tag", "Recent 30d Family Count"]
        )

        df = df.merge(father_df, on="job_indx", how="left")

    # ==========================================================
    # 🔹 Data Cleanup + PM/CM Grouping
    # ==========================================================
    if df.empty:
        no_data = True
        st.info("No job records found in the selected range.")
    else:
        # Rename
        df.rename(columns={
            "job_indx": "Index",
            "date": "Date",
            "Object_Tag": "Object_Tag",
            "department": "Department",
            "wo_number": "WO/PPM",
            "status": "Status",
            "actual_start": "Actual Start",
            "job_type": "Type",
            "performed_action": "Performed Job",
            "job_description": "Description",
            "keywords": "Keywords",
            "registered_by": "Registered By",
            "route": "Route",
            "Count_YTD": "Year Count",
            "Count_MTD": "Month Count",
        }, inplace=True)

        for col in ["Year Count", "Month Count"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(x) if str(x).isdigit() else x)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=False).reset_index(drop=True)

        # PM grouping
        df_pm = df[df["Type"].str.upper() == "PM"].copy()
        df_cm = df[df["Type"].str.upper() == "CM"].copy()

        if not df_pm.empty:
            df_pm["Route"] = df_pm["Route"].fillna("-")

            df_pm["Actual Start"] = pd.to_datetime(df_pm["Actual Start"], errors="coerce")


            grouped_pm = (
                df_pm.groupby(["Date", "Route"], as_index=False)
                .agg({
                    "WO/PPM": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                    "Status": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                    "Performed Job": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                    "Department": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                    "Object_Tag": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                    "Actual Start": lambda x: x.min(),
                })
            )


            grouped_pm["Actual Start"] = grouped_pm["Actual Start"].dt.date.fillna("-")

            grouped_pm["Index"] = "PM"
            grouped_pm["Elapsed days"] = "-"
            grouped_pm["Type"] = "PM"
            grouped_pm["Keywords"] = "-"
            grouped_pm["Description"] = "-"
            grouped_pm["Registered By"] = "-"
            grouped_pm["anomaly"] = 0
            grouped_pm["action_list"] = 0

            grouped_pm = grouped_pm[[
                "Index", "Date", "Object_Tag", "Elapsed days", "Department",
                "Type", "WO/PPM", "Actual Start", "Performed Job", "Keywords",
                "Description", "Status", "Registered By", "Route", "anomaly", "action_list"
            ]]
        else:
            grouped_pm = pd.DataFrame(columns=df.columns)

        combined_df = pd.concat([grouped_pm, df_cm], ignore_index=True)
        combined_df = combined_df.sort_values("Date", ascending=False).reset_index(drop=True)
        combined_df_export = combined_df.copy()
    # ==========================================================
    # 📤 Export + Add Job
    # ==========================================================
    col_space, col_mid, col_link = st.columns([2, 5, 1])

    with col_link:
        export_clicked = st.button("📤 Export as CSV")

    if export_clicked:
        st.session_state["open_export_dialog"] = True

    if st.session_state.get("open_export_dialog", False):
        from utils.export_tools import export_filtered_csv_dialog

        export_filtered_csv_dialog(
            job_ids=combined_df_export,
            tag="Recent Jobs",
            date_from=date_from,
            date_to=date_to,
            job_type=job_type,
            wo_filter=wo_filter,
            keyword_filter=keyword_filter,
        )
        st.session_state["open_export_dialog"] = False

    with col_space:
        render_add_job_section(user_department=department, user_name=username)

    # ==========================================================
    # Display Table
    # ==========================================================
    if not no_data:
        st.markdown("<hr style='border:none; border-top:1.5px solid darkgreen; margin:10px 0;'>",
                    unsafe_allow_html=True)
        render_job_table_with_tag(combined_df)

    # ================================
    # 🧾 Add or View a Job Record
    # ================================
    with st.expander("🧾 Add or View a Job Record", expanded=False):

        col7, col8 = st.columns([1, 1])
        selected_job = None

        # -----------------------------
        # LEFT SIDE — VIEW JOB RECORD
        # -----------------------------
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
                                   performed_action, route, registered_by, registered_date,
                                   anomaly, actual_start
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
                        render_job_row(selected_job)

                        # -------------------------------------------------------
                        # Permission Logic
                        # -------------------------------------------------------
                        col10, col11 = st.columns([0.37, 0.63])
                        user_info = get_user_info(username) or {}
                        is_admin = bool(user_info.get("is_admin", 0))
                        registered_by = str(selected_job.get("registered_by", "")).strip()
                        registered_date = selected_job.get("registered_date", "")
                        current_user = user_info.get("username", "").lower()

                        # --- Extract original registration info ---
                        first_registered_by = registered_by.split(" | ")[0].strip() if registered_by else ""
                        first_registered_date = registered_date.split(" | ")[0].strip() if registered_date else ""

                        within_7_days = False
                        try:
                            if first_registered_date:
                                reg_date = datetime.strptime(first_registered_date.split()[0], "%Y-%m-%d").date()
                                within_7_days = (datetime.today().date() - reg_date).days <= 7
                        except:
                            pass

                        same_user = current_user in first_registered_by.lower()
                        edit_enabled = is_admin or (same_user and within_7_days)

                        # -----------------------------
                        # DELETE BUTTON
                        # -----------------------------
                        with col10:
                            if edit_enabled:
                                if st.button("🗑️ Remove this record"):
                                    st.session_state.confirm_delete = True

                        # ---- PLACE THIS OUTSIDE col10 ----
                        if st.session_state.get("confirm_delete", False):
                            st.warning("⚠️ Are you sure? This cannot be undone.")
                            c1, c2 = st.columns(2)

                            with c1:
                                if st.button("Yes, delete"):
                                    with sqlite3.connect(DB_PATH) as conn:
                                        conn.execute(
                                            "DELETE FROM job_reports WHERE job_indx = ?", (job_id,)
                                        )
                                        conn.commit()
                                    st.success("Record deleted.")
                                    st.session_state.confirm_delete = False
                                    st.rerun()

                            with c2:
                                if st.button("Cancel"):
                                    st.session_state.confirm_delete = False


                        # -----------------------------
                        # EDIT BUTTON
                        # -----------------------------
                        with col11:
                            if edit_enabled:
                                if not st.session_state.get("edit_mode", False):
                                    if st.button("✏️ Edit this report"):
                                        st.session_state.edit_mode = True
                                        st.session_state.selected_job_for_edit = selected_job
                                else:
                                    if st.button("❌ Cancel Edit"):
                                        st.session_state.edit_mode = False
                                        st.session_state.selected_job_for_edit = None
                            else:
                                st.caption("🔒 Editing disabled.")

                except ValueError:
                    st.warning("Please enter a valid numeric job index.")
                except Exception as e:
                    st.error(f"Error loading job details: {e}")

        # -----------------------------
        # RIGHT SIDE — EDIT JOB RECORD
        # -----------------------------
        with col8:
            if st.session_state.get("edit_mode", False):
                from utils.job_edit_form import render_edit_job_form
                render_edit_job_form(username, st.session_state["selected_job_for_edit"])

    # ==========================================================

    st.markdown("<hr style='border:2px solid red;'>", unsafe_allow_html=True)
    st.markdown("### Trends:")
    BOX_WIDTH = "400px"
    BOX_HEIGHT = "55px"

    col22, col23 = st.columns([1, 12])

    # --- Uniform Button Size ---

    # -----------------------------------
    # 📈 1-Year Trend Charts Link
    # -----------------------------------
    with col22:
        pass
    with col23:
        trend1_url = (
            f"/trends_page?"
            f"chart_type=trend_1year"
            f"&username={username}&name={name}&department={department}"
        )

        st.markdown(f"""
        <div style='text-align:right; margin-top:20px;'>
            <a href="{trend1_url}" target="_self" style="
                display:flex;
                justify-content:center;
                align-items:center;
                background-color:#003366;
                color:white;
                width:{BOX_WIDTH};
                height:{BOX_HEIGHT};
                text-decoration:none;
                border-radius:10px;
                font-weight:600;
                font-size:16px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            " 
            onmouseover="this.style.transform='scale(1.05)';" 
            onmouseout="this.style.transform='scale(1)';">
                📈 Monthly PM/CM Report Counts (Last 12 Months)
            </a>
        </div>
        """, unsafe_allow_html=True)


        # -----------------------------------
        # 📊 Units ↔ Departments Link
        # -----------------------------------
        trend2_url = (
            f"/trends_page?"
            f"chart_type=cm_departments"
            f"&username={username}&name={name}&department={department}"
        )

        st.markdown(f"""
        <div style='text-align:right; margin-top:15px;'>
            <a href="{trend2_url}" target="_self" style="
                display:flex;
                justify-content:center;
                align-items:center;
                background-color:#4B0082;
                color:white;
                width:{BOX_WIDTH};
                height:{BOX_HEIGHT};
                text-decoration:none;
                border-radius:10px;
                font-weight:600;
                font-size:16px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            "
            onmouseover="this.style.transform='scale(1.05)';"
            onmouseout="this.style.transform='scale(1)';">
                📊 CM Report Distribution Across Units & Departments
            </a>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
