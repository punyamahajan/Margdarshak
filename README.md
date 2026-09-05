# Margdarshak AI

Margdarshak is a voice-first placement guidance platform. This branch contains:

- `margdarshak-backend` — FastAPI and Agora integration
- `margdarshak-pwa` — React student application
- `margdarshak-test-client` — optional Agora debugging page

Everything runs on localhost. Docker is not required.

## Requirements

Install these before starting:

- Python 3.10+
- Node.js 20.19+
- PostgreSQL 14+
- Redis 7+ or another locally running Redis-compatible service
- Agora project credentials and a published Agent Studio pipeline

PostgreSQL must be available on `localhost:5432` and Redis on `localhost:6379` unless you change their URLs in the backend `.env`.

## 1. Create the local database

Start PostgreSQL and Redis, then create a PostgreSQL database named `margdarshak`:

```powershell
createdb -U postgres margdarshak
```

If `createdb` is unavailable, create the database through pgAdmin or run:

```sql
CREATE DATABASE margdarshak;
```

## 2. Configure the backend

From the repository root:

```powershell
Copy-Item margdarshak-backend\.env.example margdarshak-backend\.env
```

Open `margdarshak-backend/.env`. Update the PostgreSQL password and replace the Agora placeholders:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/margdarshak
REDIS_URL=redis://localhost:6379/0

AGORA_APP_ID=your_app_id
AGORA_APP_CERTIFICATE=your_app_certificate
AGORA_CUSTOMER_ID=your_customer_id
AGORA_CUSTOMER_SECRET=your_customer_secret
AGORA_AI_AGENT=your_published_pipeline_id
```

Keep the certificate, Customer Secret, and database password in the backend only.

## 3. Install and prepare the backend

```powershell
cd margdarshak-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed_resources
python -m app.db.seed_test_data
```

The seed commands add demo students, placement drives, and learning resources. They are safe to run more than once.

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 4. Start the backend

Keep this terminal open:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check that it works:

- <http://127.0.0.1:8000/health>
- <http://127.0.0.1:8000/docs>

## 5. Get a demo student ID

Open another terminal and run:

```powershell
psql -U postgres -d margdarshak -c "SELECT id, roll_number, name FROM students ORDER BY roll_number;"
```

Copy one value from the `id` column. You can run the same query in pgAdmin if `psql` is not on your PATH.

## 6. Configure and start the student app

From the repository root:

```powershell
Copy-Item margdarshak-pwa\.env.example margdarshak-pwa\.env
```

Open `margdarshak-pwa/.env` and paste the student UUID:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_STUDENT_ID=paste_student_uuid_here
```

Then start React:

```powershell
cd margdarshak-pwa
npm.cmd install
npm.cmd run dev
```

Open <http://localhost:5173> and allow microphone access when starting a voice conversation.

## Start it again later

Once installation, migrations, and seeding are complete, normal startup only requires two terminals.

Terminal 1:

```powershell
cd margdarshak-backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminal 2:

```powershell
cd margdarshak-pwa
npm.cmd run dev
```

PostgreSQL and Redis must already be running locally.

## Run checks

Backend:

```powershell
cd margdarshak-backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd margdarshak-pwa
npm.cmd run typecheck
npm.cmd run build
```

## Common problems

### `VITE_STUDENT_ID` is missing

Create `margdarshak-pwa/.env`, add a seeded student UUID, and restart Vite.

### PostgreSQL connection fails

Confirm PostgreSQL is running, the `margdarshak` database exists, and the password in `DATABASE_URL` is correct.

### Redis connection fails

Confirm a Redis-compatible service is listening on `localhost:6379`.

## Quick Start

After the first-time setup is complete, start PostgreSQL and Redis, then open two terminals from the repository root.

Terminal 1, start the backend:

```powershell
cd margdarshak-backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, start the frontend:

```powershell
cd margdarshak-pwa
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open the app at <http://127.0.0.1:5173>. The backend health check is available at <http://127.0.0.1:8000/health>, and the API documentation is available at <http://127.0.0.1:8000/docs>.

### `npm.ps1` is blocked

Use `npm.cmd` as shown above.

### Agora agent startup fails

Confirm the App ID and certificate belong to the same project, the REST Customer credentials are valid, and `AGORA_AI_AGENT` contains a published pipeline ID.

## Current demo limitation

Agora Conversational AI startup is implemented. External coordinator invitation is still an integration boundary and currently remains in `handover_pending` state.

The configured `VITE_STUDENT_ID` is a temporary localhost/demo identity mechanism until authentication is added.
