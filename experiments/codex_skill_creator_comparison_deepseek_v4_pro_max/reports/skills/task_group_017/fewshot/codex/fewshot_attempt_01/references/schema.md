# Investigation Review Hub — Data Model Reference

## Tables and Columns

### matters

| Column | Type | Description |
|--------|------|-------------|
| matter_id | TEXT | Stable matter identifier (e.g. `MTR-SENTINEL-GJ`) |
| name | TEXT | Human-readable matter name |
| agency | TEXT | Requesting agency (DOJ, SEC, etc.) |
| investigation_type | TEXT | `grand_jury_subpoena` or `sec_subpoena` |
| issued_date | TEXT | Subpoena issue date (YYYY-MM-DD) |
| hold_date | TEXT | Litigation hold date (YYYY-MM-DD) |
| lead_partner | TEXT | Lead partner name |
| description | TEXT | Matter scope summary |
| status | TEXT | `active_review` or `closed` |

### subpoena_categories

| Column | Type | Description |
|--------|------|-------------|
| matter_id | TEXT | FK to matters |
| category_code | TEXT | Request category code (e.g. `R01`, `SEC-A`) |
| title | TEXT | Category title |
| date_start | TEXT | Time window start (YYYY-MM-DD) |
| date_end | TEXT | Time window end (YYYY-MM-DD) |
| request_text | TEXT | Full request text |
| topic_tags | TEXT | JSON array of topic keywords |

### production_stats

| Column | Type | Description |
|--------|------|-------------|
| matter_id | TEXT | FK to matters |
| batch_id | TEXT | Production batch identifier |
| batch_date | TEXT | Production date |
| category_code | TEXT | FK to subpoena_categories |
| produced_count | INTEGER | Documents produced |
| withheld_count | INTEGER | Documents withheld |
| responsive_count | INTEGER | Responsive documents identified |
| nonresponsive_count | INTEGER | Non-responsive documents identified |
| status | TEXT | `produced`, `closed`, or `pending` |
| zero_claim_reason | TEXT | Reason when zero responsive/produced was claimed |
| notes | TEXT | Freeform notes |

### custodian_sources

| Column | Type | Description |
|--------|------|-------------|
| source_id | TEXT | Stable source identifier |
| matter_id | TEXT | FK to matters |
| custodian_name | TEXT | Custodian name |
| role | TEXT | Custodian's role |
| source_type | TEXT | `email`, `laptop`, `personal_phone`, `teams_export`, `network_share`, `personal_messaging`, `shared_drive` |
| source_label | TEXT | Human-readable label |
| status | TEXT | `collected`, `not_collected`, `lost`, `partial`, `available`, `in_review`, `pending` |
| event_date | TEXT | Last status update date |
| post_hold | INTEGER | `1` if event occurred after hold date, else `0` |
| category_impacts | TEXT | JSON array of affected category codes |
| issue_tags | TEXT | JSON array of issue tags |
| notes | TEXT | Freeform notes |

### review_documents

| Column | Type | Description |
|--------|------|-------------|
| doc_id | TEXT | Stable document identifier |
| matter_id | TEXT | FK to matters |
| title | TEXT | Document title |
| doc_date | TEXT | Document date |
| custodian_name | TEXT | Custodian name |
| source_system | TEXT | `email`, `teams`, `archive`, `shared_drive` |
| category_code | TEXT | FK to subpoena_categories |
| responsiveness | TEXT | `responsive` or `nonresponsive` |
| privilege_status | TEXT | `privileged`, `nonprivileged`, or `unknown` |
| produced_status | TEXT | `produced`, `not_produced`, `withheld`, `unknown` |
| issue_tags | TEXT | JSON array of issue tags |
| summary | TEXT | Document summary |

### privilege_entries

| Column | Type | Description |
|--------|------|-------------|
| entry_id | TEXT | Stable privilege entry identifier |
| matter_id | TEXT | FK to matters |
| category_code | TEXT | FK to subpoena_categories |
| custodian_name | TEXT | Custodian name |
| doc_count | INTEGER | Total documents in this entry |
| withheld_count | INTEGER | Documents withheld as privileged |
| logged_count | INTEGER | Documents appearing on the privilege log |
| issue_type | TEXT | `clean`, `family_mismatch`, `incomplete_log`, `third_party_waiver`, `over_designated`, `miscoded_privilege` |
| third_party | INTEGER | `1` if third party present, else `0` |
| notes | TEXT | Freeform notes |

