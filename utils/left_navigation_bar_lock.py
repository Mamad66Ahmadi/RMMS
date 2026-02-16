
import streamlit as st

def lock_navigation_bar():
    st.markdown("""
    <style>
    /* Hide the sidebar completely */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* Hide the top-left hamburger menu */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Hide the floating menu button (mobile/desktop) */
    [data-testid="stHamburger"] {
        display: none !important;
    }

    /* Prevent any empty space where sidebar was */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
