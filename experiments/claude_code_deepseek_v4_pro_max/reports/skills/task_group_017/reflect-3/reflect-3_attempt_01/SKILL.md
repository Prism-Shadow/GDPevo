# Investigation Review Hub — Structured Gap Analysis Skill

## When to Use

Invoke this skill when the task involves an Investigation Review Hub matter and asks for a structured JSON deliverable: a gap analysis, remediation dashboard, retention review, privilege review, or production-readiness assessment. The hub holds multiple matters; always confirm the `matter_id` from the task payload before querying.

## Hub Access

Use the task-provided base URL (typically `http://task-env:9017/`). All read operations go through two channels:

**Dedicated GET endpoints** (no auth header required for read-only endpoints):
- `GET /api/matters` — list all matters
- `GET /api/subpoena-categories` — request categories per matter
- `GET /api/productions` — production batch stats
- `GET /api/custodian-sources` — custodian devices, archives, collection status
- `GET /api/privilege-log` — privilege entries and log gaps
- `GET /api/qc-findings` — quality-control findings
- `GET /api/retention-events` — retention and destruction events
- `GET /api/remediation-actions` — suggested remediation steps

**SQL query endpoint** (requires API key header):
- `POST /api/query` with `Content-Type: application/json` and header `X-API-Key: review-key-017`
- Body: `{"sql": "SELECT ... FROM table WHERE matter_id = 'MTR-...' ORDER BY ..."}`
- Use for cross-table joins or when you need precise filtering.

Prefer the SQL endpoint when you need to filter by `matter_id` explicitly — it returns the same data as the GET endpoints but guarantees matter-scoping. The GET endpoints may return all rows; always filter client-side by `matter_id` if you use them.

## Schema Reference

The hub exposes these tables (columns available via `GET /api/schema`):

| Table | Key columns | What it tells you |
|-------|------------|-------------------|
| `matters` | matter_id, hold_date, agency, status | Case metadata and hold timing |
| `subpoena_categories` | category_code, date_start, date_end, topic_tags | What each request category covers |
| `production_stats` | category_code, produced_count, withheld_count, status, zero_claim_reason | Per-category production completeness |
| `custodian_sources` | source_id, custodian_name, source_type, status, post_hold, issue_tags, category_impacts | Device/archive collection status |
| `review_documents` | doc_id, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary | Individual document coding and issues |
| `privilege_entries` | entry_id, category_code, doc_count, withheld_count, logged_count, issue_type, third_party | Privilege log completeness and exceptions |
| `qc_findings` | finding_id, issue_type, doc_count, affected_category, severity | Quality-control defects |
| `retention_events` | event_id, status, event_date, hold_date, affected_categories, volume_count, volume_unit | Retention loss and preservation events |
| `remediation_actions` | action_id, action_type, priority, severity, owner, target_ref, due_days | Prescribed remediation steps |

## Separating Signal from Noise

The hub deliberately includes operational noise. Treat these markers as indicators that a record is **not** a material finding:

**Explicit noise tags in remediation_actions:**
- Description contains `"Routine action included as realistic operational noise"`
- `action_id` ends with `-NOISE-` (e.g., `ACT-SENTINELGJ-NOISE-01`)

**Explicit noise markers in review_documents:**
- Summary contains `"Document appears in a noisy search result set but is not one of the stable exception records"`
- Summary contains `"Routine review item with similar wording to escalated exceptions in other matters"`
- Summary contains `"Potentially responsive family member requiring matter and category filtering"`
- Summary contains `"Review note references a source exception that is not independently escalated"`
- Summary contains `"Metadata overlay changed date fields but did not alter production status"`

**Explicit noise markers in custodian_sources:**
- `issue_tags` contains `"routine"` AND notes say `"No production-impacting issue has been escalated yet"`
- Notes contain `"Collection status differs between custodian tracker and vendor load report"` without a concrete gap description
- Notes contain `"Source map entry has minor metadata normalization issues"` as the only issue

**Explicit noise markers in privilege_entries:**
- Notes contain `"Entry included to create similar labels across matters"`
- Notes contain `"Privilege sample has ordinary review variance"`
- Notes contain `"Review team marked this item for follow-up but not immediate remediation"` without a concrete, quantified gap

**Explicit noise markers in qc_findings:**
- Notes contain `"Finding is similar to escalated records in another matter"`
- Notes contain `"Review manager requested re-sampling before escalation"`
- Notes contain `"Quality-control sample is noisy but not dispositive without source comparison"`

**Material records** have concrete, specific issue descriptions with quantified impact. Examples:
- `"Personal iPhone erased on 2025-02-04 after subpoena issuance"` → material preservation failure
- `"Privilege log covers 1410 of 3180 withheld R11 documents"` → material privilege log gap
- `"One complaint email miscoded nonresponsive for R09"` → material responsiveness miscode
- `"Six off-site bid file boxes destroyed after hold"` → material post-hold loss

