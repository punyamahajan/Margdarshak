# Margdarshak Admin — Feature Status Audit

> **Branch scanned:** `admin_panel`  
> **Audit date:** 2026-09-06  
> **Spec sections reviewed:** §23–54 (Part II — Admin Experience) · §59 (API) · §67–68 (Error/Loading states) · §76 (MVP priority)  
> **Key files inspected:**
> - `margdarshak-dashboard/app.py`
> - `margdarshak-dashboard/pages/1_Triage_Kanban.py`
> - `margdarshak-dashboard/pages/2_Telemetry.py`
> - `margdarshak-dashboard/services/api_client.py`
> - `margdarshak-backend/app/api/v1/routes_admin.py`
> - `margdarshak-backend/app/api/v1/routes_tickets.py`

Legend: ✅ DONE · ⚠️ PARTIAL · ❌ MISSING

---

## P0 — Must Have (§76)

### Admin Home (§25, §26, §27, §28, §29)

- [x] ✅ **Admin Home: header + system status** — `margdarshak-dashboard/app.py`  
  Title ("Margdarshak AI"), subtitle ("Coordinator workspace…"), and backend-connected badge all render correctly.

- [x] ✅ **Admin sidebar navigation (Home, Tickets, Stats, Knowledge)** — `margdarshak-dashboard/app.py`  
  Home / Tickets / Stats / Knowledge all registered in `st.navigation`; `pages/3_Knowledge.py` implemented.

- [x] ✅ **Admin Home: overview metrics (Open / Claimed / Waiting / Escalated / Resolved counts)** — `margdarshak-dashboard/app.py`  
  Connected to `GET /api/v1/admin/overview` via `api_client.py:get_admin_overview()`. Renders 5 visually prominent metric cards with status accent borders per §26.

- [x] ✅ **Admin Home: active placement drives list** — `margdarshak-dashboard/app.py`  
  Renders active drives list with company name, status badges, and policy references from `GET /api/v1/admin/overview` (`active_drives`) per §28. Note: standalone `GET /drives` endpoint does not exist on backend; schema notes documented in UI.

- [x] ✅ **Admin Home: recent updates feed** — `margdarshak-dashboard/app.py`  
  Renders operational activity feed from `GET /api/v1/admin/overview` (`recent_updates`) per §29, showing categorized Ticket/Knowledge event badges and relative timestamps.

---

### Tickets Page — Kanban Board (§30, §31)

- [x] ✅ **Tickets page: Kanban board (Open / Claimed / Waiting / Escalated / Resolved columns)** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  Renders all 5 columns (Open, Claimed, Waiting, Escalated, Resolved) with column counts, color-coded accents, and compact operational layout per §30–31.

---

### Ticket Card (§32)

- [x] ✅ **Ticket card (id, confidence, summary, urgency, language, status, created at)** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  Renders all required fields: Ticket ID / enrollment number, Confidence % badge, Issue summary, Urgency badge, Language, Status, formatted Created At timestamp, and a View details action button per §32.

---

### Ticket Filters (§33)

- [x] ✅ **Ticket filters (drive, company, round, coordinator, language, urgency) + refresh** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  All six filter inputs (Drive ID, Company, Round, Coordinator ID/Name, Language, Urgency) are wired to query parameters in `GET /api/v1/admin/tickets` with Refresh now button and configurable periodic auto-refresh per §33.

---

### Ticket Detail Panel (§34)

- [x] ✅ **Ticket detail panel (student info, issue info, placement context, AI intelligence, source, actions: claim/escalate/resolve/dismiss)** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  Full panel renders below Kanban when "View details" is clicked. Fetches `GET /tickets/{id}`. Actions (Claim, Escalate, Resolve, Dismiss) fire `PATCH /api/v1/admin/tickets/{id}` with correct `WorkflowUpdate` body per §44 lifecycle. Panel closes on action or ✕ button. Cache cleared and board reruns after each action.

---

### Issue Clustering (§35, §36, §37)

- [x] ✅ **Issue clustering: cluster list + cluster card** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  `render_clusters_section()` + `render_cluster_card()` added below Kanban board. Loads from `GET /api/v1/admin/clusters`. Displays: title, affected student count, company, status pill, priority badge (Critical/High/Medium/Low), priority score (server-side per §37).  
  ⚠️ **Backend gap**: `GET /api/v1/admin/clusters/{id}` does **not exist**. Single-cluster lookups are handled by filtering the list payload client-side. If a single-cluster endpoint is needed, add it to `routes_admin.py`.

