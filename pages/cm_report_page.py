import streamlit as st
from utils.top_bar import display_top_bar
from utils.job_form import render_add_job_section
from pathlib import Path
import base64

st.set_page_config(page_title="CM Report", layout="wide")
from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()

# --- Helpers ---
def qp_first(key: str, default: str = "Unknown") -> str:
    """Get the first value of a query param."""
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

# --- Global Styles ---
st.markdown("""
<style>
.stExpander { background-color: #F5FBFF; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- Main Function ---
def main():
    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")

    display_top_bar(name, department)
    st.title("🛠️ Register a CM job report")

    # --- Add Job Section ---
    with st.expander("➕ **Add** a new **CM** job report", expanded=False):
        st.session_state["show_last_job"] = True
        render_add_job_section(user_department=department, user_name=username)


    st.markdown("<hr style='border:2px solid red;'>", unsafe_allow_html=True)

    # --- Persian notice ---
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
    }}
    </style>

    <div class="persian-box">
    تنها یک هفته بعد از وارد یک ریپورت فرصت دارید آن را حذف یا ویرایش کنید.  
    بعد از این بازه زمانی، این کار تنها توسط ادمین امکان‌پذیر است.
    </div>
    """, unsafe_allow_html=True)


    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)


    with st.expander("✏️ **Edit** a **CM** job report", expanded=False):
        pass
    
    with st.expander("➖ **Remove** a **CM** job report", expanded=False):
        pass

if __name__ == "__main__":
    main()
