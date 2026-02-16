import streamlit as st
import pandas as pd
from utils.top_bar import display_top_bar
import utils.auth as auth
from utils.Select_options_function import get_department_options


st.set_page_config(page_title="User Page", layout="wide")

from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()

# --- Helpers ---
def qp_first(key: str, default: str = "Unknown") -> str:
    """Get the first value of a query param."""
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default


def reset_add_user_form():
    """Reset the add user form fields in session state."""
    st.session_state["new_username_val"] = ""
    st.session_state["new_name_val"] = ""
    st.session_state["new_department_val"] = ""
    st.session_state["new_personnel_val"] = ""
    st.session_state["new_password_val"] = ""
    st.session_state["new_is_admin_val"] = False


def display_user_table(users):
    """Display a dataframe of users."""
    df = pd.DataFrame([{
        "username": u["username"],
        "name": u["name"],
        "department": u["department"],
        "personnel": u["personnel"],
        "is_admin": u["is_admin"]
    } for u in users])
    st.dataframe(df, use_container_width=True)


# --- Add User Panel ---
def add_user_panel():
    with st.expander("➕ Add New User", expanded=False):
        col1, col2 = st.columns([1, 1])

        # --- Left: Form ---
        with col1:
            with st.form("add_user_form"):
                new_username = st.text_input("Username", key="new_username")
                new_name = st.text_input("Name", key="new_name")

                # --- Department dropdown (from utils) ---
                department_options = get_department_options()
                new_department = st.selectbox("Department", department_options, key="new_department")

                new_personnel = st.text_input("Personnel Number", key="new_personnel")
                new_password = st.text_input("Password", type="password", key="new_password")
                new_is_admin = st.checkbox("Is Admin", value=False, key="new_is_admin")

                submitted = st.form_submit_button("Add User")

                if submitted:
                    if not all([
                        new_username.strip(),
                        new_name.strip(),
                        new_department.strip(),
                        new_personnel.strip(),
                        new_password.strip()
                    ]):
                        st.warning("⚠️ لطفاً همه فیلدها را پر کنید.")
                    else:
                        success = auth.register_user(
                            username=new_username.strip(),
                            password=new_password.strip(),
                            name=new_name.strip(),
                            department=new_department.strip(),
                            personnel_number=new_personnel.strip(),
                            is_admin=int(new_is_admin)
                        )

                        if success:
                            st.success("✅ کاربر با موفقیت اضافه شد.")
                            display_user_table([{
                                "username": new_username.strip(),
                                "name": new_name.strip(),
                                "department": new_department.strip(),
                                "personnel": new_personnel.strip(),
                                "is_admin": new_is_admin
                            }])
                            reset_add_user_form()
                        else:
                            st.error("⚠️ این نام کاربری قبلاً ثبت شده است.")

        # --- Right: Explanation box (ALWAYS visible, outside form) ---
        with col2:
            st.markdown(
                """
                <div style="
                    background-color: #f9f9f9;
                    padding: 12px;
                    border-radius: 8px;
                    border: 1px solid #ddd;
                    font-size: 12px;
                    line-height: 1.8;
                    direction: rtl;
                    text-align: right;
                    font-family: Tahoma, 'IRANSans', 'Vazir', sans-serif;
                ">
                📝 <b>راهنما:</b><br>
                • نام کاربری باید یکتا باشد.<br>
                • نام و نام خانوادگی کاربر وارد شود.<br>
                • همه فیلدها باید پر شوند.<br>
                • در صورت فعال بودن گزینه <i>Is Admin</i>، کاربر دسترسی مدیریتی خواهد داشت:<br>
                <div style="margin-right:20px; line-height:1.6;">
                    - دسترسی به منوی کاربرها دارد<br>
                    - میتواند Daily Job ها را حذف یا ویرایش کند<br>
                </div>
                </div>
                """,
                unsafe_allow_html=True
            )


