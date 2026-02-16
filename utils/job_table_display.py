# job_table_display.py

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from utils.color_work_orders import colorize_wo_ppm
import urllib.parse
from utils.auth import get_user_info
import jdatetime


# =========================================================
# 🔹 Style Job Type (PM/CM)
# =========================================================
def style_job_type_html(val):
    if val is None:
        return ""
    v = str(val).strip().upper()
    if v == "PM":
        return f"<span style='color:#006400; font-weight:600;'>{val}</span>"
    elif v == "CM":
        return f"<span style='color:#FF8C00; font-weight:600;'>{val}</span>"
    return val


# =========================================================
# 🔹 Style Index by Status + Background Flags
# =========================================================
def style_index_by_status(index_val, status_val, anomaly_val=None, action_list_val=None):
    if pd.isna(index_val):
        return "-"

    # --- Text color (status) ---
    text_color = "#000000"
    if isinstance(status_val, str):
        s = status_val.strip().lower()
        if s == "completed":
            text_color = "#318F0A"
        elif s == "ongoing":
            text_color = "#D68D05"
        elif s == "on hold":
            text_color = "#8B0000"

    # --- Background color (anomaly/action list) ---
    bg_color = ""
    if anomaly_val and action_list_val:
        bg_color = "#181818FC"   # dark gray (both)
    elif anomaly_val:
        bg_color = "#8204043A"   # light red
    elif action_list_val:
        bg_color = "#FFE5B4AF"   # light orange

    style = f"color:{text_color}; font-weight:700;"
    if bg_color:
        style += f" background-color:{bg_color}; border-radius:4px; padding:2px 6px;"

    return f"<span style='{style}'>{index_val}</span>"


# =========================================================
# 🔹 Highlight Actual Start if same as Date
# =========================================================
def highlight_same_start(date_val, start_val):
    try:
        if pd.isna(date_val) or pd.isna(start_val):
            return str(start_val)
        d1 = pd.to_datetime(date_val).date()
        d2 = pd.to_datetime(start_val).date()
        if d1 == d2:
            return f"<span style='color:#016236; font-weight:500;'>{start_val}</span>"
        else:
            return str(start_val)
    except Exception:
        return str(start_val)


def gregorian_to_persian(date_val):
    try:
        if pd.isna(date_val) or str(date_val).strip() == "":
            return ""

        g = pd.to_datetime(date_val).date()  # << ensures only date

        j = jdatetime.date.fromgregorian(
            year=g.year,
            month=g.month,
            day=g.day
        )

        return j.strftime("%Y/%m/%d")

    except Exception:
        return ""


def render_tag_count_with_hover(tag_raw):
    if pd.isna(tag_raw) or str(tag_raw).strip() == "":
        return "-"
    
    tags = [t.strip() for t in str(tag_raw).split(",") if t.strip()]
    count = len(tags)
    tooltip = ", ".join(tags)

    return f"<span title='{tooltip}'>{count} tags</span>"



