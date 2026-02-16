import streamlit as st
import sqlite3
from pathlib import Path
import pandas as pd
import time

# --- DB Path Helper ---
def _get_db_path():
    return Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

# --- Safe Read Query with caching for efficiency ---
def _read_query(sql: str, params=None):
    db_path = _get_db_path()
    retries = 3
    delay = 0.5
    for attempt in range(retries):
        try:
            with sqlite3.connect(db_path, timeout=2) as conn:
                df = pd.read_sql_query(sql, conn, params=params or [])
                return df
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise
    return pd.DataFrame()

# --- Write Query with retry logic ---
def _write_query(sql: str, params=None):
    db_path = _get_db_path()
    retries = 3
    delay = 0.5
    for attempt in range(retries):
        try:
            with sqlite3.connect(db_path, timeout=2) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params or [])
                conn.commit()
                return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise
    return False

# ============================================================
#   MAIN FUNCTION TO MANAGE ROUTE TAGS (Optimized for Multi-User)
# ============================================================
def manage_route_tags(route_code: str, route_desc: str, std_job_desc: str, df):
    """UI to Add/Remove Object Tags and Edit Route Info efficiently."""

    st.markdown(
        "<hr style='border:2px solid red; margin-top:40px;'>",
        unsafe_allow_html=True
    )

    with st.expander("🔧 **Manage Routes:**"):

        col_left, col_centr, col_right, col_end = st.columns([2, 1, 2, 2])

        # Extract current tags
        current_tags = sorted(df["Object_Tag"].dropna().unique().tolist())

        # ------------------------------------------------------------
        #   ADD TAG SECTION
        # ------------------------------------------------------------
        with col_left:
            try:
                df_objects = _read_query("SELECT DISTINCT Object_Tag FROM objects ORDER BY Object_Tag ASC")
                all_available_tags = df_objects["Object_Tag"].dropna().unique().tolist()
            except Exception as e:
                st.error(f"❌ Could not load tags from objects table: {e}")
                all_available_tags = []

            selectable_tags = [t for t in all_available_tags if t not in current_tags]
            new_tag = st.selectbox("Select Tag to add", [""] + selectable_tags)

            if st.button("Add Tag to Route", key="add_route_tag"):
                if not new_tag.strip():
                    st.warning("⚠️ Please select a tag to add.")
                else:
                    success = _write_query(
                        """
                        INSERT INTO routes (PMRoute_Code, PMRoute_Desc, Object_Tag, StandardJob_Desc)
                        VALUES (?, ?, ?, ?)
                        """,
                        (route_code, route_desc, new_tag.strip(), std_job_desc)
                    )
                    if success:
                        st.success(f"✅ Tag **{new_tag}** added to route {route_code}.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add tag after multiple attempts.")

        with col_centr:
            pass

        # ------------------------------------------------------------
        #   REMOVE TAG SECTION
        # ------------------------------------------------------------
        with col_right:
            if not current_tags:
                st.info("No tags to remove.")
            else:
                tag_to_remove = st.selectbox("Select tag to remove", current_tags)
                if st.button("Remove Tag from Route", key="remove_route_tag"):
                    success = _write_query(
                        """
                        DELETE FROM routes
                        WHERE PMRoute_Code = ? AND Object_Tag = ?
                        """,
                        (route_code, tag_to_remove)
                    )
                    if success:
                        st.success(f"🗑️ Tag **{tag_to_remove}** removed from route {route_code}.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to remove tag after multiple attempts.")

        with col_end:
            pass

        # =============================================================
        #   EDIT ROUTE DESCRIPTION OR STANDARD JOB
        # =============================================================
        st.markdown("---")
        st.markdown("##### Edit Route Description or Standard Job")

        if not current_tags:
            st.info("⚠️ This route has no tags, so nothing can be edited.")
            return

        col_lef, col_cent, col_righ, col_en = st.columns([2, 0.2, 2, 2])

        with col_lef:
            edit_tag = st.selectbox("Select Tag to Edit Its Route Info", current_tags)
            df_edit = _read_query(
                """
                SELECT PMRoute_Desc, StandardJob_Desc
                FROM routes 
                WHERE PMRoute_Code = ? AND Object_Tag = ?
                """,
                [route_code, edit_tag]
            )

            if df_edit.empty:
                st.error("❌ Could not load current values.")
                return

        with col_cent:
            pass

        with col_righ:
            current_desc = df_edit.iloc[0]["PMRoute_Desc"]
            new_desc = st.text_input("PM Route Description", current_desc)

        with col_en:
            current_job = df_edit.iloc[0]["StandardJob_Desc"]
            new_job = st.text_input("Standard Job Description", current_job)

        if st.button("Modify Description or Standard Job", key="edit_route_values"):
            success = _write_query(
                """
                UPDATE routes
                SET PMRoute_Desc = ?, StandardJob_Desc = ?
                WHERE PMRoute_Code = ? AND Object_Tag = ?
                """,
                (new_desc, new_job, route_code, edit_tag)
            )
            if success:
                st.success(f"✔️ Updated Route Info for tag **{edit_tag}**.")
                st.rerun()
            else:
                st.error("❌ Failed to update record after multiple attempts.")
