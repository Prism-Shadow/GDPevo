# Investigation Review Hub — Schema Reference

Full table schemas as returned by `GET /api/schema`. Use to verify column names when crafting SQL queries or interpreting REST responses.

## matters

| Column | Type | Description |
|---|---|---|
| matter_id | TEXT | Primary identifier (e.g., `MTR-SENTINEL-GJ`) |
| name | TEXT | Display name |
| agency | TEXT | Investigating agency |
| investigation_type | TEXT | Type (e.g., `grand_jury_subpoena`, `sec_subpoena`) |
| issued_date | TEXT | Date subpoena issued (YYYY-MM-DD) |
| hold_date | TEXT | Legal hold effective date |
| lead_partner | TEXT | Lead attorney |
| description | TEXT | Matter summary |
| status | TEXT | `active_review` or `closed_monitoring` |

## subpoena_categories

| Column | Type | Description |
|---|---|---|
| matter_id | TEXT | Foreign key to matters |
| category_code | TEXT | Code (e.g., `R01`, `SEC-1`, `A`) |
| title | TEXT | Human-readable title |
| date_start | TEXT | Start of request date range |
| date_end | TEXT | End of request date range |
| request_text | TEXT | Full request language |
| topic_tags | TEXT | Comma-separated tags |

## production_stats

| Column | Type | Description |
|---|---|---|
| matter_id | TEXT | Foreign key |
| batch_id | TEXT | Batch identifier |
| batch_date | TEXT | Batch date |
| category_code | TEXT | Category code |
| produced_count | INTEGER | Documents produced |
| withheld_count | INTEGER | Documents withheld |
| responsive_count | INTEGER | Documents deemed responsive |
| nonresponsive_count | INTEGER | Documents deemed non-responsive |
| status | TEXT | `produced`, `closed`, `supplement_pending`, `rolling_review`, `zero_claim_contradicted` |
| zero_claim_reason | TEXT | Reason for zero-production claim |
| notes | TEXT | Batch notes |

## custodian_sources

| Column | Type | Description |
|---|---|---|
| source_id | TEXT | Primary key (e.g., `SRC-SENT-ALDEN-PHONE`) |
| matter_id | TEXT | Foreign key |
| custodian_name | TEXT | Custodian or source owner |
| role | TEXT | Custodian's business role |
| source_type | TEXT | `mailbox`, `personal_phone`, `teams_export`, `sharepoint_site`, `network_share`, `mobile_backup`, `contract_repository`, `personal_email`, `personal_messaging`, `laptop`, `teams_archive`, `email_archive` |
| source_label | TEXT | Human-readable label |
| status | TEXT | `collected`, `not_collected`, `partial_collection`, `lost`, `available`, `in_review` |
| event_date | TEXT | Date of relevant event |
| post_hold | INTEGER | 1 if event occurred after legal hold, 0 otherwise |
| category_impacts | TEXT/ARRAY | Category codes affected (comma-separated in SQL, array in REST) |
| issue_tags | TEXT/ARRAY | Tags indicating issue type |
| notes | TEXT | Free-text notes |

## review_documents

| Column | Type | Description |
|---|---|---|
| doc_id | TEXT | Primary key |
| matter_id | TEXT | Foreign key |
| title | TEXT | Document title |
| doc_date | TEXT | Document date |
| custodian_name | TEXT | Custodian |
| source_system | TEXT | Origin system |
| category_code | TEXT | Associated category |
| responsiveness | TEXT | `responsive`, `nonresponsive`, `needs_review` |
| privilege_status | TEXT | `privileged`, `nonprivileged`, `unknown` |
| produced_status | TEXT | `produced`, `not_produced`, `withheld` |
| issue_tags | TEXT/ARRAY | Issue tags |
| summary | TEXT | Document summary |

## privilege_entries

| Column | Type | Description |
|---|---|---|
| entry_id | TEXT | Primary key (e.g., `PRIV-SENT-LOG-GAP`) |
| matter_id | TEXT | Foreign key |
| category_code | TEXT | Category code |
| custodian_name | TEXT | Custodian |
| doc_count | INTEGER | Total documents in entry |
| withheld_count | INTEGER | Documents withheld |
| logged_count | INTEGER | Documents on privilege log |
| issue_type | TEXT | `clean`, `family_mismatch`, `incomplete_log`, `over_designated`, `third_party_waiver` |
| third_party | INTEGER | 1 if third-party involved, 0 otherwise |
| notes | TEXT | Free-text notes |

## qc_findings

| Column | Type | Description |
|---|---|---|
| finding_id | TEXT | Primary key (e.g., `QC-SENT-R09-NR`) |
| matter_id | TEXT | Foreign key |
| batch_id | TEXT | Associated batch |
| issue_type | TEXT | `miscoded_nonresponsive`, `miscoded_privilege`, `zero_claim_contradiction`, `family_break`, `metadata_gap`, `near_duplicate`, `duplicate_overlay`, `date_normalization` |
| doc_count | INTEGER | Documents affected |
| affected_category | TEXT | Category code |
| source_ref | TEXT | Referenced document or source |
| severity | TEXT | `low`, `medium`, `high` |
| notes | TEXT | Free-text notes |

## retention_events

| Column | Type | Description |
|---|---|---|
| event_id | TEXT | Primary key (e.g., `RET-HARB-EHS-POST`) |
| matter_id | TEXT | Foreign key |
| record_type | TEXT | Type of record (e.g., `email_archive`, `chat_export`, `voice_mail`, `box_storage`, `audit_report`, `lab_test_data`, `teams_messages`, `shared_drive`, `voicemail`, `ehs_correspondence`, `calverley_audit`, `offsite_bid_files`) |
| event_date | TEXT | Date of the retention event |
| hold_date | TEXT | Date of the legal hold |
| policy_section | TEXT | Policy reference or null |
| retention_period_months | INTEGER | Retention period in months or null |
| volume_count | INTEGER | Volume of records affected |
| volume_unit | TEXT | Unit: `boxes`, `days`, `months`, `records`, `reports`, `exports`, `mailboxes`, `files`, `reports`, `system_window` |
| status | TEXT | `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `system_loss`, `should_exist_missing`, `available_archive`, `preserved_available`, `retained`, `available`, `post_hold_partial_recovery` |
| affected_categories | TEXT/ARRAY | Category codes (comma-separated in SQL, array in REST) |
| source_ref | TEXT | Referenced source |
| notes | TEXT | Free-text notes |

## remediation_actions

| Column | Type | Description |
|---|---|---|
| action_id | TEXT | Primary key (e.g., `ACT-SENTINELGJ-001`) |
| matter_id | TEXT | Foreign key |
| action_type | TEXT | Action type label from the hub |
| priority | TEXT | `P1`, `P2`, `P3` |
| severity | TEXT | `low`, `medium`, `high` |
| owner | TEXT | Owner team name (hub's label) |
| target_ref | TEXT | Target record ID |
| due_days | INTEGER | Days until due |
| description | TEXT | Action description |