- [x] ✅ **Cluster priority calculation display** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  Priority badge renders the `urgency` label (Critical/High/Medium/Low) computed by `calculate_priority()` on the backend per §37 factors (affected students, ticket urgency, deadline proximity, frequency, blocked detection). Priority score also displayed inline.

---

### Cluster Incident Update + Publish (§38)

- [x] ✅ **Cluster incident update field + Publish Update button** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  `render_cluster_card()` includes: incident update textarea (pre-filled with current `incident_update` if set), **Publish update** button → `POST /api/v1/admin/clusters/{id}/publish-update` (notifies all affected students via `StudentNotification`), **Resolve cluster** button → `POST /api/v1/admin/clusters/{id}/resolve` (bulk-resolves tickets + writes `KnowledgeDocument` per §42). Both actions clear caches and rerun.

---

### Agora Admin Drafting (§39)

- [x] ✅ **Agora admin drafting button + flow** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  "Draft response with Agora" button in cluster card. Calls `POST /api/v1/admin/agora/session` and injects a Streamlit HTML component utilizing `agora-rtc-sdk-ng` and `webkitSpeechRecognition`. On transcript result, calls `POST /api/v1/admin/clusters/{id}/draft-response` and reloads.

---

### Response Approval (§40)

- [x] ✅ **Response approval (Edit / Approve & Send / Cancel)** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  When `cluster.response_draft` is present, the UI switches to "AI Drafted Response" mode, offering a text area to edit the draft, and "Approve & Send" or "Cancel" buttons.

---

### Mass Resolution & Knowledge (§41, §42)

- [x] ✅ **Mass resolution** — `margdarshak-dashboard/pages/1_Triage_Kanban.py`  
  Clicking "Approve & Send" or "Resolve cluster" calls `POST /api/v1/admin/clusters/{id}/resolve`, which resolves all associated tickets.

- [x] ✅ **Resolution memory** — `margdarshak-backend/app/api/v1/routes_admin.py`  
  `resolve_cluster` automatically creates a `KnowledgeDocument` of type `resolved_issue` with the cluster's resolution text. Functional write-back is present on the backend (no coordinator-visible confirmation needed per spec).

---

## P1 — Important (§76)

### Priority Alerts (§27)

- [x] ✅ **Admin Home: priority alerts** — `margdarshak-dashboard/app.py`  
  Surfaces high-priority incidents and active clusters from `GET /api/v1/admin/overview` and `GET /api/v1/admin/clusters`. Sorted by §27 priority factors (affected students, urgency, deadline proximity, repetition, blocked status). Renders urgency badge, affected student count, company context, deadline notice, and "View issues in Kanban →" link.

---

### Policy Ingestion / Knowledge Approval (§47, §48)

- [x] ✅ **Knowledge Approval page** — `margdarshak-dashboard/pages/3_Knowledge.py`  
  Header with backend connection status badge, tabs for draft creation and lifecycle management per §47.

- [x] ✅ **Create Policy Draft form (Drive, Source Title, Reference, Version, Eligibility, CTC, Deadline, URL, Instructions)** — `margdarshak-dashboard/pages/3_Knowledge.py`  
  Full `PolicyForm` with all 9 spec fields, active drives dropdown, validation, and "Save as Draft" (as well as "Publish Immediately") wired to `POST /api/v1/knowledge/policy` / `POST /api/v1/admin/knowledge`.

---

### Policy Lifecycle (§49, §53)

- [x] ✅ **Policy lifecycle (Draft / Published / Expired, Expire action)** — `margdarshak-dashboard/pages/3_Knowledge.py`  
  Knowledge library and lifecycle display showing color-coded status badges (`DRAFT`, `PUBLISHED`, `EXPIRED`), document details accordion, and interactive lifecycle transition actions: "Expire" (`PATCH /knowledge/{id}` status=expired), "Approve & Publish" (status=published), and "Revert to Draft" (status=draft).

---

### CSV/XLSX Ingestion + Import Workflow (§50, §51, §52)

