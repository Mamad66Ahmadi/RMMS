import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "daily_jobs.db")


def get_connection():
    """Open SQLite connection with WAL mode for safe concurrent writes."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "برنامه به پایگاه داده دسترسی ندارد. لطفاً برنامه را دوباره راه‌اندازی کنید. "
            "اتصال شبکه خود را بررسی نمایید یا با مسئول مربوطه تماس بگیرید."
        )
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def add_new_tag(tag: str, father_tag: str, unit: str, special_comment: str, integral_part: str,
                created_by: str, created_date: str) -> bool:
    """
    Insert a new tag into the objects table.
    Returns True if successful, False if tag already exists.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO objects 
            (tag, father_tag, unit, special_comment, integral_part, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tag, father_tag, unit, special_comment, integral_part, created_by, created_date))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Tag already exists
        return False
    finally:
        conn.close()


def get_all_tags():
    """Return a list of all existing tags (for dropdowns, etc)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT tag FROM objects ORDER BY tag")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def search_tags_in_its_table(tag="", father_tag="", unit="", comment="", integral="", q=""):
    """
    Search tags by optional fields or a general free-text query.
    Returns a list of dicts with all tag details, including audit fields.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT tag, father_tag, unit, special_comment, integral_part,
               created_by, created_date, modified_by
        FROM objects
        WHERE 1=1
    """
    params = []

    if tag:
        query += " AND tag LIKE ?"
        params.append(f"%{tag}%")
    if father_tag:
        query += " AND father_tag LIKE ?"
        params.append(f"%{father_tag}%")
    if unit:
        query += " AND unit LIKE ?"
        params.append(f"%{unit}%")
    if comment:
        query += " AND special_comment LIKE ?"
        params.append(f"%{comment}%")
    if integral:
        query += " AND integral_part LIKE ?"
        params.append(f"%{integral}%")
    if q:  # global search across main text fields
        query += " AND (tag LIKE ? OR father_tag LIKE ? OR special_comment LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "tag": r[0],
            "father_tag": r[1],
            "unit": r[2],
            "special_comment": r[3],
            "integral_part": r[4],
            "created_by": r[5],
            "created_date": r[6],
            "modified_by": r[7],
        }
        for r in rows
    ]


def update_tag(tag: str, father_tag: str, unit: str, special_comment: str,
               integral_part: str, modified_by: str) -> bool:
    """
    Update tag details and set modified_by.
    Returns True if row was updated.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE objects
            SET father_tag = ?, unit = ?, special_comment = ?, integral_part = ?,
                modified_by = ?
            WHERE tag = ?
        """, (father_tag, unit, special_comment, integral_part, modified_by, tag))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_tag(tag: str) -> bool:
    """
    Delete a tag from the objects table.
    Returns True if deleted.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM objects WHERE tag = ?", (tag,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
