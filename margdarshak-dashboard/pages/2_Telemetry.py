from typing import Any

import streamlit as st

from services.api_client import APIClientError, get_backend_health, get_stats

st.set_page_config(
    page_title="Stats — Margdarshak AI",
    page_icon=":material/monitoring:",
    layout="wide",
)

# Admin Design System (§65):
# Background: Light grey / blue-grey (#F8FAFC)
# Primary: Dark charcoal (#0F172A / #1E293B)
# Accent: Muted green (#2E7D32 / #166534)
# Cards: Simple borders (#E2E8F0), minimal shadows, compact operational layout
STATS_CSS = """
<style>
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    .stats-header-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 0.25rem 0;
        padding: 0;
    }
    .stats-header-subtitle {
        font-size: 0.95rem;
        color: #475569;
        margin: 0 0 1.25rem 0;
    }

    /* System status badges */
    .status-badge-connected {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-badge-connected::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #22C55E;
    }
    .status-badge-offline {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-badge-offline::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #EF4444;
    }

    /* Metric card (§45) */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        text-align: left;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .metric-val {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
    }
    .metric-lbl {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-top: 0.25rem;
    }

    /* Section header */
    .admin-section-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        margin: 1.25rem 0 0.6rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Chart Container Box */
    .chart-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1rem 1.15rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .chart-title {
        font-size: 0.92rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.75rem;
    }
</style>
"""
st.markdown(STATS_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Backend Connection Health Check
# ----------------------------------------------------------------------
backend_connected = False
try:
    health = get_backend_health()
    backend_connected = health.get("status") == "ok"
except APIClientError:
    backend_connected = False


# ----------------------------------------------------------------------
# Header Section (§45)
# ----------------------------------------------------------------------
hdr_col1, hdr_col2 = st.columns([4, 1.2])
with hdr_col1:
    st.markdown('<div class="stats-header-title">Stats</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="stats-header-subtitle">Operational placement telemetry, ticket volume, and issue metrics (Spec §45).</div>',
        unsafe_allow_html=True,
    )
with hdr_col2:
    if backend_connected:
        st.markdown(
            '<div style="text-align: right; padding-top: 0.35rem;"><span class="status-badge-connected">Backend connected</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align: right; padding-top: 0.35rem;"><span class="status-badge-offline">Backend offline</span></div>',
            unsafe_allow_html=True,
        )

if not backend_connected:
    st.error(
        "Connecting to Margdarshak failed: Backend service is unreachable (http://127.0.0.1:8000). "
        "Start the FastAPI backend and refresh.",
        icon=":material/cloud_off:",
    )
    st.stop()


# ----------------------------------------------------------------------
# Data Fetching (GET /stats per §45)
# ----------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def load_admin_stats() -> dict[str, Any]:
    return get_stats()


try:
    with st.spinner("Loading placement information..."):
        stats = load_admin_stats()
except APIClientError:
    st.error(
        "We couldn't load operational placement statistics. Please verify the backend connection and try again.",
        icon=":material/cloud_off:",
    )
    st.stop()



# Extract all 8 spec metrics (§45)
total_conversations = stats.get("total_conversations", 0)
tickets_created = stats.get("tickets_created", 0)
tickets_resolved = stats.get("tickets_resolved", 0)
students_assisted = stats.get("students_assisted", 0)
avg_res_time = stats.get("average_resolution_time_hours", 0.0)
categories = stats.get("most_common_issue_categories", {})
companies = stats.get("most_requested_companies", {})
languages = stats.get("most_common_languages", {})
active_clusters = stats.get("active_clusters", 0)


# ----------------------------------------------------------------------
# 1. Operational Metric Cards (§45)
# ----------------------------------------------------------------------
st.markdown('<div class="admin-section-header">📊 Placement Operations Overview</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-val">{total_conversations}</div>
            <div class="metric-lbl">Total Conversations</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-val">{tickets_created}</div>
            <div class="metric-lbl">Tickets Created</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 3px solid #16A34A;">
            <div class="metric-val" style="color: #166534;">{tickets_resolved}</div>
            <div class="metric-lbl">Tickets Resolved</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 3px solid #2563EB;">
            <div class="metric-val" style="color: #1D4ED8;">{students_assisted}</div>
            <div class="metric-lbl">Students Assisted</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-val">{avg_res_time} <span style="font-size: 1rem; font-weight: 500; color: #64748B;">hrs</span></div>
            <div class="metric-lbl">Avg Resolution Time</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# 2. Simple Lightweight Charts (§45)
# Note: Keep visually lightweight per §45. Avoid unnecessary analytics complexity.
# ----------------------------------------------------------------------
st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
st.markdown('<div class="admin-section-header">📈 Distribution & Trends (Spec §45)</div>', unsafe_allow_html=True)

chart_row1_c1, chart_row1_c2 = st.columns(2)

with chart_row1_c1:
    with st.container(border=True):
        st.markdown('<div class="chart-title">🏷️ Most Common Issue Categories</div>', unsafe_allow_html=True)
        if categories:
            try:
                import pandas as pd
                cat_df = pd.DataFrame(list(categories.items()), columns=["Category", "Tickets"]).sort_values(by="Tickets", ascending=False)
                st.bar_chart(cat_df.set_index("Category"), color="#2563EB")
            except Exception:
                st.bar_chart(categories)
        else:
            st.caption("No category distribution data recorded yet.")

with chart_row1_c2:
    with st.container(border=True):
        st.markdown('<div class="chart-title">🏢 Most Requested Companies</div>', unsafe_allow_html=True)
        if companies:
            try:
                import pandas as pd
                comp_df = pd.DataFrame(list(companies.items()), columns=["Company", "Tickets"]).sort_values(by="Tickets", ascending=False)
                st.bar_chart(comp_df.set_index("Company"), color="#16A34A")
            except Exception:
                st.bar_chart(companies)
        else:
            st.caption("No company queries recorded yet.")

chart_row2_c1, chart_row2_c2 = st.columns(2)

with chart_row2_c1:
    with st.container(border=True):
        st.markdown('<div class="chart-title">🌐 Most Common Languages</div>', unsafe_allow_html=True)
        if languages:
            try:
                import pandas as pd
                lang_df = pd.DataFrame(list(languages.items()), columns=["Language", "Tickets"]).sort_values(by="Tickets", ascending=False)
                st.bar_chart(lang_df.set_index("Language"), color="#7C3AED")
            except Exception:
                st.bar_chart(languages)
        else:
            st.caption("No language distribution data recorded yet.")

with chart_row2_c2:
    with st.container(border=True):
        st.markdown('<div class="chart-title">🎯 Operational Summary</div>', unsafe_allow_html=True)
        res_rate = round((tickets_resolved / tickets_created * 100), 1) if tickets_created > 0 else 100.0
        
        sum_c1, sum_c2 = st.columns(2)
        with sum_c1:
            st.metric("Resolution Rate", f"{res_rate}%")
        with sum_c2:
            st.metric("Active Incident Clusters", active_clusters)

        st.caption(
            "Stats are refreshed automatically every 30 seconds from `GET /stats`. "
            "For active issue management, navigate to the Tickets board or Knowledge approval workspace."
        )


# ----------------------------------------------------------------------
# Navigation Links
# ----------------------------------------------------------------------
st.divider()
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.page_link("app.py", label="Coordinator Home", icon=":material/home:")
with nav_col2:
    st.page_link("pages/1_Triage_Kanban.py", label="Open Tickets Kanban Board", icon=":material/view_kanban:")
with nav_col3:
    st.page_link("pages/3_Knowledge.py", label="Knowledge Approval & Policies", icon=":material/menu_book:")
