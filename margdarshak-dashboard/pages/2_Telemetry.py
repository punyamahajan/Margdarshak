from typing import Any

import pandas as pd
import streamlit as st

from services.api_client import APIClientError, get_telemetry

@st.cache_data(ttl=60, max_entries=2, show_spinner=False)
def load_telemetry() -> dict[str, Any]:
    return get_telemetry()


st.title("Stats")
st.caption("Aggregate, non-identifying activity across anonymous bridges")

metric_slot = st.container()
chart_columns = st.columns(2, gap="medium")

try:
    telemetry = load_telemetry()
except APIClientError as exc:
    st.error(
        "The backend is not reachable. Start FastAPI on port 8000 and try again.",
        icon=":material/cloud_off:",
    )
    st.caption(str(exc))
    st.stop()

status_counts = telemetry.get("bridge_status_counts", {})
top_skills = telemetry.get("top_requested_skills", [])

with metric_slot:
    st.metric(
        "Active bridges",
        int(status_counts.get("active", 0)),
        border=True,
    )

with chart_columns[0]:
    with st.container(border=True):
        st.subheader("Top requested skills")
        if top_skills:
            skills_frame = pd.DataFrame(top_skills).rename(
                columns={"skill": "Skill", "count": "Requests"}
            )
            st.bar_chart(
                skills_frame,
                x="Skill",
                y="Requests",
                horizontal=True,
            )
        else:
            st.info("No opted-in skill data is available yet.")

with chart_columns[1]:
    with st.container(border=True):
        st.subheader("Bridge status breakdown")
        status_frame = pd.DataFrame(
            [
                {"Status": status.replace("_", " ").title(), "Bridges": count}
                for status, count in status_counts.items()
            ]
        )
        if not status_frame.empty:
            st.bar_chart(status_frame, x="Status", y="Bridges")
        else:
            st.info("No bridge telemetry is available yet.")

st.caption("Data refreshes at most once per minute and contains aggregate counts only.")
