# Margdarshak AI

Margdarshak is a voice-first student support system with three core flows:

- placement-policy triage and human escalation;
- 48-hour anonymous peer matchmaking;
- learning-style diagnostics and resource recommendations.

The repository contains:

- `margdarshak-backend` — FastAPI, PostgreSQL, Redis, Alembic, Agora RTC, and WebSockets;
- `margdarshak-pwa` — the student-facing Vite/React PWA;
- `margdarshak-dashboard` — legacy Streamlit coordinator dashboard (superseded by the React `/admin` workspace);
- `margdarshak-test-client` — a minimal standalone Agora debugging client.

## Prerequisites

Install:

- Python 3.10 or newer;
- Node.js 20.19 or newer;
- PostgreSQL 14 or newer;
- Redis 7 or newer;
- an Agora project with an App ID and App Certificate;
- Docker Desktop if you want to run PostgreSQL and Redis in containers.

## Quick start: the whole project

The commands below use PowerShell. Keep the backend, PWA, and dashboard in
separate terminals.

### 1. Start PostgreSQL and Redis

For the first Docker run:

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

On later runs:

```powershell
docker start margdarshak-postgres margdarshak-redis
```

If you use locally installed services instead, create a PostgreSQL database
named `margdarshak` and ensure PostgreSQL and Redis are running.

### 2. Configure the backend

Create `margdarshak-backend/.env`:

```dotenv
APP_NAME=Margdarshak Voice-AI Placement Hotline
ENVIRONMENT=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://postgres:replace_me@localhost:5432/margdarshak
REDIS_URL=redis://localhost:6379/0

AGORA_APP_ID=replace_with_your_agora_app_id
AGORA_APP_CERTIFICATE=replace_with_your_agora_app_certificate
AGORA_AI_AGENT=replace_with_your_published_agora_agent_identifier
AGORA_TOKEN_TTL_SECONDS=3600

TRIAGE_SESSION_TTL_SECONDS=86400
EXPIRY_WORKER_INTERVAL_SECONDS=60
```