### qc_findings

| Column | Type | Description |
|--------|------|-------------|
| finding_id | TEXT | Stable QC finding identifier |
| matter_id | TEXT | FK to matters |
| batch_id | TEXT | FK to production_stats |
| issue_type | TEXT | `near_duplicate`, `metadata_gap`, `responsiveness_miscode`, `privilege_miscoding`, `zero_claim_contradiction` |
| doc_count | INTEGER | Documents affected |
| affected_category | TEXT | FK to subpoena_categories |
| source_ref | TEXT | Hub record ID supporting the finding |
| severity | TEXT | `critical`, `high`, `medium`, `low` |
| notes | TEXT | Freeform notes |

### retention_events

| Column | Type | Description |
|--------|------|-------------|
| event_id | TEXT | Stable retention event identifier |
| matter_id | TEXT | FK to matters |
| record_type | TEXT | `box_storage`, `email_archive`, `voice_mail`, `teams_messages`, `lab_results` |
| event_date | TEXT | Date of destruction/loss event (nullable) |
| hold_date | TEXT | Litigation hold date |
| policy_section | TEXT | Records policy section reference (nullable) |
| retention_period_months | INTEGER | Policy retention period (nullable) |
| volume_count | INTEGER | Volume lost/destroyed |
| volume_unit | TEXT | `boxes`, `days`, `months`, `mailboxes`, `records` |
| status | TEXT | `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `active_system_loss`, `should_exist_missing` |
| affected_categories | TEXT | JSON array of affected category codes |
| source_ref | TEXT | Records schedule or source reference |
| notes | TEXT | Freeform notes |

### remediation_actions

| Column | Type | Description |
|--------|------|-------------|
| action_id | TEXT | Stable action identifier |
| matter_id | TEXT | FK to matters |
| action_type | TEXT | `supplemental_collection`, `privilege_rework`, `qc_remediation`, `disclosure_required`, `forensic_recovery` |
| priority | TEXT | `P0`, `P1`, `P2`, `P3` |
| severity | TEXT | `critical`, `high`, `medium`, `low` |
| owner | TEXT | Responsible team |
| target_ref | TEXT | Hub record ID targeted |
| due_days | INTEGER | Days to complete |
| description | TEXT | Action description |

## Cross-Table Joins

- `matters.matter_id` joins to all tables
- `subpoena_categories.(matter_id, category_code)` joins to `production_stats`, `review_documents`, `privilege_entries`, `qc_findings`
- `custodian_sources.source_id` may match `remediation_actions.target_ref`
- `qc_findings.finding_id` cross-references with `review_documents.doc_id` via `source_ref`
- `privilege_entries.entry_id` cross-reference for log gap analysis
- `retention_events.event_id` cross-reference with `custodian_sources` for status reconciliation

## Key Business Rules

- **Privilege log gap**: privilege_entries where `withheld_count > logged_count`
- **Responsiveness miscode**: qc_findings with `issue_type = responsiveness_miscode` or `zero_claim_contradiction` pointing to documents coded nonresponsive that should be responsive
- **Zero-claim contradiction**: production_stats with non-empty `zero_claim_reason` where qc_findings indicate responsive documents exist
- **Source collection gap**: custodian_sources where `status = not_collected` for categories with production obligations
- **Preservation failure**: custodian_sources where `status = lost` or retention_events where `status = post_hold_loss`
- **Policy-compliant pre-hold destruction**: retention_events where `status = policy_destroyed_pre_hold` and `event_date < hold_date`
- **Missing required record**: retention_events where `status = should_exist_missing`
- **Third-party waiver**: privilege_entries where `third_party = 1` and `issue_type = third_party_waiver`
- **Over-designation**: privilege_entries where `issue_type = over_designated` (business-only cc on counsel copy)

## SQL Query Endpoint

```
POST /api/query
Headers: X-API-Key: review-key-017, Content-Type: application/json
Body: {"sql": "SELECT ..."}
Response: {"rows": [...], "count": N}
```

Available tables for SQL: `matters`, `subpoena_categories`, `production_stats`, `custodian_sources`, `review_documents`, `privilege_entries`, `qc_findings`, `retention_events`, `remediation_actions`.
