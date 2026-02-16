# pages/trends_page.py

import streamlit as st
from utils.trend_charts_dailyRreportPage import (
    trend_chart_object_page,
    unit_department_charts
)
from utils.top_bar import display_top_bar

# -----------------------------------------------------
# Page Title & Query Params
# -----------------------------------------------------
st.set_page_config(page_title="Trends & Analytics", layout="wide")
from utils.left_navigation_bar_lock import lock_navigation_bar
lock_navigation_bar()



chart_type = st.query_params.get("chart_type", "")
days_back = st.query_params.get("days_back", "")

# Keep your user identity / department info
username = st.query_params.get("username", "Unknown")
name = st.query_params.get("name", "")
department = st.query_params.get("department", "")



# --- Helpers ---
def qp_first(key: str, default: str = "Unknown") -> str:
    """Get the first value of a query param."""
    val = st.query_params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default


def main():
    username = qp_first("username", "Unknown")
    name = qp_first("name", "")
    department = qp_first("department", "")
    display_top_bar(name, department)



    # -----------------------------------------------------
    # Logic: Which Chart to Show?
    # -----------------------------------------------------
    if chart_type == "trend_1year":
        st.subheader("📈 Monthly PM/CM Report Counts (Last 12 Months)")
        st.markdown("---")

        trend_chart_object_page()


    elif chart_type == "cm_departments":

        st.subheader("📊 CM Report Distribution Across Units & Departments")

        # --- Time range selection (default = 365 days) ---
        days_list = ["7 days", "14 days", "30 days", "90 days", "365 days"]

        # Make "365 days" default
        default_index = days_list.index("365 days")

        period = st.selectbox(
            "Select Time Range",
            days_list,
            index=default_index
        )

        # Map to values
        days_map = {
            "7 days": 7,
            "14 days": 14,
            "30 days": 30,
            "90 days": 90,
            "365 days": 365
        }

        selected_days = days_map[period]

        # --- Show charts immediately (no button needed) ---
        unit_department_charts(days_back=selected_days)

    else:
        st.warning("No chart selected. Please use the links on the previous page.")





# --- Run ---
if __name__ == "__main__":
    main()