# =========================================================
# 🔹 Render Job Table
# =========================================================
def render_job_table(filtered_df: pd.DataFrame):
    """Display styled HTML job table inside Streamlit."""

    if filtered_df.empty:
        st.warning("No records found to display.")
        return

    # --- Combine Route and Description for PM ---
    filtered_df["Description"] = filtered_df.apply(
        lambda row: f"<b>{row['Route']}</b><br>{row['Description']}"
        if str(row["Type"]).strip().upper() == "PM" else row["Description"],
        axis=1
    )

    # --- Clean and preserve HTML breaks ---
    filtered_df["Description"] = (
        filtered_df["Description"].astype(str).apply(lambda x: x.replace("\n", "<br>"))
    )

    # === Apply style transformations ===
    filtered_df["Type"] = filtered_df["Type"].astype("string").apply(style_job_type_html)
    filtered_df["WO/PPM"] = filtered_df["WO/PPM"].apply(colorize_wo_ppm)
    filtered_df["Actual Start"] = filtered_df.apply(
        lambda r: highlight_same_start(r["Date"], r["Actual Start"]), axis=1
    )
    filtered_df["Index"] = filtered_df.apply(
        lambda r: style_index_by_status(
            r["Index"],
            r.get("Status", ""),
            r.get("anomaly", 0),
            r.get("action_list", 0)
        ),
        axis=1
    )

    # --- Drop helper columns after styling ---
    filtered_df.drop(columns=["Status", "anomaly", "action_list"], inplace=True, errors="ignore")

    # --- Final column order ---
    filtered_df = filtered_df[[
        "Index", "Date", "Elapsed days", "Department", "Type", "WO/PPM",
        "Actual Start", "Performed Job", "Keywords", "Description"
    ]]

    filtered_df["Date"] = pd.to_datetime(filtered_df["Date"]).dt.date

    # === Add Persian date hover tooltip ===
    filtered_df["Date"] = filtered_df["Date"].apply(
        lambda d: f"<span title= {gregorian_to_persian(d)}>{d}</span>"
    )

    # === Legend ===
    st.markdown("""
    <div style="
        background-color:#f9f9f9;
        border:1px solid #ccc;
        border-radius:10px;
        padding:10px 15px;
        margin-bottom:10px;
        font-size:13px;
        color:#333;
        box-shadow:0 2px 4px rgba(0,0,0,0.05);
    ">
    <b>🔹 Index Color (Status condition):                🔸 Index Background (Anomaly/Action List condition):</b><br>
    <span style='color:#318F0A; font-weight:800;'>■</span> Completed &nbsp;&nbsp;&nbsp;
    <span style='color:#D68D05; font-weight:800;'>■</span> Ongoing &nbsp;&nbsp;&nbsp;
    <span style='color:#8B0000; font-weight:800;'>■</span> On Hold               &nbsp;&nbsp;&nbsp;
    <span style='color:#820404; font-weight:800;'>■</span> Anomaly &nbsp;&nbsp;&nbsp;
    <span style='color:#FFE5B4; font-weight:800;'>■</span> Action List &nbsp;&nbsp;&nbsp;
    <span style='color:#000; font-weight:800;'>■</span> Both
    </div>
    """, unsafe_allow_html=True)


    # === Table HTML ===
    html_table = """
    <style>
    table {
        width:100%; 
        table-layout: fixed; 
        border-collapse: separate; 
        border-spacing:0; 
        border:1px solid #ddd;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size:12px;
        box-shadow:0 2px 5px rgba(0,0,0,0.05);
        border-radius:8px;
        overflow:hidden;
    }
    th {
        background-color:#0b1c48;
        color:#FFFFFF;
        font-weight:500;
        text-align:center !important;
        padding:10px;
        border-bottom:1px solid #ddd;
        font-size:14px;
    }
    td {
        padding:10px;
        text-align:center;
        border-bottom:1px solid #eee;
        vertical-align:middle;
        background-color:#fff;
        font-size:13px;
        color:#222;
    }
    tr:hover td { background-color:#f1f1f1; }

    /* Adjusted column widths */
    th:nth-child(1), td:nth-child(1) { width:3%; }
    th:nth-child(2), td:nth-child(2) { width:6.5%; }
    th:nth-child(3), td:nth-child(3) { width:5%; }
    th:nth-child(4), td:nth-child(4) { width:7.5%; }
    th:nth-child(5), td:nth-child(5) { width:3.5%; }
    th:nth-child(6), td:nth-child(6) { width:6%; }
    th:nth-child(7), td:nth-child(7) { width:6.5%; }
    th:nth-child(8), td:nth-child(8) { width:6%; }
    th:nth-child(9), td:nth-child(9) { width:8%; }
    th:nth-child(10), td:nth-child(10) { 
        width:47%; 
        text-align:left !important;
        direction: rtl;
        word-wrap:break-word;
        white-space:normal;
    }
    th, td { border-right:1px solid #f0f0f0; }
    th:last-child, td:last-child { border-right:none; }
    </style>
    """ + filtered_df.to_html(index=False, escape=False)

    num_rows = len(filtered_df)
    row_height = 40  # pixels per row (approx)
    base_height = 250  # header + padding
    dynamic_height = min(800, max(300, base_height + num_rows * row_height))
    

    components.html(html_table, height=dynamic_height, scrolling=True)


