import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Optional
import time
from datetime import datetime


# =========================================================
# 📂 Database Utilities
# =========================================================
def _get_db_path() -> Path:
    """Return database Path resolved relative to the project root."""
    return Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


def _read_query(sql: str, params=None) -> pd.DataFrame:
    """Execute a safe read-only query with automatic closing."""
    db_path = _get_db_path()
    with sqlite3.connect(db_path, check_same_thread=False, timeout=5) as conn:
        conn.execute("PRAGMA busy_timeout = 5000")  # wait up to 5s if locked
        return pd.read_sql(sql, conn, params=params or [])


def _write_query(sql: str, params=None) -> bool:
    """Execute a safe write query with minimal lock time and retry mechanism."""
    db_path = _get_db_path()

    for attempt in range(3):  # retry up to 3 times
        try:
            with sqlite3.connect(db_path, check_same_thread=False, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("BEGIN IMMEDIATE")  # lock only during commit
                conn.execute(sql, params or [])
                conn.commit()
            return True

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < 2:
                time.sleep(1.5)  # short delay before retry
            else:
                raise
    return False


# =========================================================
# 🔍 Search Tags
# =========================================================
def search_tags(limit: int = 1000) -> Optional[str]:
    """
    Search for tags and return the selected Object_Tag.
    Does not perform any editing.
    """
    # --- Initialize session state ---
    st.session_state.setdefault("search_results", None)
    st.session_state.setdefault("selected_tag", None)

    # --- Search filters ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_tag = st.text_input("Tag:").strip()
    with col2:
        search_father = st.text_input("Father Tag:").strip()
    with col3:
        search_unit = st.text_input("Unit:").strip()
    with col4:
        search_train = st.text_input("Train:").strip()

    # --- Perform search ---
    if st.button("🔎 Search"):
        conditions, params = [], []

        if search_tag:
            conditions.append("Object_Tag LIKE ?")
            params.append(f"{search_tag}%")
        if search_father:
            conditions.append("Father_Tag LIKE ?")
            params.append(f"{search_father}%")
        if search_unit:
            conditions.append("Unit_Code = ?")
            params.append(search_unit)
        if search_train:
            conditions.append("Train = ?")
            params.append(search_train)

        if not conditions:
            st.warning("Enter at least one search criterion.")
            return None

        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM objects WHERE {where_clause} ORDER BY Object_Tag LIMIT ?"
        params.append(limit)

        try:
            df = _read_query(sql, params)
            st.session_state.search_results = df
        except Exception as e:
            st.error(f"Database query failed: {e}")
            return None

    # --- Display results ---
    df = st.session_state.search_results
    if df is not None and not df.empty:
        st.success(f"Found {len(df)} record(s).")
        st.dataframe(df, use_container_width=True)

        tag_list = df["Object_Tag"].tolist()
        default_index = (
            tag_list.index(st.session_state.selected_tag)
            if st.session_state.selected_tag in tag_list
            else 0
        )

        selected_tag = st.selectbox(
            "Select a tag to continue:",
            tag_list,
            index=default_index,
            key="selected_tag_box",
        )

        st.session_state.selected_tag = selected_tag
        return selected_tag

    else:
        st.info("Search for a tag to display results.")
        return None


# =========================================================
# 🛠️ Edit Existing Tag
# =========================================================

def edit_tag(tag: str, username: str, pc_user: str):
    if not tag:
        return

    # --- Header ---
    st.markdown("---")
    st.markdown(
        f"""
        <h5 style="
            color:#1E3A8A;
            font-weight:700; 
            margin-top:10px;
            margin-bottom:15px;
        ">
            🛠️ Edit Tag: {tag}
        </h5>
        """,
        unsafe_allow_html=True,
    )

    # --- Retrieve record ---
    df = _read_query("SELECT * FROM objects WHERE Object_Tag = ?", [tag])
    if df.empty:
        st.warning("Tag not found.")
        return

    record = df.iloc[0]

    # --- Dropdown values ---
    def get_unique_values(column):
        sql = f"""
            SELECT DISTINCT {column}
            FROM objects
            WHERE {column} IS NOT NULL AND TRIM({column}) != ''
        """
        return _read_query(sql)[column].dropna().astype(str).sort_values().tolist()

    category_options = get_unique_values("Category_Desc")
    mih_options = get_unique_values("MIHLevel_Desc")
    unit_options = get_unique_values("Unit_Code")
    train_options = get_unique_values("Train")
    object_types = get_unique_values("Object_Type")
    all_tags = (
        _read_query("SELECT Object_Tag FROM objects")["Object_Tag"]
        .dropna()
        .astype(str)
        .sort_values()
        .tolist()
    )
    criticality_options = ["Vital", "Critical", "Secondary"]

    # =========================================================
    # 1️⃣  EDITABLE FORM (collect new values but DO NOT SAVE)
    # =========================================================

    col1, col2, col3, col4 = st.columns([0.2, 0.3, 0.3, 0.2])
    updated_data = {}

    with col1:
        pass

    for i, col in enumerate(df.columns):
        if col in ["Registered", "Modified"]:
            continue

        current_val = str(record[col]) if pd.notna(record[col]) else ""
        container = (col2 if i % 2 == 0 else col3)

        with container:
            # Dropdown fields
            if col == "Criticality_Desc":
                updated_data[col] = st.selectbox(
                    "Criticality:",
                    criticality_options,
                    index=criticality_options.index(current_val)
                    if current_val in criticality_options
                    else 0,
                    key=f"{tag}_{col}",
                )

            elif col == "Category_Desc":
                updated_data[col] = st.selectbox(
                    "Category:",
                    category_options,
                    index=category_options.index(current_val)
                    if current_val in category_options
                    else 0,
                    key=f"{tag}_{col}",
                )

            elif col == "MIHLevel_Desc":
                updated_data[col] = st.selectbox(
                    "MIH Level:",
                    mih_options,
                    index=mih_options.index(current_val)
                    if current_val in mih_options
                    else 0,
                    key=f"{tag}_{col}",
                )

            elif col == "Unit_Code":
                updated_data[col] = st.selectbox(
                    "Unit:",
                    unit_options,
                    index=unit_options.index(current_val)
                    if current_val in unit_options
                    else 0,
                    key=f"{tag}_{col}",
                )

            elif col == "Train":
                updated_data[col] = st.selectbox(
                    "Train:",
                    train_options,
                    index=train_options.index(current_val)
                    if current_val in train_options
                    else 0,
                    key=f"{tag}_{col}",
                )

            elif col == "Object_Type":
                opts = [current_val] + [o for o in object_types if o != current_val] + [
                    "<Type your own>"
                ]
                selected = st.selectbox(
                    "Object Type:", opts, index=0, key=f"{tag}_{col}"
                )
                updated_data[col] = (
                    st.text_input(
                        "Enter custom type:",
                        value=current_val,
                        key=f"text_{tag}_{col}",
                    )
                    if selected == "<Type your own>"
                    else selected
                )

            elif col == "Father_Tag":
                updated_data[col] = st.selectbox(
                    "Father Tag:",
                    all_tags,
                    index=all_tags.index(current_val)
                    if current_val in all_tags
                    else 0,
                    key=f"{tag}_{col}",
                )

            else:
                label = {
                    "Object_Tag": "Tag:",
                    "Long_Tag": "Long Tag:",
                    "Object_Note": "Special Object Note:",
                }.get(col, col)
                updated_data[col] = st.text_input(
                    label, current_val, key=f"{tag}_{col}"
                )

    with col4:
        pass

    # --- Registered / Modified ---
    col_d, col_a, col_b, col_c = st.columns([0.2, 0.3, 0.3, 0.2])
    with col_a:
        st.text_input("Registered", str(record.get("Registered", "")), disabled=True)
    with col_b:
        st.text_area(
            "Modified",
            str(record.get("Modified", "")),
            disabled=True,
            height=100,
        )

    # =========================================================
    # 2️⃣ DETECT CHANGES (but DO NOT SAVE YET)
    # =========================================================
    changes = {
        c: (str(record[c]), str(new_val))
        for c, new_val in updated_data.items()
        if str(new_val).strip() != str(record[c]).strip()
    }



    # =========================================================
    # 💾 SAVE CHANGES (Auto-Apply Cascading Updates)
    # =========================================================
    if st.button("💾 Save Changes", key=f"save_{tag}"):

        if not changes:
            st.info("No changes detected.")
            return

        # Detect rename
        # Detect rename and force uppercase for new object tag
        old_tag = changes["Object_Tag"][0].strip() if "Object_Tag" in changes else None
        new_tag_value = (
            changes["Object_Tag"][1].strip().upper()
            if "Object_Tag" in changes else None
        )

        # Also update the edited form value so it is saved uppercase
        if "Object_Tag" in updated_data:
            updated_data["Object_Tag"] = updated_data["Object_Tag"].strip().upper()

        father_count = 0
        long_count = 0
        df_fathers = pd.DataFrame()
        df_long_exact = pd.DataFrame()

        # =========================================================
        # 1️⃣ Detect dependent Father_Tag and Long_Tag rows
        # =========================================================
        if old_tag and new_tag_value and old_tag != new_tag_value:

            # --- Father_Tag references ---
            sql_father = "SELECT Object_Tag FROM objects WHERE Father_Tag = ?"
            df_fathers = _read_query(sql_father, [old_tag])
            father_count = len(df_fathers)

            # --- Long_Tag references ---
            sql_long = "SELECT Object_Tag, Long_Tag FROM objects WHERE Long_Tag LIKE ?"
            df_long = _read_query(sql_long, [f"%{old_tag}%"])

            df_long_exact = df_long[
                df_long["Long_Tag"].apply(
                    lambda lt: old_tag in [seg.strip() for seg in str(lt).split("/")]
                )
            ]
            long_count = len(df_long_exact)

        # =========================================================
        # 2️⃣ Update modification log
        # =========================================================
        new_entry = f"{username} ({pc_user}) | {datetime.today().strftime('%d-%m-%Y')}"
        old_mod = str(record.get("Modified", "")) if pd.notna(record.get("Modified")) else ""
        updated_data["Modified"] = old_mod + "\n" + new_entry if old_mod else new_entry

        # =========================================================
        # 3️⃣ UPDATE objects.TABLE (Main Record)
        # =========================================================
        sql = f"""
            UPDATE objects
            SET {', '.join([f'{c} = ?' for c in updated_data.keys()])}
            WHERE Object_Tag = ?
        """
        _write_query(sql, list(updated_data.values()) + [tag])

        # =========================================================
        # 4️⃣ Update job_reports if tag changed
        # =========================================================
        if old_tag and new_tag_value and old_tag != new_tag_value:
            sql_up = """
                UPDATE job_reports
                SET Object_Tag = ?
                WHERE Object_Tag = ?
            """
            _write_query(sql_up, [new_tag_value, old_tag])

        # =========================================================
        # 5️⃣ Update Father_Tag references
        # =========================================================
        if father_count > 0:
            sql_up_father = """
                UPDATE objects
                SET Father_Tag = ?
                WHERE Father_Tag = ?
            """
            _write_query(sql_up_father, [new_tag_value, old_tag])

        # =========================================================
        # 6️⃣ Update Long_Tag references
        # =========================================================
        if long_count > 0:
            for idx, row in df_long_exact.iterrows():
                obj = row["Object_Tag"]
                lt = row["Long_Tag"]

                # Replace ONLY the matching segment
                parts = [seg.strip() for seg in lt.split("/")]
                updated_lt = "/".join([new_tag_value if p == old_tag else p for p in parts])

                sql_up_long = """
                    UPDATE objects
                    SET Long_Tag = ?
                    WHERE Object_Tag = ?
                """
                _write_query(sql_up_long, [updated_lt, obj])


        # =========================================================
        # 7️⃣ Success Messages
        # =========================================================
        st.success(f"Tag '{tag}' updated successfully.")

        if old_tag and new_tag_value and old_tag != new_tag_value:
            st.info(f"🔁 Updated Object_Tag in job_reports table.")

            st.info(
                f"📌 Father_Tag updated: **{father_count} record(s)**\n"
                f"📌 Long_Tag updated: **{long_count} record(s)**"
            )

        st.markdown(
            "<div style='background:#F9F9F9;border:1px solid #CCC;"
            "border-radius:8px;padding:10px 15px;margin-top:10px;'>"
            "<b>📝 Change Details:</b><br>",
            unsafe_allow_html=True,
        )

        for c, (old, new) in changes.items():
            st.markdown(f"- **{c}**: '{old}' → **{new}**")

        st.markdown("</div>", unsafe_allow_html=True)
        st.info(f"🕒 Modification recorded as: `{new_entry}`")

    # ====# =========================================================
    # 🗑️ REMOVE TAG SECTION (Popup Confirmation)
    # =========================================================
    st.markdown("---")
    st.markdown(
        f"""
        <h5 style='color:#8B0000; font-weight:700; margin-bottom:5px;'>
            🗑️ Remove Tag: {tag}
        </h5>
        <p style='color:#444; margin-top:-10px;'>
            Use this option ONLY if this equipment is no longer used.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ========== Delete Button (opens dialog) ==========
    if st.button("❌ Delete This Tag", key=f"open_delete_dialog_{tag}"):

        # --------- Load dependency data before opening popup ---------
        sql_father = "SELECT Object_Tag FROM objects WHERE Father_Tag = ?"
        df_father_children = _read_query(sql_father, [tag])
        father_count = len(df_father_children)

        sql_jobs = "SELECT COUNT(*) AS cnt FROM job_reports WHERE Object_Tag = ?"
        df_jobs = _read_query(sql_jobs, [tag])
        reports_count = int(df_jobs['cnt'].iloc[0])

        # ========== POPUP DIALOG ==========
        @st.dialog(f"⚠️ Confirm Delete: {tag}")
        def delete_confirm_dialog():

            st.markdown(
                f"""
                <div style='text-align:center; font-size:16px;'>
                    <p>You are about to <b style='color:#b30000;'>PERMANENTLY delete</b>:</p>
                    <p style='font-size:18px;'><b>{tag}</b></p>
                </div>

                **Dependency Summary:**
                - Child tags depending on this: **{father_count}**
                - job_reports entries: **{reports_count}**

                """,
                unsafe_allow_html=True
            )

            if father_count > 0:
                st.info("Dependent tags (not deleted automatically):")
                st.dataframe(df_father_children, use_container_width=True)

            col_ok, col_cancel = st.columns([3,1])

            with col_ok:
                if st.button("YES, Delete Now", key=f"confirm_delete_{tag}"):

                    try:
                        sql_delete = "DELETE FROM objects WHERE Object_Tag = ?"
                        _write_query(sql_delete, [tag])

                        st.success(f"Tag '{tag}' deleted successfully.")

                        st.markdown(
                            f"""
                            **Impact Summary**  
                            • Removed from objects table  
                            • Dependent Father_Tag records: **{father_count}** (unchanged)  
                            • job_reports entries: **{reports_count}** (unchanged) 

                            _Note: job_reports table was NOT modified._
                            """,
                            unsafe_allow_html=True
                        )


                    except Exception as e:
                        st.error(f"Error deleting tag: {e}")




        # >>>>>>>>>>>>> IMPORTANT FIX <<<<<<<<<<<<<<
        delete_confirm_dialog()

# =========================================================
# ➕ Add New Tag
# =========================================================
def add_new_tag(username: str, pc_user: str):
    """
    Add a new Object_Tag to the database.
    Records username, PC name, and date in Registered/Modified fields.
    """
    st.markdown("---")
    st.markdown("<h3>➕ Add New Tag</h3>", unsafe_allow_html=True)

    # --- Dropdown data ---
    def get_unique_values(column):
        sql = f"SELECT DISTINCT {column} FROM objects WHERE {column} IS NOT NULL AND TRIM({column}) != ''"
        return _read_query(sql)[column].dropna().astype(str).sort_values().tolist()

    category_options = get_unique_values("Category_Desc")
    mih_options = get_unique_values("MIHLevel_Desc")
    unit_options = get_unique_values("Unit_Code")
    train_options = get_unique_values("Train")
    object_types = get_unique_values("Object_Type")
    all_tags = _read_query("SELECT Object_Tag FROM objects")["Object_Tag"].dropna().astype(str).sort_values().tolist()

    col1, col2 = st.columns(2)
    new_data = {}

    # --- Left Column ---
    with col1:
        new_data["Object_Tag"] = st.text_input("Tag:", key="new_Object_Tag")
        new_data["Father_Tag"] = st.selectbox("Father Tag:", [""] + all_tags, key="new_Father_Tag")
        new_data["Category_Desc"] = st.selectbox("Category:", [""] + category_options, key="new_Category_Desc")
        new_data["MIHLevel_Desc"] = st.selectbox("MIH Level:", [""] + mih_options, key="new_MIHLevel_Desc")
        new_data["Unit_Code"] = st.selectbox("Unit:", [""] + unit_options, key="new_Unit_Code")
        new_data["Train"] = st.selectbox("Train:", [""] + train_options, key="new_Train")

    # --- Right Column ---
    with col2:
        options_with_custom = [""] + object_types + ["<Type your own>"]
        selected_type = st.selectbox("Object Type:", options_with_custom, key="new_Object_Type")

        if selected_type == "<Type your own>":
            typed_type = st.text_input("Enter custom type:", key="new_Object_Type_custom")
            new_data["Object_Type"] = typed_type.strip() if typed_type else ""
        else:
            new_data["Object_Type"] = selected_type

        new_data["Long_Tag"] = st.text_input("Long Tag:", key="new_Long_Tag")
        new_data["Object_Note"] = st.text_input("Special Object Note:", key="new_Object_Note")
        new_data["Criticality_Desc"] = st.selectbox(
            "Criticality:", [""] + ["Vital", "Critical", "Secondary"], key="new_Criticality_Desc"
        )

    # --- Registration Info ---
    today_str = datetime.today().strftime("%d-%m-%Y")
    user_entry = f"{username} ({pc_user}) | {today_str}"
    new_data["Registered"] = user_entry

    # --- Save Button ---
    if st.button("💾 Add Tag"):
        if not new_data["Object_Tag"].strip():
            st.warning("Tag field is required.")
            return

        new_data["Object_Tag"] = new_data["Object_Tag"].upper()

        # Check duplicate
        existing = _read_query("SELECT 1 FROM objects WHERE Object_Tag = ?", [new_data["Object_Tag"]])
        if not existing.empty:
            st.error("This Tag already exists in the database.")
            return

        # Insert record
        try:
            columns = ", ".join(new_data.keys())
            placeholders = ", ".join(["?"] * len(new_data))
            sql = f"INSERT INTO objects ({columns}) VALUES ({placeholders})"
            _write_query(sql, list(new_data.values()))

            st.success(f"✅ Tag '{new_data['Object_Tag']}' added successfully.")
            st.info(f"🕒 Registered as: `{user_entry}`")

        except Exception as e:
            st.error(f"Failed to add new tag: {e}")


