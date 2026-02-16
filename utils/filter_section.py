# utils/filter_section.py
import streamlit as st
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import time
from utils.Select_options_function import get_department_options


# ======================================================
# 🔹 DB Helpers
# ======================================================
def _read_query(DB_PATH, sql, params=None, max_attempts=5):
    """
    Safe concurrency-friendly SQLite reader with retry + busy_timeout.
    """
    params = params or []

    db_uri = f"file:{DB_PATH}?mode=ro"

    for attempt in range(max_attempts):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=5) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA read_uncommitted = 1")
                return pd.read_sql_query(sql, conn, params=params, index_col=None)

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(0.25)
                continue
            else:
                raise e

    return pd.DataFrame()



def get_saved_user_filter(DB_PATH, username: str):
    db_uri = f"file:{DB_PATH}?mode=ro"

    for attempt in range(5):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=4) as conn:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA busy_timeout = 3000")
                conn.execute("PRAGMA read_uncommitted = 1")

                cur = conn.cursor()
                cur.execute("SELECT user_filter FROM users WHERE username = ?", (username,))
                row = cur.fetchone()

                if row and row[0]:
                    try:
                        return json.loads(row[0])
                    except:
                        return None
                return None

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(0.2)
                continue
            else:
                raise e

    return None


def save_user_filter(DB_PATH, username: str, data: dict | None):
    """
    Safe writer with short transaction and retry.
    """
    for attempt in range(6):
        try:
            with sqlite3.connect(DB_PATH, timeout=5) as conn:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA busy_timeout = 5000")

                conn.execute("BEGIN IMMEDIATE")   # request write lock safely

                cur = conn.cursor()

                if data:
                    cur.execute(
                        "UPDATE users SET user_filter = ? WHERE username = ?",
                        (json.dumps(data), username),
                    )
                else:
                    cur.execute(
                        "UPDATE users SET user_filter = NULL WHERE username = ?",
                        (username,)
                    )

                conn.commit()
                return True

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(0.25)
                continue
            else:
                raise e

    return False



