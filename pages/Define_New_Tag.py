import streamlit as st
from utils.top_bar import display_top_bar
import os
from utils.tag_modification import search_tags, edit_tag, add_new_tag


# --- Helpers ---
def qp_first(key: str, default: str = "Unknown") -> str:
    """Get the first value of a query param."""
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default


# --- Main Function ---
def main():
    st.set_page_config(page_title="Tag Modification", layout="wide")
    from utils.left_navigation_bar_lock import lock_navigation_bar
    lock_navigation_bar()

    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")

    try:
        pc_user = os.getlogin()
    except Exception:
        pc_user = "Unknown-PC"

    if username == "Unknown" or not username.strip():
        st.warning("⚠️ You should log in first.")
        st.markdown(
            "<a href='/' style='font-size:16px; color:blue; text-decoration:underline;'>⬅️ Go to Log-in Page</a>",
            unsafe_allow_html=True
        )
        return

    display_top_bar(name, department)
    st.title("🏷️ Tag Management")

    # --- Editable Section ---
    with st.expander("✏️ **Edit** a Tag Info", expanded=False):
        selected_tag = search_tags()
        #tag_modification.search_tags_box()
        if selected_tag:
            edit_tag(selected_tag, username=username, pc_user=pc_user)
    
    with st.expander("➕ **Add** a new Tag", expanded=False):
        add_new_tag(username=username, pc_user=pc_user)  # call add function

if __name__ == "__main__":
    main()
