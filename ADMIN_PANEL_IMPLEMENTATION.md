# Admin panel implementation

## What changed

The Streamlit coordinator dashboard has been superseded by a React coordinator workspace in `margdarshak-pwa`. Open it at `/admin` on the PWA host. It deliberately reuses the student palette—cream, sage, charcoal, soft borders, and serif headings—while using a compact, operational layout suitable for triage.

The workspace contains:

- **Home** — connection state, lifecycle metrics, priority queue, and active drives.
- **Tickets** — five-column board (`open`, `claimed`, `waiting`, `escalated`, `resolved`), company/language/urgency filters, 30-second refresh, editable ownership/classification, cluster linking, and lifecycle actions.
- **Clusters** — repeated-issue cards with affected-student count, a coordinator-notes response draft, explicit publish, and resolve actions.
- **Stats** — operational totals plus issue-category, company, and language distributions.
- **Knowledge** — full policy metadata, CSV/XLSX validation/preview/confirmation, source library, publish, and expire lifecycle actions. Resolving a cluster creates published resolved-issue knowledge automatically.

## Backend contract

The new coordinator API is under `/api/v1/admin`:

| Endpoint | Purpose |
| --- | --- |
| `GET /overview` | Dashboard metrics, priority tickets, active drives |
| `GET /tickets`, `PATCH /tickets/{id}` | Ticket board and coordinator workflow state |
| `GET/POST /clusters` | Repeated issue clusters |
| `POST /clusters/{id}/draft-response` | Draft an approval-ready response from coordinator notes |
| `POST /clusters/{id}/publish-update` | Publish the coordinator-approved incident update |
| `POST /clusters/{id}/resolve` | Resolve linked tickets and save resolution memory |
| `GET/POST /knowledge`, `PATCH /knowledge/{id}` | Knowledge library and status lifecycle |
| `POST /knowledge/shortlist-preview` | Validate and preview a CSV/XLSX shortlist before any write |
| `POST /knowledge/shortlist-import` | Confirm and persist a validated shortlist import |

## Student-side integration contract

These endpoints are the contract for the student implementation. They keep student UI concerns separate from coordinator operations while sharing the same approved data.

| Endpoint | Student-facing use |
| --- | --- |
| `GET /students/{studentId}` | Identity header/profile |
| `GET /students/{studentId}/placements` | Placement cards from approved shortlist imports |
| `GET /students/{studentId}/notifications` | Coordinator-approved incident updates |
| `GET /tickets/{ticketId}` | Ticket status and source-grounded case context |

For shortlist ingestion, first upload a CSV or XLSX to `shortlist-preview`. The backend validates the required columns (`name`, `enrollment_number`, `email`, `company`, `drive_id`, `shortlisted`, `role`, `round`) and returns a preview. Send the reviewed rows, source, title, and version to `shortlist-import` only after coordinator confirmation. The import is stored as published knowledge and becomes available to the student placement endpoint.

Coordinator workflow data is stored separately from the original student triage ticket. This preserves the existing voice/escalation lifecycle while adding `claimed` and `waiting` without changing its enum. The migration creates `ticket_workflows`, `ticket_clusters`, and `knowledge_documents`.

## Setup

1. From `margdarshak-backend`, apply the migration:

   ```powershell
   alembic upgrade head
   ```

   For a populated localhost workspace, seed the existing entities followed by
   the coordinator fixture:

   ```powershell
   python -m app.db.seed_test_data
   python -m app.db.seed_admin_demo
   ```

2. Start FastAPI and the PWA as usual, then open `http://127.0.0.1:5173/admin`.

   The backend now requires `openpyxl` and `python-multipart` for XLSX/CSV ingestion; install the updated `requirements.txt` before starting it.

3. Ensure PWA `VITE_API_BASE_URL` points to the FastAPI `/api/v1` route. The backend CORS configuration now permits `PATCH` in addition to the existing read and post operations.

4. Run `python -m app.db.seed_test_data` after the migration. On an empty local database it creates a repeatable coordinator demo: active drives, students, tickets across Open/Claimed/Waiting/Escalated, a critical Riverbank cluster, and published policy/resolution knowledge. Re-running it does not duplicate tickets.

## Product behavior and guardrails

- Publishing and resolution are explicit coordinator actions; drafts are never sent automatically.
- Resolution memory is added only when a cluster is resolved, as a published `resolved_issue` knowledge item.
- Empty, loading, and backend-error states use human-readable language rather than raw fetch errors.
- The draft endpoint is intentionally deterministic right now: it formats coordinator-provided notes into the approved response shape. It is the safe integration seam for the existing Agora transcription/AI provider when its production draft-response contract is wired.
- Every `/api/v1/admin` route requires a coordinator bearer credential. Local development uses `ADMIN_API_KEY=local-admin-demo`; production must replace it. The PWA sends `VITE_ADMIN_API_KEY`.
- The coordinator voice control requests a server-signed Agora RTC token, joins the private draft channel, publishes the microphone, and uses browser speech recognition when available. If speech recognition or Agora is unavailable, typed notes remain available and no draft is published without explicit approval.
- Repeated issues are classified and clustered automatically as conversation triage updates the ticket. Cluster priority combines affected-student count, highest urgency, blocking language, and deadline proximity when available.

## Verification performed

- Python modules compile successfully with `python -m compileall -q app` from `margdarshak-backend`.
- The local environment does not currently contain the PWA `node_modules` directory or a system npm executable, so the TypeScript build could not be run here. After dependencies are installed, run `npm.cmd run typecheck` and `npm.cmd run build` from `margdarshak-pwa`.
