# Margdarshak AI

Voice-first campus placement guidance: students talk to an Agora AI agent, tickets are triaged and routed, and coordinators get escalations when needed.

| Folder | Role |
|---|---|
| `margdarshak-backend` | FastAPI API, Postgres, Redis, Agora, query routing |
| `margdarshak-pwa` | React student app (Vite) |
| `margdarshak-test-client` | Optional Agora debug page |

Everything runs on localhost. Docker is not required.

---

## Requirements

- Python 3.10+
- Node.js 20.19+
- PostgreSQL 14+ on `localhost:5432`
- Redis 7+ on `localhost:6379`
- Agora project credentials and a published Agent Studio pipeline
- Optional: `GEMINI_API_KEY` or `OPENAI_API_KEY` for semantic query deduplication (lexical fallback works without them)

---

## How to start (first time)

### 1. Start Postgres and Redis

Create the database:

```powershell
createdb -U postgres margdarshak
```

Or in SQL:

```sql
CREATE DATABASE margdarshak;
```

### 2. Configure the backend

```powershell
Copy-Item margdarshak-backend\.env.examplee margdarshak-backend\.env
```

Edit `margdarshak-backend/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/margdarshak
REDIS_URL=redis://localhost:6379/0

AGORA_APP_ID=your_app_id
AGORA_APP_CERTIFICATE=your_app_certificate
AGORA_CUSTOMER_ID=your_customer_id
AGORA_CUSTOMER_SECRET=your_customer_secret
AGORA_AI_AGENT=your_published_pipeline_id

# Optional — semantic ticket grouping (Gemini preferred)
GEMINI_API_KEY=
OPENAI_API_KEY=
LLM_PROVIDER=auto
GEMINI_MODEL=gemini-flash-latest
```

Keep secrets in the backend `.env` only.

### 3. Install, migrate, and seed the backend

```powershell
cd margdarshak-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed_resources
python -m app.db.seed_test_data
```

If PowerShell blocks venv activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Start the backend

Keep this terminal open:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: <http://127.0.0.1:8000/health>
- API docs: <http://127.0.0.1:8000/docs>

### 5. Copy a demo student ID

In another terminal:

```powershell
psql -U postgres -d margdarshak -c "SELECT id, roll_number, name FROM students ORDER BY roll_number;"
```

Copy one `id` value (or run the same query in pgAdmin).

### 6. Configure and start the student app

```powershell
Copy-Item margdarshak-pwa\.env.example margdarshak-pwa\.env
```

Edit `margdarshak-pwa/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_STUDENT_ID=paste_student_uuid_here
```

Then:

```powershell
cd margdarshak-pwa
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173> and allow the microphone when you start a voice call.

---

## How to start again (after first setup)

1. Start PostgreSQL and Redis.
2. Open two terminals from the repo root.

**Terminal 1 — backend**

```powershell
cd margdarshak-backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend**

```powershell
cd margdarshak-pwa
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

App: <http://127.0.0.1:5173>  
API health: <http://127.0.0.1:8000/health>

If you pulled new migrations:

```powershell
cd margdarshak-backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

---

## Run checks

```powershell
cd margdarshak-backend
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd margdarshak-pwa
npm.cmd run typecheck
npm.cmd run build
```

---

## Common problems

| Problem | Fix |
|---|---|
| `VITE_STUDENT_ID` missing | Set a seeded student UUID in `margdarshak-pwa/.env`, restart Vite |
| Postgres connection fails | Confirm Postgres is up, DB `margdarshak` exists, password in `DATABASE_URL` is correct |
| Redis connection fails | Confirm Redis is listening on `localhost:6379` |
| `npm.ps1` is blocked | Use `npm.cmd` as shown above |
| Agora agent startup fails | Same Agora project for App ID + certificate; valid Customer REST credentials; published `AGORA_AI_AGENT` pipeline ID |
| Query grouping feels weak | Set `GEMINI_API_KEY` or `OPENAI_API_KEY` (without keys, lexical similarity is used) |

---

## Demo notes

- `VITE_STUDENT_ID` is a temporary demo identity until auth is added.
- New placement grievances are deduplicated by the query routing agent; duplicates are grouped and counted, new issues escalate to the coordinator via Agora.
- Coordinator invite still records `handover_pending` when a live human join API is not available for the project.
