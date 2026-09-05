from datetime import datetime
from typing import Any
import uuid

import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from services.api_client import (
    APIClientError,
    get_admin_clusters,
    get_admin_ticket,
    get_admin_tickets,
    patch_admin_ticket,
    post_admin_agora_session,
    post_cluster_draft_response,
    post_cluster_publish_update,
    post_cluster_resolve,
)

st.set_page_config(
    page_title="Tickets — Margdarshak AI",
    page_icon=":material/view_kanban:",
    layout="wide",
)

# Admin Design System (§65):
# Background: Light grey / blue-grey (#F8FAFC)
# Primary: Dark charcoal (#0F172A / #1E293B)
# Accent: Muted green (#2E7D32 / #166534)
# Cards: Simple borders (#E2E8F0), minimal shadows, compact operational layout
# ──────────────────────────────────────────────
# Styles: Kanban board + ticket detail panel (§34)
# ──────────────────────────────────────────────
KANBAN_CSS = """
<style>
    /* Base background and layout */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Header layout (§30) */
    .tickets-header-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 0.25rem 0;
        padding: 0;
    }
    .tickets-header-subtitle {
        font-size: 0.95rem;
        color: #475569;
        margin: 0 0 1.25rem 0;
    }

    /* Column Header (§31) */
    .kanban-col-header {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.6rem 0.85rem;
        margin-bottom: 0.75rem;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .col-count-badge {
        background-color: #F1F5F9;
        color: #334155;
        border: 1px solid #CBD5E1;
        padding: 0.1rem 0.45rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Ticket Card Component (§32) */
    .ticket-card-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.85rem 0.95rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .ticket-card-box:hover {
        border-color: #CBD5E1;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .ticket-card-box.urgent-critical {
        border-left: 4px solid #DC2626;
        background-color: #FEF2F208;
    }
    .ticket-card-box.urgent-high {
        border-left: 4px solid #EA580C;
    }
    .ticket-card-box.urgent-medium {
        border-left: 4px solid #D97706;
    }
    .ticket-card-box.urgent-low {
        border-left: 4px solid #16A34A;
    }
    
    .ticket-card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.45rem;
    }
    .ticket-id-tag {
        font-size: 0.82rem;
        font-weight: 700;
        color: #0F172A;
    }
    .ticket-confidence-badge {
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
    }
    .confidence-high {
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
    }
    .confidence-medium {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .confidence-low {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
    }

    .ticket-summary {
        font-size: 0.88rem;
        font-weight: 500;
        color: #1E293B;
        line-height: 1.35;
        margin-bottom: 0.6rem;
    }

    .ticket-meta-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.35rem 0.5rem;
        font-size: 0.75rem;
        color: #64748B;
        margin-bottom: 0.55rem;
        border-top: 1px solid #F1F5F9;
        padding-top: 0.45rem;
    }
    .ticket-meta-grid span strong {
        color: #334155;
    }

    .urgency-pill {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 0.1rem 0.35rem;
        border-radius: 3px;
    }
    .urgency-critical {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
    }
    .urgency-high {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .urgency-medium {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }
    .urgency-low {
        background-color: #F0FDF4;
        color: #15803D;
        border: 1px solid #BBF7D0;
    }

    .ticket-created {
        font-size: 0.72rem;
        color: #94A3B8;
        margin-bottom: 0.5rem;
    }

    .kanban-empty {
        background-color: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 6px;
        padding: 1.5rem 0.75rem;
        text-align: center;
        color: #94A3B8;
        font-size: 0.8rem;
    }

    /* ── Detail Panel (§34) ── */
    .panel-section-header {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 0.3rem;
        margin: 1rem 0 0.5rem 0;
    }
    .panel-field-row {
        display: flex;
        gap: 0.4rem;
        margin-bottom: 0.3rem;
        font-size: 0.83rem;
        line-height: 1.4;
    }
    .panel-field-label {
        color: #64748B;
        min-width: 7rem;
        flex-shrink: 0;
        font-weight: 500;
    }
    .panel-field-value {
        color: #0F172A;
        font-weight: 500;
        word-break: break-word;
    }
    .panel-field-value.empty {
        color: #94A3B8;
        font-style: italic;
        font-weight: 400;
    }
    .panel-source-badge {
        display: inline-block;
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-right: 0.3rem;
        margin-bottom: 0.3rem;
    }
    .panel-action-bar {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 1rem;
        padding-top: 0.75rem;
        border-top: 1px solid #E2E8F0;
    }

    /* ── Cluster Cards (§36, §37, §38) ── */
    .cluster-section-header {
        font-size: 1rem;
        font-weight: 700;
        color: #0F172A;
        margin: 1.75rem 0 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .cluster-section-subtitle {
        font-size: 0.82rem;
        color: #64748B;
        margin-bottom: 1rem;
    }
    .cluster-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .cluster-card-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .cluster-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #0F172A;
    }
    .cluster-meta {
        font-size: 0.78rem;
        color: #475569;
        margin-bottom: 0.6rem;
    }
    .cluster-meta strong {
        color: #0F172A;
    }
    .cluster-priority-badge {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        white-space: nowrap;
    }
    .cluster-priority-critical { background-color: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
    .cluster-priority-high     { background-color: #FFF7ED; color: #9A3412; border: 1px solid #FED7AA; }
    .cluster-priority-medium   { background-color: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
    .cluster-priority-low      { background-color: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
    .cluster-resolved-badge    { background-color: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }
    .cluster-status-pill {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.12rem 0.45rem;
        border-radius: 9999px;
        text-transform: capitalize;
    }
    .cluster-status-open      { background-color: #EFF6FF; color: #1D4ED8; }
    .cluster-status-resolved  { background-color: #F1F5F9; color: #64748B; }
    .cluster-incident-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.25rem;
        margin-top: 0.75rem;
    }
    .cluster-incident-preview {
        font-size: 0.8rem;
        color: #334155;
        font-style: italic;
        padding: 0.4rem 0.65rem;
        background-color: #F8FAFC;
        border-left: 3px solid #CBD5E1;
        border-radius: 0 4px 4px 0;
        margin-bottom: 0.6rem;
    }
    .cluster-empty {
        background-color: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 0.35rem;
        color: #94A3B8;
        font-size: 0.82rem;
    }

    /* ── Agora & Draft Response (§39, §40) ── */
    .agora-session-box {
        background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
    }
    .agora-session-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.82rem;
        font-weight: 700;
        color: #1E40AF;
        margin-bottom: 0.25rem;
    }
    .agora-status-pill {
        background-color: #DBEAFE;
        color: #1E40AF;
        font-size: 0.7rem;
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
        font-weight: 600;
    }
    .draft-response-container {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
    }
    .draft-response-header {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #166534;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .draft-response-body {
        font-size: 0.88rem;
        color: #0F172A;
        white-space: pre-wrap;
        line-height: 1.5;
        background-color: #FFFFFF;
        border: 1px solid #DCFCE7;
        border-radius: 6px;
        padding: 0.75rem 0.85rem;
        margin-bottom: 0.75rem;
    }
</style>
"""

