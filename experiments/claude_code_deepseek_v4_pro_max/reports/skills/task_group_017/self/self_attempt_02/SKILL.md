# Investigation Review Hub — Gap Analysis & Remediation Dashboard

## Purpose

Generate a structured JSON deliverable for a legal investigation review by querying a shared Investigation Review Hub REST API, mapping its evidence (matters, subpoena categories, productions, custodian sources, documents, privilege-log entries, QC findings, retention events, and remediation actions) into a formal answer that conforms to a task-supplied JSON answer template.

## When to Use

The task prompt asks you to use an Investigation Review Hub at a configurable base URL and requests a structured JSON output — typically a gap analysis, retention/preservation review, production-readiness assessment, remediation dashboard, or priority action plan tied to subpoena/request categories.

---

## Operating Rules

### 1. Resolve the Environment

- Read `environment_access.md` in the working directory if it exists. It provides:
  - `base_url` — the real hub base URL (overrides any `<TASK_ENV_BASE_URL>` placeholder in prompt text or payloads).
  - `credentials.sql_endpoint_header` and `credentials.sql_endpoint_api_key` — the header name and value for the read-only SQL query endpoint.
  - `allowed_endpoints` — the exact list of hub endpoints available for this task run.
  - `runtime_notes` — additional constraints (e.g., "use `http://task-env:9017/` from inside the Docker agent container").
- Substitute `<TASK_ENV_BASE_URL>` with the resolved `base_url` everywhere it appears.
- Use the credential header (`X-API-Key` with the supplied key) on the `POST /api/query` endpoint only. Other endpoints may or may not require it — follow the task's explicit instructions.

### 2. Read All Task Inputs

Every train task provides three kinds of input files under `input/`:

| File | Purpose |
|---|---|
| `prompt.txt` | Natural-language task description, matter identifier, deliverable type, and any special focus areas. |
| `payloads/answer_template.json` | The exact JSON schema your output must satisfy — top-level keys, field types, enum choices, ordering rules, and numeric precision. |
| `payloads/<context_file>.json` | Task-specific metadata: matter ID, client, category synopses, allowed/excluded sources, request type. May be named `request_context.json`, `review_scope.json`, or `matter_context.json`. |

**Critical**: The answer template is a *schema*, not a skeleton. It defines *what* you must produce, not *what the answer is*. Read every field description, enum list, and ordering rule.

### 3. Source of Record

- **Only** the Investigation Review Hub endpoints are the source of record for business evidence.
- **Do not** inspect, read, or use:
  - Local environment source files
  - Database files (`.db`, `.sqlite`, etc.)
  - Generated manifests or seed data
  - `setup.sh`, `.env`, or environment variable files
  - Any task answer, evaluation, or hidden files
- Local payload files (`review_scope.json`, etc.) provide **context labels only** (category titles, client name, request type). They do **not** supply counts, statuses, finding IDs, or metrics.

### 4. Hub Endpoint Inventory

The hub exposes these read-only endpoints (exact list confirmed by `environment_access.md`):

| Method | Path | Returns |
|---|---|---|
| GET | `/` | Hub root / health |
| GET | `/api/schema` | Table/view/column definitions available via SQL query |
| GET | `/api/matters` | Matter metadata (matter ID, client, type, status, hold dates) |
| GET | `/api/subpoena-categories` | Request category codes, descriptions, response status per matter |
| GET | `/api/productions` | Rolling production records with document counts per category |
| GET | `/api/custodian-sources` | Custodian data sources, collection status, device types |
| GET | `/api/documents/search` | Document-level coding, privilege, and production metadata (supports query params) |
| GET | `/api/privilege-log` | Privilege log entries — logged vs. withheld vs. waived |
| GET | `/api/qc-findings` | QC review findings — miscodes, responsiveness errors, coding defects |
| GET | `/api/retention-events` | Retention events — policy destructions, auto-purges, post-hold losses, missing records |
| GET | `/api/remediation-actions` | Previously logged or recommended remediation actions |
| POST | `/api/query` | Read-only SQL queries against the hub's backing store |

Use the SQL endpoint **sparingly** — prefer the structured GET endpoints when they return the needed evidence directly.

### 5. Answer Template Conformance

Every answer template follows a consistent meta-schema. Obey these rules without exception:

#### Top-Level Keys
- Include **exactly** the keys listed in `required_top_level_keys` (no extras, no omissions).
- Each key's type and structure are defined in `fields.<key>` or `schema.<key>`.

#### Ordering Rules
- Lists must be sorted per `ordering_rules`. Common patterns:
  - Findings/risks/issues sorted by `finding_id` / `risk_id` / `issue_id` / `event_id` / `correction_id` ascending.
  - Category statuses/coverage sorted by `category_code` ascending.
  - Action plans sorted by `priority_rank` or `rank` ascending (1 = highest).
  - Category code lists within items sorted ascending.
  - Source/reference ID lists within items sorted ascending.
- When in doubt, the ordering rule takes precedence over the natural order of hub records.