# ===================================================================
# 🔍 MAIN: RENDER FILTERS + BUILT QUERY + RETURN FILTERED DATAFRAME
# ===================================================================
def render_filter_and_query(DB_PATH: str, username: str, user_department: str):
    """
    Renders the full filter UI + executes SQL + returns filtered df.
    """

    # ======================================================
    # Load saved defaults from DB (only once)
    # ======================================================
    saved = get_saved_user_filter(DB_PATH, username)

    if saved and "filters_loaded" not in st.session_state:
        for k, v in saved.items():
            st.session_state[k] = v
        st.session_state.filters_loaded = True

    # ======================================================
    # Default values (last 7 days)
    # ======================================================

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

    # If user is from these → default to their department
    # Else (Utility, Process, Method, HSE, Lab, Admin…) → show ALL
    default_department_filter = (
        user_department if user_department in MAINT_DEPTS else "All"
    )

    # ======================================================
    # Default values (last 7 days)
    # ======================================================
    today = datetime.today().date()
    seven_days = today - timedelta(days=7)

    default_filter = {
        "date_from": seven_days,
        "date_to": today,
        "job_type": "All",
        "department_filter": default_department_filter,
        "wo_filter": "",
        "permit_filter": "",
        "actual_start_filter": None,
        "tag_filter": "",
        "father_tag_filter": "",
        "unit_filter": "",
        "train_filter": "",
        "keyword_filter": "",
        "recent_days": "",
    }



    # Initialize into session_state
    for k, v in default_filter.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ======================================================
    # 🔍 FILTER UI
    # ======================================================

    with st.expander("🔍 Filter Job Records", expanded=False):

        # ======================================================
        # 🔹 First Row: Dates, Job Type, WO, Department, Keyword, Tag
        # ======================================================
        col1, col2, col_recent, col3, col4, col5, col6, col14 = st.columns(
            [1, 1, 1, 0.6, 1, 1, 1, 1]
        )

        with col1:
            date_from = st.date_input(
                "From Date",
                value=None
            )

        with col2:
            date_to = st.date_input(
                "To Date",
                value=None
            )

        with col_recent:
            recent_days = st.text_input(
                "Recent Days",
                value=st.session_state.recent_days,
                placeholder="e.g. 7",
                help="Recent Days works mainly for saved default filters. \
                For temporary filters it may not apply if From/To dates are already set.\
                این فیلتر بیشتر برای ذخیره فیلترهای پیش‌فرض استفاده می‌شود. \
                در فیلترهای موقت، اگر تاریخ شروع یا پایان وارد شده باشد، ممکن است اعمال نشود."
            )

        with col3:
            job_type = st.selectbox(
                "Job Type",
                ["All", "PM", "CM"],
                index=["All", "PM", "CM"].index(st.session_state.job_type)
            )

        with col4:
            department_options = get_department_options()
            if user_department and user_department not in department_options:
                department_options.append(user_department)

            department_filter = st.selectbox(
                "Department",
                ["All"] + department_options,
                index=(["All"] + department_options).index(st.session_state.department_filter)
                if st.session_state.department_filter in department_options else 0
            )

        with col5:
            wo_filter = st.text_input(
                "WO/PPM (contains)",
                st.session_state.wo_filter
            )

        with col6:
            permit_filter = st.text_input(
                "Permit Number (contains)",
                st.session_state.permit_filter
            )

        with col14:
            actual_start_filter = st.date_input(
                "Actual Start Date",
                value=None
            )


        # ======================================================
        # 🔹 Second Row: Tag, Father Tag, Unit, Train, Keyword
        # ======================================================
        col7, col8, col9, col10, col11 = st.columns(
            [1, 1, 0.55, 0.55, 3]
        )

        with col7:
            tag_filter = st.text_input(
                "Object Tag (contains)",
                st.session_state.tag_filter,
                placeholder="e.g. 103-K-101,103-K-201",
                help="You can enter one or more tags separated by commas, e.g. 103-K-101,103-K-201"
            )

        with col8:
            father_tag_filter = st.text_input(
                "Father Tag (contains)",
                st.session_state.father_tag_filter,
                placeholder="e.g. 103-K-101,103-K-201",
                help="You can enter one or more tags separated by commas, e.g. 103-K-101,103-K-201"
            )

        with col9:
            unit_filter = st.text_input(
                "Unit",
                st.session_state.unit_filter,
                placeholder="e.g. 103,106",
                help="You can enter one or more units separated by commas, e.g. 103,106"
            )

        with col10:
            train_filter = st.text_input(
                "Train",
                st.session_state.train_filter,
                placeholder="e.g. 1,2,3",
                help="You can enter one or more trains separated by commas, e.g. 1,2"
            )

        with col11:
            keyword_filter = st.text_input(
                "Keyword/Description (contains)",
                st.session_state.keyword_filter
            )


        colA, colB, colC, colD = st.columns([1, 4, 1, 1])
        apply_btn = colA.button("Apply Filters")
        save_default_btn = colC.button("💾 Save as Default")
        reset_btn = colD.button("♻️ Reset Default")

        # ==========================
        # 💾 SAVE DEFAULT (Dialog)
        # ==========================
        if save_default_btn:
            @st.dialog("⚠️ تایید ذخیره فیلترها")
            def confirm_save_default():
                st.markdown("""
                <div class="dialog-persian">
                آیا مطمئن هستید که می‌خواهید فیلترهای فعلی را به عنوان
                <b>فیلتر پیش‌فرض دائمی</b> ذخیره کنید؟  
                از این پس، در زمان باز شدن صفحه، این فیلترها به طور خودکار اعمال خواهند شد.
                </div>
                """, unsafe_allow_html=True)

                col_ok, col_cancel = st.columns(2)
                with col_ok:
                    if st.button("✅ بله، ذخیره شود", use_container_width=True, type="primary"):
                        st.session_state.confirm_save_default = True
                        st.rerun()

                with col_cancel:
                    if st.button("❌ خیر، انصراف", use_container_width=True):
                        st.session_state.confirm_save_default = False
                        st.rerun()

            confirm_save_default()

        # --- After dialog confirmed ---
        if st.session_state.get("confirm_save_default", False):
            to_save = {
                "recent_days": recent_days,
                "job_type": job_type,
                "department_filter": department_filter,
                "wo_filter": wo_filter,
                "permit_filter": permit_filter,
                "actual_start_filter": str(actual_start_filter) if actual_start_filter else None,
                "tag_filter": tag_filter,
                "father_tag_filter": father_tag_filter,
                "unit_filter": unit_filter,
                "train_filter": train_filter,
                "keyword_filter": keyword_filter,
            }
            save_user_filter(DB_PATH, username, to_save)
            st.success("💾 فیلترهای فعلی با موفقیت ذخیره شدند.")
            st.session_state.confirm_save_default = False
            st.rerun()

        # ==========================
        # ♻️ RESET DEFAULT (Dialog)
        # ==========================
        if reset_btn:
            @st.dialog("⚠️ تایید بازگشت به حالت اولیه")
            def confirm_reset_default():
                st.markdown("""
                <div class="dialog-persian">
                آیا از حذف فیلترهای ذخیره‌شده و بازگشت به
                <b>حالت اولیه</b>
                اطمینان دارید؟
                </div>
                """, unsafe_allow_html=True)

                col_ok, col_cancel = st.columns(2)
                with col_ok:
                    if st.button("✅ بله، بازگردان", use_container_width=True, type="primary"):
                        st.session_state.confirm_reset_default = True
                        st.rerun()

                with col_cancel:
                    if st.button("❌ خیر، انصراف", use_container_width=True):
                        st.session_state.confirm_reset_default = False
                        st.rerun()

            confirm_reset_default()

        # --- After dialog confirmed ---
        if st.session_state.get("confirm_reset_default", False):
            save_user_filter(DB_PATH, username, None)

            # Restore defaults to session
            for k, v in default_filter.items():
                st.session_state[k] = v

            st.success("♻️ فیلترهای پیش‌فرض حذف و مقداردهی اولیه شدند.")
            st.session_state.confirm_reset_default = False
            st.rerun()

        # ==========================
        # APPLY → store in session
        # ==========================
        # Track which dates are user-selected
        if "user_set_from_date" not in st.session_state:
            st.session_state.user_set_from_date = False

        if "user_set_to_date" not in st.session_state:
            st.session_state.user_set_to_date = False

        if apply_btn:
            st.session_state.job_type = job_type
            st.session_state.department_filter = department_filter
            st.session_state.wo_filter = wo_filter
            st.session_state.permit_filter = permit_filter
            st.session_state.actual_start_filter = actual_start_filter
            st.session_state.tag_filter = tag_filter
            st.session_state.father_tag_filter = father_tag_filter
            st.session_state.unit_filter = unit_filter
            st.session_state.train_filter = train_filter
            st.session_state.keyword_filter = keyword_filter

            st.session_state.user_set_from_date = date_from is not None
            st.session_state.user_set_to_date   = date_to is not None


            # save values
            st.session_state.date_from = date_from
            st.session_state.date_to = date_to
            st.session_state.recent_days = recent_days    # update recent


    # END OF UI

    # ======================================================
    # Build SQL based on session_state values
    # ======================================================
    q = """
        WITH base AS (
            SELECT job_indx, date, Object_Tag, department, wo_number, permit_number,
                status, actual_start, job_type, performed_action, job_description,
                keywords, registered_by, route, anomaly, action_list
            FROM job_reports
        )
        SELECT 
            b.*,
            (
                SELECT COUNT(*)
                FROM base x
                WHERE x.Object_Tag = b.Object_Tag
                AND x.date <= b.date
                AND x.date >= date(b.date, '-365 day')
            ) AS Count_YTD,
            (
                SELECT COUNT(*)
                FROM base y
                WHERE y.Object_Tag = b.Object_Tag
                AND y.date <= b.date
                AND y.date >= date(b.date, '-30 day')
            ) AS Count_MTD
        FROM base b
        WHERE 1=1
    """


    params = []

    # ======================================================
    # 🧠 SMART DATE LOGIC (Corrected)
    # ======================================================

    # convenience
    s_recent = str(st.session_state.recent_days).strip()

    user_from = st.session_state.user_set_from_date
    user_to   = st.session_state.user_set_to_date

    # -----------------------------------------------------
    # 1) USER selected From/To → PRIORITY
    # -----------------------------------------------------
    if user_from or user_to:
        date_from = st.session_state.date_from if user_from else datetime(1970,1,1).date()
        date_to   = st.session_state.date_to if user_to else datetime.today().date()

    # -----------------------------------------------------
    # 2) USER did NOT select From/To → use recent_days
    # -----------------------------------------------------
    else:
        # If no valid recent_days → use default = 7
        if s_recent.isdigit() and int(s_recent) > 0:
            N = int(s_recent)
        else:
            N = 7
            st.session_state.recent_days = "7"

        date_from = datetime.today().date() - timedelta(days=N)
        date_to   = datetime.today().date()

    # APPLY filter conditions
    q += " AND b.date >= ?"
    params.append(str(date_from))

    q += " AND b.date <= ?"
    params.append(str(date_to))


    # job type
    if st.session_state.job_type != "All":
        q += " AND UPPER(b.job_type) = ?"
        params.append(st.session_state.job_type.upper())

    # department
    if st.session_state.department_filter != "All":
        q += " AND UPPER(b.department) = ?"
        params.append(st.session_state.department_filter.upper())

    # WO
    if st.session_state.wo_filter.strip():
        q += " AND b.wo_number LIKE ?"
        params.append(f"%{st.session_state.wo_filter.strip()}%")

    # permit
    if st.session_state.permit_filter.strip():
        q += " AND b.permit_number LIKE ?"
        params.append(f"%{st.session_state.permit_filter.strip()}%")

    # keyword
    if st.session_state.keyword_filter.strip():
        q += " AND (b.keywords LIKE ? OR b.job_description LIKE ?)"
        params.append(f"%{st.session_state.keyword_filter.strip()}%")
        params.append(f"%{st.session_state.keyword_filter.strip()}%")

    # tag filter(s)
    if st.session_state.tag_filter.strip():
        tags = [t.strip() for t in st.session_state.tag_filter.split(",") if t.strip()]
        cond = " OR ".join(["b.Object_Tag LIKE ?" for _ in tags])
        q += f" AND ({cond})"
        params.extend([f"%{t}%" for t in tags])

    # actual start
    if st.session_state.actual_start_filter:
        q += " AND date(b.actual_start) = ?"
        params.append(str(st.session_state.actual_start_filter))

    # father/unit/train filters → require join with objects table
    join_needed = False
    join_conditions = []
    join_params = []

    # father tag
    if st.session_state.father_tag_filter.strip():
        vals = [v.strip() for v in st.session_state.father_tag_filter.split(",") if v.strip()]
        conds = []
        for v in vals:
            conds.append("(o.Long_Tag = ? OR o.Long_Tag LIKE ?)")
            join_params.extend([v, f"%{v}%"])
        join_conditions.append("(" + " OR ".join(conds) + ")")
        join_needed = True

    # unit
    if st.session_state.unit_filter.strip():
        vals = [v.strip() for v in st.session_state.unit_filter.split(",") if v.strip()]
        conds = " OR ".join(["o.Unit_Code = ?" for _ in vals])
        join_conditions.append("(" + conds + ")")
        join_params.extend(vals)
        join_needed = True

    # train
    if st.session_state.train_filter.strip():
        vals = [v.strip() for v in st.session_state.train_filter.split(",") if v.strip()]
        conds = " OR ".join(["o.Train = ?" for _ in vals])
        join_conditions.append("(" + conds + ")")
        join_params.extend(vals)
        join_needed = True

    if join_needed:
        q = q.replace(
            "FROM base b",
            "FROM base b LEFT JOIN objects o ON o.Object_Tag = b.Object_Tag"
        )
        q += " AND " + " AND ".join(join_conditions)
        params.extend(join_params)


    q += " ORDER BY b.date DESC, b.job_indx DESC LIMIT 150"

    # ======================================================
    # 🔢 Count total matches
    # ======================================================
    count_sql = f"SELECT COUNT(*) AS total FROM ({q})"
    total_df = _read_query(DB_PATH, count_sql, params)

    try:
        total_matches = int(total_df.iloc[0]["total"])
    except:
        total_matches = 0

    # ======================================================
    # RETURN RESULTS
    # ======================================================
    df = _read_query(DB_PATH, q, params)

    return (
        df,
        total_matches,
        st.session_state.date_from,
        st.session_state.date_to,
        st.session_state.job_type,
        st.session_state.wo_filter,
        st.session_state.keyword_filter,
    )
