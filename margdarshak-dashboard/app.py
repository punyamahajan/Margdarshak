from datetime import datetime, timezone
from typing import Any

import streamlit as st

from services.api_client import (
    APIClientError,
    get_admin_clusters,
    get_admin_overview,
    get_backend_health,
)

st.set_page_config(
    page_title="Margdarshak AI — Coordinator Workspace",
    page_icon=":material/support_agent:",
    layout="wide",
)

# Admin Design System (§65):
# Background: Light grey / blue-grey (#F4F6F8)
# Primary: Dark charcoal (#0F172A / #1E293B)
# Accent: Muted green (#2E7D32 / #166534)
# Cards: Simple borders (#E2E8F0), minimal shadows, compact operational layout
ADMIN_CSS = """
<style>
    /* Base background and text tokens */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Compact operational typography */
    h1, h2, h3, h4 {
        color: #0F172A !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }
    
    /* Header layout */
    .admin-header-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 0.25rem 0;
        padding: 0;
    }
    
    .admin-header-subtitle {
        font-size: 0.95rem;
        color: #475569;
        margin: 0 0 1.25rem 0;
    }
    
    /* System status badge (§25.2) */
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

    /* Section headers */
    .admin-section-header {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        margin: 1.5rem 0 0.6rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Overview Metric Card (§26) */
    .metric-card-container {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        transition: border-color 0.15s ease;
    }
    .metric-card-container:hover {
        border-color: #CBD5E1;
    }
    .metric-card-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-bottom: 0.2rem;
    }
    .metric-card-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
    }

    /* Priority Alert Card (§27) */
    .priority-alert-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #DC2626;
        border-radius: 6px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .priority-alert-card.high {
        border-left-color: #D97706;
    }
    .priority-alert-card.medium {
        border-left-color: #2563EB;
    }
    .priority-alert-card.low {
        border-left-color: #16A34A;
    }
    .priority-badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        margin-bottom: 0.4rem;
    }
    .priority-badge.critical {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
    }
    .priority-badge.high {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .priority-badge.medium {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }
    .priority-badge.low {
        background-color: #F0FDF4;
        color: #15803D;
        border: 1px solid #BBF7D0;
    }
    .priority-title {
        font-size: 1rem;
        font-weight: 600;
        color: #0F172A;
        margin: 0 0 0.35rem 0;
    }
    .priority-meta {
        font-size: 0.82rem;
        color: #475569;
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        align-items: center;
    }
    .priority-meta strong {
        color: #0F172A;
    }

    /* Active Drive Card (§28) */
    .drive-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .drive-company {
        font-size: 0.95rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .drive-detail {
        font-size: 0.82rem;
        color: #475569;
    }
    .drive-status-pill {
        display: inline-block;
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }

    /* Recent Updates Feed (§29) */
    .update-item {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.65rem 0.9rem;
        margin-bottom: 0.45rem;
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        font-size: 0.84rem;
        color: #1E293B;
    }
    .update-kind-tag {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        padding: 0.1rem 0.35rem;
        border-radius: 3px;
        white-space: nowrap;
        margin-top: 0.1rem;
    }
    .update-kind-ticket {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
    }
    .update-kind-knowledge {
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
    }
    .update-time {
        margin-left: auto;
        font-size: 0.74rem;
        color: #94A3B8;
        white-space: nowrap;
        padding-left: 0.5rem;
    }

    /* Endpoint Notice Box */
    .endpoint-flag-notice {
        background-color: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 6px;
        padding: 0.6rem 0.9rem;
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 1.5rem;
    }
</style>
"""


@st.cache_data(ttl=15, show_spinner=False)
def load_overview_data() -> dict[str, Any]:
    """Fetch aggregated admin overview data from GET /api/v1/admin/overview."""
    return get_admin_overview()


@st.cache_data(ttl=15, show_spinner=False)
def load_clusters_data() -> list[dict[str, Any]]:
    """Fetch issue clusters from GET /api/v1/admin/clusters to enrich priority alerts."""
    try:
        return get_admin_clusters()
    except Exception:
        return []