When in doubt: if the description is vague ("similar to another matter," "requires re-sampling," "minor metadata normalization," "no issue escalated yet"), treat it as noise.

## Building the Answer

### 1. Start with the answer template

Every task provides `input/payloads/answer_template.json`. Read it first. It defines:
- Required top-level keys
- Enum values for every categorical field (use ONLY these values, not the hub's own labels)
- Ordering rules (sorting requirements)
- Required keys per list item
- Numeric precision rules

### 2. Query all relevant hub tables for the target matter

Query every table that maps to the template sections. Use `WHERE matter_id = 'MTR-...'` in SQL, or filter GET results by matter_id. Always sort by the primary key to get a stable order.

### 3. Map hub records to template sections

Each answer template section draws from specific hub tables:

**Gap analysis / remediation dashboard patterns:**
- Findings/risks → material records from `custodian_sources`, `retention_events`, `privilege_entries`, `qc_findings`
- Category statuses → derived from `production_stats` plus material issues per category
- Metrics → aggregated counts from the material records
- Priority actions → material records from `remediation_actions` (exclude NOISE entries)

**Retention review patterns:**
- Retention events → all rows from `retention_events` table, mapped to template enums
- Communication gaps → retention events about communication systems + uncollected custodian sources
- Available archives → custodian sources with `status = 'available'` or retention events with `status = 'retained'` / `'available'`
- Metrics → aggregated counts from the table rows

**Privilege/production readiness patterns:**
- Readiness statuses → per-category readiness derived from privilege entries and QC findings
- Issue ledger → material privilege entries and QC findings mapped to issue template
- Privilege corrections → material privilege entries requiring remediation
- Metrics → aggregated privilege and QC counts

### 4. Use stable hub IDs

Use record IDs exactly as they appear in the hub:
- Source IDs: `SRC-...`
- Privilege entry IDs: `PRIV-...`
- QC finding IDs: `QC-...`
- Retention event IDs: `RET-...`
- Document IDs: `DOC-...`

When a template field asks for `source_refs`, `record_refs`, `target_refs`, or `blocking_refs`, use the stable hub IDs. Sort them ascending within each list.

### 5. Map hub values to template enums

Each template defines its own enum vocabulary. Common mappings:

| Hub value | Common template enum mapping |
|-----------|------------------------------|
| `lost` (source status) | `"lost"` or `"destroyed"` depending on template |
| `not_collected` (source) | `"not_collected"` |
| `incomplete_log` (privilege) | `"incomplete_log"` or `"privilege_log_gap"` |
| `third_party_waiver` | `"third_party_waiver"` |
| `over_designated` | `"over_designation"` or `"privilege_miscoding"` |
| `post_hold_loss` (retention) | `"post_hold_loss"` or `"preservation_failure"` |
| `policy_destroyed_pre_hold` | `"policy_destroyed_pre_hold"` or `"retention_loss"` |
| `system_loss` | `"active_system_loss"` or `"retention_loss"` |
| `should_exist_missing` | `"should_exist_missing"` or `"missing_required_record"` |
| `miscoded_nonresponsive` (QC) | `"responsiveness_miscode"` |
| `miscoded_privilege` (QC) | `"privilege_miscoding"` |

Always verify against the specific template's enum list. If a hub value has no direct template enum match, choose the closest enum from the template's allowed values.

### 6. Ordering

Sort every list according to the template's `ordering_rules`. Common patterns:
- Findings/risks: by `finding_id` or `priority_rank` ascending
- Category lists: by `category_code` ascending (lexicographic)
- Actions: by `priority_rank` ascending (1 = highest priority)
- IDs within arrays (source_refs, category_impacts): sorted ascending

### 7. Counts and metrics

- All counts are whole integers (per template `numeric_precision`)
- `unlogged_count = withheld_count - logged_count` (when the template uses this formula)
- When a count is not applicable, use `0` (not `null`)
- Aggregate only from material records, not noise

### 8. Boolean fields

When the template has a boolean like `rolling_production_ready` or `production_ready`, set to `false` if any material open issues exist for any category. Set to `true` only when all categories are confirmed complete with no open gaps.

## Common Pitfalls

1. **Including noise as findings.** Always check the description/notes for noise markers before including a record as a finding.
2. **Using hub labels instead of template enums.** The hub may say `"supplemental_collection"` but the template requires `"collect_source"` or `"collect_personal_device"`.
3. **Synthesizing new IDs.** Use hub stable IDs; don't invent IDs like `"FIND-001"` or `"PA-001"` unless the template explicitly allows synthetic keys.
4. **Wrong date comparisons.** Compare `event_date` to `hold_date` to determine pre-hold vs post-hold. Events on or after the hold date are post-hold.
5. **Ignoring ordering rules.** The template ordering rules are strict — sort exactly as specified.
6. **Null vs 0.** Use `0` for numeric fields when not applicable, use `null`/`None` only for string fields when not applicable.
7. **Mixing matters.** Always scope queries to the target `matter_id`. The hub contains 16 matters with similar-looking record IDs.
