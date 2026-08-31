# Margdarshak AI

Margdarshak AI contains two separate applications:

- `margdarshak-backend`: FastAPI, PostgreSQL, Redis, Alembic, Agora RTC, and WebSockets.
- `margdarshak-dashboard`: read-only Streamlit coordinator dashboard.

## Prerequisites

Install the following before starting:

- Python 3.10 or newer
- PostgreSQL 14 or newer
- Redis 7 or newer
- Agora App ID and App Certificate
- Docker Desktop (optional, for running PostgreSQL and Redis locally)

## 1. Start PostgreSQL and Redis

If PostgreSQL and Redis are already installed, create a database named
`margdarshak` and ensure both services are running.

Alternatively, start both with Docker:

```powershell
docker run --name margdarshak-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=replace_me `
  -e POSTGRES_DB=margdarshak `
  -p 5432:5432 `
  -d postgres:16

docker run --name margdarshak-redis `
  -p 6379:6379 `
  -d redis:7-alpine
```

For later runs, restart the existing containers with:

```powershell
docker start margdarshak-postgres margdarshak-redis
```

## 2. Configure and install the backend

Open PowerShell in the repository root:

```powershell
cd margdarshak-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Create or update `margdarshak-backend/.env` with the following variables:

```dotenv
APP_NAME=Margdarshak Voice-AI Placement Hotline
ENVIRONMENT=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://postgres:replace_me@localhost:5432/margdarshak
REDIS_URL=redis://localhost:6379/0

AGORA_APP_ID=replace_with_your_agora_app_id
AGORA_APP_CERTIFICATE=replace_with_your_agora_app_certificate
AGORA_AI_AGENT=replace_with_your_agora_agent_identifier
AGORA_TOKEN_TTL_SECONDS=3600

TRIAGE_SESSION_TTL_SECONDS=86400
EXPIRY_WORKER_INTERVAL_SECONDS=60
```

Never commit `.env` or expose `AGORA_APP_CERTIFICATE` to a client. Replace
`replace_me` in `DATABASE_URL` with the password used for PostgreSQL.

## 3. Apply database migrations

From `margdarshak-backend`, with its virtual environment active:

```powershell
alembic upgrade head
```

Check the current migration revision if needed:

```powershell
alembic current
```

## 4. Run the FastAPI backend

From `margdarshak-backend`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at:

- API: <http://127.0.0.1:8000>
- Swagger documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>
- WebSocket base: `ws://127.0.0.1:8000/ws`

Keep this terminal running.

## 5. Configure and install the dashboard

Open a second PowerShell terminal in the repository root:

```powershell
cd margdarshak-dashboard
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create or update `margdarshak-dashboard/.env`:

```dotenv
MARGDARSHAK_API_URL=http://127.0.0.1:8000/api/v1
```

The dashboard reads all data through FastAPI. It does not connect to
PostgreSQL directly.

## 6. Run the Streamlit dashboard

From `margdarshak-dashboard`:

```powershell
streamlit run app.py --server.port 8501
```

Open <http://localhost:8501>. The dashboard contains:

- Placement triage Kanban
- Aggregate Matchmaker telemetry

## Running tests

Backend tests:

```powershell
cd margdarshak-backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

## Recommended startup order

1. Start PostgreSQL.
2. Start Redis.
3. Activate the backend environment and apply migrations.
4. Start FastAPI on port `8000`.
5. Activate the dashboard environment in a second terminal.
6. Start Streamlit on port `8501`.

## Common issues

### `alembic` or `uvicorn` is not recognized

Activate `margdarshak-backend/.venv` and run `pip install -r requirements.txt`.

### Backend cannot connect to PostgreSQL

Verify PostgreSQL is running, the database exists, and `DATABASE_URL` contains
the correct username, password, host, port, and database name.

### Redis connection errors

Verify Redis is running on the address configured in `REDIS_URL`. For the
Docker setup above, use `redis://localhost:6379/0`.

### Dashboard cannot load data

Confirm the FastAPI process is running and that `MARGDARSHAK_API_URL` ends in
`/api/v1`.

### Agora token or handoff errors

Verify `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, and `AGORA_AI_AGENT`. The
Conversational AI agent-start and human-handover HTTP calls are currently
explicit integration stubs; RTC token generation is implemented.
