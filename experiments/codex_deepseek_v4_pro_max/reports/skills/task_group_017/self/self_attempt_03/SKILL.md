 # Investigation Review Hub Skill

 ## Overview

This skill enables an agent to interact with a shared **Investigation Review Hub** — a fictional REST API that serves as the canonical source of record for legal investigation, eDiscovery, privilege review, retention tracking, and remediation management. The hub supports structured JSON answer generation for gap analyses, retention reviews, production-readiness assessments, and cross-system remediation dashboards.

## Environment Setup

The Investigation Review Hub base URL is provided through the environment variable `GDPEVO_ENV_BASE_URL`. The agent must read this variable at the start of every run and use it as the root for all API calls.

All API calls require the header:

```
X-API-Key: review-key-017
```

When the task payload or prompt provides an alternative base URL placeholder (e.g., `<TASK_ENV_BASE_URL>`), substitute it with the value from `GDPEVO_ENV_BASE_URL`.

## Available Endpoints

### GET Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | API health / root |
| `GET /api/schema` | Database and API schema metadata |
| `GET /api/matters` | List of all matters (MTR-*) with metadata |
| `GET /api/subpoena-categories` | Request/subpoena categories per matter |
| `GET /api/productions` | Production records, status, and volumes |
| `GET /api/custodian-sources` | Custodian data sources, collection status, device info |
| `GET /api/documents/search` | Search documents by matter, category, coding, privilege status |
| `GET /api/privilege-log` | Privilege log entries with withheld/logged/waived counts |
| `GET /api/qc-findings` | QC review findings (miscodes, responsiveness, privilege issues) |
| `GET /api/retention-events` | Retention events, hold dates, purge events, system losses |
| `GET /api/remediation-actions` | Recorded or proposed remediation actions |

### POST Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/query` | Run a read-only SQL SELECT query against the hub database |

#### SQL Query Endpoint Details

- **URL**: `{GDPEVO_ENV_BASE_URL}/api/query`
- **Content-Type**: `application/json`
- **Required Headers**: `X-API-Key: review-key-017`
- **Request Body**:
  ```json
  {"sql": "<SELECT statement>", "params": ["<value1>", "<value2>"]}
  ```
- **Example**:
  ```bash
  curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/query" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: review-key-017" \
    -d '{"sql":"SELECT * FROM matters WHERE matter_id = ?","params":["MTR-EXAMPLE-GJ"]}'
  ```

Use parameterized queries with `?` placeholders. Only SELECT statements are permitted.

## Domain Concepts

### Matters

A **matter** is a legal investigation identified by a stable ID in the format `MTR-{CLIENT}-{AGENCY}` (e.g., `MTR-SENTINEL-GJ`, `MTR-NORTHBAY-SEC`). The matter is the top-level organizational unit. Every answer must include the `matter_id`.

### Request / Subpoena Categories

Each matter has a set of **request categories** (also called subpoena categories) identified by uppercase codes (e.g., `A`, `B`, `C`, or `SEC-1`, `SEC-2`). Categories define what types of documents or records the government or agency has requested. Category codes should always be referenced in uppercase and sorted ascending when listed.

### Custodian Sources

**Custodians** are individuals whose data is subject to collection. Each custodian may have multiple **sources** (email accounts, laptops, phones, shared drives, messaging platforms, offsite records). Sources have collection statuses and may be lost, destroyed, not collected, partially collected, or fully collected.

### Productions

A **production** is a set of documents produced to the government or agency. Productions may be rolling (batched over time). Production status, document counts, and readiness states are tracked per category.

### Privilege Log

The **privilege log** tracks documents withheld from production on privilege grounds. Key fields include:
- Documents **withheld** (total withheld)
- Documents **logged** (described on the privilege log)
- Documents **unlogged** (withheld but not yet described — a compliance gap)
- **Waiver** status (privilege waived, intentionally or not)
- **Over-designation** (documents marked privileged that are not)

### QC Findings