- [x] ✅ **CSV/XLSX ingestion form + full import workflow (upload → parse → validate → preview → confirm → import)** — `margdarshak-dashboard/pages/3_Knowledge.py`  
  `ImportForm` with Drive select, title, source reference, version prefix, and CSV/XLSX file upload. Implements complete workflow: parses file, validates all 8 columns (`name`, `enrollment_number`, `email`, `company`, `drive_id`, `shortlisted`, `role`, `round`), displays Section 67 inline error states ("Invalid CSV", "Missing required fields"), renders candidate preview table with metrics, and provides coordinator confirmation box to import via `POST /knowledge/import`.

---

### Knowledge Library Table (§53)

- [x] ✅ **Knowledge Library table (Document, Type, Company, Version, Status, Source, Last Updated)** — `margdarshak-dashboard/pages/3_Knowledge.py`  
  Renders structured knowledge document cards with type pill, company, version, status pill, source reference, formatted creation timestamp, filter/search controls, content explorer, and interactive lifecycle transition actions (`Expire`, `Approve`, `Draft`).


---

### Admin Filters (§33)

- [ ] ⚠️ **Admin ticket filters** — `margdarshak-dashboard/pages/1_Triage_Kanban.py:99-109`  
  See P0 Ticket Filters entry above; partially implemented (1 of 6 filters present).

---

### Student Notifications (§21)

- [ ] ⚠️ **Student notifications** — `margdarshak-backend/app/api/v1/routes_admin.py:259`  
  `publish_cluster_update` inserts `StudentNotification` rows for all affected students; **no delivery mechanism** (push, email, WebSocket fan-out) is wired — records are stored but never sent to the student frontend.

---

### Stats Page — All 8 Metrics (§45)

- [x] ✅ **Stats page — all 8 metrics from §45** — `margdarshak-dashboard/pages/2_Telemetry.py`  
  Connected to `GET /api/v1/stats` (and `GET /api/v1/admin/stats`) via `api_client.py:get_stats()`. Replaced peer-matchmaker telemetry with the 8 spec-required operational metrics in a visually lightweight layout (§45):
  - Total conversations (metric card)
  - Tickets created (metric card)
  - Tickets resolved (metric card)
  - Average resolution time in hours (metric card)
  - Students assisted (metric card)
  - Active clusters (metric card)
  - Most common issue categories (simple bar chart & breakdown)
  - Most requested companies (simple bar chart & breakdown)
  - Most common languages (simple bar chart & breakdown)
  Includes backend offline banner, refresh button, and quick navigation links to Kanban and Knowledge Library.

---

## P2 — Nice to Have (§76)

> P2 items (anonymous peer chat, advanced analytics, complex role permissions, advanced recommendation systems) are out of scope for this audit pass and have no admin-panel relevance.

---

## Backend Endpoints from §59 Relevant to Admin

| Spec endpoint | Implementation | Status |
|---|---|---|
| `POST /tickets` | `routes_voice.py` (ticket created during voice session) | ✅ DONE |
| `GET /tickets` | `routes_tickets.py:41` | ✅ DONE |
| `GET /tickets/{id}` | `routes_tickets.py:30` | ✅ DONE |
| `PATCH /tickets/{id}` | `routes_admin.py:160` (`PATCH /admin/tickets/{id}`) | ✅ DONE |
| `GET /ticket-clusters` | `routes_admin.py:205` (`GET /admin/clusters`) | ✅ DONE (path differs from spec) |
| `GET /ticket-clusters/{id}` | not implemented | ❌ MISSING |
| `POST /ticket-clusters/{id}/resolve` | `routes_admin.py:263` | ✅ DONE |
| `POST /ticket-clusters/{id}/publish-update` | `routes_admin.py:253` | ✅ DONE |
| `POST /ticket-clusters/{id}/draft-response` | `routes_admin.py:245` | ✅ DONE |
| `POST /knowledge/policy` | `routes_admin.py:280` (`POST /admin/knowledge`) | ✅ DONE (path differs) |
| `POST /knowledge/import` | `routes_admin.py:292` (`POST /admin/knowledge/shortlist-import`) | ✅ DONE (path differs) |
| `GET /knowledge` | `routes_admin.py:274` | ✅ DONE |
| `PATCH /knowledge/{id}` | `routes_admin.py:306` | ✅ DONE |
| `GET /stats` | `routes_admin.py:184` (`GET /admin/stats`) | ✅ DONE (path differs) |
| `POST /knowledge/shortlist-preview` | `routes_admin.py:286` | ✅ DONE (bonus) |
| `POST /admin/agora/session` | `routes_admin.py:233` | ✅ DONE (bonus) |
| `GET /admin/overview` | `routes_admin.py:172` | ✅ DONE (bonus) |
| `POST /admin/clusters` | `routes_admin.py:226` | ✅ DONE (bonus) |

