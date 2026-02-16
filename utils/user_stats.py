import sqlite3
import time
from pathlib import Path

# --- Database path ---
DB_PATH = Path(__file__).parent.parent / "data" / "daily_jobs.db"


# ============================================================
# 🔹 Utility: Safe SQLite Query Executor (Read-only)
# ============================================================
def _safe_read_query(query: str, params=(), retries: int = 3, delay: float = 1.0):
    """
    Execute a read-only SQLite query with retry handling.
    Returns list of tuples or [] on failure.
    """
    db_uri = f"file:{DB_PATH}?mode=ro"
    for attempt in range(retries):
        try:
            with sqlite3.connect(db_uri, uri=True, timeout=3) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
                continue
            raise
        except Exception:
            return []
    return []


# ============================================================
# 🔹 1. Get Job Report Counts (Total, PM, CM)
# ============================================================
def get_user_job_report_count(username: str, retries: int = 3, delay: float = 1.0) -> dict:
    """
    Return total, PM, and CM job report counts for the given username.
    Supports multi-user access via retry logic.
    """
    if not username:
        return {"total": 0, "pm": 0, "cm": 0}

    query = """
        SELECT 
            COUNT(*) AS total_count,
            SUM(CASE WHEN job_type LIKE '%PM%' THEN 1 ELSE 0 END) AS pm_count,
            SUM(CASE WHEN job_type LIKE '%CM%' THEN 1 ELSE 0 END) AS cm_count
        FROM job_reports
        WHERE registered_by LIKE ?;
    """
    rows = _safe_read_query(query, (f"{username}%",), retries, delay)
    if not rows or not rows[0]:
        return {"total": 0, "pm": 0, "cm": 0}

    total, pm, cm = rows[0]
    return {
        "total": total or 0,
        "pm": pm or 0,
        "cm": cm or 0,
    }


# ============================================================
# 🔹 2. Get Top Tags by Job Count
# ============================================================
def get_user_top_tags(username: str, limit: int = 4, retries: int = 3, delay: float = 1.0):
    """
    Return the top Object_Tags (up to limit) where this user has most job reports.
    Includes PM% per tag.
    """
    if not username:
        return []

    query = """
        SELECT 
            Object_Tag,
            COUNT(*) AS total_count,
            ROUND(SUM(CASE WHEN job_type LIKE '%PM%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pm_percent
        FROM job_reports
        WHERE registered_by LIKE ?
        GROUP BY Object_Tag
        ORDER BY total_count DESC
        LIMIT ?;
    """

    rows = _safe_read_query(query, (f"{username}%", limit), retries, delay)
    return [(r[0], r[1] or 0, r[2] or 0.0) for r in rows] if rows else []


# ============================================================
# 🔹 3. Get Most Recent Jobs by User
# ============================================================
def get_user_recent_jobs(username: str, limit: int = 2, retries: int = 3, delay: float = 1.0):
    """
    Return the most recent job reports (tag, date, job_type) registered by this user.
    Sorted by date and rowid for deterministic ordering.
    """
    if not username:
        return []

    query = """
        SELECT Object_Tag, date, job_type
        FROM job_reports
        WHERE registered_by LIKE ?
        ORDER BY date DESC, rowid DESC
        LIMIT ?;
    """

    rows = _safe_read_query(query, (f"{username}%", limit), retries, delay)
    return [(r[0] or "-", r[1] or "-", r[2] or "-") for r in rows] if rows else []
