import pandas as pd
from pathlib import Path
import streamlit as st
import os
import tkinter as tk
from tkinter import filedialog
import platform
import subprocess
import time

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "Object_Folder_Locations.csv"


# --------------------------------------------------------------------
# PICK FOLDER USING TKINTER DIALOG
# --------------------------------------------------------------------
def pick_folder() -> str:
    """
    Open a folder picker dialog and return the selected folder path.
    """
    root = tk.Tk()
    root.withdraw()  # Hide main window
    root.attributes("-topmost", True)  # Bring dialog to front

    folder_selected = filedialog.askdirectory()
    root.destroy()
    return folder_selected


# --------------------------------------------------------------------
# LOAD FOLDER LOCATIONS FOR A TAG
# --------------------------------------------------------------------
def load_folder_locations(tag: str):
    if not CSV_PATH.exists():
        return []

    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
        df.columns = df.columns.str.strip().str.lower()

        if not all(col in df.columns for col in ["object_tag", "folder_name", "folder_path"]):
            return []

        tag = tag.strip().upper()
        filtered = df[df["object_tag"].str.upper() == tag]

        return filtered[["folder_name", "folder_path"]].dropna().to_dict(orient="records")
    except Exception as e:
        st.error(f"⚠️ Error reading folder location CSV: {e}")
        return []


# --------------------------------------------------------------------
# ADD NEW FOLDER TO CSV
# --------------------------------------------------------------------
def add_folder_location(tag: str, folder_name: str, folder_path: str):
    tag = tag.strip().upper()
    folder_name = folder_name.strip()
    folder_path = folder_path.strip()

    # Create CSV if missing
    if not CSV_PATH.exists():
        df = pd.DataFrame(columns=["object_tag", "folder_name", "folder_path"])
        df.to_csv(CSV_PATH, index=False)

    df = pd.read_csv(CSV_PATH, dtype=str)

    # Prevent duplicates (same tag + folder name + folder path)
    exists = ((df["object_tag"].str.upper() == tag) &
              (df["folder_name"].str.strip().str.lower() == folder_name.lower()) &
              (df["folder_path"].str.strip().str.lower() == folder_path.lower())).any()
    if exists:
        st.warning("⚠️ This folder entry is already saved.")
        return

    # Append new row
    new_row = pd.DataFrame({
        "object_tag": [tag],
        "folder_name": [folder_name],
        "folder_path": [folder_path]
    })
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_PATH, index=False)

    st.success("✅ Folder location added successfully!")


# --------------------------------------------------------------------
# OPEN FOLDER (WINDOWS ONLY)
# --------------------------------------------------------------------
def open_folder_windows(path: str):
    path = os.path.normpath(path)
    subprocess.Popen(f'explorer "{path}"')
    time.sleep(0.4)  # Allow explorer to open

    try:
        import win32gui
        import win32con

        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if path.split("\\")[-1].lower() in title.lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)

        win32gui.EnumWindows(enum_handler, None)
    except:
        pass


