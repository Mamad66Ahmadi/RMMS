import streamlit as st
from pathlib import Path
import base64
from utils.route_search import show_route_search
from utils.top_bar import display_top_bar



st.set_page_config(page_title="PM Report", layout="wide")
from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()


# --- Helpers ---
def qp_first(key: str, default: str = "Unknown") -> str:
    """Get the first value of a query param."""
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

# --- Main Function ---
def main():
    # --- Get query params ---
    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")


    # --- Display top bar ---
    display_top_bar(name, department)
    st.title("🛠️ Route & PPM Management")

    st.markdown("""
<style>
/* Target all expanders */
.stExpander {
    background-color: #EFFBF9;  /* very light blue */
    border-radius: 8px;          /* optional: rounded corners */
}

</style>
""", unsafe_allow_html=True)

    with st.expander("➕ **Add** a new **PPM** job report", expanded=False):
        selected_route = show_route_search(username,name,department)

        if selected_route is not None:
            st.write("✅ Selected route details:")
            st.json(selected_route.to_dict())

    st.markdown("<hr style='border:3px solid green;'>", unsafe_allow_html=True)

    


    
    # --- Read font file ---
    font_path = Path(__file__).parent.parent / "fonts" / "Vazirmatn-Bold.woff2"
    with open(font_path, "rb") as f:
        font_data = f.read()
    font_base64 = base64.b64encode(font_data).decode()

    # --- Apply font to Persian box ---
    st.markdown(f"""
    <style>
    @font-face {{
        font-family: 'Vazirmatn';
        src: url(data:font/woff2;base64,{font_base64}) format('woff2');
        font-weight: bold;
    }}
    .persian-box {{
        font-family: 'Vazirmatn', sans-serif;
        border: 2px solid #599d9c;
        background-color: #b7bda920;
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
    فهرست کارهای تعمیرات پیشگیرانه (PM) که اخیراً توسط واحد شما انجام شده است، در جدول زیر نمایش داده شده است.
    </div>
    """, unsafe_allow_html=True)


    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)



    from utils.pm_grouped_table import show_grouped_pm_table

    DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

    #st.markdown("<hr style='border:2px solid green;'>", unsafe_allow_html=True)

    show_grouped_pm_table(
        DB_PATH,
        {
            "username": username,
            "name": name,
            "department": department,
        }
    )





if __name__ == "__main__":
    main()
