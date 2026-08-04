---
name: investigation-review-hub
description: Generate structured JSON deliverables for legal investigation reviews using the Investigation Review Hub API. Use for gap analyses, remediation dashboards, production readiness reviews, and retention/hold assessments. The skill covers hub API access, schema-conformant output production, evidence sourcing rules, and common deliverable patterns.
---

# Investigation Review Hub — Reusable Operating Rules

## Overview

This skill governs how to produce structured JSON deliverables for legal investigation reviews (gap analyses, remediation dashboards, retention assessments, production-readiness checks) using a shared Investigation Review Hub. The hub is a read-only HTTP API that serves as the sole source of record for matter metadata, subpoena categories, production status, custodian sources, review documents, privilege-log data, QC findings, retention events, and remediation actions.

**Key principle**: All business evidence comes from the hub API. Local input files provide task context and the required output schema — never business facts.

## Step 1 — Discover Environment Access

Read `environment_access.md` in the workspace root. It supplies:

- `GDPEVO_ENV_BASE_URL`: the base URL of the hub (referenced as `<TASK_ENV_BASE_URL>` in prompts).
- Allowed GET and POST endpoints.
- Auth requirements.

The hub always uses the header `X-API-Key: review-key-017` for the SQL query endpoint.

## Step 2 — Read Task Inputs

For the given task, read every file in `input/`:

1. **`prompt.txt`** — Task description with the matter ID, review type, and deliverable instructions.
2. **`payloads/answer_template.json`** — Required output schema: top-level keys, enums, field definitions, ordering rules, numeric precision.
3. **`payloads/` context file** (typically `request_context.json`, `review_scope.json`, or `matter_context.json`) — Task parameters: `matter_id`, client name, category synopses, source constraints, and environment notes.

The context file may reiterate the base URL, auth, and exclusions. Obey these constraints — they always match `environment_access.md`.

## Step 3 — Hub API Catalog (Fixed)

These are the available endpoints. Use them as the exclusive source of business evidence.

### GET endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | Hub health / root |
| `GET /api/schema` | Database schema for constructing SQL queries |
| `GET /api/matters` | Matter metadata (matter IDs, clients, hold dates, status) |
| `GET /api/subpoena-categories` | Request/subpoena categories (codes, titles, descriptions) |
| `GET /api/productions` | Production status per matter/category |
| `GET /api/custodian-sources` | Custodian data sources (types, collection status, retention characteristics) |
| `GET /api/documents/search` | Document review records with coding, privilege, and production status |
| `GET /api/privilege-log` | Privilege log entries (withheld, logged, waiver, third-party) |
| `GET /api/qc-findings` | QC finding records (responsiveness miscodes, privilege recodes) |
| `GET /api/retention-events` | Retention events (destruction, auto-purge, loss events, holds) |
| `GET /api/remediation-actions` | Remediation action records (status, owner, dates) |

### POST endpoint — SQL query

`POST /api/query`

- **Content-Type**: `application/json`
- **Required header**: `X-API-Key: review-key-017`
- **Body**: `{"sql": "<SELECT statement>", "params": ["<value>", ...]}`

The query endpoint supports read-only SELECT. Use parameterized queries. Discover table names and column schemas from `GET /api/schema`.

## Step 4 — Gather Evidence

1. Start by fetching the **matter record** to confirm the matter ID exists and get hold dates, status.
2. Fetch **subpoena categories** to get the full set of category codes and titles relevant to the matter.
3. Fetch entity records relevant to the review type:
   - For gap analysis: `productions`, `custodian-sources`, `documents/search`, `privilege-log`, `qc-findings`.
   - For retention review: `retention-events`, `custodian-sources`, `productions`.
   - For remediation dashboard: `retention-events`, `custodian-sources`, `documents/search`, `qc-findings`, `privilege-log`, `remediation-actions`.
   - For production readiness: `documents/search`, `privilege-log`, `qc-findings`, `productions`.
4. Use `POST /api/query` for any complex joins or filtered aggregations not available from the fixed GET endpoints. Always use parameterized queries.

## Step 5 — Build the Output JSON

### Schema Compliance (Non-Negotiable)

The answer template is law. Obey it exactly:

- **Output exactly one JSON object** — no surrounding prose, no markdown fences, no explanation text.
- **Include every key** listed in `required_top_level_keys`.
- **Use only enum values** listed under `enums` in the template. Never invent new values.
- **Follow field types** from `fields` exactly: correct keys, correct value types (string, integer, list, object, null).
- **Counts are whole integers** — no floats, no strings for numeric fields.
- **Apply ordering rules** from `ordering_rules` exactly: sort lists by the specified key and direction.
- **Use stable hub record IDs** as keys (finding_id, risk_id, event_id, source_id, issue_id, action_id, correction_id). Copy IDs verbatim from hub API responses.

### Structural Patterns by Review Type

