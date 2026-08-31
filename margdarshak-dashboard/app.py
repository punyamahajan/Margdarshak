import streamlit as st

from services.api_client import APIClientError, get_backend_health

st.set_page_config(
    page_title="Margdarshak AI",
    page_icon=":material/support_agent:",
    layout="wide",
)


def home() -> None:
    st.title("Margdarshak AI")
    st.write("Coordinator workspace for placement support and peer matching.")

    try:
        health = get_backend_health()
    except APIClientError as exc:
        st.error(
            "Backend is offline. Start PostgreSQL, Redis, and FastAPI before "
            "using the dashboard.",
            icon=":material/cloud_off:",
        )
        st.caption(str(exc))
    else:
        if health.get("status") == "ok":
            st.success("Backend connected", icon=":material/cloud_done:")

    with st.container(border=True):
        st.subheader("Tickets")
        st.write("Review open, escalated, and resolved placement cases.")
        st.page_link(
            "pages/1_Triage_Kanban.py",
            label="Open tickets",
            icon=":material/view_kanban:",
        )

    with st.container(border=True):
        st.subheader("Stats")
        st.write("View anonymous Matchmaker activity and requested skills.")
        st.page_link(
            "pages/2_Telemetry.py",
            label="Open stats",
            icon=":material/monitoring:",
        )

    st.info(
        "This is a read-only coordinator dashboard. Live call audio requires "
        "a separate student-facing Agora web or mobile client, which is not "
        "part of this dashboard.",
        icon=":material/info:",
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
    ],
    position="sidebar",
)
page.run()
