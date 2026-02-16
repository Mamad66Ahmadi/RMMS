# ===========================================
# 📦 Daily Safe SQLite Backup (ZIP with real DB file, keep last 3 backups)
# ===========================================
import sqlite3
import datetime
import zipfile
from pathlib import Path
import streamlit as st


def daily_sqlite_backup(keep_days: int = 3):

    # Paths
    db_path = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"
    backup_root = Path(__file__).resolve().parents[1] / "backups"
    backup_root.mkdir(exist_ok=True)

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # ZIP file name
    zip_file = backup_root / f"daily_backup_{today_str}.zip"

    # skip if already exists
    if zip_file.exists():
        return

    # ---------------------------------------------
    # Create safe backup into a temporary .db file
    # ---------------------------------------------
    temp_backup_db = backup_root / f"temp_daily_backup.db"

    try:
        src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        dst = sqlite3.connect(temp_backup_db)
        src.backup(dst)    # safe even with many concurrent users
        dst.close()
        src.close()
    except Exception as e:
        st.warning(f"Daily SQLite backup failed: {e}")
        return

    # ---------------------------------------------
    # Put this .db file into ZIP, then delete temp
    # ---------------------------------------------
    try:
        with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(temp_backup_db, arcname="daily_jobs_backup.db")
    except Exception as e:
        st.warning(f"ZIP creation failed: {e}")
        return
    finally:
        try:
            temp_backup_db.unlink()
        except:
            pass

    # ---------------------------------------------
    # Cleanup old daily ZIP backups (keep last 3)
    # ---------------------------------------------
    files = sorted(
        [f for f in backup_root.iterdir() if f.is_file() and f.suffix == ".zip"],
        key=lambda x: x.name
    )

    if len(files) > keep_days:
        for f in files[:-keep_days]:
            try:
                f.unlink()
            except:
                pass
# ============================================================
# 📦 Weekly Backup (ZIP): copy oldest daily ZIP 
# Output name = SAME as daily ZIP name
# Keeps last 3 weekly backups
# ============================================================
import shutil
import datetime
from pathlib import Path
import streamlit as st


def weekly_backup_zip():

    base_path   = Path(__file__).resolve().parents[1]
    daily_root  = base_path / "backups"
    weekly_root = base_path / "weekly_backup"

    weekly_root.mkdir(exist_ok=True)

    today = datetime.date.today()

    # ------------------------------------------------------------
    # 1) Get all weekly backup ZIPs
    # ------------------------------------------------------------
    weekly_files = sorted(
        [f for f in weekly_root.iterdir() if f.is_file() and f.suffix == ".zip"],
        key=lambda x: x.name
    )

    # ------------------------------------------------------------
    # 2) Check last weekly backup date (7-day rule)
    # ------------------------------------------------------------
    for f in weekly_files:
        try:
            # extract date from name: daily_backup_2025-11-18.zip
            date_str = f.name.replace("daily_backup_", "").replace(".zip", "")
            file_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            continue

        if (today - file_date).days < 7:
            return  # weekly backup already done within last 7 days → skip

    # ------------------------------------------------------------
    # 3) Find the *oldest* daily backup file
    # ------------------------------------------------------------
    daily_files = sorted(
        [f for f in daily_root.iterdir() if f.is_file() and f.name.startswith("daily_backup_")],
        key=lambda x: x.name
    )

    if not daily_files:
        return  # No daily backups exist

    oldest_daily_zip = daily_files[0]   # 🎯 always the oldest based on date

    # ------------------------------------------------------------
    # 4) Copy oldest daily ZIP into weekly folder
    #    → weekly backup name = SAME name as daily file
    # ------------------------------------------------------------
    target_zip = weekly_root / oldest_daily_zip.name   # SAME NAME

    try:
        shutil.copy2(oldest_daily_zip, target_zip)
    except Exception as e:
        st.warning(f"Weekly backup failed: {e}")
        return

    # ------------------------------------------------------------
    # 5) KEEP ONLY LAST 3 WEEKLY BACKUPS
    # ------------------------------------------------------------
    weekly_files = sorted(
        [f for f in weekly_root.iterdir() if f.is_file() and f.suffix == ".zip"],
        key=lambda x: x.name
    )

    if len(weekly_files) > 3:
        old_files = weekly_files[:-3]
        for f in old_files:
            try:
                f.unlink()
            except:
                pass