#### Gap Analysis (e.g., train_001 pattern)

Top-level keys typically include: `matter_id`, `critical_findings`, `category_statuses`, `metrics`, `priority_actions`.

- **`critical_findings`**: One object per material gap or defect. Anchor with a hub record ID. Include document/withheld/logged/unlogged counts (use 0 when not applicable).
- **`category_statuses`**: One object for each request category with a non-complete status.
- **`metrics`**: Numeric rollup (unlogged privilege docs, miscoded responsive docs, lost/uncollected source counts, categories with open gaps, readiness boolean).
- **`priority_actions`**: Ranked action plan with action_id, priority_rank, owner, target_refs, category_impacts.

#### Retention/Preservation Review (e.g., train_002 pattern)

Top-level keys typically include: `matter_id`, `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`.

- **`retention_events`**: One object per loss/destruction/retention event. Include dates, hold dates, policy sections, volume counts and units.
- **`communication_gaps`**: System-level gaps (auto-purge, active system loss, uncollected sources). Include purge windows, cutoff dates.
- **`available_archives`**: Archives that still exist and can remediate losses. Include retention years, affected categories, and which losses they can limit.
- **`metrics`**: Counts by status (pre-hold destroyed, post-hold loss, communication gaps, should-exist-missing, available archives, boxes destroyed).

#### Cross-System Remediation Dashboard (e.g., train_003, train_005 patterns)

Top-level keys typically include: `matter_id`, `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan`.

- **`top_risks`**: Ranked by priority_rank. Each has issue_type, risk_level, status, source_status, production_impact, affected_categories, source_refs, counts (document, volume, withheld, logged, unlogged), third_party, recommended_action.
- **`category_coverage`**: Per-category status with production_impact, issue_refs, open_issue_count, recommended_action.
- **`retained_or_available_sources`**: Sources with availability_status, active_system_issue, affected_categories, limits_loss_for_categories, owner, priority.
- **`action_plan`**: Ranked actions with action_type, owner, priority, target_refs, affected_categories, due_days.

#### Production Readiness Review (e.g., train_004 pattern)

Top-level keys typically include: `matter_id`, `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions`.

- **`readiness_statuses`**: Per-category readiness with blocking_refs and required_actions.
- **`issue_ledger`**: Material issues with issue_type, severity, status, source_status, coding fields (current_coding, produced_status, corrected_disposition), counts, owner, priority.
- **`privilege_corrections`**: Privilege-specific correction records with correction_type, privilege_status, withheld/logged/unlogged counts, third_party.

## Step 6 — Evidence Sourcing Rules

### Where facts come from

| Information | Source |
|---|---|
| Matter metadata, hold dates | `GET /api/matters` or `POST /api/query` on matters table |
| Subpoena/request categories | `GET /api/subpoena-categories` |
| Production status | `GET /api/productions` |
| Custodian source details | `GET /api/custodian-sources` |
| Document coding, privilege, production | `GET /api/documents/search` or `POST /api/query` |
| Privilege log entries | `GET /api/privilege-log` or `POST /api/query` |
| QC findings | `GET /api/qc-findings` or `POST /api/query` |
| Retention events | `GET /api/retention-events` or `POST /api/query` |
| Remediation actions | `GET /api/remediation-actions` or `POST /api/query` |
| Answer schema | `input/payloads/answer_template.json` (local) |
| Task parameters (matter_id, client) | `input/payloads/<context>.json` (local) |
| Category synopses/titles | `input/payloads/<context>.json` (local) AND `GET /api/subpoena-categories` |

### What to NEVER use for evidence

- Local environment source files (`.py`, `.js`, `.sql`, etc.)
- Local database files (`.db`, `.sqlite`, etc.)
- Generated data files, seeds, or manifests
- Hidden notes or standard answer files
- Task evaluation or reference files

## Step 7 — Query Construction Patterns

When using `POST /api/query`:

- Always parameterize: use `?` placeholders and the `params` array.
- Filter to the target `matter_id` unless the query is schema-discovery.
- Use `GET /api/schema` first to discover table names, column names, and join paths.
- Common query targets: matters, subpoena_categories, productions, custodian_sources, documents, privilege_log, qc_findings, retention_events, remediation_actions.

Example:
```json
{"sql": "SELECT * FROM documents WHERE matter_id = ? AND privilege_status = ?", "params": ["MTR-EXAMPLE", "withheld"]}
```

## Step 8 — Deliverable

The final output is a single JSON object. No markdown, no explanation, no surrounding text. The JSON must:

1. Be valid (parseable as JSON).
2. Include every `required_top_level_key` from the answer template.
3. Conform to all field types, enums, ordering rules, and numeric precision declared in the template.
4. Use stable hub record IDs exactly as they appear in API responses.
5. Use exact string values for enums — no aliases, no abbreviations, no case variations.
