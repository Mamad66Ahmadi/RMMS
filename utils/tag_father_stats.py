# utils/tag_helpers.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

def get_father_and_recent_count(tag: str, record_date: str) -> tuple[str, int]:
    """
    Return (father_tag_display, recent_30d_count) for the given Object_Tag.
    Counts all records of father + children within 30 days ending at the given record_date.
    Handles same-level (father == unit) logic automatically.
    """
    if not tag or not record_date:
        return ("-", 0)

    db_uri = f"file:{DB_PATH}?mode=ro&cache=shared"

    try:
        record_dt = datetime.strptime(str(record_date), "%Y-%m-%d").date()
        start_date = record_dt - timedelta(days=30)

        with sqlite3.connect(db_uri, uri=True, timeout=5, check_same_thread=False) as conn:
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

            # 1️⃣ Get father tag, unit, and long tag
            info = conn.execute("""
                SELECT Father_Tag, Unit_Code, Long_Tag
                FROM objects
                WHERE Object_Tag = ?
                LIMIT 1
            """, (tag,)).fetchone()

            if not info:
                return ("-", 0)

            father_tag, unit, long_tag = info

            # 2️⃣ Determine display and pattern logic
            if father_tag and unit and father_tag == unit:
                father_display = tag
                pattern = long_tag or ""
            else:
                father_display = father_tag or "-"
                if long_tag and "/" in long_tag:
                    pattern = long_tag.rsplit("/", 1)[0]
                else:
                    pattern = long_tag or ""

            like_pattern = pattern + "%"

            # 3️⃣ Count all records of father group between start_date and record_date
            cur = conn.execute("""
                SELECT COUNT(*) 
                FROM job_reports jr
                INNER JOIN objects o ON o.Object_Tag = jr.Object_Tag
                WHERE (o.Long_Tag = ? OR o.Long_Tag LIKE ?)
                AND jr.date BETWEEN ? AND ?
            """, (pattern, like_pattern, start_date.isoformat(), record_dt.isoformat()))

            count_30d = cur.fetchone()[0] or 0

            return (father_display, count_30d)

    except Exception as e:
        print(f"⚠️ Error in get_father_and_recent_count({tag}, {record_date}): {e}")
        return ("-", 0)
