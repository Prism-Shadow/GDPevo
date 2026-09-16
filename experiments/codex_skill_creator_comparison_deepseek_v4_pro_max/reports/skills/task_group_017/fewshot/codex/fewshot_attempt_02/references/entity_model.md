# Entity Model

The Investigation Review Hub organizes data around a legal matter. Each matter has subpoena categories defining what must be produced. Evidence sources flow from custodians, through review coding and QC, into privilege logs and production batches. Retention events track preservation history.

## Core relationships

```
Matter ──► Subpoena Categories ──► Production Batches
    │
    ├──► Custodian Sources ──► Documents ──► QC Findings
    │                           │
    │                           ▼
    │                       Privilege Log
    │
    ├──► Retention Events
    └──► Remediation Actions
```

## Entity identifiers

Every entity has a stable identifier field that must be used verbatim from hub responses:

| Entity | ID field | Example |
|---|---|---|
| Matter | `matter_id` | `MTR-SENTINEL-GJ` |
| Subpoena category | `category_code` | `R09`, `SEC-3`, `A` |
| Production batch | `production_id` | from hub response |
| Custodian source | `source_id` | `SRC-SENT-ALDEN-PHONE` |
| Document | `doc_id` | `DOC-SENT-ALDEN-DEALER-ESC` |
| Privilege log entry | `log_id` | `PRIV-SENT-LOG-GAP` |
| QC finding | `finding_id` | `QC-SENT-R09-NR` |
| Retention event | `event_id` | `RET-HARB-EHS-POST` |
| Remediation action | `action_id` | `ACT-SENT-001` |

## Common patterns

### Sources and collection gaps

A custodian source with `collection_status: "not_collected"` means the source was never collected. A source with `collection_status: "lost"` means it existed but was destroyed or became unreachable. Either creates a collection gap that affects every subpoena category the source maps to.

### Privilege-log gaps

Compare `documents` rows coded as `privileged` (and marked `withheld`) against `privilege_log` entries. A gap exists when withheld privileged documents lack corresponding log entries. Metrics: `withheld_count` = total privileged withheld; `logged_count` = entries in the log; `unlogged_count` = withheld minus logged.

### QC findings as evidence

QC findings are the primary source for coding defects. A finding with `issue_type: "responsiveness_miscode"` indicates a document coded nonresponsive should have been responsive. Record the finding ID, the affected document IDs, and the category impacts.

### Retention events

Retention events describe what happened to records over time. Key status codes:

- `policy_destroyed_pre_hold` — destroyed per retention policy before the litigation hold; low risk.
- `post_hold_loss` — destroyed after the hold was issued; critical/high risk, requires disclosure.
- `auto_purged` — system auto-deletion (e.g., voicemail after 90 days); medium risk, document the gap.
- `active_system_loss` — current system does not retain the data (e.g., Teams messages before a cutoff date); medium risk.
- `should_exist_missing` — records expected to exist per policy but not found; high risk.

### Archives as remediation paths

When a custodian source or retention event has a related archive source (e.g., an email archive that covers Teams messages), the archive's `limits_loss_for_categories` indicates which categories it can remediate. Mark such sources under `retained_or_available_sources` with `availability_status: "available_archive"`.

### Third-party waiver

When a privilege log entry references a `third_party` and the QC finding or log note indicates communication with that third party waived privilege, treat it as a `third_party_waiver` issue. The volume is the count of affected emails/documents.

### Derived fields in deliverables

When a deliverable asks for fields not directly in the API (e.g., `missing_component`, `current_coding`, `corrected_disposition`), derive them from hub data:

- `missing_component` — a short string describing what is absent (e.g., `"business_only_counsel_copy_overdesignation"`)
- `current_coding` — from `documents.coding` field
- `corrected_disposition` — what should happen after remediation (`responsive_produce`, `supplement_log`, `waiver_assessment`, etc.)
- `produced_status` — from `documents.produced_status` field