#### Enum Discipline
- Every string field typed as `enum:<set>` or listed under `enums` must use **only** values from the declared set.
- Do not invent, approximate, or paraphrase enum values.
- If no enum value perfectly matches the evidence, pick the **closest** declared value — do not create a new one.

#### Numeric Precision
- All counts are **whole integers** (no decimals, no floats, no nulls).
- Use `0` when a count is not applicable (never omit the key, never use `null`).
- Where a count is described as "from selected incomplete-log blockers only" or similar qualifier, scope it exactly as described.

#### Stable Record IDs
- Every finding, risk, issue, source, event, or correction you anchor must use the **exact stable record ID** from the hub response (`id`, `source_id`, `event_id`, `finding_id`, `correction_id`, etc.).
- Do not generate synthetic IDs, sequential numbers, or composite keys.
- When a finding references multiple hub records, list them all in `source_refs` / `record_refs` / `blocking_refs` / `issue_refs` as appropriate.

### 6. Evidence-to-Finding Mapping

When converting raw hub evidence into template items:

1. **Identify gaps**: Compare what the subpoena categories request against what productions, custodian sources, and documents actually deliver. Look for:
   - Categories with zero or under-scale productions.
   - Custodian sources marked as `lost`, `not_collected`, `partial`, or `should_exist_missing`.
   - Documents coded responsive but not produced.
   - Privilege-log entries that are withheld but unlogged (withheld count > logged count).
   - QC findings flagging miscoded responsive documents.
   - Retention events showing post-hold losses, auto-purges, or policy destructions.

2. **Quantify each finding**: Pull document counts, withheld/logged/unlogged counts, source counts, and volume numbers from the hub data. Every count in your output must be traceable to a specific hub record or aggregation of hub records.

3. **Assign severity/risk**: Match the gap magnitude and legal exposure to the template's severity/risk enum. Critical = certain regulatory impact or spoliation risk. High = material gap with uncertain remediation. Medium = partial gap with known remediation path. Low = minor, remediable, or policy-compliant pre-hold.

4. **Link to categories**: Every finding must list which request category codes it impacts (`category_impacts`, `affected_categories`, or `category_impacts` depending on template). Use the exact codes from the hub's subpoena categories.

5. **Recommend actions**: Match each finding to an action from the template's `action_type` enum. Escalation actions (disclose, waiver assessment) come before remediation actions (collect, recode, supplement log). Monitoring-only actions go last.

### 7. Metrics Construction

Metrics objects aggregate counts across all findings/events/sources. Rules:

- **Read the required_keys list** in the template's metrics definition — those exact keys must be present.
- **Sum conservatively**: When the template asks for "unlogged privilege docs," count every document where `withheld_count > logged_count` in the privilege-log data.
- **Count distinct categories**: When the template asks for `categories_with_open_gaps` or `categories_with_open_risk`, list the unique category codes, not a count of findings.
- **Boolean readiness**: `rolling_production_ready` / `production_ready` is `true` only when **zero** categories have open material gaps or unresolved blockers.
- **Box counts**: Some templates have specific box-count metrics (`destroyed_lab_archive_box_count`, `destroyed_box_count`). Pull these from retention-event volume data. If the destroyed source is measured in records not boxes and the template says "or 0 when the task's destroyed source is not measured in boxes," use `0`.

### 8. Action Plan Construction

- Each action targets one or more hub record IDs (`target_refs`) and impacts one or more category codes (`category_impacts` / `affected_categories`).
- Rank by operational priority: P0/P1 (rank 1,2) = blocking production or requiring immediate disclosure. P2 (rank 3,4,…) = remediation with known path. P3 (last) = monitor or no action.
- Assign `owner` from the template's owner enum — match the owner to the action type (e.g., `forensics` for device collection, `privilege_team` for privilege-log supplements, `outside_counsel` for disclosures).
- When the template includes `due_days`, estimate based on the urgency implied by the severity and production timeline.

### 9. Output Format

- Return **one JSON object** and **no prose** outside the JSON.
- The JSON must parse as valid JSON (double-quoted keys and strings, no trailing commas).
- Do not wrap the JSON in markdown code fences unless the task prompt explicitly permits it. Prefer raw JSON.
- All strings use the exact casing from hub data or template enums.

### 10. Verification Checklist (Before Returning)

Run this checklist against your output before delivering:

- [ ] Every key in `required_top_level_keys` is present; no extra top-level keys.
- [ ] Every list is sorted per `ordering_rules`.
- [ ] Every string field constrained by an enum uses only declared values.
- [ ] Every count is a whole integer (0 for not-applicable, never null or missing).
- [ ] Every finding/risk/issue ID is a real hub record ID, not synthetic.
- [ ] Every `source_refs` / `record_refs` / `blocking_refs` / `target_refs` list is sorted ascending.
- [ ] Every category code list within items is sorted ascending.
- [ ] Metrics sum correctly and match the enumerated findings.
- [ ] Priority ranks start at 1 and are contiguous.
- [ ] No prose, no markdown framing, no commentary outside the JSON object.