# =========================================================
# 🔹 Render Job Table (with Object Tag shown)
# =========================================================
def render_job_table_with_tag(filtered_df: pd.DataFrame):
    """Display styled HTML job table that includes Tag (clickable, like your Route Code links),
    RTL Persian-safe Description, and PM grouping.
    """

    if filtered_df.empty:
        st.warning("No records found to display.")
        return



    # --- Identify PM-grouped summary rows ---
    is_grouped_pm = (filtered_df["Index"] == "-") & (filtered_df["Type"].str.upper() == "PM")

    # --- Combine Route and Description for PM ---
    filtered_df["Description"] = filtered_df.apply(
        lambda row: (
            f"<b> {row.get('Route','')} 🟢</b><br><i>Grouped PM summary</i>"
            if str(row.get("Type", "")).upper() == "PM"
            else f"<b>{row.get('Route','')}</b><br>{row['Description']}"
            if str(row.get("Type", "")).upper() == "PM" else row["Description"]
        ),
        axis=1
    )

    filtered_df["Description"] = filtered_df["Description"].astype(str).apply(lambda x: x.replace("\n", "<br>"))

    # === Apply style transformations ===
    filtered_df["Type"] = filtered_df["Type"].astype("string").apply(style_job_type_html)
    filtered_df["WO/PPM"] = filtered_df["WO/PPM"].apply(colorize_wo_ppm)
    filtered_df["Actual Start"] = filtered_df.apply(
        lambda r: highlight_same_start(r["Date"], r["Actual Start"]), axis=1
    )
    filtered_df["Index"] = filtered_df.apply(
        lambda r: style_index_by_status(
            r["Index"], r.get("Status", ""), r.get("anomaly", 0), r.get("action_list", 0)
        ),
        axis=1
    )

    filtered_df.drop(columns=["Status", "anomaly", "action_list"], inplace=True, errors="ignore")

    # --- Rename Object_Tag → Tag ---
    filtered_df.rename(columns={"Object_Tag": "Tag"}, inplace=True)

    filtered_df.loc[
        filtered_df["Type"].str.contains("PM", case=False, na=False),
        "Tag"
    ] = filtered_df.loc[
        filtered_df["Type"].str.contains("PM", case=False, na=False),
        "Tag"
    ].apply(render_tag_count_with_hover)

    # ✅ Make Tag clickable exactly like Route links
    query_username = st.query_params.get("username", "")
    query_name = st.query_params.get("name", "")
    query_department = st.query_params.get("department", "")

    try:
        user_info = get_user_info(query_username)
    except Exception:
        user_info = None

    username = user_info["username"] if user_info else query_username
    name = user_info["name"] if user_info else query_name
    department = user_info["department"] if user_info else query_department

    def make_clickable_tag(row):
        tag = str(row.get("Tag", "")).strip()
        job_type = str(row.get("Type", "")).strip().upper()
        route = str(row.get("Route", "")).strip() if "Route" in row else ""

        if not tag or tag == "-":
            return "-"

        base_params = {
            "username": username,
            "name": name,
            "department": department,
        }

        # ✅ If PM → link to route details
        if job_type == "<SPAN STYLE='COLOR:#006400; FONT-WEIGHT:600;'>PM</SPAN>" and route and route != "-":
            base_params["route"] = route
            url = f"/route_details_page?{urllib.parse.urlencode(base_params, quote_via=urllib.parse.quote)}"
            return f"<a href='{url}' target='_blank' style='color:#1E40AF; text-decoration:none; font-weight:600;'>{tag}</a>"

        # ✅ If CM → link to object details
        elif job_type == "<SPAN STYLE='COLOR:#FF8C00; FONT-WEIGHT:600;'>CM</SPAN>":
            base_params["tag"] = tag
            url = f"/Object_Details_page?{urllib.parse.urlencode(base_params, quote_via=urllib.parse.quote)}"
            return f"<a href='{url}' target='_blank' style='color:#000; text-decoration:none; font-weight:600;'>{tag}</a>"

        # Fallback (for grouped or unknown)
        return tag
    
    filtered_df["Tag"] = filtered_df.apply(make_clickable_tag, axis=1)



    # --- Colorize Month Count column ---
    def colorize_month_count(val):
        """Return colored HTML for month count values."""
        try:
            if val == "" or pd.isna(val):
                return ""
            v = int(val)
            if v > 8:
                return f"<span style='color:#8B0000; font-weight:700;'>{v}</span>"  # dark red
            elif v > 4:
                return f"<span style='color:#D68D05; font-weight:700;'>{v}</span>"  # orange
            else:
                return str(v)
        except Exception:
            return str(val)

    if "Month Count" in filtered_df.columns:
        filtered_df["Month Count"] = filtered_df["Month Count"].apply(colorize_month_count)


    def colorize_year_count(val):
        """Return colored HTML for month count values."""
        try:
            if val == "" or pd.isna(val):
                return ""
            else:
                v = int(val)
                return str(v)
        except Exception:
            return str(val)
        
    if "Year Count" in filtered_df.columns:
        filtered_df["Year Count"] = filtered_df["Year Count"].apply(colorize_year_count)
    # --- Final column order ---

    # --- Rename Recent 30d Family Count → Month Family Count ---
    if "Recent 30d Family Count" in filtered_df.columns:
        filtered_df.rename(columns={"Recent 30d Family Count": "Month Family Count"}, inplace=True)

    # --- Convert Month Family Count to int if possible ---
    if "Month Family Count" in filtered_df.columns:
        filtered_df["Month Family Count"] = filtered_df["Month Family Count"].apply(colorize_year_count)
    # --- Apply dark green color to Father Tag and Month Family Count ---
    def style_dark_green(val):
        if pd.isna(val) or str(val).strip() == "":
            return ""
        return f"<span style='color:#733902; font-weight:520;'>{val}</span>"

    # === Make Father Tag clickable using the SAME method ===
    def make_clickable_father_tag(row):
        father = row.get("Father Tag", "")

        # Handle NaN, None, empty, or "-" → return empty string
        if father is None or pd.isna(father):
            return ""
        
        father = str(father).strip()
        if father == "" or father == "-":
            return ""

        # build params exactly like Tag links
        base_params = {
            "username": username,
            "name": name,
            "department": department,
            "father_tag": father
        }

        # link exactly like your pattern
        url = f"/father_page?{urllib.parse.urlencode(base_params, quote_via=urllib.parse.quote)}"

        # colored hyperlink (dark orange)
        return (
            f"<a href='{url}' target='_blank' "
            f"style='color:#733902; text-decoration:none; font-weight:520;'>{father}</a>"
        )


    # apply
    if "Father Tag" in filtered_df.columns:
        filtered_df["Father Tag"] = filtered_df.apply(make_clickable_father_tag, axis=1)



    if "Month Family Count" in filtered_df.columns:
        filtered_df["Month Family Count"] = filtered_df["Month Family Count"].apply(style_dark_green)

    # --- 🔹 Add Day of Week column with color codes ---
    dow_colors = {
        "Monday": "#b20000",
        "Tuesday": "#36454f",
        "Wednesday": "#a83569",
        "Thursday": "#006400",
        "Friday": "#b27300",
        "Saturday": "#0073b2",
        "Sunday": "#4b0082"
    }

    try:
        filtered_df["Day"] = pd.to_datetime(filtered_df["Date"], errors="coerce").dt.strftime("%A")
    except Exception:
        filtered_df["Day"] = "-"

    def colorize_day(val):
        if pd.isna(val) or str(val).strip() == "-":
            return "-"
        color = dow_colors.get(str(val), "#000000")
        return f"<span style='color:{color}; font-weight:500;'>{val}</span>"

    filtered_df["Day"] = filtered_df["Day"].apply(colorize_day)

    # --- Final column order (insert Day after Date) ---
    filtered_df = filtered_df[[
        "Index", "Date", "Day", "Tag",
        "Year Count", "Month Count", "Department",
        "WO/PPM", "Actual Start", "Description", "Father Tag", "Month Family Count"
    ]]


    filtered_df["Date"] = pd.to_datetime(filtered_df["Date"]).dt.date

    # === Add Persian date hover tooltip ===
    filtered_df["Date"] = filtered_df["Date"].apply(
        lambda d: f"<span title= {gregorian_to_persian(d)}>{d}</span>"
    )

    # === Legend ===
    st.markdown("""
    <div style="
        background-color:#f9f9f9;
        border:1px solid #ccc;
        border-radius:10px;
        padding:10px 15px;
        margin-bottom:10px;
        font-size:13px;
        color:#333;
        box-shadow:0 2px 4px rgba(0,0,0,0.05);
    ">
    <b>🔹 Index Color (Status condition):                🔸 Index Background (Anomaly/Action List condition):</b><br>
    <span style='color:#318F0A; font-weight:800;'>■</span> Completed &nbsp;&nbsp;&nbsp;
    <span style='color:#D68D05; font-weight:800;'>■</span> Ongoing &nbsp;&nbsp;&nbsp;
    <span style='color:#8B0000; font-weight:800;'>■</span> On Hold               &nbsp;&nbsp;&nbsp;
    <span style='color:#820404; font-weight:800;'>■</span> Anomaly &nbsp;&nbsp;&nbsp;
    <span style='color:#FFE5B4; font-weight:800;'>■</span> Action List &nbsp;&nbsp;&nbsp;
    <span style='color:#000; font-weight:800;'>■</span> Both
    </div>
    """, unsafe_allow_html=True)

    # === Table HTML ===
    html_table = """
    <style>
    table {
        width:100%;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing:0;
        border:1px solid #ddd;
        font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size:12px;
        box-shadow:0 2px 5px rgba(0,0,0,0.05);
        border-radius:8px;
        overflow:hidden;
    }
    th {
        background-color:#2c5e1a;
        color:#FFFFFF;
        font-weight:500;
        text-align:center !important;
        padding:10px;
        border-bottom:1px solid #ddd;
        font-size:14px;
    }
    td {
        padding:10px;
        text-align:center;
        border-bottom:1px solid #eee;
        vertical-align:middle;
        background-color:#fff;
        font-size:13px;
        color:#222;
    }
    tr:hover td { background-color:#f1f1f1; }
    tr:has(td:contains('🔹')) td { background-color:#f7f7f7 !important; }

    /* Adjusted column widths */
    th:nth-child(1), td:nth-child(1) { width:3%; }
    th:nth-child(2), td:nth-child(2) { width:7%; }
    th:nth-child(3), td:nth-child(3) { width:6%; }

    th:nth-child(4), td:nth-child(4) { width:8%; }

    th:nth-child(5), td:nth-child(5) { width:4%; }
    th:nth-child(6), td:nth-child(6) { width:4%; }

    th:nth-child(7), td:nth-child(7) { width:7%; }
    th:nth-child(8), td:nth-child(8) { width:6%; }
    th:nth-child(9), td:nth-child(9) { width:8%; }

    th:nth-child(10), td:nth-child(10) { 
        width:38%;
        text-align:left !important;
        direction: rtl;
        word-wrap:break-word;
        white-space:normal;
    }
    th:nth-child(11), td:nth-child(11) { width:7%; }
    th:nth-child(12), td:nth-child(12) { width:4%; }

    th, td { border-right:1px solid #f0f0f0; }
    th:last-child, td:last-child { border-right:none; }
    </style>
    """ + filtered_df.to_html(index=False, escape=False)

    num_rows = len(filtered_df)
    row_height = 40
    base_height = 250
    dynamic_height = min(800, max(300, base_height + num_rows * row_height))

    components.html(html_table, height=dynamic_height, scrolling=True)


