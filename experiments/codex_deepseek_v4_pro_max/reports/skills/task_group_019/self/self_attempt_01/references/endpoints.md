# Licensing Environment Endpoints

Base URL: `http://task-env:9019` (or `<TASK_ENV_BASE_URL>` from prompt).

## GET Endpoints

### Policies
- `GET /api/policies` — Current regulatory baseline. Fetch first in every task.

### Contractor Domain
- `GET /api/contractor/applications` — Application records with status and details.
- `GET /api/contractor/bonds` — Surety bond records with coverage amounts, status, effective dates.
- `GET /api/contractor/insurance` — Liability insurance records with coverage amounts, status, effective dates.
- `GET /api/contractor/license-history` — License history including suspensions and status changes.
- `GET /api/contractor/violations` — Violation records with severity, status, dates.
- `GET /api/contractor/correspondence` — Correspondence log with IDs, dates, verification status.
- `GET /api/contractor/inspections` — Inspection records with document status, safety flags.

### Liquor Domain
- `GET /api/liquor/applications` — Application records with license type, location, status.
- `GET /api/liquor/settlements` — Settlement and agreement records.
- `GET /api/liquor/privileges` — Privilege and entitlement records tied to licenses/locations.
- `GET /api/liquor/incidents` — Incident reports including type, date, resolution.
- `GET /api/liquor/site-evidence` — Site-level evidence: camera, food-service, floor plans, signage, photos.

### Alcohol Renewal Domain
- `GET /api/alcohol/licensees` — Licensee records for renewal screening.
- `GET /api/alcohol/violations` — Violation records tied to alcohol licensees.
- `GET /api/renewal/rules` — Renewal rules: release boundary date, queue size, lookback windows.

## POST Endpoints

### SQL Query
- `POST /api/sql` — SQLite-backed query endpoint.
- Required headers: `X-Task-Token: licensing-review-019`, `Content-Type: application/json`
- Body: `{"query": "<SELECT statement>", "params": ["val1", ...], "limit": <int>}`
- Use parameterized queries only. Never interpolate values into SQL strings.

### Common SQL Queries

Discover tables:
{"query": "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"}

Inspect table schema:
{"query": "PRAGMA table_info(applications)"}

Filter by multiple IDs:
{"query": "SELECT * FROM bonds WHERE application_id IN (?,?,?,?)", "params": ["C-TR1-001","C-TR1-002","C-TR1-003","C-TR1-004"]}

Aggregate violations for ranking:
{"query": "SELECT licensee_id, COUNT(*) as cnt, MAX(violation_date) as latest FROM violations WHERE licensee_id IN (?,?,?) GROUP BY licensee_id ORDER BY cnt DESC, latest DESC", "params": ["AL1","AL2","AL3"]}
