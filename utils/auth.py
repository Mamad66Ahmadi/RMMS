import sqlite3
import hashlib
import hmac
import os

# --- Safe DB path (always relative to this file, not cwd) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "daily_jobs.db")

def get_connection():
    """Open a SQLite connection with concurrency optimizations.
    If the DB file is missing, raise a clear error in Persian.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "،برنامه به پایگاه داده دسترسی ندارد. لطفاً برنامه را دوباره راه‌اندازی کنید" 
            ".اتصال شبکه خود را بررسی نمایید یا با مسئول مربوطه تماس بگیرید"
        )

    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")    # Enable Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL;")  # Faster but safe writes
        return conn
    except sqlite3.Error as e:
        raise RuntimeError(
            f"خطا در اتصال به پایگاه داده: {str(e)}"
        )

# --- Password hashing/verification ---
def hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt, hashed = stored_password.split(":")
    except ValueError:
        return False
    check_hash = hashlib.sha256((salt + provided_password).encode()).hexdigest()
    return hmac.compare_digest(hashed, check_hash)


# --- User functions ---
def register_user(username: str, password: str, name="", department="", personnel_number="", is_admin=0) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        hashed_pw = hash_password(password)
        cur.execute("""
            INSERT INTO users (username, password, name, department, personnel_number, is_admin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, hashed_pw, name, department, personnel_number, is_admin))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success


def verify_user(username: str, password: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False
    return verify_password(row[0], password)


def search_users(username="", name="", personnel="", department=""):
    """
    Search users by optional fields.
    Returns a list of dicts with columns: username, name, department, personnel, is_admin
    """
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT username, name, department, personnel_number, is_admin FROM users WHERE 1=1"
    params = []

    if username:
        query += " AND username LIKE ?"
        params.append(f"%{username}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if personnel:
        query += " AND personnel_number LIKE ?"
        params.append(f"%{personnel}%")
    if department:
        query += " AND department LIKE ?"
        params.append(f"%{department}%")

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "username": r[0],
            "name": r[1],
            "department": r[2],
            "personnel": r[3],
            "is_admin": bool(r[4])
        }
        for r in rows
    ]


def update_user(username: str, name: str = None, department: str = None, personnel: str = None, is_admin: int = None):
    """Update user info in the database based on username."""
    conn = get_connection()
    cur = conn.cursor()

    updates = []
    params = []

    if name is not None:
        updates.append("name=?")
        params.append(name)
    if department is not None:
        updates.append("department=?")
        params.append(department)
    if personnel is not None:
        updates.append("personnel_number=?")
        params.append(personnel)
    if is_admin is not None:
        updates.append("is_admin=?")
        params.append(is_admin)

    if not updates:
        conn.close()
        return  # Nothing to update

    sql = f"UPDATE users SET {', '.join(updates)} WHERE username=?"
    params.append(username)

    cur.execute(sql, tuple(params))
    conn.commit()
    conn.close()


def change_password(username: str, new_password: str):
    """Change the password for a user."""
    conn = get_connection()
    cur = conn.cursor()
    hashed_pw = hash_password(new_password)
    cur.execute("UPDATE users SET password=? WHERE username=?", (hashed_pw, username))
    conn.commit()
    conn.close()


def delete_user(username: str) -> bool:
    """Delete a user by username."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        success = cur.rowcount > 0
    except Exception as e:
        print("Delete error:", e)
        success = False
    finally:
        conn.close()
    return success


def get_user_info(username: str):
    """Retrieve full info for a single user."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, name, department, personnel_number, is_admin FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "username": row[0],
            "name": row[1],
            "department": row[2],
            "personnel_number": row[3],
            "is_admin": row[4]
        }
    return None
