# Output Guidance

## Template-Driven Output Strategy

Every task provides an `answer_template.json` that serves as the contract for the
output structure. The solver must:

1. **Read the template first** — before pulling hub data, understand the output shape.
2. **Map entities to template sections** — identify which sections correspond to which
   hub endpoints.
3. **Build bottom-up from evidence** — gather records, then assemble sections.

## Cross-Entity Linking Patterns

The five train tasks reveal common linking patterns between hub entities and output
fields:

### Sources → Custodian Sources Endpoint

When a task involves collection/preservation gaps:

- Source IDs come from `GET /api/custodian-sources` and map to fields like
  `source_refs`, `target_refs`.
- Source statuses (`collected`, `not_collected`, `lost`, `partial`) map to template
  enums like `source_status` or `availability_status`.
- Personal devices (phones, personal email, Signal, SMS) that are not collected
  appear as `personal_source_gap` or `collection_gap` issues.
- Archives that are available despite deletions appear under
  `retained_or_available_sources`.

### Documents → Documents Endpoint

- Document IDs (DOC-*) anchor individual miscoding and production findings.
- Fields like `document_count`, `withheld_count`, `logged_count`, `unlogged_count`
  roll up from document-level coding and privilege status.
- `current_coding` and `produced_status` map to template coding/produced enums.
- Responsiveness miscodes (e.g., "coded nonresponsive but is responsive") are
  identified by comparing document coding against QC findings.

### Privilege Log → Privilege Log Endpoint

- Incomplete privilege logs show `logged_count` < `withheld_count`, producing
  `unlogged_count` = `withheld_count` - `logged_count`.
- Third-party waiver records carry a named third party.
- Privilege miscoding corrections link QC findings back to privilege log entries.
- `privilege_status` maps to template enums like `incomplete_log`, `waived`,
  `over_designated`.

### QC Findings → QC Findings Endpoint

- QC findings flag individual miscoded documents and provide corrected dispositions.
- A "zero-claim contradiction" means a document was coded nonresponsive but QC
  identified it as responsive.
- QC findings link to both documents and subpoena categories.

### Retention Events → Retention Events Endpoint

- Retention events have `status` values distinguishing pre-hold policy destruction
  (`policy_destroyed_pre_hold`) from post-hold losses (`post_hold_loss`) and
  auto-purges (`auto_purged`).
- Events carry `hold_date`, `event_date`, `policy_section`, `volume_count`, and
  `volume_unit`.
- Lost records that should exist but are missing have status
  `should_exist_missing`.
- Active system losses (Teams messages pre-cutoff, auto-purged voicemail) form
  communication gap records.

### Remediation Actions → Remediation Actions Endpoint

- Existing action records (ACT-*) may already exist in the hub.
- New actions in the output `action_plan` or `priority_actions` should use new
  synthesized IDs (e.g., `ACT-MATTER-NNN`) and reference hub record IDs as targets.

## Sorting and Ordering

Templates mandate specific ordering rules. Always follow them exactly:

- **Category codes**: ASCII ascending (e.g., "A" < "B" < "C", "R07" < "R08" < "R09",
  "SEC-1" < "SEC-2").
- **Record IDs**: ASCII ascending by their string representation.
- **Priority ranks**: Numeric ascending (1 first, then 2, etc.).
- **List items within sections**: Sort by the specified key (e.g., `finding_id`
  ascending, `risk_id` ascending, `category_code` ascending).

## Numeric Aggregation Rules

When rolling up counts across entities:

- **Document counts**: Sum individual document records. Each DOC-* is one document
  unless the hub indicates multi-document groupings.
- **Withheld counts**: Count documents with `withheld` or `not_produced` status in
  the privilege log.
- **Logged counts**: Count entries with complete log records.
- **Unlogged counts**: `withheld - logged` for the relevant privilege log subset.
- **Source counts**: Count unique source IDs in the affected set.
- **Event counts**: Count unique retention or communication-gap event IDs.
- **Box counts**: Sum `volume_count` where `volume_unit` is `boxes`.
- **Days counts**: Sum or use as-is where `volume_unit` is `days`.
- **Category counts**: Count unique category codes in the affected set.

All counts are whole integers. Zero is used when the count is not applicable.

## Boolean Derivation

- `rolling_production_ready` / `production_ready`: `false` if any request category
  has a blocking gap (preservation risk, collection gap, privilege log gap,
  responsiveness gap, withholding gap). `true` only if all categories are complete
  or have `no_current_gap` / `no_open_gap`.

## Priority Assignment Heuristic

The train answers show consistent priority assignment:

| Risk/Severity                | Priority | Typical due_days |
|------------------------------|----------|------------------|
| Critical preservation loss   | P0       | 3                |
| High-severity gaps           | P1       | 3-7              |
| Privilege waiver exposure    | P1       | 3-5              |
| QC recoding                  | P1       | 5                |
| Supplement privilege log     | P1       | 5                |
| Collect personal source      | P1       | 7                |
| Search archive               | P1       | 10               |
| Medium-severity corrections  | P2       | varies           |
| Low-risk policy losses       | P3       | varies           |

Disclosure actions (to government, to opposing party) always rank highest.

## Owner Assignment

Match owners to the action type:
- **Disclosure**: `outside_counsel` or `litigation_counsel`
- **Forensic recovery / collection**: `ediscovery_vendor`, `forensics`, `client_it`
- **Privilege log / waiver**: `privilege_team`, `privilege_counsel`
- **Recoding / QC remediation**: `review_qc`, `review_vendor`
- **Archive search**: `ediscovery_vendor`
- **Missing records**: `compliance_audit`, `records_management`
- **System gap documentation**: `it_messaging`

Use only owners present in the template's owner enum.
