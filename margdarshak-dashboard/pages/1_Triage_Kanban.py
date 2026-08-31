from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from services.api_client import APIClientError, get_ticket, get_tickets

STATUSES = (
    ("open", "Open"),
    ("escalated", "Escalated"),
    ("resolved", "Resolved"),
)
CONFIDENCE_THRESHOLD = 0.90


@st.cache_data(ttl=10, max_entries=12, show_spinner=False)
def load_status(status: str) -> list[dict[str, Any]]:
    return get_tickets(status=status)


@st.cache_data(ttl=10, max_entries=100, show_spinner=False)
def load_ticket_detail(ticket_id: str) -> dict[str, Any]:
    return get_ticket(ticket_id)


def ticket_search_text(ticket: dict[str, Any]) -> str:
    case_card = ticket.get("case_card") or {}
    policy = case_card.get("policy") or {}
    values = (
        ticket.get("drive_id"),
        ticket.get("company_name"),
        case_card.get("drive_id"),
        policy.get("company_name"),
    )
    return " ".join(str(value) for value in values if value).lower()


def format_created_at(value: str | None) -> str:
    if not value:
        return "Unknown"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def truncate(value: str, limit: int = 145) -> str:
    normalized = " ".join(value.split())
    return normalized if len(normalized) <= limit else f"{normalized[: limit - 1]}…"


def render_case_card(case_card: dict[str, Any] | None) -> None:
    if not case_card:
        st.info("No case card has been recorded for this ticket yet.")
        return
    st.json(case_card, expanded=True)


def render_ticket(ticket: dict[str, Any]) -> None:
    ticket_id = str(ticket["id"])
    confidence = float(ticket.get("confidence_score") or 0.0)
    badge_color = "green" if confidence >= CONFIDENCE_THRESHOLD else "red"
    escalated_to = str(ticket.get("escalated_to") or "").strip()

    with st.container(border=True):
        st.markdown(f"**{ticket.get('roll_number_snapshot') or 'Unknown roll number'}**")
        st.markdown(f":{badge_color}-badge[Confidence {confidence:.0%}]")
        st.write(truncate(str(ticket.get("issue_summary") or "No issue summary")))
        if escalated_to:
            st.caption(f"Escalated to: {escalated_to}")
        st.caption(f"Created: {format_created_at(ticket.get('created_at'))}")

        is_selected = st.session_state.get("triage_selected_ticket") == ticket_id
        button_label = "Hide details" if is_selected else "View details"
        if st.button(
            button_label,
            key=f"triage_details_{ticket_id}",
            icon=":material/description:",
            width="stretch",
        ):
            st.session_state.triage_selected_ticket = None if is_selected else ticket_id
            st.rerun()

        if is_selected:
            try:
                detail = load_ticket_detail(ticket_id)
            except APIClientError as exc:
                st.error(f"Could not load case card: {exc}")
            else:
                render_case_card(detail.get("case_card"))


st.title("Tickets")
st.caption("Automatically refreshes every 15 seconds")

with st.sidebar:
    st.header("Filters")
    drive_filter = st.text_input(
        "Drive or company name",
        placeholder="Search by company or drive ID",
    ).strip().lower()
    if st.button("Refresh now", icon=":material/refresh:", width="stretch"):
        load_status.clear()
        load_ticket_detail.clear()
        st.rerun()
    st.caption("Read-only data from the Margdarshak API")

st_autorefresh(interval=15_000, key="triage_board_refresh")

board_columns = st.columns(3, gap="medium")

try:
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            status: executor.submit(load_status, status) for status, _ in STATUSES
        }
        tickets_by_status = {
            status: futures[status].result() for status, _ in STATUSES
        }
except APIClientError as exc:
    st.error(
        "The backend is not reachable. Start FastAPI on port 8000 and try again.",
        icon=":material/cloud_off:",
    )
    st.caption(str(exc))
    st.stop()

if not any(tickets_by_status.values()):
    st.info(
        "Connected successfully, but there are no tickets yet. Tickets appear "
        "after a voice triage session is started.",
        icon=":material/inbox:",
    )

for column, (status, label) in zip(board_columns, STATUSES):
    tickets = tickets_by_status[status]
    if drive_filter:
        tickets = [
            ticket for ticket in tickets if drive_filter in ticket_search_text(ticket)
        ]

    with column:
        st.subheader(f"{label} · {len(tickets)}")
        if not tickets:
            st.caption("No matching tickets")
        for ticket in tickets:
            render_ticket(ticket)
