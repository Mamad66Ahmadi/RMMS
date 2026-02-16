import streamlit as st
import pandas as pd
import sqlite3
import time
from pathlib import Path
import urllib.parse



# =========================================================
# 📂 Database Configuration
# =========================================================
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "daily_jobs.db"


# =========================================================
# 🔹 Function 1: Display Object Information Section
# =========================================================
def render_object_info_section(active_tag: str, obj_info: dict, username: str, is_admin: bool):
    """Display detailed object information and allow editing for admins."""

    if not obj_info:
        return

    with st.expander(f"📋 Object Details: {active_tag}", expanded=False):

        # --- Object Details Card ---
        specs_html = f"""
        <div style="
            background:#ffffff;
            border:1px solid #cccccc;
            border-radius:10px;
            padding:15px 20px;
            margin:10px 0;
            box-shadow:0 2px 6px rgba(0,0,0,0.05);
            font-size:14px;
            line-height:1.6;
        ">
            <b>🧾 Description:</b> {obj_info.get('Description', '-')}<br>
            <b>🏷️ Category:</b> {obj_info.get('Category', '-')}<br>
            <b>⚙️ Type:</b> {obj_info.get('Type', '-')}<br>
            <b>🚦 Criticality:</b> {obj_info.get('Criticality', '-')}<br>
            <b>🏗️ MIH Level:</b> {obj_info.get('MIH Level', '-')}<br>
            <b>📦 Unit:</b> {obj_info.get('Unit', '-')} — 
            <b>Train:</b> {obj_info.get('Train', '-')}<br>
            <b>🔗 Father Tag:</b> {obj_info.get('Father Tag', '-')}<br>
            <b>🧩 Long Tag:</b> {obj_info.get('Long Tag', '-')}<br>
            <b>🕒 Registered:</b> {obj_info.get('Registered', '-')}<br>
            <b>✏️ Modified:</b> {obj_info.get('Modified', '-')}<br>
            <b>🗒️ Notes:</b> {obj_info.get('Note', '-')}
        </div>
        """
        st.markdown(specs_html, unsafe_allow_html=True)

        # --- Admin Section ---
        if is_admin:
            if st.button("✏️ Edit This Tag", key=f"edit_{active_tag}"):
                # Toggle edit mode for this tag
                st.session_state[f"edit_mode_{active_tag}"] = not st.session_state.get(
                    f"edit_mode_{active_tag}", False
                )

            # Lazy import to prevent circular dependency
            from utils.tag_modification import edit_tag
            import getpass
            import platform

            # Identify current PC user
            pc_user = getpass.getuser() or platform.node()

            # Display edit form when edit mode is active
            if st.session_state.get(f"edit_mode_{active_tag}", False):
                edit_tag(active_tag, username, pc_user)


# =========================================================
# 🔹 Function 2: Display Route Information Section
# =========================================================



# ✅ Reuse same CSS styling from your Route_Detail page
TABLE_CSS = """
<style>
table {
    width: 100%;
    table-layout: fixed;
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid #ddd;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 12px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    border-radius: 8px;
    overflow: hidden;
}
th {
    background-color: #CFCBCE;
    color: #333;
    font-weight: 600;
    text-align: center !important;
    padding: 10px;
    border-bottom: 1px solid #ddd;
}
td {
    padding: 10px;
    text-align: center;
    border-bottom: 1px solid #3C3C3D;
    vertical-align: middle;
    background-color: #fff;
}
tr:hover td {
    background-color: #f7fbfd;
}
th:nth-child(3), td:nth-child(3) {
    width: 45%;
    text-align: left !important;
    word-wrap: break-word;
    white-space: normal;
}
th, td {
    border-right: 1px solid #f0f0f0;
}
th:last-child, td:last-child {
    border-right: none;
}
</style>
"""


def render_route_section(active_tag: str, username: str = "", name: str = "", department: str = ""):
    """Display all PM routes associated with the selected object tag (styled + clickable)."""

    with st.expander(f"Routes for {active_tag}", expanded=False):

        if st.button("🔄 Load Route Data", key=f"load_routes_{active_tag}"):
            max_attempts = 3
            delay = 1.5

            for attempt in range(max_attempts):
                try:
                    db_uri = f"file:{DB_PATH}?mode=ro"
                    with sqlite3.connect(db_uri, uri=True, timeout=3) as conn:
                        conn.execute("PRAGMA busy_timeout = 4000")
                        query = """
                            SELECT PMRoute_Code, PMRoute_Desc, StandardJob_Desc
                            FROM routes
                            WHERE Object_Tag = ?
                            ORDER BY PMRoute_Code ASC
                        """
                        df = pd.read_sql_query(query, conn, params=[active_tag])

                    if df.empty:
                        st.warning(f"No routes found for tag **{active_tag}**.")
                    else:
                        # Rename columns
                        df.rename(
                            columns={
                                "PMRoute_Code": "Route Code",
                                "PMRoute_Desc": "Route Description",
                                "StandardJob_Desc": "Standard Job Description",
                            },
                            inplace=True,
                        )

                        # ✅ Make Route Code clickable (exactly like your Route_Detail hyperlinks)
                        def make_clickable(route_code: str):
                            base_params = {
                                "username": username,
                                "name": name,
                                "department": department,
                                "route": route_code,
                            }
                            url = f"/route_details_page?{urllib.parse.urlencode(base_params, quote_via=urllib.parse.quote)}"
                            return f"<a href='{url}' target='_blank' style='color:#1E40AF; text-decoration:none; font-weight:600;'>{route_code}</a>"

                        df["Route Code"] = df["Route Code"].apply(make_clickable)

                        # ✅ Build display table with your exact CSS style
                        st.markdown(TABLE_CSS, unsafe_allow_html=True)
                        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

                    break  # success → exit retry loop

                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_attempts - 1:
                        time.sleep(delay)
                        continue
                    else:
                        st.error(f"Database busy or error: {e}")
                        break

                except Exception as e:
                    st.error(f"Unexpected error while fetching routes: {e}")
                    break