STATUSES = (
    ("open", "OPEN", "#DC2626"),
    ("claimed", "CLAIMED", "#2563EB"),
    ("waiting", "WAITING", "#D97706"),
    ("escalated", "ESCALATED", "#9333EA"),
    ("resolved", "RESOLVED", "#16A34A"),
)


@st.cache_data(ttl=15, show_spinner=False)
def load_admin_tickets_data(
    drive_id: str | None,
    company: str | None,
    round_name: str | None,
    coordinator: str | None,
    language: str | None,
    urgency: str | None,
) -> list[dict[str, Any]]:
    """Fetch tickets filtered by coordinator parameters."""
    return get_admin_tickets(
        drive_id=drive_id or None,
        company=company or None,
        round_name=round_name or None,
        coordinator=coordinator or None,
        language=language or None,
        urgency=urgency or None,
    )


def format_created_at(value: str | datetime | None) -> str:
    """Format created date per §32: 'Created: 05 Sep 2026 · 20:57'."""
    if not value:
        return "Unknown"
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y · %H:%M")
    except Exception:
        return str(value)[:16]


import json

AGORA_HTML = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; background: #EFF6FF; margin: 0; padding: 15px; border-radius: 8px; border: 1px solid #BFDBFE; color: #1E40AF; }
    h4 { margin: 0 0 10px 0; font-size: 14px; display: flex; align-items: center; }
    p { font-size: 13px; margin: 5px 0; }
    button { background: #1E40AF; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; margin-top: 10px; font-weight: 600; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
  </style>
  <script src="https://download.agora.io/sdk/release/AgoraRTC_N-4.20.0.js"></script>
</head>
<body>
  <h4>🎙️ Agora Voice Session</h4>
  <p id="status">Connecting to backend AI...</p>
  <button id="btn" disabled>■ Stop & Generate Draft</button>
  <script>
    const session = _SESSION_JSON_;
    const clusterId = "_CLUSTER_ID_";
    const apiUrl = "_API_URL_";
    let transcript = "";
    
    async function start() {
      try {
        const client = AgoraRTC.createClient({mode:"rtc", codec:"vp8"});
        await client.join(session.app_id, session.channel_name, session.rtc_token, session.uid);
        const mic = await AgoraRTC.createMicrophoneAudioTrack();
        await client.publish(mic);
        
        document.getElementById("status").innerText = "Listening... Speak the student update.";
        document.getElementById("btn").disabled = false;
        
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
          const rec = new SpeechRec();
          rec.continuous = true;
          rec.interimResults = false;
          rec.lang = "en-IN";
          rec.onresult = (e) => {
             transcript = Array.from(e.results).map(r => r[0].transcript).join(" ");
          };
          rec.start();
          
          document.getElementById("btn").onclick = async () => {
            rec.stop();
            mic.stop(); mic.close(); await client.leave();
            document.getElementById("status").innerText = "Drafting with AI...";
            document.getElementById("btn").disabled = true;
            
            fetch(`${apiUrl}/admin/clusters/${clusterId}/draft-response`, {
               method: "POST",
               headers: { "Content-Type": "application/json", "Authorization": "Bearer local-admin-demo" },
               body: JSON.stringify({ notes: transcript || "The placement team is reviewing this issue." })
            }).then(() => {
               window.parent.location.reload();
            }).catch(err => {
               document.getElementById("status").innerText = "Failed to draft: " + err.message;
            });
          };
        } else {
           document.getElementById("status").innerText = "Browser doesn't support speech recognition.";
        }
      } catch (err) {
        document.getElementById("status").innerText = "Error connecting to Agora: " + err.message;
      }
    }
    start();
  </script>
