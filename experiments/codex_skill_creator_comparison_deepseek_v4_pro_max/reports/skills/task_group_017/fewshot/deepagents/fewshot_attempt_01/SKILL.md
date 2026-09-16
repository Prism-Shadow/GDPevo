---
name: investigation-review-hub
description: "Structured gap, risk, and remediation analysis for legal eDiscovery matters using an Investigation Review Hub REST API. Use when the task requires: (1) rolling production gap analysis, (2) retention and litigation-hold gap review, (3) production-readiness review, (4) cross-system remediation dashboards, (5) privilege-log completeness checks, (6) QC finding triage, or (7) any structured eDiscovery dashboard delivered as JSON against a provided answer template. Triggers include references to matters, subpoena categories, productions, custodian sources, privilege logs, QC findings, retention events, remediation actions, or an Investigation Review Hub base URL."
license: MIT
compatibility: designed for deepagents-code
---

# Investigation Review Hub

## Quick Start

Every task using this skill operates against a live Investigation Review Hub REST API. The
task prompt always provides the base URL (typically `<TASK_ENV_BASE_URL>`) and a list of
allowed endpoints. Start by calling `GET /` to confirm the environment is reachable,
then use `GET /api/schema` to understand the entity model.

### Standard Endpoint Inventory

All tasks share these endpoints. Not every task uses every endpoint, but the full set is:

| Method | Path                      | Purpose                                       |
|--------|---------------------------|-----------------------------------------------|
| GET    | `/`                     | Health check / root navigation                |
| GET    | `/api/schema`           | Entity model and relationships                |
| GET    | `/api/matters`          | Matter metadata (case ID, client, workstream) |
| GET    | `/api/subpoena-categories` | Request categories mapped to the matter    |
| GET    | `/api/productions`      | Rolling production status by category         |
| GET    | `/api/custodian-sources`| Custodian devices, archives, collection status|
| GET    | `/api/documents/search` | Document-level coding and production records  |
| GET    | `/api/privilege-log`    | Privilege withhold/waiver log entries         |
| GET    | `/api/qc-findings`      | QC review findings (miscodes, gaps)           |
| GET    | `/api/retention-events` | Retention destruction, purge, and loss events |
| GET    | `/api/remediation-actions`| Remediation action records                  |
| POST   | `/api/query`            | Read-only SQL-style query (see query header)  |

### SQL Query Header

When using `POST /api/query` for SQL-style access, include the header:

```
X-API-Key: review-key-017
```

No other authentication is required for the read-only GET endpoints.

## Core Principle: Hub as Source of Record

The Investigation Review Hub is the single source of record. Task-local payload files
(`review_scope.json`, `matter_context.json`, `request_context.json`) provide
client-facing labels and request context only. All evidence — counts, statuses, record
IDs, dates, event data — must come from the live API. Never inspect local environment
files, database files, generation manifests, or hidden notes for business data.

## Workflow

### 1. Explore the Schema

Start with `GET /api/schema` to understand which entities are available for this task
and how they relate. The schema reveals field names, foreign-key relationships, and
enum-like value domains without requiring a separate documentation call.

### 2. Gather Matter Context

Call `GET /api/matters` to confirm the matter ID and retrieve the matter-level
metadata. Subsequent calls to subpoena-categories, productions, and custodian-sources
are scoped to this matter.

### 3. Pull the Evidence Layers

For a typical task, pull these layers in parallel or sequentially as needed:

- **Categories**: `GET /api/subpoena-categories` — category codes, descriptions, and
  request scope.
- **Sources**: `GET /api/custodian-sources` — custodians, devices, archives, and
  collection/preservation status per source.
- **Documents**: `GET /api/documents/search` — coding decisions (responsive,
  nonresponsive, privileged), production status, and link to categories and sources.
- **Privilege log**: `GET /api/privilege-log` — withheld documents, log completeness,
  waiver events, third-party exposure.