# --- Search / Edit / Remove Users Panel ---
def search_user_panel():
    with st.expander("🔍 Edit/Remove Users", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1: search_username = st.text_input("Username", key="search_username")
        with col2: search_name = st.text_input("Name", key="search_name")
        with col3: search_personnel = st.text_input("Personnel No.", key="search_personnel")
        with col4: search_department = st.text_input("Department", key="search_department")

        if st.button("Search"):
            results = auth.search_users(
                username=search_username.strip(),
                name=search_name.strip(),
                personnel=search_personnel.strip(),
                department=search_department.strip(),
            )
            st.session_state.search_results = results
            st.session_state.selected_users = []

        if "search_results" in st.session_state and st.session_state.search_results:
            st.subheader("Found Users")
            selected_users = []
            for u in st.session_state.search_results:
                admin_status = "Yes" if u.get("is_admin") else "No"
                checked = st.checkbox(
                    f"{u['username']} | {u['name']} | {u['personnel']} | {u['department']} | Admin: {admin_status}",
                    key=f"chk_{u['username']}"
                )
                if checked:
                    selected_users.append(u)
            st.session_state.selected_users = selected_users

            # Dotted gray line
            st.markdown("""
            <hr style='border: 0.5px dotted rgba(128,128,128,0.3); margin-top: -5px; margin-bottom: 5px;'>
            """, unsafe_allow_html=True)

            # Edit and Remove buttons next to each other
            edit_clicked = st.button("Edit Selected User")
            remove_clicked = st.button("Remove Selected User(s)")
            
            if edit_clicked:
                if len(st.session_state.selected_users) != 1:
                    st.warning("⚠️ Please select exactly one user to edit.")
                else:
                    st.session_state.edit_user = st.session_state.selected_users[0]
            
            if remove_clicked:
                if not st.session_state.selected_users:
                    st.warning("⚠️ Please select at least one user to remove.")
                else:
                    for u in st.session_state.selected_users:
                        auth.delete_user(u["username"])
                    st.success(".کاربر(ها) با موفقیت حذف شد")
                    # Refresh search results
                    st.session_state.search_results = auth.search_users(
                        username=search_username.strip(),
                        name=search_name.strip(),
                        personnel=search_personnel.strip(),
                        department=search_department.strip(),
                    )
                    st.session_state.selected_users = []


# --- Edit Panel ---
def edit_user_panel():
    if "edit_user" in st.session_state:
        st.subheader("✏️ Edit User")
        selected_user = st.session_state.edit_user
        selected_username = selected_user["username"]

        new_name = st.text_input("Name", value=selected_user["name"])
        new_department = st.text_input("Department", value=selected_user["department"])
        new_personnel = st.text_input("Personnel Number", value=selected_user["personnel"])
        new_is_admin = st.checkbox("Is Admin", value=selected_user["is_admin"])
        new_password = st.text_input("New Password (leave blank to keep current)", type="password")

        if st.button("Save Changes"):
            if not all([new_name.strip(), new_department.strip(), new_personnel.strip()]): # type: ignore
                st.warning("⚠️ لطفاً همه فیلدهای ضروری را پر کنید.")
            else:
                auth.update_user(
                    username=selected_username,
                    name=new_name, # type: ignore
                    department=new_department, # type: ignore
                    personnel=new_personnel, # type: ignore
                    is_admin=int(new_is_admin)
                )
                if new_password.strip():
                    auth.change_password(selected_username, new_password.strip())
                st.success(".تغییرات با موفقیت ثبت شد")

                # Refresh search results
                if "search_results" in st.session_state:
                    st.session_state.search_results = auth.search_users(
                        username="",
                        name="",
                        personnel="",
                        department="",
                    )

                del st.session_state.edit_user


# --- Main Function ---
def main():
    # --- Get query params ---
    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")

    if username == "Unknown" or not username.strip():
        st.warning("⚠️ You should log in first.")
        st.markdown(
            "<a href='/' style='font-size:16px; color:blue; text-decoration:underline;'>⬅️ Go to Log-in Page</a>",
            unsafe_allow_html=True
        )
        return

    # --- Display top bar ---
    display_top_bar(name, department)
    st.title("👤 User Management")

    # --- Panels ---
    add_user_panel()
    search_user_panel()
    edit_user_panel()


if __name__ == "__main__":
    main()
