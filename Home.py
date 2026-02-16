import streamlit as st
import urllib.parse
from datetime import datetime
import utils.auth as auth   # make sure auth.py is in a folder called "utils"
from utils.user_stats import get_user_job_report_count, get_user_top_tags, get_user_recent_jobs
import base64
from pathlib import Path
from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()


today = datetime.today().strftime("%A, %B %d, %Y")
st.markdown(f"<div style='text-align:right; color:#555;'>{today}</div>", unsafe_allow_html=True)





# --- Custom Main Title ---
st.markdown("""
    <h1 style="
        text-align: center;
        color: #1E3A8A;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        margin-bottom: 0px;
        line-height: 1.2;
    ">
        Reporting Maintenance Management System<br>
        <span style="
            font-size: 0.8em;
            color: #2563EB;
            letter-spacing: 3px;
        ">
            (RMMS)
        </span>
    </h1>
    <hr style='border: 1px solid #3B82F6; margin-top: 10px; margin-bottom: 30px;'>
""", unsafe_allow_html=True)



# --- Session state init ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None

# --- Login form ---
if not st.session_state.logged_in:
    st.subheader("🔑 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if auth.verify_user(username, password):
            user_info = auth.get_user_info(username)
            if user_info:
                st.session_state.logged_in = True
                st.session_state.user_info = user_info
                st.success(f"✅ Welcome, {user_info['name'] or user_info['username']}!")
                st.rerun()  # rerun to refresh UI
            else:
                st.error("⚠️ یوزر یا پسورد اشتباه است")
        else:
            st.error("❌ یوزر یا پسورد اشتباه است")

else:
    # --- Show logged-in info ---
    user_info = st.session_state.user_info
    assert user_info is not None

    username = user_info["username"]

    # --- backup $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
    from utils.backup_functions import daily_sqlite_backup, weekly_backup_zip
    weekly_backup_zip()
    daily_sqlite_backup()
    # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

    # --- Layout: Two columns ---
    col_left, col_right = st.columns([2, 3])  # wider left column for info

    # Persian Font
    font_path = Path(__file__).parent / "fonts" / "Vazirmatn-Regular.woff2"
    with open(font_path, "rb") as f:
        font_data = f.read()
    font_base64 = base64.b64encode(font_data).decode()

    with col_left:
        st.markdown(f"""
        <style>
        @font-face {{
            font-family: 'Vazirmatn';
            src: url(data:font/woff2;base64,{font_base64}) format('woff2');
            font-weight: normal;
        }}
        .persian-name {{
            font-family: 'Vazirmatn', sans-serif;
        }}
        </style>

        <div style="
            margin-bottom:20px; 
            padding:15px; 
            border:1px solid #ccc; 
            border-radius:10px; 
            background-color:#f9fafb;
            box-shadow:0 2px 6px rgba(0,0,0,0.05);
            font-family: 'Segoe UI', sans-serif;
            font-size:1em;
            font-weight: 600;
            color: #111;
            line-height:1.5em;
        ">
            <p>👤 <b>User:</b> {user_info['username']}</p>
            <p>📛 <b>Name:</b> <span class="persian-name">{user_info['name']}</span></p>
            <p>🏢 <b>Department:</b> {user_info['department']}</p>
            <p>🆔 <b>Personnel Number:</b> {user_info['personnel_number']}</p>
            <p>🔑 <b>Admin:</b> {"Yes" if user_info['is_admin'] else "No"}</p>
        </div>
        """, unsafe_allow_html=True)


    with col_right:
        top_tags = get_user_top_tags(username)
        counts = get_user_job_report_count(username)
        total_jobs = counts["total"]
        pm_count = counts["pm"]
        cm_count = counts["cm"]

        # --- Build "Most Registered Tags" with clickable hyperlinks ---
        # --- Common query params (include user info) ---
        base_params = {
            "username": user_info.get("username", ""),
            "name": user_info.get("name", ""),
            "department": user_info.get("department", "")
        }

        # --- Build "Most Registered Tags" with clickable hyperlinks ---
        if top_tags:
            tag_html = "".join([
                f'<div style="margin:2px 0; text-align:center;">'
                f'<a href="/Object_Details_page?{urllib.parse.urlencode({**base_params, "tag": tag})}" '
                f'target="_blank" style="color:#1E40AF; font-weight:600; text-decoration:none;">{tag}</a> &nbsp;&nbsp;'
                f'<span style="color:#000000; font-weight:400;">registered</span> &nbsp;&nbsp;'
                f'<span style="color:#047857; font-weight:600;"> {count} </span> &nbsp;&nbsp;'
                f'<span style="color:#000000; font-weight:400;"> times by you</span>&nbsp;'
                f'<span style="color:#003049; font-weight:400;">, PM = </span>'
                f'<span style="color:#450693; font-weight:600;"> {pm_percent}% </span>'
                f'</div>'
                for tag, count, pm_percent in top_tags
            ])
        else:
            tag_html = "<div style='text-align:center; font-size:0.75em; color:gray;'>No reports registered yet.</div>"

        # --- Build "Recent Jobs" with clickable hyperlinks ---
        recent_jobs = get_user_recent_jobs(username)
        if recent_jobs:
            recent_html_parts = []
            for tag, date, job_type in recent_jobs:
                job_type_upper = (job_type or "").strip().upper()
                if "PM" in job_type_upper:
                    color = "#6D28D9"
                elif "CM" in job_type_upper:
                    color = "#8B0000"
                else:
                    color = "#000000"

                tag_url = urllib.parse.urlencode({**base_params, "tag": tag})
                recent_html_parts.append(
                    f'<div style="margin:2px 0; text-align:center;">'
                    f'<a href="/Object_Details_page?{tag_url}" '
                    f'target="_blank" style="color:#1E40AF; font-weight:600; text-decoration:none;">{tag}</a> &nbsp;'
                    f'<span style="color:{color};">({job_type})</span> &nbsp;'
                    f'<span style="color:#6B7280;">[{date}]</span>'
                    f'</div>'
                )
            recent_html = "".join(recent_html_parts)
        else:
            recent_html = "<div style='text-align:center; font-size:0.8em; color:gray;'>No recent jobs found.</div>"


        # --- Combined summary box ---
        st.write(f"""
        <div style="
            margin-bottom:20px; 
            padding:15px; 
            border:1px solid #ccc; 
            border-radius:10px; 
            background-color:#EBEBEB;
            box-shadow:0 2px 6px rgba(0,0,0,0.05);
            font-family: 'Segoe UI', sans-serif;
            font-size:0.98em;
            font-weight: 600;
            color: #111;
        ">
            🗂️ Total Registered Reports :
            <span style="color:#2563EB;">{total_jobs}</span>
            (<span style="color:#6D28D9;">{pm_count} PM</span> |
            <span style="color:#8B0000;">{cm_count} CM</span>)
            <hr style="margin:5px 0; border:0.5px solid #ccc;">
            🏷️ Most Registered Tags:<br>
            <div style="font-size:0.75em;">
            {tag_html}
            </div>
            <hr style="margin:5px 0; border:0.5px solid #ccc;">
            Recent Jobs:<br>
            <div style="font-size:0.75em;">{recent_html}</div>
        </div>
        """, unsafe_allow_html=True)




    st.markdown("""
        <hr style="
            border: 0; 
            height: 2px; 
            background-color: darkred; 
            margin-top: 5px; 
            margin-bottom: 5px;
        ">
    """, unsafe_allow_html=True)

    
    # --- Encode multiple query params ---
    if user_info is not None:
        query_params = {
            "username": user_info.get("username", ""),
            "name": user_info.get("name", ""),
            "department": user_info.get("department", "")
        }
    else:
        query_params = {
            "username": "",
            "name": "",
            "department": ""
        }
    encoded_params = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
   # st.info(encoded_params)


    st.markdown("""
        <h2 style="color:#780000;">Dashboard Links:</h2>
    """, unsafe_allow_html=True)
    
    # --- Top row ---
    # --- Dashboard Links Section ---
    BOX_WIDTH = "220px"   # uniform width
    BOX_HEIGHT = "50px"   # uniform height

    # --- First row ---
    BOX_WIDTH = "220px"
    BOX_HEIGHT = "50px"

    # --- First row ---
    col1, col2, col7 = st.columns(3)
    with col1:
        pass

    with col2:
        st.markdown(f"""
            <a href='/daily_jobs?{encoded_params}' target="_blank" style="
                display:flex;
                justify-content:center;
                align-items:center;
                background-color:#1E90FF;
                color:white;
                width:{BOX_WIDTH};
                height:{BOX_HEIGHT};
                text-decoration:none;
                border-radius:8px;
                font-weight:600;
                font-size:16px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            " onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">
                Daily Reports
            </a>

        """, unsafe_allow_html=True)

    with col7:
        st.markdown(f"""
            <a href='/Object_Details_page?{encoded_params}' target="_blank" style="
                display:flex;
                justify-content:center;
                align-items:center;
                background-color:#FFA500;
                color:white;
                width:{BOX_WIDTH};
                height:{BOX_HEIGHT};
                text-decoration:none;
                border-radius:8px;
                font-weight:600;
                font-size:16px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            " onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">
                Equipment Details
            </a>
        """, unsafe_allow_html=True)

    st.markdown("""<hr style='border: 0.5px dotted rgba(128,128,128,0.3); margin:10px 0;'>""", unsafe_allow_html=True)

    # --- Second row ---
    col8, col3, col4 = st.columns(3)
    with col8:
        pass

    with col3:
        st.markdown(f"""
            <a href='/routes_page?{encoded_params}' target="_blank" style="
                display:flex;
                justify-content:center;
                align-items:center;
                background-color:#344E41;
                color:white;
                width:{BOX_WIDTH};
                height:{BOX_HEIGHT};
                text-decoration:none;
                border-radius:8px;
                font-weight:600;
                font-size:16px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            " onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">
                Add/Update PM Reports
            </a>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <a href='/cm_report_page?{encoded_params}' target="_blank" style="
                display:flex;
                justify-content:center;
                align-items:center;
                background-color:#03045E;
                color:white;
                width:{BOX_WIDTH};
                height:{BOX_HEIGHT};
                text-decoration:none;
                border-radius:8px;
                font-weight:600;
                font-size:16px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            " onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">
                Add/Update CM Reports
            </a>
        """, unsafe_allow_html=True)

    # --- Admin row ---
    if user_info.get("is_admin", False):
        st.markdown("""<hr style='border: 0.5px dotted rgba(128,128,128,0.3); margin:10px 0;'>""", unsafe_allow_html=True)
        col9, col5, col6 = st.columns(3)
        with col9:
            pass

        with col5:
            st.markdown(f"""
                <a href='/Define_New_Tag?{encoded_params}' target="_blank" style="
                    display:flex;
                    justify-content:center;
                    align-items:center;
                    background-color:purple;
                    color:white;
                    width:{BOX_WIDTH};
                    height:{BOX_HEIGHT};
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:600;
                    font-size:16px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.2);
                    transition: transform 0.2s;
                " onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">
                    Add/Update Tag info
                </a>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
                <a href='/User_Management?{encoded_params}' target="_blank" style="
                    display:flex;
                    justify-content:center;
                    align-items:center;
                    background-color:#228B22;
                    color:white;
                    width:{BOX_WIDTH};
                    height:{BOX_HEIGHT};
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:600;
                    font-size:16px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.2);
                    transition: transform 0.2s;
                " onmouseover="this.style.transform='scale(1.05)';" onmouseout="this.style.transform='scale(1)';">
                    User Management
                </a>
            """, unsafe_allow_html=True)




    st.markdown("""<hr style='border: 0; height: 2px; background-color: darkred; margin:10px 0;'>""", unsafe_allow_html=True)


    

    # --- Logout ---
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()
