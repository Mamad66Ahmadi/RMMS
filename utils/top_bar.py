import streamlit as st
from datetime import datetime
import jdatetime
import os
from pathlib import Path
import base64

def to_persian_digits(number_str: str) -> str:
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    return ''.join(persian_digits[int(ch)] if ch.isdigit() else ch for ch in str(number_str))

def display_top_bar(name: str, department: str):
    """Display the top bar with Gregorian & Jalali dates and user info using Vazirmatn font."""

    # --- Load local font ---
    font_path = Path(__file__).parent.parent / "fonts" / "Vazirmatn-Regular.woff2"
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode()

    # --- Embed the font in CSS ---
    st.markdown(f"""
    <style>
    @font-face {{
        font-family: 'Vazirmatn';
        src: url(data:font/woff2;base64,{font_base64}) format('woff2');
        font-weight: normal;
        font-style: normal;
    }}
    .vazir-topbar {{
        font-family: 'Vazirmatn', sans-serif !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # --- Day of week colors ---
    dow_colors = {
        "Monday": "#b20000",
        "Tuesday": "#36454f",
        "Wednesday": "#a83569",
        "Thursday": "#006400",
        "Friday": "#b27300",
        "Saturday": "#0073b2",
        "Sunday": "#4b0082"
    }

    # --- PC login ---
    try:
        pc_user = os.getlogin()
    except Exception:
        pc_user = "Unknown-PC"

    # --- Dates ---
    today_dt = datetime.today()
    dow = today_dt.strftime("%A")
    dow_color = dow_colors.get(dow, "#000000")
    gregorian_date = today_dt.strftime("%Y/%m/%d")
    gregorian_display = f"<span style='color:{dow_color}; font-weight:bold;'>{dow}</span>: {gregorian_date}"

    jalali_today_obj = jdatetime.date.today()
    jalali_today = f"{jalali_today_obj.year}/{jalali_today_obj.month:02}/{jalali_today_obj.day:02}"
    jalali_today_persian = to_persian_digits(jalali_today)

    # --- Top bar markup (same as before, only added Vazirmatn font class) ---
    st.markdown(
        f"""
        <div class="vazir-topbar" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0px; padding-bottom:2px;">
            <div style="text-align:left; font-size:14px; color:#000000;">
                {gregorian_display} | <span style="color:#001514; font-weight:bold;">{jalali_today_persian}</span>
            </div>
            <div style="text-align:right; font-size:15px;">
                🖥️ {pc_user} | 👤 {name} | 🏢 {department}
            </div>
        </div>
        <hr style="border:1px solid #ccc; margin-top:2px; margin-bottom:5px;">
        """,
        unsafe_allow_html=True
    )
