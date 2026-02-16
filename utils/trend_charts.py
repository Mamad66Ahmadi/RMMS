import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_monthly_trends(df, active_tag):
    """Render monthly PM/CM trend and Top Keywords charts side-by-side (last 24 months)."""

    
    if df.empty or "Date" not in df.columns:
        st.info("No valid data available to generate monthly trend.")
        return

    # --- Prepare data ---
    df_trend = df.copy()
    df_trend["Date"] = pd.to_datetime(df_trend["Date"], errors="coerce")
    df_trend = df_trend.dropna(subset=["Date"])

    two_year_ago = pd.Timestamp.now() - pd.DateOffset(months=24)
    df_trend = df_trend[df_trend["Date"] >= two_year_ago]

    df_trend["Month"] = df_trend["Date"].dt.to_period("M")
    df_trend["Month_Label"] = df_trend["Date"].dt.strftime("%b %Y")

    # --- Overall trend ---
    total_counts = df_trend.groupby("Month_Label").size().reset_index(name="Total")
    pm_counts = (
        df_trend[df_trend["Type"].str.upper() == "PM"]
        .groupby("Month_Label").size().reset_index(name="PM")
    )
    cm_counts = (
        df_trend[df_trend["Type"].str.upper() == "CM"]
        .groupby("Month_Label").size().reset_index(name="CM")
    )

    monthly = total_counts.merge(pm_counts, on="Month_Label", how="outer").merge(
        cm_counts, on="Month_Label", how="outer"
    ).fillna(0)

    # Ensure chronological order
    monthly["Month_Order"] = pd.to_datetime(monthly["Month_Label"], errors="coerce")
    monthly = monthly.sort_values("Month_Order")

    # --- Layout side-by-side: left (monthly trend), right (keywords)
    col1, col2 = st.columns([2.5, 1])

    # ===============================
    # 📈 MONTHLY TREND (LEFT)
    # ===============================
    with col1:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=monthly["Month_Label"],
            y=monthly["PM"],
            name="PM",
            marker_color="#2E8B57"  # green
        ))

        fig.add_trace(go.Bar(
            x=monthly["Month_Label"],
            y=monthly["CM"],
            name="CM",
            marker_color="#fc8a10"  # orange
        ))

        fig.update_layout(
            title=f"Monthly Trend (Last 2 Years): {active_tag}",
            xaxis_title="Month",
            yaxis_title="Record Count",
            template="simple_white",
            height=400,
            barmode="stack",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                x=0.5,
                xanchor="center",
                y=1.1
            ),
        )


        st.plotly_chart(fig, use_container_width=True)

    # ===============================
    # 🏷️ TOP KEYWORDS (RIGHT)
    # ===============================

    with col2:
        if "Keywords" in df.columns and not df["Keywords"].dropna().empty:
            # ✅ If WO number exists, keep only the first record per WO
            if "WO/PPM" in df.columns:
                wo_col = None
                for candidate in ["WO/PPM"]:
                    if candidate in df.columns:
                        wo_col = candidate
                        break
                if wo_col:
                    df_unique = df.drop_duplicates(subset=[wo_col], keep="first")
                else:
                    df_unique = df.copy()
            else:
                df_unique = df.copy()

            # ✅ Process keywords only from the de-duplicated dataframe
            all_keywords = (
                df_unique["Keywords"]
                .dropna()
                .astype(str)
                .str.split(",")
                .explode()
                .str.strip()
                .str.lower()
            )
            all_keywords = all_keywords[all_keywords != ""]

            if not all_keywords.empty:
                keyword_counts = all_keywords.value_counts().head(5).reset_index()
                keyword_counts.columns = ["Keyword", "Count"]

                # ✅ Sort descending so highest is on top
                keyword_counts = keyword_counts.sort_values("Count", ascending=True)

                # ✅ Slimmer, elegant bars with a nice color
                fig_kw = go.Figure(
                    go.Bar(
                        x=keyword_counts["Count"],
                        y=keyword_counts["Keyword"],
                        orientation="h",
                        marker=dict(
                            color="#148F77",         # modern teal tone
                            line=dict(color="#0E6655", width=0.8)
                        ),
                        width=0.4,
                        text=keyword_counts["Count"],
                        textposition="auto",
                    )
                )
                fig_kw.update_layout(
                    title=dict(
                        text=f"<b>Top 5 Keywords (Unique WO)</b>",
                        font=dict(color="#083358", size=16)
                    ),
                    xaxis_title="Frequency",
                    yaxis_title="Keyword",
                    template="simple_white",
                    height=400,
                    margin=dict(l=40, r=20, t=50, b=40),
                    xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)"),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_kw, use_container_width=True)
            else:
                st.markdown("No valid keywords found.")
        else:
            st.markdown("No keyword data available.")


    # ===============================
    # 📊 SUMMARY STATISTICS (Compact One-Line)
    # ===============================
    if not df_trend.empty:
        df_trend["Date"] = pd.to_datetime(df_trend["Date"], errors="coerce")
        cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=2)
        df_trend = df_trend[df_trend["Date"] >= cutoff_date]
        # --- Separate PM & CM ---
        pm_df = df_trend[df_trend["Type"].str.upper() == "PM"]
        cm_df = df_trend[df_trend["Type"].str.upper() == "CM"]

        def calc_avg_interval(sub_df):
            if len(sub_df) < 2:
                return None
            days = (sub_df["Date"].max() - sub_df["Date"].min()).days
            avg_interval = days / (len(sub_df) - 1)
            return round(avg_interval, 1) if avg_interval > 0 else None

        pm_avg = calc_avg_interval(pm_df)
        cm_avg = calc_avg_interval(cm_df)

        # --- Build sentence dynamically ---
        parts = []
        if pm_avg:
            parts.append(f"<b style='color:#006400;'>PM</b> every <b style='color:#006400;'>{pm_avg} days</b>")
        if cm_avg:
            parts.append(f"<b style='color:#8B0000;'>CM</b> every <b style='color:#8B0000;'>{cm_avg} days</b>")

        if parts:
            summary_text = ", ".join(parts)
            st.markdown(
                f"""
                🔹 <b style='color:#00264d;'>{active_tag}</b>: {summary_text} (average frequency, last 2 years)
                """,
                unsafe_allow_html=True
            )

    # ===============================
    # 📊 SPLIT BY DEPARTMENT (BOTTOM)
    # ===============================
    st.markdown(
        "<hr style='border:none; border-top:1.5px solid #bbb; margin-top:0px; margin-bottom:0px;'>",
        unsafe_allow_html=True
    )
    col1, col2 = st.columns(2)

    # --- PM by department ---
    df_pm = df_trend[df_trend["Type"].str.upper() == "PM"]
    if not df_pm.empty:
        pm_by_dept = (
            df_pm.groupby([df_pm["Date"].dt.to_period("M"), "Department"])
            .size().reset_index(name="Count")
        )
        pm_by_dept["Month"] = pm_by_dept["Date"].astype(str)
        pm_by_dept = pm_by_dept.sort_values("Month")

        fig_pm = go.Figure()
        for dept in pm_by_dept["Department"].unique():
            data = pm_by_dept[pm_by_dept["Department"] == dept]
            fig_pm.add_trace(go.Scatter(
                x=data["Month"],
                y=data["Count"],
                mode="lines+markers",
                name=dept,
                line=dict(width=2),
                marker=dict(size=6)
            ))

        # ✅ Always show legend, placed on top
        fig_pm.update_layout(
            title=dict(text="<b>PM by Department</b>", font=dict(color="#072D5A", size=16)),
            xaxis_title="Month",
            yaxis_title="PM Count",
            template="simple_white",
            height=350,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            )
        )
        with col1:
            st.plotly_chart(fig_pm, use_container_width=True)
    else:
        with col1:
            st.markdown("No PM Data")

    # --- CM by department ---
    df_cm = df_trend[df_trend["Type"].str.upper() == "CM"]
    if not df_cm.empty:
        cm_by_dept = (
            df_cm.groupby([df_cm["Date"].dt.to_period("M"), "Department"])
            .size().reset_index(name="Count")
        )
        cm_by_dept["Month"] = cm_by_dept["Date"].astype(str)
        cm_by_dept = cm_by_dept.sort_values("Month")

        fig_cm = go.Figure()
        for dept in cm_by_dept["Department"].unique():
            data = cm_by_dept[cm_by_dept["Department"] == dept]
            fig_cm.add_trace(go.Scatter(
                x=data["Month"],
                y=data["Count"],
                mode="lines+markers",
                name=dept,
                line=dict(width=2),
                marker=dict(size=6)
            ))

        # ✅ Always show legend, placed on top
        fig_cm.update_layout(
            title=dict(text="<b>CM by Department</b>", font=dict(color="#751508", size=16)),
            xaxis_title="Month",
            yaxis_title="CM Count",
            template="simple_white",
            height=350,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            )
        )
        with col2:
            st.plotly_chart(fig_cm, use_container_width=True)
    else:
        with col2:
            st.markdown("No CM Data")