</body>
</html>
"""

@st.cache_data(ttl=30, show_spinner=False)
def load_admin_clusters_data() -> list[dict[str, Any]]:
    """Fetch and cache the cluster list. TTL matches ticket refresh cycle."""
    return get_admin_clusters()


def _cluster_priority_badge(urgency: str, status: str) -> str:
    """Return HTML badge for cluster priority (§37)."""
    if status == "resolved":
        return '<span class="cluster-priority-badge cluster-resolved-badge">Resolved</span>'
    u = urgency.lower()
    css = {
        "critical": "cluster-priority-critical",
        "high": "cluster-priority-high",
        "medium": "cluster-priority-medium",
        "low": "cluster-priority-low",
    }.get(u, "cluster-priority-medium")
    return f'<span class="cluster-priority-badge {css}">{u.capitalize()}</span>'


def _cluster_status_pill(status: str) -> str:
    css = "cluster-status-resolved" if status == "resolved" else "cluster-status-open"
    return f'<span class="cluster-status-pill {css}">{status.capitalize()}</span>'


def render_cluster_card(cluster: dict[str, Any]) -> None:
    """Render one ClusterCard per spec §36 / §37 / §38.

    Header:  Title · N students · Status  +  Priority badge
    Body:    Company, Priority score (from server §37 calculation)
             Existing incident update preview (if any)
             Incident update textarea  +  [ Publish update ]  [ Resolve cluster ]
    """
    cluster_id = str(cluster.get("id") or "")
    title = str(cluster.get("title") or "Untitled cluster")
    company = cluster.get("company_name") or ""
    urgency = str(cluster.get("urgency") or "medium")
    status = str(cluster.get("status") or "open").lower()
    affected = int(cluster.get("affected_students") or 0)
    priority_score = cluster.get("priority_score")
    incident_update = cluster.get("incident_update") or ""
    response_draft = cluster.get("response_draft") or ""
    is_resolved = status == "resolved"

    badge_html = _cluster_priority_badge(urgency, status)
    status_html = _cluster_status_pill(status)
    score_text = (
        f" &nbsp;&middot;&nbsp; Score: {priority_score:.1f}"
        if isinstance(priority_score, (int, float))
        else ""
    )
    company_html = (
        f' &nbsp;&middot;&nbsp; <strong>{company}</strong>' if company else ""
    )

    # ── Card header (HTML only — no interactive widgets inside) ──
    st.markdown(
        f"""
        <div class="cluster-card">
            <div class="cluster-card-header">
                <div>
                    <div class="cluster-title">{title}</div>
                    <div class="cluster-meta">
                        <strong>{affected}</strong> student{'s' if affected != 1 else ''} affected
                        {company_html}
                        &nbsp;&middot;&nbsp; {status_html}{score_text}
                    </div>
                </div>
                {badge_html}
            </div>""",
        unsafe_allow_html=True,
    )

    # Show existing incident update preview
    if incident_update:
        st.markdown(
            f"""
            <div class="cluster-incident-label">Last update</div>
            <div class="cluster-incident-preview">{incident_update}</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if is_resolved:
        st.caption("\u2713 Resolved — archived as institutional knowledge.")
        return

    # ── AI Draft Response / Edit / Approve (§39, §40, §41, §42) ──
    if response_draft:
        st.markdown('<div class="draft-response-container">', unsafe_allow_html=True)
        st.markdown('<div class="draft-response-header">:material/auto_awesome: AI Drafted Response</div>', unsafe_allow_html=True)
        
        edited_draft = st.text_area(
            "Review and edit draft",
            value=response_draft,
            height=120,
            key=f"edit_draft_{cluster_id}",
            label_visibility="collapsed"
        )
        
        app_col, can_col, _ = st.columns([0.35, 0.3, 0.35])
        with app_col:
            if st.button("Approve & Send", key=f"approve_{cluster_id}", type="primary", use_container_width=True, help="Send to students, mark tickets resolved, and save to knowledge"):
                try:
                    with st.spinner("Publishing response and resolving linked tickets..."):
                        # Publish update (sends StudentNotifications)
                        post_cluster_publish_update(cluster_id, message=edited_draft.strip())
                        # Resolve cluster (resolves tickets + adds KnowledgeDocument per §42)
                        resolved_info = post_cluster_resolve(cluster_id)
                    count = resolved_info.get("resolved", "?")
                    load_admin_clusters_data.clear()
                    load_admin_tickets_data.clear()
                    st.success(f"Update sent! {count} tickets resolved and added to knowledge.", icon=":material/check_circle:")
                    st.rerun()
                except APIClientError:
                    st.error("We couldn't approve and publish the response. Please try again.", icon=":material/error:")
        
        with can_col:
            if st.button("Cancel", key=f"cancel_{cluster_id}", use_container_width=True):
                # The backend doesn't have a route to clear the draft, so we just clear our local view by re-fetching
                load_admin_clusters_data.clear()
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)
        return  # hide the standard update box while reviewing draft

    # ── Incident update textarea + actions (§38) ──
    update_text = st.text_area(
        "Incident update",
        key=f"cluster_update_text_{cluster_id}",
        placeholder="Write an update to send to all affected students…",
        height=90,
        label_visibility="collapsed",
        help="Delivered as a StudentNotification to every student in this cluster.",
    )

    agora_col, pub_col, res_col = st.columns([0.36, 0.32, 0.32])

    with agora_col:
        draft_key = f"agora_draft_{cluster_id}"
        if st.button("Draft response with Agora", key=f"draft_{cluster_id}", icon=":material/mic:", use_container_width=True):
            st.session_state[draft_key] = True

    if st.session_state.get(draft_key):
        try:
            with st.spinner("Connecting to Margdarshak..."):
                session = post_admin_agora_session()
            html_content = AGORA_HTML.replace("_SESSION_JSON_", json.dumps(session)) \
                                     .replace("_CLUSTER_ID_", cluster_id) \
                                     .replace("_API_URL_", "http://127.0.0.1:8000/api/v1")
            components.html(html_content, height=180)
        except Exception:
            st.error(
                "Agora connection failed: We couldn't establish a voice drafting channel. "
                "You can still draft responses or publish incident updates using the text editor below.",
                icon=":material/mic_off:",
            )

    with pub_col:
        if st.button(
            "Publish update",
            key=f"cluster_publish_{cluster_id}",
            icon=":material/send:",
            disabled=not (update_text or "").strip(),
            use_container_width=True,
            help="Send this update to all affected students and record it on the cluster.",
        ):
            try:
                with st.spinner("Publishing update to affected students..."):
                    result = post_cluster_publish_update(cluster_id, message=update_text.strip())
                notified = result.get("notified_students", "?")
                load_admin_clusters_data.clear()
                load_admin_tickets_data.clear()
                st.success(
                    f"Update published — {notified} student notification(s) sent.",
                    icon=":material/check_circle:",
                )
                st.rerun()
            except APIClientError:
                st.error("We couldn't publish the incident update. Please try again.", icon=":material/error:")

    with res_col:
        if st.button(
            "Resolve cluster",
            key=f"cluster_resolve_{cluster_id}",
            icon=":material/check:",
            type="primary",
            use_container_width=True,
            help=(
                "Resolve cluster: marks all linked tickets as resolved "
                "and saves the resolution as institutional knowledge (§42)."
            ),
        ):
            try:
                with st.spinner("Resolving issue cluster and saving to knowledge base..."):
                    result = post_cluster_resolve(cluster_id)
                resolved_count = result.get("resolved", "?")
                load_admin_clusters_data.clear()
                load_admin_tickets_data.clear()
                st.success(
                    f"Cluster resolved — {resolved_count} ticket(s) closed and saved to knowledge base.",
                    icon=":material/check_circle:",
                )
                st.rerun()
            except APIClientError:
                st.error("We couldn't resolve the cluster. Please try again.", icon=":material/error:")