# =========================================================
# 🔹 Render Family Job Table (used in father_page.py)
# =========================================================
def render_family_job_table(df: pd.DataFrame):
    """Render HTML-styled job table for all family tag job records."""
    if df.empty:
        st.warning("No job records found for this Father Tag family.")
        return

    # 🧹 Remove duplicate columns & unify date column
    df = df.loc[:, ~df.columns.duplicated()]
    if "date" in df.columns and "Date" not in df.columns:
        df.rename(columns={"date": "Date"}, inplace=True)

    # --- Rename columns safely ---
    df.rename(columns={
        "job_indx": "Index",
        "Object_Tag": "Tag",
        "department": "Department",
        "job_type": "Type",
        "wo_number": "WO/PPM",
        "permit_number": "Permit",
        "performed_action": "Performed Job",
        "job_description": "Description",
        "keywords": "Keywords",
        "employee": "Employee",
        "route": "Route",
        "registered_by": "Registered By",
        "registered_date": "Registered Date",
        "status": "Status",
        "actual_start": "Actual Start"
    }, inplace=True, errors="ignore")

    # --- Sort & clean ---
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date", ascending=False)

    # --- Combine Route + Description for PMs ---
    df["Description"] = df.apply(
        lambda row: f"<b>{row.get('Route', '')}</b><br>{row['Description']}"
        if str(row.get("Type", "")).strip().upper() == "PM" else row["Description"],
        axis=1
    ).astype(str).apply(lambda x: x.replace("\n", "<br>"))

    # === Apply style transformations ===
    df["Type"] = df["Type"].astype(str).apply(style_job_type_html)
    df["WO/PPM"] = df["WO/PPM"].apply(colorize_wo_ppm)
    df["Actual Start"] = df.apply(lambda r: highlight_same_start(r["Date"], r.get("Actual Start", "")), axis=1)
    df["Index"] = df.apply(
        lambda r: style_index_by_status(
            r["Index"], r.get("Status", ""), r.get("anomaly", 0), r.get("action_list", 0)
        ),
        axis=1
    )

    # --- Make Object Tag clickable ---
    q = st.query_params
    username, name, department = q.get("username", ""), q.get("name", ""), q.get("department", "")
    for i, tag in enumerate(df["Tag"].astype(str)):
        base_params = {"username": username, "name": name, "department": department, "tag": tag}
        link = f"/Object_Details_page?{urllib.parse.urlencode(base_params, quote_via=urllib.parse.quote)}"
        df.at[i, "Tag"] = (
            f"<a href='{link}' target='_blank' "
            f"style='color:#000; text-decoration:none; font-weight:600;'>{tag}</a>"
        )

    # --- Clean columns ---
    df.drop(columns=["Status", "anomaly", "action_list"], inplace=True, errors="ignore")

    # --- Final column order ---
    column_order = [
        "Index", "Date", "Tag", "Department", "Type", "WO/PPM",
        "Actual Start", "Performed Job", "Keywords", "Description"
    ]
    df = df[[c for c in column_order if c in df.columns]]


    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # === Add Persian date hover tooltip ===
    df["Date"] = df["Date"].apply(
        lambda d: f"<span title= {gregorian_to_persian(d)}>{d}</span>"
    )

        # === Legend ===
    st.markdown("""
    <div style="
        background-color:#f9f9f9;
        border:1px solid #ccc;
        border-radius:10px;
        padding:10px 15px;
        margin-bottom:10px;
        font-size:13px;
        color:#333;
        box-shadow:0 2px 4px rgba(0,0,0,0.05);
    ">
    <b>🔹 Index Color (Status condition):                🔸 Index Background (Anomaly/Action List condition):</b><br>
    <span style='color:#318F0A; font-weight:800;'>■</span> Completed &nbsp;&nbsp;&nbsp;
    <span style='color:#D68D05; font-weight:800;'>■</span> Ongoing &nbsp;&nbsp;&nbsp;
    <span style='color:#8B0000; font-weight:800;'>■</span> On Hold               &nbsp;&nbsp;&nbsp;
    <span style='color:#820404; font-weight:800;'>■</span> Anomaly &nbsp;&nbsp;&nbsp;
    <span style='color:#FFE5B4; font-weight:800;'>■</span> Action List &nbsp;&nbsp;&nbsp;
    <span style='color:#000; font-weight:800;'>■</span> Both
    </div>
    """, unsafe_allow_html=True)

    # === HTML Table ===
    html_table = """
    <style>
    table {
        width:100%;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing:0;
        border:1px solid #ddd;
        font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size:12px;
        box-shadow:0 2px 5px rgba(0,0,0,0.05);
        border-radius:8px;
        overflow:hidden;
    }
    th {
        background-color:#43334C;
        color:#FFFFFF;
        font-weight:500;
        text-align:center !important;
        padding:10px;
        border-bottom:1px solid #ddd;
        font-size:14px;
    }
    td {
        padding:10px;
        text-align:center;
        border-bottom:1px solid #eee;
        vertical-align:middle;
        background-color:#fff;
        font-size:13px;
        color:#222;
    }
    tr:hover td { background-color:#f1f1f1; }
    th:nth-child(1), td:nth-child(1) { width:3%; }
    th:nth-child(2), td:nth-child(2) { width:6.5%; }
    th:nth-child(3), td:nth-child(3) { width:8%; }
    th:nth-child(4), td:nth-child(4) { width:8%; }
    th:nth-child(5), td:nth-child(5) { width:4%; }
    th:nth-child(6), td:nth-child(6) { width:7%; }
    th:nth-child(7), td:nth-child(7) { width:8%; }
    th:nth-child(8), td:nth-child(8) { width:7%; }
    th:nth-child(9), td:nth-child(9) { width:7%; }
    th:nth-child(10), td:nth-child(10) {
        width:40%;
        text-align:left !important;
        direction: rtl;
        word-wrap:break-word;
        white-space:normal;
    }
    th, td { border-right:1px solid #f0f0f0; }
    th:last-child, td:last-child { border-right:none; }
    </style>
    """ + df.to_html(index=False, escape=False)

    # --- Dynamic height ---
    num_rows = len(df)
    row_height = 40
    base_height = 250
    dynamic_height = min(800, max(300, base_height + num_rows * row_height))
    components.html(html_table, height=dynamic_height, scrolling=True)
