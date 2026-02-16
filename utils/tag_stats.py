import sqlite3
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from typing import Optional


# --- Database path ---
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


# ==========================================================
# 🔹 Function 1: Fetch job counts (now with PM ratio)
# ==========================================================
def get_job_counts(
    tag: str,
    father_tag: Optional[str] = None,
    long_tag: Optional[str] = None,
    unit: Optional[str] = None,
    train: Optional[str] = None,
):
    """
    Return job stats for:
      - current tag
      - parent long-tag group
      - unit+train group

    Each entry in results is a tuple:
        (total, month, year, pm_total, pm_year)

    where:
        total     = all-time job count
        month     = jobs in last 30 days
        year      = jobs in last 365 days
        pm_total  = %PM of all jobs (all-time)
        pm_year   = %PM of jobs in last 365 days
    """
    if not tag:
        return {}

    db_uri = f"file:{DB_PATH}?mode=ro&cache=shared"

    now = datetime.now()
    month_ago = (now - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    year_ago = (now - pd.Timedelta(days=365)).strftime("%Y-%m-%d")

    results = {}
    DEFAULT = (0, 0, 0, 0.0, 0.0)

    # ------------------------------------------------------
    # Common SELECT fragment (only differs by WHERE/JOIN)
    # ------------------------------------------------------
    TAG_SQL = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN date >= ? THEN 1 ELSE 0 END) AS month,
            SUM(CASE WHEN date >= ? THEN 1 ELSE 0 END) AS year,

            ROUND(
                100.0 * SUM(CASE WHEN job_type = 'PM' THEN 1 ELSE 0 END) /
                NULLIF(COUNT(*), 0),
            1) AS pm_total,

            ROUND(
                100.0 *
                SUM(CASE WHEN date >= ? AND job_type = 'PM' THEN 1 ELSE 0 END) /
                NULLIF(
                    SUM(CASE WHEN date >= ? THEN 1 ELSE 0 END),
                0),
            1) AS pm_year
        FROM job_reports
        WHERE Object_Tag = ?
    """

    LONG_SQL = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN jr.date >= ? THEN 1 ELSE 0 END) AS month,
            SUM(CASE WHEN jr.date >= ? THEN 1 ELSE 0 END) AS year,

            ROUND(
                100.0 * SUM(CASE WHEN jr.job_type = 'PM' THEN 1 ELSE 0 END) /
                NULLIF(COUNT(*), 0),
            1) AS pm_total,

            ROUND(
                100.0 *
                SUM(CASE WHEN jr.date >= ? AND jr.job_type = 'PM' THEN 1 ELSE 0 END) /
                NULLIF(
                    SUM(CASE WHEN jr.date >= ? THEN 1 ELSE 0 END),
                0),
            1) AS pm_year
        FROM job_reports jr
        INNER JOIN objects o ON o.Object_Tag = jr.Object_Tag
        WHERE o.Long_Tag = ? OR o.Long_Tag LIKE ?
    """

    UNIT_SQL = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN jr.date >= ? THEN 1 ELSE 0 END) AS month,
            SUM(CASE WHEN jr.date >= ? THEN 1 ELSE 0 END) AS year,

            ROUND(
                100.0 * SUM(CASE WHEN jr.job_type = 'PM' THEN 1 ELSE 0 END) /
                NULLIF(COUNT(*), 0),
            1) AS pm_total,

            ROUND(
                100.0 *
                SUM(CASE WHEN jr.date >= ? AND jr.job_type = 'PM' THEN 1 ELSE 0 END) /
                NULLIF(
                    SUM(CASE WHEN jr.date >= ? THEN 1 ELSE 0 END),
                0),
            1) AS pm_year
        FROM job_reports jr
        INNER JOIN objects o ON o.Object_Tag = jr.Object_Tag
        WHERE o.Unit_Code = ? AND o.Train = ?
    """

    # ------------------------------------------------------
    # Main DB access with retry
    # ------------------------------------------------------
    for attempt in range(3):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=5, check_same_thread=False) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")

                cur = conn.cursor()

                # 1) TAG
                cur.execute(
                    TAG_SQL,
                    (month_ago, year_ago, year_ago, year_ago, tag)
                )
                results["tag"] = cur.fetchone() or DEFAULT

                # 2) LONG GROUP (father / parent tree)
                if long_tag:
                    if father_tag and unit and father_tag == unit:
                        base_pattern = long_tag
                    else:
                        base_pattern = long_tag.rsplit("/", 1)[0] if "/" in long_tag else long_tag
                    like_pattern = base_pattern + "%"

                    cur.execute(
                        LONG_SQL,
                        (month_ago, year_ago, year_ago, year_ago, base_pattern, like_pattern)
                    )
                    results["long_group"] = cur.fetchone() or DEFAULT
                else:
                    results["long_group"] = DEFAULT

                # 3) UNIT + TRAIN
                if unit and train:
                    cur.execute(
                        UNIT_SQL,
                        (month_ago, year_ago, year_ago, year_ago, unit, train)
                    )
                    results["unit_train"] = cur.fetchone() or DEFAULT
                else:
                    results["unit_train"] = DEFAULT

            break  # success → exit retry loop

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 2:
                time.sleep(1 + attempt)
                continue
            st.error(f"DB Error (job counts): {e}")
            results.setdefault("tag", DEFAULT)
            results.setdefault("long_group", DEFAULT)
            results.setdefault("unit_train", DEFAULT)
            break

    return results

# ==========================================================
# 🔹 Function 2: Render stats boxes (with PM ratio)
# ==========================================================
def render_job_stats_section(active_tag: str, obj_info: dict, stats: dict):
    """
    Render three job statistics boxes:
      - Tag Activity
      - Parent Long Tag Group Activity
      - Unit & Train Activity
    Each includes PM percentage.
    """
    tag_total, tag_month, tag_year, tag_pm_total, tag_pm_year = stats.get("tag", (0,0,0,0.0,0.0))
    long_total, long_month, long_year, long_pm_total, long_pm_year = stats.get("long_group", (0,0,0,0.0,0.0))
    unit_total, unit_month, unit_year, unit_pm_total, unit_pm_year = stats.get("unit_train", (0,0,0,0.0,0.0))


    father_tag = obj_info.get("Father Tag") if obj_info else None
    unit_tag = obj_info.get("Unit") if obj_info else None

    # ✅ Same rule as in your Object-Details section:
    # if father == unit → show Object Tag instead of Father Tag
    if father_tag and unit_tag and father_tag == unit_tag:
        parent_display = active_tag
    else:
        parent_display = (
            father_tag
            or (obj_info.get("Long Tag").rsplit("/", 1)[0]
                if obj_info.get("Long Tag") and "/" in obj_info.get("Long Tag")
                else "-")
        )

    col4, col5, col6 = st.columns(3)




    def stat_box(title, total, year, month, pm_total, pm_year, color):
        return f"""
        <div style="
            background:#ececec;
            color:#003366;
            padding:12px 18px;
            border-radius:10px;
            font-size:16px;
            font-weight:600;
            border:2px solid {color};
            box-shadow:0 3px 10px rgba(0,0,0,0.08);
            margin-bottom:15px;
            text-align:center;">
            {title}<br>
            <span style='font-size:13px; color:#333;'>
                Total: <b>{total}</b> |
                Yearly: <b>{year}</b> |
                Monthly: <b>{month}</b><br>
                <span style='color:#006400;'>PM Total Ratio: <b>{pm_total}%</b> | PM Year Ratio: <b>{pm_year}%</b></span>
            </span>
        </div>
        """

    with col4:
        st.markdown(
            stat_box(
                f"📊 Tag ({active_tag}) Counts:",
                tag_total, tag_year, tag_month, tag_pm_total, tag_pm_year,
                "#173F5F"
            ),
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            stat_box(
                f"🧩 Parent Group ({parent_display}) Counts:",
                long_total, long_year, long_month, long_pm_total, long_pm_year,
                "#20639B"
            ),
            unsafe_allow_html=True,
        )

    with col6:
        st.markdown(
            stat_box(
                "Unit & Train Counts:",
                unit_total, unit_year, unit_month, unit_pm_total, unit_pm_year,
                "#3CAEA3"
            ),
            unsafe_allow_html=True,
        )