**QC (Quality Control) findings** are issues discovered during document review QA. Common types:
- **Responsiveness miscodes**: Documents coded non-responsive that are actually responsive
- **Privilege miscodes**: Documents coded privileged that are not, or vice versa
- **Zero-claim contradictions**: Asserting zero responsive documents when responsive documents exist

### Retention Events

**Retention events** track what happened to records over time. Key statuses:
- **Pre-hold policy destruction**: Records destroyed per normal retention policy before a litigation hold was issued
- **Post-hold loss**: Records lost or destroyed after a litigation hold was in effect (preservation risk)
- **Auto-purge**: System-automated deletion (e.g., chat retention policies)
- **Active system loss**: Data lost due to system failures, migrations, or deletions
- **Should-exist-missing**: Records that should exist based on business practice but cannot be located

### Remediation Actions

**Remediation actions** are steps to address gaps, defects, or risks. Types include disclosure to government, forensic recovery, supplemental collection, recoding and reproduction, privilege log supplementation, QC re-review, and investigation.

## Task Types and Output Patterns

The hub supports four primary review workflows. The agent must identify which workflow is requested from the prompt and match the output to the corresponding answer template.

### 1. Gap Analysis (Rolling Production)

Assesses what is missing, miscoded, or unlogged in an active production. The answer focuses on:
- **Critical findings**: Material gaps or defects with severity and production impact
- **Category statuses**: Per-category production readiness
- **Metrics**: Privilege docs (unlogged, miscoded), source counts (lost devices, uncollected sources), category gap counts, readiness boolean
- **Priority actions**: Ranked remediation steps with owners

### 2. Retention and Litigation-Hold Gap Review

Evaluates records retention compliance and preservation risk. The answer focuses on:
- **Retention events**: What was destroyed, when, under what policy, and whether pre- or post-hold
- **Communication gaps**: System-level gaps such as auto-purges, uncollected sources, missing records
- **Available archives**: Sources that still exist and can limit irretrievable loss
- **Metrics**: Event counts, box counts, category coverage
- **Recommended actions**: Ranked actions with risk levels

### 3. Cross-System Remediation Dashboard

A comprehensive dashboard covering retention, privilege, QC, and source gaps. The answer focuses on:
- **Top risks**: Ranked risks with full detail (source status, counts, third-party involvement)
- **Category coverage**: Per-category status with open issue counts
- **Retained or available sources**: Archives and sources that can remediate losses
- **Metrics**: Risk counts, destroyed box counts, privilege doc counts, waiver counts, miscode counts
- **Action plan**: Ranked actions with due dates

### 4. Production Readiness Review

Assesses whether a matter is ready to produce, with emphasis on privilege and QC blockers. The answer focuses on:
- **Readiness statuses**: Per-category readiness assessment with blocking references
- **Issue ledger**: Detailed issue tracking with coding status, production status, corrected dispositions
- **Privilege corrections**: Privilege-specific correction package
- **Metrics**: Withheld/logged/unlogged privilege docs, waiver counts, miscode counts, source gap counts
- **Priority actions**: Ranked actions with owners

## Answer Construction Rules

### Source of Truth

- The **Investigation Review Hub API** is always the canonical source for business evidence (matter data, documents, privilege logs, QC findings, retention events, etc.).
- **Task-local payload files** (e.g., `review_scope.json`, `matter_context.json`, `request_context.json`) provide contextual metadata such as category labels, matter identifiers, and client names. Use them for reference but never treat them as the primary data source.
- **Never** inspect local environment files, database files, source code, hidden manifests, generation scripts, or answer/evaluation files.

### Stable Identifiers

- Use stable record IDs **exactly as they appear** in the hub API responses. Do not invent, abbreviate, or transform IDs.
- Common ID prefixes include: matter IDs (`MTR-*`), source IDs, event IDs, QC finding IDs, document IDs, action IDs, and category codes.

### JSON Output

