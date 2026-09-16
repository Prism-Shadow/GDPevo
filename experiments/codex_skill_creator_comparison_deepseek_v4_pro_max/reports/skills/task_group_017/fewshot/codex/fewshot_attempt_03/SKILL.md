---
name: investigation-review-hub
description: Access and analyze the Investigation Review Hub API for eDiscovery and legal investigation review tasks. Query matter metadata, subpoena categories, custodian sources, production stats, privilege logs, QC findings, retention events, and remediation actions through REST endpoints and read-only SQL. Use when the task involves production gap analysis, retention and litigation-hold reviews, cross-system remediation dashboards, production-readiness reviews, privilege log audits, custodian-source collection assessments, or any structured deliverable that must be built from shared hub records.
---

# Investigation Review Hub

## Overview

The Investigation Review Hub is a shared, read-only REST API that holds
eDiscovery and legal review records for active matters. It exposes pre-built
GET endpoints for common entity types plus a read-only SQL query endpoint. All
business evidence must come from the hub; do not inspect environment source
files, database files, or hidden manifests.

Base URL: `<TASK_ENV_BASE_URL>` from the task prompt or request context payload.

Query endpoint header: `X-API-Key: review-key-017` (provided in the task when
SQL access is needed).

## Endpoint inventory

| Method | Path                        | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | `/`                         | Service status and endpoint list   |
| GET    | `/api/schema`               | Table names and column definitions |
| GET    | `/api/matters`              | All matter records                 |
| GET    | `/api/subpoena-categories`  | Request-category records           |
| GET    | `/api/productions`          | Production batch stats             |
| GET    | `/api/custodian-sources`    | Custodian and source records       |
| GET    | `/api/documents/search`     | Review document records            |
| GET    | `/api/privilege-log`        | Privilege entry records            |
| GET    | `/api/qc-findings`          | QC finding records                 |
| GET    | `/api/retention-events`     | Retention event records            |
| GET    | `/api/remediation-actions`  | Remediation action records         |
| POST   | `/api/query`                | Read-only SQL queries              |

## Calling the API

Pre-built GET endpoints return JSON with a `rows` array and a `count` field:

```bash
curl -s <TASK_ENV_BASE_URL>/api/matters
curl -s <TASK_ENV_BASE_URL>/api/custodian-sources
```

The SQL endpoint accepts a POST with `Content-Type: application/json` and a
JSON body containing `{"sql": "<query>"}`:

```bash
curl -s -X POST <TASK_ENV_BASE_URL>/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: review-key-017" \
  -d '{"sql": "SELECT * FROM retention_events WHERE matter_id = '\''MTR-EXAMPLE'\''"}'
```

Use single-quote escaping inside double-quoted `-d` JSON strings in bash.

## Data model

Every table includes `matter_id`. Filter by `matter_id` first when the task
scopes to one matter. Category codes are uppercase strings (e.g. `R09`,
`SEC-1`, `A`). Stable record IDs from the hub anchor every finding, status,
risk, and action -- use them exactly as they appear; do not invent identifiers.

For the complete column listing and type annotations, read
[references/api_schema.md](references/api_schema.md).

## Analysis workflows

Common review deliverables follow consistent data-gathering patterns documented
in [references/analysis_workflows.md](references/analysis_workflows.md):

- **Production gap analysis** -- Identify miscoded documents, privilege log
  gaps, preservation failures, and collection gaps per category.
- **Retention and litigation-hold review** -- Compare retention events against
  hold dates to classify pre-hold policy losses, post-hold losses, auto-purges,
  and available archives.
- **Cross-system remediation dashboard** -- Rank risks by severity, summarize
  category coverage, list retained/available remediation sources, and deliver a
  prioritized action plan.
- **Production-readiness review** -- Check per-category readiness, quantify
  privilege blockers, flag responsiveness miscodes, and produce a readiness
  action plan.

The workflows reference describes the data sources and decision logic for each
deliverable. Read it before starting analysis so the data-gathering pass is
complete and the deliverable schema is respected.

## Output contract

The task prompt always specifies an answer template file
(`input/payloads/answer_template.json`). Read that template first. It defines:

- Required top-level keys
- Enum value sets for every categorical field
- Ordering rules
- Numeric precision constraints
- Field descriptions

Return exactly one JSON object conforming to the template. Do not mix prose
with the JSON. Use stable hub record IDs for all finding IDs, risk IDs,
source refs, and target refs. Category code lists must be sorted ascending.
Record lists under a key must follow the sort order declared in the template.