# --------------------------------------------------------------------
# STREAMLIT UI: PICK AND SAVE FOLDER
# --------------------------------------------------------------------
def render_folder_location_section(tag: str):
    with st.expander(f"📁 Documents for {tag} (Added by users)", expanded=False):

        st.markdown("""<hr style="border:none; border-top:2px solid #fff; margin:10px 0;">""",
            unsafe_allow_html=True)
        # Load saved locations
        locations = load_folder_locations(tag)

        # Display each folder with "Open" button
        #st.markdown("""<hr style="border:none; border-top:1px solid #09476f; margin:5px 0;">""",unsafe_allow_html=True)

        if locations:
            for i, loc in enumerate(locations, start=1):
                st.markdown("""<hr style="border:none; border-top:1px solid #09476f; margin:5px 0;">""",unsafe_allow_html=True)


                name = loc['folder_name'] or "Unnamed"
                st.markdown(f"**{i}. {name}** — `{loc['folder_path']}`")
                cols = st.columns([0.04, 0.7, 0.05])
                with cols[0]:
                    pass

                with cols[1]:
                    if st.button("Open", key=f"open_{i}"):
                        if platform.system() == "Windows":
                            open_folder_windows(loc['folder_path'])
                        else:
                            st.error("Folder opening is only supported on Windows.")
                with cols[2]:
                    if st.button("Delete", key=f"delete_{i}"):
                        confirm_delete_folder(tag, loc['folder_path'], loc['folder_name'])


                #st.markdown("""<hr style="border:none; border-top:1px solid #09476f; margin:5px 0;">""",unsafe_allow_html=True)


        else:
            st.info("No folder locations saved yet.")


        st.markdown("""<hr style="border:none; border-top:4px solid #fff; margin:60px 0;">""",unsafe_allow_html=True)

        st.markdown("""<hr style="border:none; border-top:4px solid #ca2530; margin:5px 0;">""",unsafe_allow_html=True)

        st.markdown("#### ➕ Add a New Folder Location")
        col31, col32 = st.columns([0.5, 0.5])

        with col31:
            # Input for folder name
            folder_name_input = st.text_input("Folder Name")

            # Choose folder button
            if st.button("Choose Folder"):
                folder = pick_folder()
                if folder:
                    st.session_state.selected_folder = folder
                    st.success(f"Selected Folder: {folder}")

            folder_path = st.session_state.get("selected_folder", "")

            # Save folder button
            if st.button("Save Folder Location"):
                if not folder_name_input.strip():
                    st.error("❗ Please enter a folder name.")
                elif not folder_path:
                    st.error("❗ Please choose a folder first.")
                else:
                    add_folder_location(tag, folder_name_input.strip(), folder_path)
                    st.session_state.selected_folder = ""  # Clear after saving
        with col32:
            st.markdown("""
            <div class="persian-box" style="
                border: 2px solid #ca2530;
                background-color: #ffeaea;
                padding: 15px;
                border-radius: 10px;
                font-family: 'Vazirmatn', sans-serif;
                font-weight: bold;
                text-align: right;
                direction: rtl;
                line-height: 1.7;
                color: #000000;
            ">
                <p style='margin-bottom:8px; font-size:15px; color:#ca2530;'> راهنمای وارد کردن مسیر جدید</p>
                <ol style='margin:0; padding-right: 18px; font-size:13px;'>
                    <li>ابتدا <b>نام داکیومنت</b> (دلخواه) مورد نظر خود را وارد کنید.</li>
                    <li>سپس روی دکمه <b>انتخاب پوشه</b> کلیک کرده و مسیر پوشه مورد نظر را انتخاب کنید.</li>
                    <li>در نهایت با فشردن دکمه <b>ذخیره</b>، مسیر انتخاب شده به لیست پوشه‌ها اضافه خواهد شد.</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("""<hr style="border:none; border-top:4px solid #ca2530; margin:5px 0;">""",unsafe_allow_html=True)

# --------------------------------------------------------------------
# DELETE FOLDER LOCATION
# --------------------------------------------------------------------
def delete_folder_location(tag: str, folder_path: str, folder_name: str):
    """Remove a folder entry from the CSV for a given tag, path, and name."""
    if not CSV_PATH.exists():
        return

    df = pd.read_csv(CSV_PATH, dtype=str)

    # Normalize paths for comparison
    folder_path_norm = os.path.normpath(folder_path).replace("\\", "/").lower()
    df["folder_path_norm"] = df["folder_path"].str.strip().str.replace("\\", "/").str.lower()
    df["folder_name_norm"] = df["folder_name"].fillna("").str.strip().str.lower()

    # Filter out the entry to delete
    mask = ~((df["object_tag"].str.upper() == tag.strip().upper()) &
             (df["folder_path_norm"] == folder_path_norm) &
             (df["folder_name_norm"] == folder_name.strip().lower()))

    df = df[mask].drop(columns=["folder_path_norm", "folder_name_norm"])
    df.to_csv(CSV_PATH, index=False)
    st.success("✅ Folder location deleted successfully!")



# --------------------------------------------------------------------
# DELETE FOLDER LOCATION WITH CONFIRMATION DIALOG (PRETTIER & BILINGUAL)
# --------------------------------------------------------------------
def confirm_delete_folder(tag: str, folder_path: str, folder_name: str):
    """Show a confirmation dialog before deleting a folder entry."""
    
    @st.dialog(f"⚠️ Confirm Delete: {folder_name or folder_path}")
    def delete_confirm_dialog():
        st.markdown(
            f"""
            <div style="
                text-align:center;
                font-size:16px;
                padding:15px;
                border-radius:10px;
                background-color:#fff3f3;
                border:2px solid #ff4d4d;
                margin-bottom:15px;
            ">
                <p style='font-size:20px; font-weight:bold; color:#b30000;'>⚠️ Are you sure?</p>
                 <p>شما در حال حذف مسیر زیر هستید:</p>
                <p>You are about to <b style='color:#b30000;'>delete</b> the following folder location:</p>
                <p style='font-size:18px;'><b>{folder_name}</b> — <code>{folder_path}</code></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Buttons side by side
        col1, col2 = st.columns([0.75, 0.25])
        with col1:
            if st.button("✅ Confirm Delete"):
                delete_folder_location(tag, folder_path, folder_name)
                st.rerun()  # Refresh page after deletion
        with col2:
            if st.button("❌ Cancel"):
                st.info("Deletion cancelled")
                st.rerun()  # Refresh page after deletion


    # Call the dialog so it actually appears
    delete_confirm_dialog()
