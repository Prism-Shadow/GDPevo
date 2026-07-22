# Investigation Review Hub — Structured Assessment Skill

## Purpose

Produce a single, conformant JSON assessment for a legal investigation matter by
querying the shared Investigation Review Hub REST and SQL endpoints. The hub is
the **sole source of record** for matter metadata, subpoena/request categories,
production status, custodian sources, review documents, privilege-log data, QC
findings, retention events, and remediation actions.

## Environment Access

Read the task-provided `environment_access.md` (or equivalent) for:

- **`base_url`** — the root URL of the Investigation Review Hub (e.g.
  `http://task-env:9017/`). Use this for **every** endpoint call.
- **`credentials.sql_endpoint_header`** — the HTTP header name required for
  `POST /api/query` (typically `X-API-Key`).
- **`credentials.sql_endpoint_api_key`** — the header value.

If the prompt or payload references `<TASK_ENV_BASE_URL>`, substitute
`base_url` from `environment_access.md`.

## Available Endpoints

| Method | Path                        | Purpose                                         |
|--------|-----------------------------|-------------------------------------------------|
| GET    | `/`                         | Hub health / root                               |
| GET    | `/api/schema`               | Full relational schema (tables, columns, types) |
| GET    | `/api/matters`              | Matter metadata (name, type, dates, status)     |
| GET    | `/api/subpoena-categories`  | Request/subpoena category codes and descriptions|
| GET    | `/api/productions`          | Production rounds and per-category volumes      |
| GET    | `/api/custodian-sources`    | Custodian data sources and collection status    |
| GET    | `/api/documents/search`     | Search documents by matter, coding, or status   |
| GET    | `/api/privilege-log`        | Privilege assertions, log entries, gaps         |
| GET    | `/api/qc-findings`          | QC review issues, miscodes, discrepancies       |
| GET    | `/api/retention-events`     | Retention / preservation events and losses      |
| GET    | `/api/remediation-actions`  | Existing or recommended remediation steps       |
| POST   | `/api/query`                | Read-only SQL queries (requires auth header)    |

The `POST /api/query` endpoint accepts a JSON body with a `"query"` field
containing a read-only SQL `SELECT` statement. Send the API key header from
`environment_access.md`. Use SQL for cross-entity joins, aggregations, or
filtered lookups that single-entity GET endpoints cannot express.

## General Workflow

### 1. Read All Task-Local Inputs

- **`prompt.txt`** — the natural-language task description identifying the
  matter ID, workstream type, and deliverable shape.
- **`payloads/answer_template.json`** — the required output JSON schema
  (top-level keys, per-item required keys, enum choices, ordering rules,
  numeric precision).
- **`payloads/request_context.json`** (if present) — client name,
  workstream label, matter ID, requesting role, cutoff date.
- **`payloads/review_scope.json`** (if present) — request category synopsis,
  category codes and their human-readable titles.
- **`payloads/matter_context.json`** (if present) — matter-specific
  environment overrides, endpoint lists, output contract notes.

### 2. Explore the Hub Schema

Call `GET /api/schema` early to understand the relational model. Identify which
tables hold:

- Matters and their attributes
- Subpoena/request categories per matter
- Custodian sources and collection statuses
- Documents (coding, production status, privilege assertions)
- Privilege log entries (withheld/logged/unlogged counts)
- QC findings (miscoding, zero-claim contradictions, privilege defects)
- Retention events (dates, policy sections, volumes, risk levels)
- Remediation actions (owners, priorities, targets)

### 3. Gather Matter-Specific Evidence

#### For gap/readiness analyses (like train 001, 004):

- Query documents for responsiveness miscodes, zero-claim contradictions, and
  production blockers.
- Query privilege-log for incomplete logs (where `withheld > logged`),
  third-party waiver risks, and over-designation.
- Query custodian sources for lost, destroyed, uncollected, or partial sources.
- Query QC findings for confirmed miscoding defects.
- Join across tables to associate each finding with affected request categories.

#### For retention/preservation reviews (like train 002):