def format_relative_time(iso_timestamp: str | None) -> str:
    """Format an ISO timestamp into a readable compact representation."""
    if not iso_timestamp:
        return "recently"
    try:
        clean_ts = iso_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        now = datetime.now(timezone.utc)
        diff = now - dt if dt.tzinfo else datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except Exception:
        return str(iso_timestamp)[:16]


def calculate_priority_score(item: dict[str, Any]) -> int:
    """Sort priority alerts per §27:

    Priority increases with:
    1. Number of affected students
    2. Urgency level (critical > high > medium > low)
    3. Deadline proximity
    4. Repetition / clustering
    5. Students blocked from progressing (keywords: link, fail, error, timeout, access)
    """
    urgency = str(
        item.get("urgency")
        or item.get("intelligence", {}).get("urgency", "medium")
    ).lower()
    urgency_scores = {"critical": 40, "high": 30, "medium": 20, "low": 10}
    base_score = urgency_scores.get(urgency, 15)

    affected = int(item.get("affected_students") or 1)
    affected_score = affected * 5

    # Check for blocking keywords in issue summary or title
    summary_text = str(
        item.get("title") or item.get("issue_summary") or ""
    ).lower()
    blocked_keywords = ("link", "fail", "timeout", "blocked", "access", "cannot", "error", "portal")
    is_blocked = any(kw in summary_text for kw in blocked_keywords)
    blocked_score = 15 if is_blocked else 0

    # Repetition score (multiple affected or clustered)
    is_repeated = affected > 1 or bool(item.get("ticket_ids"))
    repetition_score = 10 if is_repeated else 0

    # Deadline proximity
    deadline = item.get("deadline") or item.get("placement", {}).get("deadline")
    deadline_score = 0
    if deadline:
        d_str = str(deadline).lower()
        if "today" in d_str or "imminent" in d_str or "now" in d_str:
            deadline_score = 25
        else:
            deadline_score = 10

    return base_score + affected_score + blocked_score + repetition_score + deadline_score