- **Return only a single JSON object**. Do not include any prose, explanation, markdown fences, or commentary outside the JSON.
- Conform precisely to the structure defined in `input/payloads/answer_template.json` for the active task.
- Every required key must be present. Use `null` for nullable fields when no value exists, and `0` for integer counts when not applicable.
- All counts are **whole integers**.

### Ordering

- Lists of findings, risks, issues, or actions: sort by the designated rank/ID field **ascending**.
- Lists of categories or category codes: sort **ascending** within each array.
- Lists of source references or record IDs: sort **ascending**.

### Enum Values

Use only the enum values defined in the answer template. Do not introduce custom values. Common enums that appear across multiple templates include:

**Severity / Risk Level**: `critical`, `high`, `medium`, `low`
**Priority**: `P0`, `P1`, `P2`, `P3`
**Source Status**: `lost`, `not_collected`, `partial`, `collected`, `pending`, `not_applicable`, `destroyed`, `available_archive`, `should_exist_missing`, `unknown`
**Production Impact**: `source_lost`, `source_missing`, `not_produced`, `withheld_unlogged`, `underproduced`, `recode_needed`, `no_production_impact`, `privilege_exposure`
**Action Types**: Vary by template but commonly include `disclose_to_government`, `forensic_recovery`, `collect_source`, `recode_and_produce`, `supplement_privilege_log`, `quality_control_review`, `privilege_re_review`, `investigate`, `no_action`, `search_archive`, `waiver_assessment_and_disclosure`, `locate_missing_record`, `monitor_only`
**Owners**: `outside_counsel`, `client_legal`, `client_it`, `ediscovery_vendor`, `review_vendor`, `privilege_team`, `records_vendor`, `investigation_team`, `forensics`, `review_qc`, `privilege_counsel`, `compliance_audit`, `litigation_counsel`, `records_management`, `it_messaging`, `legal_operations`, `review_operations`

### Data Collection Protocol

1. Read `GDPEVO_ENV_BASE_URL` from the environment.
2. Read the task prompt and identify the workflow type (gap analysis, retention review, remediation dashboard, or production readiness).
3. Read the answer template from `input/payloads/answer_template.json` to understand the required output structure and enum choices.
4. Read any contextual payload files (e.g., `review_scope.json`, `request_context.json`, `matter_context.json`) for matter ID, category labels, and client context.
5. Query the hub API endpoints to collect business evidence:
   - Start with `GET /api/matters` and `GET /api/subpoena-categories` to understand the matter and its categories.
   - Use `POST /api/query` for targeted SQL queries when the standard GET endpoints do not provide sufficient filtering or aggregation.
   - Gather data from all relevant endpoints: productions, custodian-sources, documents/search, privilege-log, qc-findings, retention-events, remediation-actions.
6. Assemble the JSON answer strictly following the template structure, ordering rules, and enum constraints.
7. Output the complete JSON object and nothing else.

### Error Handling

- If an API endpoint returns an error, retry once with the same parameters. If it fails again, note the endpoint and error in a structured way but continue collecting data from other endpoints.
- If the matter ID from the prompt does not match any matter in `GET /api/matters`, use the prompt-provided matter ID and note the discrepancy.
- If a required metric cannot be computed because the relevant endpoint returned no data, use `0` for counts and `false` for booleans.

### Curl Examples for Common Queries

```bash
# Get all matters
curl -sS "$GDPEVO_ENV_BASE_URL/api/matters" -H "X-API-Key: review-key-017"

# Get subpoena categories for a specific matter
curl -sS "$GDPEVO_ENV_BASE_URL/api/subpoena-categories" -H "X-API-Key: review-key-017"

# Get privilege log entries
curl -sS "$GDPEVO_ENV_BASE_URL/api/privilege-log" -H "X-API-Key: review-key-017"

# Get QC findings
curl -sS "$GDPEVO_ENV_BASE_URL/api/qc-findings" -H "X-API-Key: review-key-017"

# Targeted SQL query
curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: review-key-017" \
  -d '{"sql":"SELECT * FROM retention_events WHERE matter_id = ?","params":["MTR-EXAMPLE-GJ"]}'
```