---

## Error / Loading States Relevant to Admin (§67, §68)

| State | Status | Note |
|---|---|---|
| Backend offline banner — Home page | ✅ DONE | `app.py:418-425` |
| Backend offline banner — Tickets page | ✅ DONE | `1_Triage_Kanban.py:1145-1152` |
| Backend offline banner — Stats page | ✅ DONE | `2_Telemetry.py:168-175` |
| Empty ticket state ("no tickets yet") | ✅ DONE | `1_Triage_Kanban.py:1161-1167` |
| Case card load error on detail panel | ✅ DONE | `1_Triage_Kanban.py:920-924` |
| Invalid CSV error (backend 400) | ✅ DONE | `routes_admin.py:92` & `3_Knowledge.py:818-832` |
| Missing required CSV columns (backend 422) | ✅ DONE | `routes_admin.py:99-101` & `3_Knowledge.py:833-847` |
| Invalid knowledge status guard | ✅ DONE | `routes_admin.py:310` |
| Empty knowledge state | ✅ DONE | `3_Knowledge.py` renders friendly empty state card |
| Agora connection failed — admin | ✅ DONE | Friendly fallback banner + note editor in `1_Triage_Kanban.py:688-693` |
| Loading states / "Searching…" messages | ✅ DONE | `st.spinner` with spec-standard copy on all data fetches & actions (§68) |
| "Knowledge unavailable" state | ✅ DONE | Friendly alert banner & error handling in `3_Knowledge.py:439-446` |

---

## Summary Table

| Feature | P | Status |
|---|---|---|
| Admin sidebar — Home, Tickets, Stats | P0 | ✅ DONE |
| Admin sidebar — Knowledge | P0 | ✅ DONE |
| Admin Home: header + system status | P0 | ✅ DONE |
| Admin Home: overview metrics (5 counts) | P0 | ✅ DONE |
| Admin Home: active placement drives | P0 | ✅ DONE |
| Admin Home: recent updates feed | P0 | ✅ DONE |
| Tickets: Kanban board (5 columns) | P0 | ✅ DONE |
| Ticket card (all 7 fields + ownership + sources) | P0 | ✅ DONE |
| Ticket detail panel (structured + 4 actions) | P0 | ✅ DONE |
| Issue clustering — cluster list + card | P0 | ✅ DONE |
| Cluster priority calculation display | P0 | ✅ DONE |
| Cluster incident update + publish | P0 | ✅ DONE |
| Agora admin drafting button + flow | P0 | ✅ DONE |
| Response approval (Edit/Approve/Cancel) | P0 | ✅ DONE |
| Mass resolution (Resolve cluster) | P0 | ✅ DONE |
| Resolution memory / knowledge write-back | P0 | ✅ DONE (backend auto) |
| `GET /ticket-clusters/{id}` endpoint | P0 | ❌ MISSING (handled client-side by filtering list) |
| Admin Home: priority alerts | P1 | ✅ DONE |
| Knowledge Approval page | P1 | ✅ DONE |
| Create Policy Draft form | P1 | ✅ DONE |
| Policy lifecycle (Draft/Published/Expired/Expire action) | P1 | ✅ DONE |
| CSV/XLSX ingestion + import workflow | P1 | ✅ DONE |
| Knowledge Library table | P1 | ✅ DONE |
| Admin ticket filters (6 filters + refresh + reset) | P1 | ✅ DONE |
| Student notifications delivery | P1 | ⚠️ PARTIAL — stored in DB, no student push/fanout |
| Stats page — all 8 §45 metrics | P1 | ✅ DONE |
| Admin error/loading states (§67–68) | P1 | ✅ DONE |


