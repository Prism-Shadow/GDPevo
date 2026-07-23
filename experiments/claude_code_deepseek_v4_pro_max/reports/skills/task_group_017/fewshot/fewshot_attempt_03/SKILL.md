# Investigation Review Hub — Structured Legal-Review JSON Deliverable

Use the **Investigation Review Hub** REST+SQL API to produce structured JSON
deliverables for eDiscovery, privilege review, production readiness, retention
gap analysis, and remediation dashboards. Every deliverable conforms to a
task-supplied `answer_template.json` schema; evidence comes exclusively from
Hub endpoints, never from local environment files, database files, or manifests.

---

## 1. Input Anatomy

Each task directory contains:

| Path | Role |
|---|---|
| `input/prompt.txt` | Natural-language task brief — identifies the matter, the deliverable type, and any focus areas. |
| `input/payloads/answer_template.json` | **The required output schema.** Read this first and keep it open while you work. |
| `input/payloads/*.json` (other) | Task-level context: matter metadata, review scope, category synopses, client details. These are **reference only** — they do not replace Hub evidence. |

The `answer_template.json` is the authoritative contract. It defines:

- **`required_top_level_keys`** — every key that must appear in the root object.
- **`fields` / `schema` / `item_fields` / `item_field_types`** — per-field types, required sub-keys, and descriptions.
- **`enums` / `enum_choices`** — closed vocabularies for every categorical field. Always pick from these.
- **`ordering_rules`** — sort order for each list (e.g., "Sort by `finding_id` ascending").
- **`numeric_precision`** — all counts are whole integers unless noted otherwise.

## 2. Hub API Access

All tasks share one investigation review environment. Use the endpoints listed in
`environment_access.md` (or the equivalent `environment_base_url` field in the
task payload). The environment file overrides any `localhost` or `127.0.0.1`
references found in task inputs.

### Authentication

Every request to the SQL query endpoint uses the header:

```
X-API-Key: review-key-017
```

REST GET endpoints may or may not require the header — include it for all requests
to be safe.

### REST Endpoints (Reference)

| Method | Path | Returns |
|---|---|---|
| `GET` | `/` | Hub status / available endpoint listing |
| `GET` | `/api/schema` | Table/column descriptions for the SQL query endpoint |
| `GET` | `/api/matters` | Matter-level metadata (matter_id, client, agency, hold dates) |
| `GET` | `/api/subpoena-categories` | Request/subpoena category codes, titles, and scopes |
| `GET` | `/api/productions` | Rolling production records and statuses |
| `GET` | `/api/custodian-sources` | Per-custodian data sources and collection statuses |
| `GET` | `/api/documents/search` | Document-level metadata, coding decisions, and production status |
| `GET` | `/api/privilege-log` | Privilege assertions, log entries, waiver issues |
| `GET` | `/api/qc-findings` | QC review findings (miscodes, coding contradictions) |
| `GET` | `/api/retention-events` | Retention and preservation events (losses, purges, archives) |
| `GET` | `/api/remediation-actions` | Previously recommended or in-progress remediation actions |

### SQL Query Endpoint

```
POST /api/query
Headers: X-API-Key: review-key-017
Body: {"query": "<SQL SELECT statement>"}
```

Use this when you need cross-entity joins, aggregations, or filtered subsets that
the REST endpoints don't surface directly. Always inspect `/api/schema` first to
understand the table schemas.

## 3. Workflow

Follow this sequence for every task.

### Step 1 — Understand the deliverable schema

Read `answer_template.json` top to bottom. Note:

- Every required top-level key.
- The enum choices available for each categorical field.
- The ordering rules for list fields.
- Which integer fields are counts vs. ranks vs. null-able.

### Step 2 — Read the task brief and context

Read `prompt.txt` to understand the matter, workstream, and deliverable. Read
any additional context payloads (`request_context.json`, `review_scope.json`,
`matter_context.json`) for client framing and category labels.

### Step 3 — Discover the Hub schema (optional but recommended)

`GET /api/schema` to see available tables. This is essential before writing SQL
queries. Also call `GET /` to confirm the Hub is reachable.

### Step 4 — Gather evidence from the Hub

Query each relevant endpoint, mapping the deliverable's sections to evidence
sources:

| Deliverable section | Typical evidence endpoints |
|---|---|
| Findings / risks / issues | `/api/documents/search`, `/api/qc-findings`, `/api/privilege-log`, `/api/retention-events` |
| Category statuses / coverage | `/api/subpoena-categories`, `/api/custodian-sources`, `/api/productions` |
| Source / archive inventory | `/api/custodian-sources`, `/api/retention-events` |
| Privilege corrections | `/api/privilege-log`, `/api/qc-findings` |
| Metrics (counts) | Aggregated from the endpoints above, or via `POST /api/query` |
| Existing remediation actions | `/api/remediation-actions` |

**Use stable record IDs exactly as they appear in the Hub.** Every document,
source, event, finding, and action has a stable identifier — use it unchanged in
`source_refs`, `record_refs`, `blocking_refs`, `target_refs`, etc.

### Step 5 — Synthesize the answer

Construct a JSON object that matches the template exactly:

1. **`matter_id`** — use the stable matter identifier from the Hub's `/api/matters` endpoint (not from the prompt alone).
2. **List fields** — build one object per material item. A "material" item is one
   where the data shows a real gap, risk, non-ready status, or required action —
   do not fabricate items to pad the list. Use `0` and `"not_applicable"` for
   count/status fields when an item doesn't involve that dimension.
3. **Enum discipline** — every categorical value must be an exact string from the
   template's enum list. Case-sensitive.
4. **Ordering** — sort every list exactly as specified in `ordering_rules`.
5. **Counts** — derive counts from Hub data. Do not estimate. When a count is
   "not applicable" for a given finding, use `0` or the null sentinel the schema allows.
6. **Category codes** — use the exact code strings from the Hub (uppercase, as
   they appear). Sort category codes ascending within every list.
7. **Metrics** — compute aggregate metrics from the evidence. Cross-check that
   sub-counts sum consistently (e.g., `logged + unlogged = withheld` for
   privilege-log gaps).
8. **Action plan** — derive actions from findings, not the other way around.
   Each action should target a specific Hub record (source, document batch, QC
   finding, privilege entry). Assign owners from the template's `owner` enum
   based on the action type (e.g., privilege work → `privilege_team`, forensics
   collection → `forensics`, disclosure decisions → `outside_counsel`).

### Step 6 — Validate before returning

- Every required top-level key is present.
- Every required sub-key is present in every list item.
- Every enum field uses an exact value from the template's enum list.
- All list ordering matches the template's `ordering_rules`.
- All numeric values are whole integers.
- All `source_refs` / `record_refs` / `target_refs` use stable Hub IDs.
- Category codes match the Hub's codes exactly and are sorted ascending within each list.

## 4. Common Evidence Patterns

### Privilege-log gaps

When `/api/privilege-log` shows `withheld_count > logged_count`, there is an
unlogged gap. The `unlogged_count` is `withheld - logged`. This typically maps
to `issue_type: "privilege_log_gap"` or similar, and `recommended_action:
"supplement_privilege_log"`.

### Responsiveness miscodes

When `/api/qc-findings` shows a document coded non-responsive but flagged as
responsive by QC, it is a miscode. The `issue_type` is
`"responsiveness_miscode"`, `current_coding` is `"nonresponsive"`, and
`recommended_action` is `"recode_and_produce"`.

### Source gaps

A custodian source with status `"not_collected"` or `"lost"` is a gap. If the
source is a personal device/account, `issue_type` is `"personal_source_gap"`
or `"collection_gap"`. If it was destroyed post-hold, `issue_type` is
`"post_hold_loss"`. Lost sources that cannot be remediated typically require
`"disclose_to_government"` or `"disclose_preservation_issue"`.

### Retention events

Retention-event endpoints return events with a status and dates. Compare
`event_date` against the matter's `hold_date` to classify:
- Event date before hold date → `"policy_destroyed_pre_hold"` (low risk, policy-compliant)
- Event date after hold date → `"post_hold_loss"` (high/critical risk)
- Auto-purge/system loss → `"active_system_loss"` or `"auto_purged"` (medium risk)

### Third-party waiver

When privilege-log entries show communication with a third party (consultant,
external recipient), privilege may be waived. `issue_type` is
`"third_party_waiver"`, `privilege_status` is `"waived"`, and
`recommended_action` is `"waiver_assessment_and_disclosure"`.

### Archives and available sources

A source with `archive_status: "available_archive"` is a remediation path. It
`limits_irretrievable_loss_for_categories` for the categories it covers.
`recommended_action` is typically `"collect_archive"` or `"search_archive"`.

## 5. Action Planning Conventions

Assign priority using these heuristics (the template's enum provides the exact
strings, e.g., `P0`–`P3`):

- **P0** — disclosure obligations: post-hold losses, destroyed evidence that
  must be disclosed to the government/regulator. Owner: `outside_counsel`.
- **P1** — active remediation: privilege log supplementation, waiver assessment,
  recoding and re-producing documents, collecting personal sources. Owners:
  `privilege_team`, `privilege_counsel`, `review_qc`, `forensics`.
- **P2** — secondary remediation: over-designation downgrades, archive searches
  with longer timelines, QC clean-up.
- **P3** — monitoring-only items or policy-compliant losses requiring no action.

Every action references specific Hub record IDs in `target_refs`. Category
impacts on an action should be all categories affected by the underlying
finding, sorted ascending.

Due dates (when the template includes `due_days`): use short windows (1–3 days)
for disclosure actions, medium (5–7 days) for privilege and recoding work,
longer (7–14 days) for collection and archive searches.

## 6. SQL Query Tips

When using `POST /api/query`:

1. Call `GET /api/schema` first and note exact table and column names.
2. Use `SELECT` statements only — the endpoint is read-only.
3. For counts, use `SELECT COUNT(*) FROM <table> WHERE <conditions>`.
4. For cross-entity queries, `JOIN` on stable ID columns (the schema endpoint
   documents the relationships).
5. Filter by `matter_id` to scope results to the current matter.
6. When REST endpoints already return the needed data, prefer them over SQL —
   use SQL only for aggregations or joins the REST endpoints don't provide.
