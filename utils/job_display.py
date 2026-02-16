import streamlit as st
import jdatetime
from datetime import datetime
import html as _html  # for HTML escaping
from pathlib import Path


def render_job_row(job: dict):
    """
    Render a single job report in two columns:
    - Left: main info (color-coded by job type & day name)
    - Right: Job description (RTL + LTR compatible with Persian font)
    """

    # Helper to safely escape text for HTML
    def esc(val, default="-"):
        if val is None:
            return default
        s = str(val)
        return _html.escape(s) if s.strip() != "" else default

    # --- Parse date and compute day name + Persian date ---
    date_str_raw = job.get("date")
    day_name, persian_date = "", ""

    try:
        dt = datetime.strptime(str(date_str_raw), "%Y-%m-%d")
        day_name = dt.strftime("%A")
        jdt = jdatetime.date.fromgregorian(date=dt.date())
        persian_date = f"{jdt.year}/{jdt.month:02}/{jdt.day:02}"
    except Exception:
        pass

    # 🎨 Unique color for each day of week
    day_colors = {
        "Sunday": "#C0392B",     # Red
        "Monday": "#27AE60",     # Green
        "Tuesday": "#2980B9",    # Blue
        "Wednesday": "#8E44AD",  # Purple
        "Thursday": "#D35400",   # Orange
        "Friday": "#2C3E50",     # Dark Gray
        "Saturday": "#021FA0"    # Teal
    }
    day_color = day_colors.get(day_name, "#333333")

    # --- Job type color ---
    job_type = str(job.get("job_type", "")).strip().upper()
    job_color = "#006400" if job_type == "PM" else "#e27d3d" if job_type == "CM" else "#333333"

    # --- Action list indicator ---
    action_list = bool(job.get("action_list"))
    action_html = (
        "<span style='color:#ca2530; font-weight:bold;'>Yes</span>"
        if action_list else
        "<span style='color:gray;'>No</span>"
    )
    # --- Anomaly indicator ---
    anomaly_list = bool(job.get("anomaly"))
    anomaly_html = (
        "<span style='color:#ca2530; font-weight:bold;'>Yes</span>"
        if anomaly_list else
        "<span style='color:gray;'>No</span>"
    )

    # Escape all fields that will be interpolated into HTML
    date_str = esc(date_str_raw)
    persian_date_html = esc(persian_date)
    object_tag = esc(job.get("Object_Tag"))
    department = esc(job.get("department"))
    wo_number = esc(job.get("wo_number"))
    permit_number = esc(job.get("permit_number"))
    status = esc(job.get("status"))
    performed_action = esc(job.get("performed_action"))
    keywords = esc(job.get("keywords"))
    employee = esc(job.get("employee"))
    registered_by = esc(job.get("registered_by"))
    registered_date = esc(job.get("registered_date"))
    route_code = esc(job.get("route"))

    # --- Two columns layout ---
    col_left, col_right = st.columns([2, 3])

    with col_left:
        # Only include Route Code for PM
        route_html = ""
        if job_type == "PM":
            route_html = (
                f"<b style='color:#0b1c48;'>Route Code:</b> "
                f"<span style='color:#004d40;'>{route_code}</span><br>"
            )

        st.markdown(f"""
        <div style="
            background-color:#FFFFFF;
            border:2px solid #ccc;
            border-radius:12px;
            padding:15px 18px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
            font-family:'Segoe UI', sans-serif;
            font-size:14px;
            line-height:1.7;
        ">
            <b style='color:#0b1c48;'>Date:</b> {date_str} 
            <span style='color:{day_color};'>({_html.escape(day_name)})</span><br>
            <b style='color:#0b1c48;'>Persian Date:</b> 
            <span style='direction:rtl; unicode-bidi:plaintext;'>{persian_date_html}</span><br>
            <b style='color:#0b1c48;'>Object Tag:</b> {object_tag}<br>
            <b style='color:#0b1c48;'>Department:</b> {department}<br>
            <b style='color:#0b1c48;'>W.O. Number:</b> {wo_number}<br>
            <b style='color:#0b1c48;'>Permit Number:</b> {permit_number}<br>
            <b style='color:#0b1c48;'>Status:</b> {status}<br>
            <b style='color:#0b1c48;'>Action List:</b> {action_html}<br>
            <b style='color:#0b1c48;'>Anomaly:</b> {anomaly_html}<br>
            <b style='color:#0b1c48;'>Performed Action:</b> {performed_action}<br>
            <b style='color:#0b1c48;'>Keywords:</b> {keywords}<br>
            <b style='color:#0b1c48;'>Employee:</b> {employee}<br>
            <b style='color:#0b1c48;'>Registered By:</b> {registered_by}<br>
            <b style='color:#0b1c48;'>Registered Date:</b> {registered_date}<br>
            <b style='color:#0b1c48;'>Job Type:</b> 
            <span style='color:{job_color}; font-weight:bold;'>{_html.escape(job.get("job_type", ""))}</span>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        # Description: escape first, then allow <br> for line breaks
        desc_raw = job.get("job_description", "") or ""
        desc_html = _html.escape(str(desc_raw)).replace("\n", "<br>")
        st.markdown(f"""
        <div style="
            font-weight:bold; 
            margin-bottom:8px; 
            color: #0b1c48; 
            font-size:1em; 
        ">
            Job Description:
        </div>
        <div style="
            background-color:#FFFFFF;
            font-family: 'Vazirmatn', sans-serif;
            border-radius: 12px; 
            padding:15px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            direction: rtl; 
            unicode-bidi: plaintext;
            text-align: right;
            line-height:1.5em;
            font-size:0.95em;
        ">
            {desc_html}
        </div>
        """, unsafe_allow_html=True)

        import base64
        font_path = Path(__file__).parent.parent / "fonts" / "Vazirmatn-Bold.woff2"
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()

        st.markdown(f"""
        <style>
        @font-face {{
            font-family: 'Vazirmatn';
            src: url(data:font/woff2;base64,{font_base64}) format('woff2');
            font-weight: bold;
        }}
        .persian-box {{
            font-family: 'Vazirmatn', sans-serif;
            border: 2px solid #ff4b4b;
            background-color: #ffeaea;
            padding: 12px 15px;
            border-radius: 10px;
            color: #000000;
            font-weight: bold;
            text-align: right;
            direction: rtl;
            line-height: 1.8;
            font-size: 11px;  /* 👈 Add this line */
            margin-top: 20px;

        }}
        </style>

        <div class="persian-box">
        تنها یک هفته بعد از وارد یک ریپورت فرصت دارید آن را حذف یا ویرایش کنید.  
        بعد از این بازه زمانی، این کار تنها توسط ادمین امکان‌پذیر است.
        </div>
        """, unsafe_allow_html=True)