- Query retention events for pre-hold policy destructions, post-hold losses,
  active-system losses, auto-purges, and missing-required-record events.
- Separate pre-hold policy-compliant destructions from post-hold preservation
  failures.
- Identify communication gaps (e.g., purged collaboration-platform messages,
  auto-deleted voicemail) and their purge windows.
- Query available archives that can limit irretrievable loss for affected
  categories.

#### For cross-system remediation dashboards (like train 003, 005):

- Rank material risks by severity (critical > high > medium > low).
- For each risk, identify: issue type, status, source status, production
  impact, affected categories, supporting record IDs, document/volume counts,
  withheld/logged/unlogged splits, third-party exposure, and recommended action.
- Build per-category coverage: status, production impact, supporting issue
  refs, recommended action, and open-issue count.
- List retained or available sources (archives, retained devices, cloud backups)
  with availability status, active-system issues, affected categories, and
  which categories the source can still remediate.
- Roll up metrics: counts for top risks, destroyed sources, post-hold losses,
  uncollected personal sources, available archives, miscoded docs, privilege
  gaps, waiver exposures, missing records, affected categories, and the set of
  categories with open risk.
- Build a ranked action plan with owners, priorities, target refs, affected
  categories, and due-days.

### 4. Build the Answer JSON

Construct a single JSON object whose top-level keys **exactly** match
`answer_template.json`'s `required_top_level_keys`.

#### For every list:

- **Sort** according to the template's `ordering_rules`.
- Use only **stable hub record IDs** for `*_id`, `*_refs`, `source_refs`,
  `issue_refs`, `target_refs`, `blocking_refs`, `record_refs` fields.
- Match **every** `item_required_keys` list per object.

#### For every enum field:

- Use **only** values from the template's `enums` block. Do not invent new
  enum values.

#### For every count field:

- Use whole integers. Use `0` when not applicable (unless the field description
  says otherwise). Never use `null` for a count field that expects an integer.

#### For boolean fields:

- Use JSON `true` or `false` (not strings).

### 5. Validate Before Returning

- **Top-level keys**: present and matching the template exactly.
- **Sort order**: every list sorted per the template's `ordering_rules`.
- **Enums**: every enum field draws from the template's allowed values.
- **Stable IDs**: all references use hub record IDs, not synthesized keys
  (unless the template instructs otherwise for action IDs like `ACT-*-*`).
- **Numeric precision**: all counts are whole integers.
- **No prose**: return only the JSON object; no explanatory text.
- **No local-source contamination**: every factual assertion traces to a hub
  endpoint response. Never use local files, seeds, manifests, or answer files
  as data sources.

## Common Enum Families (Conceptual)

The templates across tasks share recurring conceptual categories. The **exact**
allowed values are always in the task-local `answer_template.json`; the
summaries below are for orientation only.

### Issue / Risk Types

- **Preservation / retention failures**: `preservation_failure`,
  `post_hold_loss`, `retention_loss`, `collection_gap`, `auto_purge`,
  `active_system_loss`, `should_exist_missing`, `missing_required_record`.
- **Privilege defects**: `privilege_log_gap`, `privilege_waiver`,
  `third_party_waiver`, `over_designation`, `miscoded_privilege`,
  `privilege_miscoding`.
- **Review / coding defects**: `responsiveness_miscode`,
  `zero_claim_contradiction`, `responsive_miscoding`.
- **Source gaps**: `personal_source_gap`, `personal_email_gap`,
  `personal_phone_gap`, `archive_available`.

### Severity / Risk Levels

Typically `critical`, `high`, `medium`, `low`.

### Status Families

- **Finding status**: `open`, `confirmed`, `remediation_pending`,
  `protocol_noncompliant`, `ready`, `no_gap`.
- **Source status**: `lost`, `destroyed`, `not_collected`, `partial`,
  `collected`, `pending`, `not_applicable`, `available_archive`,
  `should_exist_missing`, `unknown`.