def render_clusters_section() -> None:
    """Render the 'Repeated issue clusters' section per spec §36.

    Loads all clusters from GET /admin/clusters (priority calculated server-side
    per §37 factors: affected_students, ticket urgency, deadline proximity,
    frequency, blocked status). Sorts by priority_score descending.
    Active clusters shown first; resolved clusters in a collapsed expander.

    Backend gap flagged: GET /admin/clusters/{id} does NOT exist.
    Single-cluster reads are handled by filtering the list response client-side.
    """
    try:
        with st.spinner("Loading placement information..."):
            clusters = load_admin_clusters_data()
    except APIClientError:
        st.warning(
            "We couldn't load repeated issue clusters. Please verify the backend connection and try again.",
            icon=":material/warning:",
        )
        return

    if not clusters:
        st.markdown(
            '<div class="cluster-empty">No issue clusters found. Clusters are created '
            'automatically when multiple students report the same problem.</div>',
            unsafe_allow_html=True,
        )
        return

    def _sort_key(c: dict[str, Any]) -> tuple[float, int]:
        """Sort by priority_score desc, then affected_students desc (§37)."""
        return (-float(c.get("priority_score") or 0), -int(c.get("affected_students") or 0))

    sorted_clusters = sorted(clusters, key=_sort_key)
    active = [c for c in sorted_clusters if str(c.get("status") or "open") != "resolved"]
    resolved = [c for c in sorted_clusters if str(c.get("status") or "open") == "resolved"]

    for cluster in active:
        render_cluster_card(cluster)

    if resolved:
        with st.expander(f"\u2713 {len(resolved)} resolved cluster(s)", expanded=False):
            for cluster in resolved:
                render_cluster_card(cluster)


