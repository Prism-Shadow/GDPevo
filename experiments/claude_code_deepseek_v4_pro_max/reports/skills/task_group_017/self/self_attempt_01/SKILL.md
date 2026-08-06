# Investigation Review Hub — Agent Operating Rules

These are the reusable operating rules for working with the Investigation Review
Hub, distilled from gap-analysis, retention-review, remediation-dashboard, and
production-readiness tasks. Follow these rules whenever a task directs you to
the Hub.

## 1. Environment Resolution

- The task prompt and payloads reference the Hub with the placeholder
  `<TASK_ENV_BASE_URL>`. Resolve this by reading the task-local file
  `environment_access.md` (or, if absent, the `base_url` / `environment` block
  in the task's context payload) to obtain the actual base URL and credentials.
- The standard read-only API key header is `X-API-Key`; the key value is
  `review-key-017` unless the task provides different credentials.
- The Hub runs inside the task container network; use the resolved URL for all
  API calls.

## 2. API Surface

The Hub exposes a consistent set of REST endpoints. Not every task uses every
endpoint; query only the ones relevant to the assigned review.

### Read-only GET endpoints
| Endpoint | Purpose |
|---|---|
| `GET /` | Health check |
| `GET /api/schema` | Database schema / table catalog |
| `GET /api/matters` | Matter metadata (matter ID, client, dates, status) |
| `GET /api/subpoena-categories` | Request/subpoena category codes and titles |
| `GET /api/productions` | Production status by category and source |
| `GET /api/custodian-sources` | Custodian and data-source inventory |
| `GET /api/documents/search` | Document-level search with filters |
| `GET /api/privilege-log` | Privilege-log entries (withheld, logged, waived) |
| `GET /api/qc-findings` | QC findings (responsiveness, coding, privilege) |
| `GET /api/retention-events` | Retention, purging, and hold-related events |
| `GET /api/remediation-actions` | Known or proposed remediation actions |

### Read-only SQL endpoint
| Endpoint | Purpose |
|---|---|
| `POST /api/query` | Ad-hoc SQL queries (read-only). Send `X-API-Key: review-key-017` header. Body: `{"sql": "<query>"}` |

- Use `GET /api/schema` first to understand the table layout before crafting SQL.
- Prefer the REST endpoints when they directly answer a question; use
  `POST /api/query` only when a cross-table join, aggregation, or filter is
  needed that the REST endpoints don't cover.

## 3. Source Discipline (Non-Negotiable)

Every train task repeats the same constraint. Treat it as a hard rule:

- **Use the remote Hub endpoints as the source of record** for all business
  evidence: matter metadata, categories, production status, custodians,
  documents, privilege log, QC findings, retention events, and remediation
  actions.
- **Do not inspect** local environment files, source code, database files,
  generated manifests, setup scripts, hidden notes, seed data, or evaluation
  files — even if they appear to overlap with the Hub's domain.
- Task-local payload files (`request_context.json`, `review_scope.json`,
  `matter_context.json`) are **client-facing briefing documents only**. They
  provide category labels, matter IDs, and review scope framing; they do not
  supply the underlying evidence data. All counts, statuses, record IDs, and
  metrics must be derived from Hub responses.

## 4. Task Input Anatomy

Every task follows this structure inside `input/`:

```
input/
├── prompt.txt                    # Natural-language task instructions
├── payloads/
│   ├── <context_payload>.json    # Matter context, category synopsis, client info
│   └── answer_template.json      # Output schema, enums, ordering, and precision rules
```

### 4a. Prompt (`prompt.txt`)

- Names the client and matter.
- Describes the review type (gap analysis, retention review, remediation
  dashboard, production-readiness review).
- Points to the Hub and template.
- Reiterates the source constraint.

### 4b. Context payload

- Contains client-facing framing: `matter_id`, `client`, review scope,
  category synopsis or labels.
- May restate the Hub URL and API key; the Hub is still the source of record.
- Provides no underlying evidence counts — extract those from the Hub.

### 4c. Answer template (`answer_template.json`)

- Defines the exact output schema:

  | Key | Purpose |
  |---|---|
  | `required_top_level_keys` | The keys that must appear in the answer JSON. |
  | `ordering_rules` | How to sort each list (ascending by stable ID, rank, or code). |
  | `enums` (or `enum_choices`) | The closed vocabulary for every coded field. |
  | `fields` (or `schema`) | Per-key schema: item required keys, field types, descriptions. |
  | `numeric_precision` | All counts are whole integers; no fractional or float values. |

## 5. Output Discipline

- **Return exactly one JSON object.** No prose, no markdown fences, no
  surrounding explanation — unless the prompt explicitly says otherwise.
- **Conform to every rule in the answer template:**
  - Include every `required_top_level_key`.
  - For every list item, include every `item_required_key`.
  - Use only values from the template's `enums` / `enum_choices` for coded
    fields.
  - Follow the `ordering_rules` exactly (ascending stable ID, ascending
    category code, ascending rank).
  - All numeric fields are whole integers; use `0` when a count is not
    applicable (never `null` for a count field).
- **Use stable hub record IDs** — sourcing IDs, event IDs, finding IDs,
  document IDs, action IDs, and category codes exactly as they appear in Hub
  responses. Do not synthesize or re-number IDs.
- **Sort category-code lists** ascending within every `category_impacts`,
  `affected_categories`, and similar list field.

## 6. Common Answer Schema Patterns

Across all five train tasks the answer JSON shares these structural themes:

| Top-level key | Recurrence | Purpose |
|---|---|---|
| `matter_id` | Every task | The stable matter identifier from the Hub. |
| `critical_findings` / `top_risks` / `issue_ledger` | Every task | Material gaps, risks, or issues — each keyed by a stable hub record ID. |
| `category_statuses` / `category_coverage` / `readiness_statuses` | Every task | Per-request-category status, production impact, and recommended action. |
| `retention_events` / `communication_gaps` | Retention tasks | Retention lifecycle events and communication/purge gaps. |
| `available_archives` / `retained_or_available_sources` | Remediation tasks | Sources that remain available for collection or serve as remediation paths. |
| `privilege_corrections` | Privilege tasks | Privilege-specific correction packages. |
| `metrics` | Every task | Roll-up integer counts: documents, sources, categories, events. |
| `priority_actions` / `recommended_actions` / `action_plan` | Every task | Ranked action items with owner, action type, target refs, and category impacts. |

### Item-level fields that recur across schemas

When a schema includes findings, risks, or issues, expect most or all of these
per-item keys:

- `finding_id` / `risk_id` / `issue_id` — stable hub record ID
- `issue_type` — enum
- `severity` / `risk_level` — enum (critical, high, medium, low)
- `finding_status` / `status` / `risk_status` — enum
- `source_status` — enum
- `production_impact` — enum
- `category_impacts` / `affected_categories` — sorted list of category codes
- `source_refs` / `record_refs` — sorted list of supporting hub record IDs
- `document_count`, `withheld_count`, `logged_count`, `unlogged_count` — whole integers (`0` when N/A)
- `recommended_action` — enum

### Metrics objects

Every task has a `metrics` key with whole-integer counts. Common metric fields:

- Privilege: `unlogged_privilege_docs`, `withheld_privilege_docs`,
  `logged_privilege_docs`, `waived_privilege_doc_count`, `miscoded_privileged_doc_count`
- Responsiveness: `miscoded_responsive_doc_count`
- Sources: `uncollected_personal_source_count`, `lost_personal_device_count`,
  `available_archive_count`
- Categories: `categories_with_open_gaps`, `nonready_category_count`,
  `affected_category_count`, `categories_with_open_risk`
- Production readiness: `rolling_production_ready`, `production_ready` (boolean)

## 7. Workflow: Step-by-Step Investigation Sequence

Follow this sequence for every Hub-based task:

1. **Read the answer template first.** Parse every required key, enum, ordering
   rule, and field type. Build a mental map of what the output must contain
   before touching the Hub.

2. **Read the context payload.** Extract the `matter_id`, category synopsis or
   codes, and any review-scope framing. Note that this is client-facing
   context, not evidence.

3. **Explore the Hub schema.** Call `GET /api/schema` to understand the
   available tables and columns. This informs whether REST endpoints suffice or
   SQL queries are needed.

4. **Pull matter and category metadata.** Call `GET /api/matters` and
   `GET /api/subpoena-categories` to confirm the matter exists and to enumerate
   the request categories in scope.

5. **Collect evidence from the relevant endpoints** for the review type:
   - Gap analysis: productions, custodian sources, documents, privilege log, QC
     findings.
   - Retention review: retention events, custodian sources, productions.
   - Remediation dashboard: all of the above plus remediation actions.
   - Production readiness: productions, documents, privilege log, QC findings,
     custodian sources.

6. **Cross-reference.** Correlate records across endpoints using stable IDs.
   For example, link a production gap to the specific category codes and source
   IDs that explain it; link a privilege-log gap to affected documents and
   categories.

7. **Compute metrics.** Derive every metric count from Hub responses — not from
   the context payload, not from assumptions. If a count is zero, write `0`.

8. **Assemble the output.** Build the JSON object key-by-key from the template.
   Apply ordering rules. Validate every enum value. Confirm every required key
   is present. Strip any prose or commentary.

9. **Validate before returning.** Check: all top-level keys present; all list
   item keys present; all enum values match the template; all counts are whole
   integers; all lists are sorted per the ordering rules; all IDs match their
   Hub source exactly.

## 8. Domain Vocabulary Reference

These terms appear across all train tasks with consistent meanings:

| Term | Meaning |
|---|---|
| **Matter** | A legal matter (case, investigation, subpoena response) tracked in the Hub. |
| **Request category / subpoena category** | A numbered or lettered topic in the subpoena or document request. |
| **Production** | A set of documents produced (or to be produced) to the requesting party. |
| **Rolling production** | Documents produced in batches on an ongoing schedule rather than all at once. |
| **Custodian** | An individual whose data sources (email, devices, files) are in scope. |
| **Custodian source** | A specific data source (mailbox, phone, laptop, shared drive) belonging to a custodian. |
| **Privilege log** | A record of documents withheld from production due to attorney-client privilege or work-product protection. |
| **QC finding** | A quality-control finding — e.g., a document miscoded as non-responsive when it is in fact responsive. |
| **Retention event** | A lifecycle event for records: policy-driven destruction, auto-purge, system loss, or hold preservation. |
| **Litigation hold** | A legal notice suspending normal deletion/retention policies to preserve evidence. |
| **Pre-hold / post-hold** | Whether a retention event occurred before or after the litigation hold was issued. |
| **Remediation action** | A corrective step: collect a missing source, recode documents, supplement a privilege log, disclose a preservation issue. |
| **Gap** | A shortfall between what was requested and what has been preserved, collected, reviewed, or produced. |
| **Waiver** | Loss of privilege protection, typically through disclosure to a third party. |
| **Over-designation** | Marking a document as privileged at too high a level (e.g., work product when only attorney-client applies). |

## 9. Error Prevention Checklist

Before returning the answer JSON, verify:

- [ ] Every `required_top_level_key` is present.
- [ ] Every list item contains all `item_required_keys`.
- [ ] All enum-coded fields use values from the template's enum definitions exactly.
- [ ] All lists are sorted per `ordering_rules`.
- [ ] All category-code lists are sorted ascending.
- [ ] All counts are whole integers; `0` is used when a count field is not applicable.
- [ ] All record IDs match their Hub source exactly (no synthesized IDs).
- [ ] No prose, explanation, or markdown fences surround the JSON object.
- [ ] No local env files, database files, manifests, or seeds were consulted.
- [ ] The `matter_id` matches the task's matter identifier.