- **Category status**: varies by template — `complete`, `incomplete`,
  `preservation_loss`, `collection_gap`, `privilege_log_gap`,
  `responsiveness_gap`, `source_gap_with_archive_available`, `archive_available`,
  `underproduced_privilege_corrections`, `mixed_preservation_and_missing_record`,
  `no_open_gap`.

### Production Impact

`source_lost`, `source_missing`, `source_available`, `not_produced`,
`underproduced`, `withheld_unlogged`, `privilege_exposure`, `recode_needed`,
`missing_record`, `no_production_impact`, `multiple_impacts`.

### Action Types

- **Disclosure / escalation**: `disclose_to_government`,
  `disclose_preservation_issue`, `waiver_assessment_and_disclosure`,
  `escalate_to_counsel`.
- **Collection / recovery**: `collect_source`, `collect_personal_device`,
  `collect_personal_email`, `collect_signal_messages`, `collect_archive`,
  `forensic_recovery`, `search_archive`, `restore_from_backup`.
- **Review / recoding**: `recode_and_produce`, `qc_remediation`,
  `privilege_re_review`, `privilege_recode_and_log`, `quality_control_review`.
- **Log remediation**: `supplement_privilege_log`.
- **Investigation**: `investigate`, `locate_missing_record`,
  `custodian_followup`.
- **Documentation**: `document_system_gap`, `no_action_policy_loss`.
- **Passive**: `monitor_only`, `no_action`.

### Owners / Responsible Roles

`outside_counsel`, `client_legal`, `client_it`, `ediscovery_vendor`,
`review_vendor`, `review_qc`, `privilege_team`, `privilege_counsel`,
`records_vendor`, `records_management`, `investigation_team`, `forensics`,
`it_messaging`, `compliance_audit`, `legal_operations`, `litigation_counsel`,
`review_operations`.

### Priority Levels

`P0` (highest), `P1`, `P2`, `P3` (lowest).

## SQL Query Patterns

When using `POST /api/query`, structure queries to answer specific questions:

- **Cross-entity joins**: Join documents ↔ privilege-log ↔ QC-findings ↔
  custodian-sources on matter ID and stable record IDs.
- **Aggregation**: `COUNT`, `SUM` for document counts, withheld/logged/unlogged
  splits, source counts, box counts.
- **Filtering**: By `matter_id`, `category_code`, `status`, `severity`, date
  ranges, coding values.
- **Grouping**: By category, issue type, severity, or owner for roll-up metrics.

Keep queries read-only (`SELECT` only). Parameterize the matter ID rather than
hard-coding it.

## Anti-Patterns (Do Not Do)

- **Never** inspect local environment source files, database files, seed data,
  generation manifests, hidden notes, or task answer/evaluation files for
  business evidence.
- **Never** use `localhost`, `127.0.0.1`, or `env/setup.sh` URLs — always use
  the `base_url` from `environment_access.md`.
- **Never** return prose outside the JSON object unless the prompt explicitly
  asks for a narrative memo.
- **Never** invent enum values — if a situation doesn't match any allowed enum,
  choose the closest fit (or `other` / `unknown` if available).
- **Never** use `null` for integer count fields that expect `0` when not
  applicable.
- **Never** skip a required top-level key or a required per-item key.
- **Never** output lists in arbitrary order — always follow the template's
  `ordering_rules`.

## Quick-Start Checklist

1. [ ] Read `environment_access.md` → note `base_url` and API key.
2. [ ] Read `prompt.txt` → identify matter ID and workstream type.
3. [ ] Read all files in `payloads/` → note the answer template schema, any
   category synopses, and matter-specific constraints.
4. [ ] Call `GET /api/schema` → map tables to the evidence needed.
5. [ ] Call relevant GET endpoints for the matter (`/api/matters`,
   `/api/subpoena-categories`, etc.) filtering by matter ID.
6. [ ] Use `POST /api/query` for cross-entity joins and aggregations.
7. [ ] Build the JSON answer matching the template's structure, enums, ordering,
   and numeric precision.
8. [ ] Validate: stable IDs, sort order, required keys, integer counts, no prose.
9. [ ] Return the single JSON object.