See [What to put in each `.env` value](#what-to-put-in-each-env-value) for a
field-by-field explanation.

### 3. Install, migrate, and seed the backend

```powershell
cd margdarshak-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed_resources
python -m app.db.seed_test_data
```

Both seed scripts are idempotent. Run `seed_resources.py` before
`seed_test_data.py` after migrations.

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

### 4. Start FastAPI — terminal 1

From `margdarshak-backend`, with the virtual environment active:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful backend links:

- API root: <http://127.0.0.1:8000>
- Swagger: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>
- WebSocket base: `ws://127.0.0.1:8000/ws`

### 5. Find a seeded student UUID

The PWA temporarily uses a configured student UUID until authentication is
implemented. Query one after running the seed scripts:

```powershell
docker exec margdarshak-postgres psql -U postgres -d margdarshak `
  -c "SELECT id, roll_number, name FROM students ORDER BY roll_number;"
```

If PostgreSQL is installed locally, run the equivalent command with `psql`:

```powershell
psql -U postgres -d margdarshak -c "SELECT id, roll_number, name FROM students ORDER BY roll_number;"
```

Copy one value from the `id` column.

### 6. Configure and start the student PWA — terminal 2

Copy `margdarshak-pwa/.env.example` to `margdarshak-pwa/.env` and replace the
student UUID:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_STUDENT_ID=paste_a_student_uuid_from_step_5
```

Then run:

```powershell
cd margdarshak-pwa
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173>.

Use `npm` instead of `npm.cmd` on macOS or Linux. PowerShell may block
`npm.ps1`; `npm.cmd` avoids changing the execution policy.

### 7. Open the coordinator workspace

The coordinator experience is part of the React PWA. With the PWA running,
open <http://127.0.0.1:5173/admin>. It includes Home, Tickets, Stats, and
Knowledge management. Apply `alembic upgrade head` before using it so the
coordinator workflow, cluster, and knowledge tables are available. See
[the admin implementation guide](ADMIN_PANEL_IMPLEMENTATION.md) for its API
contract and operational behavior.

## What to put in each `.env` value

Never commit a real `.env` file. The repository ignores these files because
they can contain credentials. In particular, never expose
`AGORA_APP_CERTIFICATE` in the PWA, dashboard, or browser.

### Backend: `margdarshak-backend/.env`

| Variable | What to enter |
|---|---|
| `APP_NAME` | A display name for FastAPI. The supplied default is fine. |
| `ENVIRONMENT` | Use `development` locally. |
| `LOG_LEVEL` | Use `INFO` normally or `DEBUG` for more local logs. |
| `DATABASE_URL` | The PostgreSQL connection URL. Format: `postgresql+asyncpg://USERNAME:PASSWORD@HOST:PORT/DATABASE`. With the Docker command above, use `postgresql+asyncpg://postgres:replace_me@localhost:5432/margdarshak`. If the password contains symbols such as `@`, URL-encode it. |
| `REDIS_URL` | The Redis connection URL. Local Docker value: `redis://localhost:6379/0`. The final `0` is the Redis database number. |
| `AGORA_APP_ID` | The public App ID from the Agora Console project settings. It is safe for the backend to return this ID to the Web SDK. |
| `AGORA_APP_CERTIFICATE` | The private App Certificate from the same Agora project. Keep it backend-only. |
| `AGORA_AI_AGENT` | The identifier/name of the Agora Conversational AI agent configured for this project. Confirm the agent is **Published**, not Draft. |
| `AGORA_TOKEN_TTL_SECONDS` | RTC token lifetime. `3600` means one hour. |
| `TRIAGE_SESSION_TTL_SECONDS` | How long Redis retains in-progress conversation state. `86400` means 24 hours. |
| `EXPIRY_WORKER_INTERVAL_SECONDS` | How often the worker checks expired matchmaker bridges. `60` means once per minute. |

`DATABASE_URL` and `REDIS_URL` are service links, not web pages. Do not paste
Swagger, pgAdmin, RedisInsight, or browser URLs into these values.

### Student PWA: `margdarshak-pwa/.env`

| Variable | What to enter |
|---|---|
| `VITE_API_BASE_URL` | The public FastAPI v1 URL. Local value: `http://127.0.0.1:8000/api/v1`. Keep `/api/v1` at the end. |
| `VITE_STUDENT_ID` | A real UUID from the `students` table. Use the query in step 5 after seeding. This is a temporary development identity until login/authentication is added. |

Every variable beginning with `VITE_` is included in browser JavaScript. Never
put database passwords, Agora certificates, or other secrets in a Vite `.env`.

### Dashboard: `margdarshak-dashboard/.env`

| Variable | What to enter |
|---|---|
| `MARGDARSHAK_API_URL` | The same FastAPI v1 URL used by the PWA: `http://127.0.0.1:8000/api/v1`. The dashboard never connects directly to PostgreSQL. |

### Production URL examples

If the backend is deployed at `https://api.example.com`, use:

```dotenv
# margdarshak-pwa/.env
VITE_API_BASE_URL=https://api.example.com/api/v1

# margdarshak-dashboard/.env
MARGDARSHAK_API_URL=https://api.example.com/api/v1
```

The PWA derives its secure WebSocket URL (`wss://api.example.com/ws/...`) from
`VITE_API_BASE_URL`. Production pages using HTTPS must use HTTPS/WSS backend
links; browsers block insecure HTTP/WS calls from secure pages.

## Optional: run the minimal Agora test client

This client is useful for debugging RTC without the full PWA:

```powershell
cd margdarshak-test-client
python -m http.server 8080
```

Open <http://127.0.0.1:8080>. Its backend URL is the
`BACKEND_BASE_URL` constant at the top of `app.js`.

## Tests

### Normal backend suite

```powershell
cd margdarshak-backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

### Full PostgreSQL + Redis smoke suite

The end-to-end tests deliberately require explicit service URLs so they never
write to a database accidentally. Create a separate migrated test database,
then set the values in the current terminal:

```powershell
$env:E2E_DATABASE_URL="postgresql+asyncpg://postgres:replace_me@localhost:5432/margdarshak_test"
$env:E2E_REDIS_URL="redis://localhost:6379/15"
$env:DATABASE_URL=$env:E2E_DATABASE_URL
alembic upgrade head
pytest -q tests/e2e/test_full_flow.py
Remove-Item Env:DATABASE_URL
```

Create `margdarshak_test` before running these commands. The temporary
`DATABASE_URL` override makes Alembic target the test database; removing it
afterward restores normal `.env` loading. Do not point `E2E_DATABASE_URL` at
production.

### PWA checks

```powershell
cd margdarshak-pwa
npm.cmd run typecheck
npm.cmd run build
```

## Recommended startup order

1. Start PostgreSQL and Redis.
2. Apply Alembic migrations.
3. Run `seed_resources.py`, then `seed_test_data.py`.
4. Start FastAPI on port `8000`.
5. Start the PWA on port `5173`.
6. Open `/admin` in the PWA for the coordinator workspace.

## Current integration limitation

RTC token generation, browser microphone publication, remote-audio
subscription, transcripts, and handoff state are implemented. However,
`app/services/agora_service.py::start_agent_session` and the final external
human invite are still explicit provider-integration stubs. A published Agora
agent will not automatically join until the real Conversational AI start API
and account-specific authentication contract are wired into that service.

## Common issues

### `alembic`, `uvicorn`, or `streamlit` is not recognized

Activate the relevant Python virtual environment and install its
`requirements.txt`.

### `npm.ps1` cannot be loaded

Use `npm.cmd install` and `npm.cmd run dev` in PowerShell.

### Backend cannot connect to PostgreSQL

Confirm PostgreSQL is running and that the username, password, port, and
database in `DATABASE_URL` match the instance. For Docker, also confirm the
container is running with `docker ps`.

### Redis connection errors

Confirm Redis is running at the address in `REDIS_URL`. The local Docker value
is `redis://localhost:6379/0`.

### PWA reports that `VITE_STUDENT_ID` is missing

Create `margdarshak-pwa/.env`, paste an existing student UUID, and restart the
Vite development server. Vite reads `.env` only when it starts.

### Dashboard cannot load data

Confirm FastAPI is running and `MARGDARSHAK_API_URL` ends in `/api/v1`.

### Agora token or audio errors

Confirm the App ID and Certificate belong to the same Agora project, the agent
identifier is correct, and the agent is Published. Remember that automatic
agent startup remains a backend stub as described above.
