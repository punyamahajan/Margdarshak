# Margdarshak test client

This is a minimal browser client for testing the FastAPI-to-Agora voice path.
It is deliberately not the production PWA.

## Required configuration

Two environment/configuration values must be checked before testing:

1. **Backend URL:** set `BACKEND_BASE_URL` at the top of `app.js`. The default
   is `http://127.0.0.1:8000/api/v1`.
2. **Agora agent state:** confirm the agent referenced by the backend's
   `AGORA_AI_AGENT` value is **Published**, not **Draft**, in Agora Console.

The browser receives the Agora App ID and short-lived RTC token from FastAPI.
The Agora App Certificate stays only in the backend `.env`.

> Backend limitation: `app/services/agora_service.py::start_agent_session` is
> currently a stub that returns `start_pending`. Until the real Agora
> Conversational AI start API is connected, the backend will not launch the
> published agent automatically. The client can still join, publish its mic,
> and play audio from any remote Agora user that joins the same channel.

## Run

1. Start the backend from `margdarshak-backend`:

   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

2. Serve this directory with any static file server. For example:

   ```powershell
   cd margdarshak-test-client
   python -m http.server 8080
   ```

3. Open <http://127.0.0.1:8080>, enter an existing student's UUID, and select
   **Start Call**. Allow microphone access when the browser asks.

Use `localhost` or `127.0.0.1` for the static server; the backend's debug CORS
rule intentionally allows only those origins. Microphone capture requires a
secure context, and browsers treat these local origins as secure for testing.