def render_ticket_card(ticket: dict[str, Any]) -> None:
    """Render the TicketCard component per spec section 32 and UX rules §66:

    Displays:
    - Ticket ID & Student Name (§66)
    - Confidence %
    - Issue Summary
    - Urgency (with visual priority accent per §66)
    - Ownership / Assigned Coordinator (§66)
    - Language
    - Status
    - Placement Context (Company / Drive / Round)
    - Knowledge Source (verified policy/doc/shortlist used per §66)
    - Created At
    - [ View details ] button
    """
    ticket_id = str(ticket.get("id") or "")
    student = ticket.get("student") or {}
    enrollment = student.get("enrollment_number") or ticket.get("roll_number_snapshot") or ticket_id[:8]
    student_name = student.get("name")
    card_title = f"Ticket {enrollment}" + (f" · {student_name}" if student_name else "")

    confidence = float(ticket.get("confidence_score") or 0.0)
    conf_pct = int(round(confidence * 100))
    if conf_pct >= 90:
        conf_class = "confidence-high"
    elif conf_pct >= 70:
        conf_class = "confidence-medium"
    else:
        conf_class = "confidence-low"

    summary = str(ticket.get("issue_summary") or "No issue summary recorded")
    intelligence = ticket.get("intelligence") or {}
    urgency = str(intelligence.get("urgency") or "medium").lower()
    urgency_class = f"urgency-{urgency}" if urgency in {"critical", "high", "medium", "low"} else "urgency-medium"
    card_urgency_class = f"urgent-{urgency}" if urgency in {"critical", "high", "medium", "low"} else "urgent-medium"

    coordinator = intelligence.get("assigned_coordinator") or "Unassigned"
    language = str(intelligence.get("language") or "English")
    status_label = str(ticket.get("status") or "open").capitalize()
    created_str = format_created_at(ticket.get("created_at"))

    placement = ticket.get("placement") or {}
    company_name = placement.get("company") or ticket.get("company_name") or "General"
    
    # Knowledge source per §66
    case_card = ticket.get("case_card") or {}
    policy = case_card.get("policy") if isinstance(case_card.get("policy"), dict) else {}
    source_ref = ticket.get("source") or policy.get("source") or case_card.get("source") or "Placement policy"
    source_str = str(source_ref).lower()
    if "shortlist" in source_str:
        source_display = "Shortlist"
    elif "resolved" in source_str:
        source_display = "Resolved issue"
    elif "policy" in source_str or "manual" in source_str:
        source_display = "Placement policy"
    else:
        source_display = "Company doc"

    st.markdown(
        f"""
        <div class="ticket-card-box {card_urgency_class}">
            <div class="ticket-card-top">
                <span class="ticket-id-tag">{card_title}</span>
                <span class="ticket-confidence-badge {conf_class}">Confidence {conf_pct}%</span>
            </div>
            <div class="ticket-summary">{summary}</div>
            <div class="ticket-meta-grid">
                <span>Urgency: <span class="urgency-pill {urgency_class}">{urgency.capitalize()}</span></span>
                <span>Owner: <strong>{coordinator}</strong></span>
                <span>Language: <strong>{language}</strong></span>
                <span>Status: <strong>{status_label}</strong></span>
                <span>Context: <strong>{company_name}</strong></span>
                <span>Source: <strong>{source_display}</strong></span>
            </div>
            <div class="ticket-created">Created: {created_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # [ View details ] button — toggles the side panel via session state
    is_open = st.session_state.get("detail_panel_ticket_id") == ticket_id
    btn_label = "Close panel" if is_open else "View details"
    btn_icon = ":material/close:" if is_open else ":material/description:"
    if st.button(
        btn_label,
        key=f"btn_details_{ticket_id}",
        icon=btn_icon,
        use_container_width=True,
    ):
        if is_open:
            st.session_state.pop("detail_panel_ticket_id", None)
        else:
            st.session_state["detail_panel_ticket_id"] = ticket_id
        st.rerun()


def _field(label: str, value: Any, *, empty_text: str = "Not recorded") -> str:
    """Render a key/value row for the detail panel."""
    v = str(value).strip() if value else ""
    val_class = "panel-field-value" if v else "panel-field-value empty"
    display = v if v else empty_text
    return (
        f'<div class="panel-field-row">'
        f'<span class="panel-field-label">{label}</span>'
        f'<span class="{val_class}">{display}</span>'
        f"</div>"
    )



def render_ticket_detail_panel(ticket_id: str) -> None:
    """Full ticket detail side panel per spec §34.

    Sections:
    1. Student Information
    2. Issue Information
    3. Placement Context
    4. AI Intelligence
    5. Source
    6. Actions: Claim / Escalate / Resolve / Dismiss (wired to PATCH /admin/tickets/{id})
    """
    try:
        with st.spinner("Loading placement information..."):
            ticket = get_admin_ticket(ticket_id)
    except APIClientError:
        st.error("We couldn't load the ticket details. Please try again.", icon=":material/error:")
        return

    student = ticket.get("student") or {}
    intelligence = ticket.get("intelligence") or {}
    placement = ticket.get("placement") or {}
    case_card = ticket.get("case_card") or {}
    policy = case_card.get("policy") if isinstance(case_card.get("policy"), dict) else {}
    current_status = str(ticket.get("status") or "open").lower()
    enrollment = student.get("enrollment_number") or ticket_id[:8]

    st.markdown(
        f'<div class="panel-section-header">Student — Ticket {enrollment}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _field("Name", student.get("name"))
        + _field("Enrollment", student.get("enrollment_number"))
        + _field("Email", student.get("email")),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel-section-header">Issue Information</div>', unsafe_allow_html=True)
    st.markdown(
        _field("Summary", ticket.get("issue_summary"))
        + _field("Original request", ticket.get("original_request"))
        + _field("Conversation summary", ticket.get("conversation_summary"))
        + _field("Category", intelligence.get("category")),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel-section-header">Placement Context</div>', unsafe_allow_html=True)
    st.markdown(
        _field("Company", placement.get("company"))
        + _field("Drive ID", placement.get("drive_id"))
        + _field("Role", placement.get("role"))
        + _field("Round", placement.get("round"))
        + _field("Deadline", placement.get("deadline")),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel-section-header">AI Intelligence</div>', unsafe_allow_html=True)
    confidence = float(ticket.get("confidence_score") or 0.0)
    st.markdown(
        _field("Detected language", intelligence.get("language"))
        + _field("Confidence", f"{int(round(confidence * 100))}%")
        + _field("Urgency", (intelligence.get("urgency") or "medium").capitalize())
        + _field("Assigned Coordinator", intelligence.get("assigned_coordinator") or "Unassigned")
        + _field("Cluster", intelligence.get("cluster_id"), empty_text="None"),
        unsafe_allow_html=True,
    )

    # Source section — surface verified knowledge used during analysis
    st.markdown('<div class="panel-section-header">Source</div>', unsafe_allow_html=True)
    source_ref = (
        ticket.get("source")
        or policy.get("source")
        or case_card.get("source")
    )
    if source_ref:
        kind = str(source_ref).lower()
        if "shortlist" in kind:
            badge_text = "Shortlist"
        elif "resolved" in kind:
            badge_text = "Resolved issue"
        elif "policy" in kind or "manual" in kind:
            badge_text = "Placement policy"
        else:
            badge_text = "Company document"
        st.markdown(
            f'<span class="panel-source-badge">{badge_text}</span><br/>'
            f'<small style="color:#64748B">{source_ref}</small>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No verified source matched during analysis.")

    # ── Actions (§34, §44 lifecycle) ──────────────────────────────
    st.markdown('<div class="panel-section-header">Actions</div>', unsafe_allow_html=True)

    def _do_patch(new_status: str, summary_note: str | None = None) -> None:
        """Fire PATCH, show success/failure, clear caches and rerun."""
        try:
            with st.spinner("Updating ticket status..."):
                patch_admin_ticket(
                    ticket_id,
                    status=new_status,
                    conversation_summary=summary_note,
                )
            st.session_state.pop("detail_panel_ticket_id", None)
            load_admin_tickets_data.clear()
            st.success(
                f"Ticket {enrollment} → {new_status.capitalize()}",
                icon=":material/check_circle:",
            )
            st.rerun()
        except APIClientError:
            st.error("We couldn't update the ticket status. Please try again.", icon=":material/error:")

    # Lifecycle §44: OPEN → CLAIMED → WAITING/ESCALATED → RESOLVED
    # Show contextually relevant actions based on current status
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)

    with action_col1:
        claim_disabled = current_status in {"claimed", "resolved"}
        if st.button(
            "Claim",
            key=f"action_claim_{ticket_id}",
            icon=":material/person:",
            disabled=claim_disabled,
            use_container_width=True,
            help="Mark this ticket as claimed by a coordinator (OPEN → CLAIMED).",
        ):
            _do_patch("claimed")

    with action_col2:
        escalate_disabled = current_status == "resolved"
        if st.button(
            "Escalate",
            key=f"action_escalate_{ticket_id}",
            icon=":material/arrow_upward:",
            disabled=escalate_disabled,
            use_container_width=True,
            help="Escalate this ticket (→ ESCALATED). Use when the issue needs senior review.",
        ):
            _do_patch("escalated")

    with action_col3:
        resolve_disabled = current_status == "resolved"
        if st.button(
            "Resolve",
            key=f"action_resolve_{ticket_id}",
            icon=":material/check:",
            type="primary",
            disabled=resolve_disabled,
            use_container_width=True,
            help="Mark as resolved. Resolution becomes reusable knowledge (§42).",
        ):
            _do_patch("resolved")

    with action_col4:
        dismiss_disabled = current_status == "resolved"
        if st.button(
            "Dismiss",
            key=f"action_dismiss_{ticket_id}",
            icon=":material/cancel:",
            disabled=dismiss_disabled,
            use_container_width=True,
            help="Dismiss this ticket (closes without resolution).",
        ):
            _do_patch(
                "resolved",
                summary_note="Dismissed by coordinator — no further action required.",
            )


def main() -> None:
    st.markdown(KANBAN_CSS, unsafe_allow_html=True)

    # Section 30: Header
    st.markdown('<h1 class="tickets-header-title">Tickets</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="tickets-header-subtitle">Triage placement questions, keep ownership visible, and close the loop with students.</p>',
        unsafe_allow_html=True,
    )

    # Section 33: Ticket Filters & Controls in Sidebar
    with st.sidebar:
        st.header("Ticket Filters (§33)")
        
        # 1. Drive ID filter
        drive_filter = st.text_input(
            "Drive ID",
            placeholder="e.g. UUID or drive search",
            help="Filter by placement drive ID or identifier",
            key="t_filter_drive",
        ).strip()

        # 2. Company filter
        company_filter = st.text_input(
            "Company",
            placeholder="e.g. Acme, Riverbank",
            help="Filter by company name",
            key="t_filter_company",
        ).strip()

        # 3. Round filter
        round_filter = st.text_input(
            "Round",
            placeholder="e.g. Round 1, Technical",
            help="Filter by assessment or interview round",
            key="t_filter_round",
        ).strip()

        # 4. Coordinator filter (Ownership §66)
        coordinator_filter = st.text_input(
            "Coordinator ID / Name",
            placeholder="e.g. Priya",
            help="Filter by assigned coordinator (Ownership §66)",
            key="t_filter_coord",
        ).strip()

        # 5. Language filter
        language_options = ["All", "English", "Hindi", "Hinglish", "Tamil", "Telugu", "Other"]
        language_choice = st.selectbox("Language", options=language_options, index=0, key="t_filter_lang")
        language_filter = None if language_choice == "All" else language_choice

        # 6. Urgency filter
        urgency_options = ["All", "Critical", "High", "Medium", "Low"]
        urgency_choice = st.selectbox("Urgency", options=urgency_options, index=0, key="t_filter_urg")
        urgency_filter = None if urgency_choice == "All" else urgency_choice.lower()

        st.divider()

        # Action buttons for fast filtering per §66
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Refresh now", icon=":material/refresh:", use_container_width=True):
                load_admin_tickets_data.clear()
                st.rerun()
        with btn_col2:
            if st.button("Reset filters", icon=":material/filter_alt_off:", use_container_width=True):
                st.session_state["t_filter_drive"] = ""
                st.session_state["t_filter_company"] = ""
                st.session_state["t_filter_round"] = ""
                st.session_state["t_filter_coord"] = ""
                st.session_state["t_filter_lang"] = "All"
                st.session_state["t_filter_urg"] = "All"
                load_admin_tickets_data.clear()
                st.rerun()

        # Auto-refresh control per §33
        enable_autorefresh = st.checkbox("Periodic auto-refresh", value=True)
        if enable_autorefresh:
            refresh_interval = st.slider("Interval (seconds)", min_value=5, max_value=60, value=15, step=5)
            st_autorefresh(interval=refresh_interval * 1000, key="kanban_auto_refresh")
            st.caption(f"Refreshing automatically every {refresh_interval}s")

    # Load tickets with query parameters for the filters (Loading state per §68)
    try:
        with st.spinner("Searching approved placement information..."):
            tickets = load_admin_tickets_data(
                drive_id=drive_filter or None,
                company=company_filter or None,
                round_name=round_filter or None,
                coordinator=coordinator_filter or None,
                language=language_filter,
                urgency=urgency_filter,
            )
    except APIClientError:
        # Error state per §67: Avoid raw error messages like "Failed to fetch"
        st.error(
            "We couldn't load the support tickets. Please ensure the Margdarshak backend is reachable and try again.",
            icon=":material/cloud_off:",
        )
        st.stop()

    # Client-side fallback filter for drive free text (if non-UUID)
    if drive_filter:
        try:
            uuid.UUID(drive_filter)
        except ValueError:
            df_lower = drive_filter.lower()
            tickets = [
                t for t in tickets
                if df_lower in str(t.get("placement", {}).get("drive_id", "")).lower()
                or df_lower in str(t.get("placement", {}).get("company", "")).lower()
            ]

    # Empty ticket state per §67
    if not tickets:
        st.info(
            "📭 Empty ticket state: No support tickets found matching your filter criteria. "
            "All student queries are resolved or pending voice sessions.",
            icon=":material/inbox:",
        )

    # Section 31: Ticket Status Board (5 Kanban columns)
    tickets_by_status: dict[str, list[dict[str, Any]]] = {
        key: [] for key, _, _ in STATUSES
    }
    for ticket in tickets:
        st_val = str(ticket.get("status") or "open").lower()
        if st_val in tickets_by_status:
            tickets_by_status[st_val].append(ticket)
        else:
            tickets_by_status["open"].append(ticket)

    kanban_cols = st.columns(5, gap="small")
    urgency_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    for col, (status_key, label, accent_color) in zip(kanban_cols, STATUSES):
        # Visually prioritize urgent issues at the top of every column (UX Rule §66)
        col_tickets = sorted(
            tickets_by_status[status_key],
            key=lambda t: (
                urgency_rank.get(str(t.get("intelligence", {}).get("urgency", "medium")).lower(), 2),
                str(t.get("created_at") or ""),
            ),
        )
        with col:
            st.markdown(
                f"""
                <div class="kanban-col-header" style="border-top: 3px solid {accent_color};">
                    <span>{label}</span>
                    <span class="col-count-badge">{len(col_tickets)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if col_tickets:
                for t in col_tickets:
                    render_ticket_card(t)
            else:
                st.markdown(
                    f'<div class="kanban-empty">No {label.lower()} tickets</div>',
                    unsafe_allow_html=True,
                )


    # ── Repeated Issue Clusters (§36-§38) ──────────────────────────────
    st.divider()
    st.markdown(
        '<div class="cluster-section-header">'
        ':material/hub: Repeated issue clusters'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="cluster-section-subtitle">'
        'Groups of students reporting the same problem — sorted by priority score (§37).'
        '</div>',
        unsafe_allow_html=True,
    )
    render_clusters_section()


    # ── Detail Panel (§34) ──────────────────────────────────────────
    selected_ticket_id = st.session_state.get("detail_panel_ticket_id")
    if selected_ticket_id:
        st.divider()
        with st.container(border=True):
            close_col, title_col = st.columns([0.08, 0.92])
            with close_col:
                if st.button(
                    "✕",
                    key="close_detail_panel",
                    help="Close panel",
                ):
                    st.session_state.pop("detail_panel_ticket_id", None)
                    st.rerun()
            with title_col:
                st.markdown(
                    "<strong style='font-size:1rem; color:#0F172A;'>Ticket Detail</strong>",
                    unsafe_allow_html=True,
                )
            render_ticket_detail_panel(selected_ticket_id)


main()

