import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from pathlib import Path
import time

# --- Path to your main DB ---
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


def export_filtered_csv_dialog(
    job_ids=None,   # can be list[int] OR pd.DataFrame
    tag: str = "",
    date_from=None,
    date_to=None,
    job_type="All",
    wo_filter="",
    keyword_filter="",
    max_attempts: int = 5,
    delay: float = 1.0
):
    """
    🔹 Universal export dialog for CSV download.

    Supports both:
      - job_ids: list[int] → re-query DB for full job data (old behavior)
      - job_ids: pd.DataFrame → export directly (new behavior for grouped data)
    """

    # Handle empty or invalid input
    if job_ids is None or (isinstance(job_ids, (list, pd.Series)) and len(job_ids) == 0):
        st.warning("⚠️ No job records found to export.")
        return

    # --- Detect if DataFrame passed ---
    is_dataframe = isinstance(job_ids, pd.DataFrame)

    @st.dialog(f"Export Data for {tag}")
    def confirm_export_dialog():
        n_records = len(job_ids) if not is_dataframe else len(job_ids.index)

        st.markdown("""
        You are about to download a **CSV file** with all job details
        for the filtered job records.
        """)
        st.markdown(f"""
        - **From Date:** {str(date_from) if date_from else "-"}  
        - **To Date:** {str(date_to) if date_to else "-"}  
        - **Job Type:** {job_type or "-"}  
        - **WO/PPM Contains:** {wo_filter or "-"}  
        - **Keyword/Description Contains:** {keyword_filter or "-"}  
        - **Number of Records:** {n_records}  
        """)
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            confirm = st.button("✅ Yes, Export", use_container_width=True)
        with c2:
            cancel = st.button("❌ Cancel", use_container_width=True)

        if confirm:
            try:
                # ==================================================
                # 🧾 CASE 1: Direct DataFrame export (for grouped data)
                # ==================================================
                if is_dataframe:
                    export_df = job_ids.copy()

                # ==================================================
                # 🧾 CASE 2: job_ids → fetch from database
                # ==================================================
                else:
                    db_uri = f"file:{DB_PATH}?mode=ro"
                    export_df = pd.DataFrame()

                    query = f"""
                        SELECT *
                        FROM job_reports
                        WHERE job_indx IN ({','.join(['?'] * len(job_ids))})
                        ORDER BY date DESC, rowid DESC
                    """

                    # Retry-safe DB read
                    for attempt in range(1, max_attempts + 1):
                        try:
                            with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
                                conn.execute("PRAGMA busy_timeout = 5000")
                                export_df = pd.read_sql_query(query, conn, params=job_ids)
                            break
                        except sqlite3.OperationalError as e:
                            if "locked" in str(e).lower():
                                st.toast(f"⏳ Database busy (attempt {attempt}/{max_attempts})...", icon="🔄")
                                time.sleep(delay)
                            else:
                                raise
                    else:
                        st.error("❌ Database was locked too long. Please try again later.")
                        return

                # ==================================================
                # 🧹 Clean up and Export
                # ==================================================
                for col in export_df.columns:
                    export_df[col] = (
                        export_df[col]
                        .astype(str)
                        .str.replace(r"<.*?>", "", regex=True)
                        .str.replace(r"&nbsp;", " ", regex=True)
                        .str.replace(r"\s+", " ", regex=True)
                        .str.strip()
                    )

                file_name = f"{tag}_{pd.Timestamp.now():%Y%m%d_%H%M%S}.csv"
                csv_buffer = BytesIO()
                export_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
                csv_bytes = csv_buffer.getvalue()

                st.success("✅ File ready for download.")
                st.download_button(
                    "⬇️ Download CSV File",
                    data=csv_bytes,
                    file_name=file_name,
                    mime="text/csv",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"❌ Unexpected export error:\n{e}")

        elif cancel:
            st.toast("❌ Export canceled", icon="🛑")
            st.session_state["open_export_dialog"] = False
            st.rerun()

    confirm_export_dialog()