- **QC findings**: `GET /api/qc-findings` — miscoded documents, zero-claim
  contradictions, and review-quality gaps.
- **Retention events**: `GET /api/retention-events` — destruction, purge, and loss
  events with dates, hold dates, policy sections, and volumes.
- **Remediation actions**: `GET /api/remediation-actions` — existing action records
  tracked in the hub.
- **Productions**: `GET /api/productions` — production batches and rolling production
  status by category.

When a cross-entity join or filtered aggregation is needed that the GET endpoints do
not directly support, use `POST /api/query` with the SQL query header.

### 4. Cross-Reference with Stable IDs

Every entity returned by the hub carries a stable record ID (for example, `DOC-*`,
`PRIV-*`, `QC-*`, `RET-*`, `SRC-*`, `ACT-*`). Use these IDs as anchors when:

- Linking a QC finding to the document it flags.
- Tying a retention event to the affected subpoena categories.
- Connecting a source gap to the categories it leaves underproduced.
- Building `source_refs`, `target_refs`, `issue_refs`, or `blocking_refs` lists in the
  output.

Sort ID lists ascending unless the template specifies a different order.

### 5. Build the Structured Output

Every task supplies an `answer_template.json` in the input payloads. This template
defines:

- **Required top-level keys** and their ordering.
- **Enum choices** for every categorical field.
- **Required keys per list item** and their field types.
- **Ordering rules** (e.g., sort by category_code ascending, sort by priority_rank
  ascending).
- **Numeric precision** rules (always whole integers).

Read the answer template carefully before assembling the output. Build the JSON
programmatically — do not hand-edit large structures — and validate it against the
template before returning.

See [references/output_guidance.md](references/output_guidance.md) for detailed
conventions.

### 6. Fill Metrics and Action Plans

**Metrics** objects roll up counts from the evidence layers (document counts, source
counts, event counts, category counts) into a single top-level summary. Derive each
metric from hub data, not from local assumptions.

**Action plans / priority actions** map each material finding to a concrete remediation
step with an owner, priority, target refs, and affected categories. Assign owners from
the template's owner enum. Prioritize by risk severity: P0 for critical preservation
failures that require immediate disclosure, P1 for high-severity gaps and privilege
exposures, P2 for medium-severity corrections, and P3 for low-risk or policy-compliant
losses.

## Key Business Entities

Understanding how entities relate is essential for cross-referencing:

```
Matter
 ├── SubpoenaCategory (request categories with codes)
 ├── CustodianSource (people, devices, archives)
 │    └── linked to Documents and RetentionEvents
 ├── Document (coding, privilege, production status)
 │    ├── linked to SubpoenaCategory
 │    ├── linked to CustodianSource
 │    └── referenced by QCFinding and PrivilegeLogEntry
 ├── PrivilegeLogEntry (withhold/waiver records)
 │    └── linked to Document and SubpoenaCategory
 ├── QCFinding (review quality flags)
 │    └── linked to Document and SubpoenaCategory
 ├── RetentionEvent (destruction/purge/loss events)
 │    └── linked to CustodianSource and SubpoenaCategory
 ├── RemediationAction (remediation steps)
 │    └── linked to source records and SubpoenaCategory
 └── Production (rolling production batches)
      └── linked to SubpoenaCategory
```

## Tips

- **Sort everything as specified.** Template ordering rules are strict. Sort category
  codes ascending, IDs ascending, priority ranks ascending.
- **Use `null` for missing optional fields**, never omit the key.
- **Counts must be whole integers.** If a count is not applicable, use `0`, not `null`.
- **Boolean fields** like `rolling_production_ready` or `production_ready` derive from
  whether any blocking readiness gaps remain.
- **Third-party fields** take a string identifier when a waiver involves a named third
  party, otherwise `null`.
- **When the template provides enums**, use only those exact values. Do not invent new
  enum members.
- **The SQL endpoint is read-only.** Use `SELECT` queries only. Parameterize with the
  matter ID to scope results.
