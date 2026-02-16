import streamlit as st
import pandas as pd
import sqlite3
import time
from pathlib import Path
import urllib.parse
from utils.top_bar import display_top_bar
from utils.PPM_job_form import add_daily_jobs_form



# --- Page Config ---
route_code = st.query_params.get("route", None)
st.set_page_config(
    page_title=f"Route {route_code}" if route_code else "Route Details",
    layout="wide",
)
from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()

# --- Helpers ---
def qp_first(key: str, default: str = "Unknown") -> str:
    """Get the first value of a query param."""
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

# --- Database Helpers ---
def _get_db_path():
    return Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"

def _read_query(sql: str, params=None, retries: int = 3, delay: float = 1.0):
    """Read SQL query with retry logic (no URI mode)."""
    db_path = _get_db_path()

    for attempt in range(retries):
        try:
            with sqlite3.connect(db_path, timeout=2) as conn:
                df = pd.read_sql_query(sql, conn, params=params or [])
                return df

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay)
                continue
            else:
                raise

    return pd.DataFrame()



# --- Main Function ---
def main():
    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")
    display_top_bar(name, department)

    if not route_code:
        st.error("❌ No route specified in the URL.")
        return

    # --- Styled Route Header ---
    st.markdown(f"""
        <style>
            .route-header {{
                background: linear-gradient(90deg, #003366 0%, #0066CC 100%);
                color: white;
                padding: 16px 22px;
                border-radius: 12px;
                font-size: 22px;
                font-weight: bold;
                box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }}
            .route-header .emoji {{
                font-size: 26px;
            }}
            .route-header .code {{
                background-color: #ffffff22;
                padding: 4px 10px;
                border-radius: 8px;
                font-weight: 600;
                color: #FFD700;
            }}
            .route-info {{
                background-color: #f0f8ff;
                border: 1px solid #cce0ff;
                border-radius: 12px;
                padding: 20px 25px;
                margin-top: 10px;
                line-height: 1.8;
                font-size: 16px;
                box-shadow: 0 3px 12px rgba(0,0,0,0.08);
            }}
            .route-info strong {{
                color: #003366;
            }}
            .tag-box {{
                color: #006400;  /* dark green */
                font-weight: 600;
                font-family: monospace;
            }}
            .stExpander {{
                background-color: #EFFBF9;
                border-radius: 8px;
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
                margin-top: 15px;
            }}
        </style>

        <div class="route-header">
            <span class="emoji">🛠️</span>
            Route Details — <span class="code">{route_code}</span>
        </div>
    """, unsafe_allow_html=True)

    # --- Fetch Route Data ---
    query = "SELECT * FROM routes WHERE PMRoute_Code = ?"
    df = _read_query(query, [route_code])
    if df.empty:
        st.warning("⚠️ No data found for this route.")
        return

    # --- Summary Info ---
    route_desc = df["PMRoute_Desc"].mode()[0] if "PMRoute_Desc" in df else "—"
    std_job_desc = df["StandardJob_Desc"].mode()[0] if "StandardJob_Desc" in df else "—"
    tags = sorted(df["Object_Tag"].dropna().unique().tolist()) if "Object_Tag" in df else []

    # 🔗 Build dark-green hyperlink tags (no underline)
    base_params = {"username": username, "name": name, "department": department}
    tag_links = []
    for t in tags:
        params = {**base_params, "tag": t}
        link = f"/Object_Details_page?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
        tag_links.append(
            f"<a href='{link}' target='_blank' class='tag-box' "
            f"style='color:#006400; text-decoration:none; font-weight:600;'>{t}</a>"
        )

    tags_html = ", ".join(tag_links)

    st.markdown(f"""
        <div class="route-info">
            <p><strong>Primary Route Description:</strong> {route_desc}</p>
            <p><strong>Primary Route Standard Job:</strong> {std_job_desc}</p>
            <p><strong>Tags:</strong> {tags_html}</p>
        </div>
    """, unsafe_allow_html=True)



    # --- Link to Last Records Page ---

    params = {
        "route": route_code,
        "name": name,
        "department": department,
        "username": username,
    }

    last_records_url = "/LastRecords?" + urllib.parse.urlencode(
        params,
        quote_via=urllib.parse.quote
    )

    st.markdown(
        f"""
        <div style='text-align:right; margin-top:15px;'>
            <a href="{last_records_url}" target="_self" style="
                background-color:#003366;
                color:white;
                padding:8px 18px;
                text-decoration:none;
                border-radius:8px;
                font-weight:600;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);
            ">
            📌 View Last Records of This Route
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<hr style='border:2px solid red;'>", unsafe_allow_html=True)

    # --- Expanders for Job Actions ---
    # --- Read font once ---
    # font_path = Path(__file__).parent.parent / "fonts" / "Vazirmatn-Bold.woff2"
    # with open(font_path, "rb") as f:
    #     font_data = f.read()
    # font_base64 = base64.b64encode(font_data).decode()

    # def persian_notice(font_base64):
    #     st.markdown(f"""
    #     <style>
    #     @font-face {{
    #         font-family: 'Vazirmatn';
    #         src: url(data:font/woff2;base64,{font_base64}) format('woff2');
    #         font-weight: bold;
    #     }}
    #     .persian-box {{
    #         font-family: 'Vazirmatn', sans-serif;
    #         border: 2px solid #ff4b4b;
    #         background-color: #ffeaea;
    #         padding: 12px 15px;
    #         border-radius: 10px;
    #         color: #000000;
    #         font-weight: bold;
    #         text-align: right;
    #         direction: rtl;
    #         line-height: 1.8;
    #     }}
    #     </style>
    #     <div class="persian-box">
    #     تنها یک هفته بعد از وارد یک ریپورت فرصت دارید آن را حذف یا ویرایش کنید.  
    #     بعد از این بازه زمانی، این کار تنها توسط ادمین امکان‌پذیر است.
    #     </div>
    #     """, unsafe_allow_html=True)

    # --- Expanders ---
    with st.expander("➕ **Add** a new **PPM** job report", expanded=False):
        add_daily_jobs_form(tags, username, name, department, route_code)
        # Your "add job" code goes here

    st.markdown("""
    <hr style="
        border: none;
        border-top: 1px dotted gray;
        margin: 20px 0;
    ">
    """, unsafe_allow_html=True)

    with st.expander("✏️ **Edit** an existing **PPM** job report", expanded=False):
        #persian_notice(font_base64)
        from utils.PPM_edit_form import edit_daily_jobs_form
        edit_daily_jobs_form(tags, username, name, department, route_code)
        # Your "edit job" code goes here



    from utils.auth import get_user_info
    def is_admin(username: str) -> bool:
        """Return True if the user is admin."""
        user = get_user_info(username)
        if not user:
            return False
        return bool(user.get("is_admin", 0))
    if is_admin(username):
        from utils.manage_route_tags import manage_route_tags
        manage_route_tags(route_code, route_desc, std_job_desc, df)


# --- Run ---
if __name__ == "__main__":
    main()
