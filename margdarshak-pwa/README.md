# Margdarshak PWA

## Local setup

Copy `.env.example` to `.env` and set `VITE_STUDENT_ID` to an existing
student UUID from the backend database. Authentication is not implemented yet,
so this environment value is the temporary development identity boundary.

```powershell
npm.cmd install
npm.cmd run dev
```

The call screen uses `agora-rtc-sdk-ng` directly. It starts a backend voice
session, joins and publishes microphone audio, subscribes to remote agent
audio, and samples both tracks' volume levels for the waveform.

Human-handoff state uses polling: while a call is active, the client requests
`GET /api/v1/voice/session/{session_id}/status` every 2.5 seconds. When an
escalated ticket is observed, it briefly shows the POC name without replacing
or restarting the Agora audio connection.

Live summary cards also use polling because the backend does not yet publish
case-card updates over WebSocket. The call screen requests
`GET /api/v1/tickets/{ticket_id}` every 1.5 seconds, diffs `case_card` against
the prior snapshot, and shows at most the five fields changed by that update.

The anonymous matchmaker uses the backend WebSocket at
`/ws/matchmaker/{bridge_id}` for chat messages. Mutual-consent actions show the
same neutral waiting state regardless of which participant acts first; the UI
only changes when the shared reveal or voice-upgrade state is complete.