def home() -> None:
    # Inject Admin Design System CSS (§65)
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)

    # 1. Header & System Status (§25)
    header_col, status_col = st.columns([3, 1])
    with header_col:
        st.markdown('<h1 class="admin-header-title">Margdarshak AI</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="admin-header-subtitle">Coordinator workspace for placement support and peer matching.</p>',
            unsafe_allow_html=True,
        )

    backend_online = False
    try:
        health = get_backend_health()
        backend_online = health.get("status") == "ok"
    except APIClientError:
        backend_online = False

    with status_col:
        if backend_online:
            st.markdown(
                '<div style="text-align: right; padding-top: 0.5rem;">'
                '<span class="status-badge-connected">Backend connected</span>'
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align: right; padding-top: 0.5rem;">'
                '<span class="status-badge-offline">Backend offline</span>'
                "</div>",
                unsafe_allow_html=True,
            )

    # Fetch data from real backend endpoints
    overview_data: dict[str, Any] = {}
    overview_error: str | None = None
    clusters_data: list[dict[str, Any]] = []

    if backend_online:
        try:
            with st.spinner("Loading placement information..."):
                overview_data = load_overview_data()
                clusters_data = load_clusters_data()
        except APIClientError:
            overview_error = "We couldn't load placement information. Please verify that the Margdarshak backend is reachable and try again."
    else:
        overview_error = (
            "We couldn't connect to Margdarshak. Please ensure the backend server is running at http://127.0.0.1:8000 and try again."
        )

    if overview_error:
        st.error(overview_error, icon=":material/cloud_off:")


    # 2. Admin Overview Metrics (§26)
    st.markdown(
        '<div class="admin-section-header">:material/dashboard: Overview Metrics</div>',
        unsafe_allow_html=True,
    )
    metrics = overview_data.get("metrics") or {}
    m_open = metrics.get("open", 0)
    m_claimed = metrics.get("claimed", 0)
    m_waiting = metrics.get("waiting", 0)
    m_escalated = metrics.get("escalated", 0)
    m_resolved = metrics.get("resolved", 0)

    metric_cols = st.columns(5)
    metric_definitions = [
        ("Open", m_open, "#DC2626"),
        ("Claimed", m_claimed, "#2563EB"),
        ("Waiting", m_waiting, "#D97706"),
        ("Escalated", m_escalated, "#9333EA"),
        ("Resolved", m_resolved, "#16A34A"),
    ]

    for col, (label, value, accent_color) in zip(metric_cols, metric_definitions):
        with col:
            st.markdown(
                f"""
                <div class="metric-card-container" style="border-top: 3px solid {accent_color};">
                    <div class="metric-card-label">{label}</div>
                    <div class="metric-card-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 3. Two-Column Operational Layout for Alerts & Drives/Feed
    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    with col_left:
        # Priority Alerts (§27)
        st.markdown(
            '<div class="admin-section-header">:material/notification_important: Priority Alerts</div>',
            unsafe_allow_html=True,
        )

        # Merge clusters and priority tickets to rank incidents per §27
        alert_items: list[dict[str, Any]] = []

        # Add active clusters
        for cluster in clusters_data:
            if cluster.get("status") != "resolved":
                alert_items.append({
                    "id": cluster.get("id"),
                    "title": cluster.get("title"),
                    "urgency": cluster.get("urgency", "high"),
                    "affected_students": cluster.get("affected_students", 2),
                    "company": cluster.get("company_name"),
                    "context": cluster.get("incident_update") or cluster.get("response_draft") or "Repeated issue cluster",
                    "deadline": None,
                    "is_cluster": True,
                })

        # Add priority tickets from overview
        for ticket in overview_data.get("priority_tickets", []):
            intel = ticket.get("intelligence") or {}
            plac = ticket.get("placement") or {}
            # Avoid duplicate if ticket is already part of a cluster alert
            alert_items.append({
                "id": ticket.get("id"),
                "title": ticket.get("issue_summary"),
                "urgency": intel.get("urgency", "medium"),
                "affected_students": 1,
                "company": plac.get("company") or ticket.get("company_name"),
                "context": f"Role: {plac.get('role') or 'General'} · Round: {plac.get('round') or 'Assessment'}",
                "deadline": plac.get("deadline"),
                "is_cluster": False,
                "ticket_id": ticket.get("id"),
                "student_roll": ticket.get("student", {}).get("enrollment_number"),
            })

        # Sort per §27 priority factors
        alert_items.sort(key=calculate_priority_score, reverse=True)

        # Display top alerts
        top_alerts = alert_items[:4]
        if top_alerts:
            for alert in top_alerts:
                urgency = str(alert.get("urgency", "medium")).lower()
                badge_class = urgency if urgency in {"critical", "high", "medium", "low"} else "medium"
                badge_label = f"⚠ {urgency.upper()} PRIORITY" if urgency in {"critical", "high"} else f"{urgency.upper()} PRIORITY"
                
                title = alert.get("title") or "Placement incident"
                affected_count = alert.get("affected_students", 1)
                affected_str = f"{affected_count} student{'s' if affected_count != 1 else ''} affected"
                company = alert.get("company") or "Active Drive"
                context = alert.get("context") or ""
                deadline = alert.get("deadline")

                deadline_html = (
                    f'<span style="color: #DC2626; font-weight: 500;">Deadline: {deadline}</span> · '
                    if deadline
                    else ""
                )

                st.markdown(
                    f"""
                    <div class="priority-alert-card {badge_class}">
                        <span class="priority-badge {badge_class}">{badge_label}</span>
                        <div class="priority-title">{title}</div>
                        <div class="priority-meta">
                            <span><strong>{affected_str}</strong></span> ·
                            <span>{company}</span> ·
                            <span>{context}</span> ·
                            {deadline_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            
            st.page_link(
                "pages/1_Triage_Kanban.py",
                label="View issues in Kanban →",
                icon=":material/arrow_forward:",
            )
        else:
            st.info(
                "No urgent incidents or high-priority tickets flagged at this time.",
                icon=":material/check_circle:",
            )

    with col_right:
        # Active Placement Drives (§28)
        st.markdown(
            '<div class="admin-section-header">:material/business_center: Active Placement Drives</div>',
            unsafe_allow_html=True,
        )
        active_drives = overview_data.get("active_drives", [])

        if active_drives:
            for drive in active_drives:
                company = drive.get("company") or "Company Drive"
                status = str(drive.get("status", "active")).upper()
                policy = drive.get("policy") or "Policy active"
                st.markdown(
                    f"""
                    <div class="drive-card">
                        <span class="drive-status-pill">{status}</span>
                        <div class="drive-company">{company}</div>
                        <div class="drive-detail">{policy}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No active placement drives found in the system.")

        # Recent Updates Feed (§29)
        st.markdown(
            '<div class="admin-section-header">:material/history: Recent Updates</div>',
            unsafe_allow_html=True,
        )
        recent_updates = overview_data.get("recent_updates", [])

        if recent_updates:
            for update in recent_updates:
                kind = str(update.get("kind", "ticket")).lower()
                kind_class = "update-kind-ticket" if kind == "ticket" else "update-kind-knowledge"
                kind_label = "TICKET" if kind == "ticket" else "KNOWLEDGE"
                text = update.get("text", "")
                formatted_time = format_relative_time(update.get("at"))

                st.markdown(
                    f"""
                    <div class="update-item">
                        <span class="update-kind-tag {kind_class}">{kind_label}</span>
                        <div style="flex: 1;">{text}</div>
                        <span class="update-time">{formatted_time}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No recent updates recorded yet.")

    # Operational Navigation Links & Endpoint Specification Footnote
    st.divider()
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        st.page_link(
            "pages/1_Triage_Kanban.py",
            label="Open Tickets Kanban Board",
            icon=":material/view_kanban:",
        )
    with nav_col2:
        st.page_link(
            "pages/2_Telemetry.py",
            label="Open Coordinator Stats",
            icon=":material/monitoring:",
        )
    with nav_col3:
        st.page_link(
            "pages/3_Knowledge.py",
            label="Open Knowledge Approval",
            icon=":material/menu_book:",
        )

    # Endpoint notes per specification requirements
    st.markdown(
        """
        <div class="endpoint-flag-notice">
            <strong>Operational API Mapping Notes:</strong><br/>
            • <strong>Overview & Metrics:</strong> Sourced live from <code>GET /api/v1/admin/overview</code>.<br/>
            • <strong>Drives:</strong> Standalone <code>GET /drives</code> does not exist on backend; active drives are retrieved from <code>GET /api/v1/admin/overview</code>. <code>PlacementDrive</code> stores policy reference; role/round fields are mapped when shortlists are linked.<br/>
            • <strong>Stats:</strong> Lifecycle metrics are retrieved from <code>GET /api/v1/admin/overview</code>; operational telemetry is at <code>GET /api/v1/admin/stats</code>.<br/>
            • <strong>Knowledge Management:</strong> Policies & lifecycle wired to <code>POST /knowledge/policy</code>, <code>GET /knowledge</code>, and <code>PATCH /knowledge/{id}</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )


page = st.navigation(
    [
        st.Page(home, title="Home", icon=":material/home:"),
        st.Page(
            "pages/1_Triage_Kanban.py",
            title="Tickets",
            icon=":material/view_kanban:",
        ),
        st.Page(
            "pages/2_Telemetry.py",
            title="Stats",
            icon=":material/monitoring:",
        ),
        st.Page(
            "pages/3_Knowledge.py",
            title="Knowledge",
            icon=":material/menu_book:",
        ),
    ],
    position="sidebar",
)
page.run()


