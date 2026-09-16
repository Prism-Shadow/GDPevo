# Investigation Review Hub API Schema

Complete column listing for every table in the shared hub. All tables
share `matter_id` as the matter-scoping key. Use the `POST /api/query`
endpoint with `X-API-Key: review-key-017` for SQL access.

## matters

| Column           | Type   | Notes                                    |
|------------------|--------|------------------------------------------|
| matter_id        | TEXT   | Primary stable identifier                |
| name             | TEXT   | Display name                             |
| agency           | TEXT   | Issuing agency (e.g. "SEC Enforcement")  |
| investigation_type | TEXT | "grand_jury_subpoena" or "sec_subpoena"  |
| issued_date      | TEXT   | YYYY-MM-DD                               |
| hold_date        | TEXT   | Litigation hold start date, YYYY-MM-DD   |
| lead_partner     | TEXT   | Lead attorney name                       |
| description      | TEXT   | Short matter description                 |
| status           | TEXT   | "active_review" or "closed_monitoring"   |

## subpoena_categories

| Column        | Type   | Notes                                      |
|---------------|--------|--------------------------------------------|
| matter_id     | TEXT   |                                            |
| category_code | TEXT   | Uppercase (e.g. R01, SEC-1, A)             |
| title         | TEXT   | Category label                             |
| date_start    | TEXT   | Request date range start, YYYY-MM-DD       |
| date_end      | TEXT   | Request date range end, YYYY-MM-DD         |
| request_text  | TEXT   | Full request description                   |
| topic_tags    | TEXT   | JSON array of string tags                  |

## custodian_sources

| Column            | Type    | Notes                                                |
|-------------------|---------|------------------------------------------------------|
| source_id         | TEXT    | Stable source identifier                             |
| matter_id         | TEXT    |                                                      |
| custodian_name    | TEXT    |                                                      |
| role              | TEXT    | Custodian role                                       |
| source_type       | TEXT    | e.g. personal_phone, mailbox, teams_export, sharepoint_site, network_share |
| source_label      | TEXT    | Human-readable label                                 |
| status            | TEXT    | collected, not_collected, lost, available, in_review, partial_collection |
| event_date        | TEXT    | YYYY-MM-DD, or null                                  |
| post_hold         | INTEGER | 1 if event is after hold date, 0 otherwise           |
| category_impacts  | TEXT    | Comma-separated category codes, e.g. "R07,R08,R09"   |
| issue_tags        | TEXT    | Comma-separated tags, e.g. "collection_gap,board_materials" |
| notes             | TEXT    |                                                      |

## production_stats

| Column            | Type    | Notes                                             |
|-------------------|---------|---------------------------------------------------|
| matter_id         | TEXT    |                                                   |
| batch_id          | TEXT    | e.g. BATCH-SENTINELGJ-001                         |
| batch_date        | TEXT    | YYYY-MM-DD                                        |
| category_code     | TEXT    |                                                   |
| produced_count    | INTEGER |                                                   |
| withheld_count    | INTEGER |                                                   |
| responsive_count  | INTEGER |                                                   |
| nonresponsive_count | INTEGER |                                                 |
| status            | TEXT    | produced, rolling_review, supplement_pending, closed |
| zero_claim_reason | TEXT    | Non-empty when production claims zero responsive  |
| notes             | TEXT    |                                                   |

## review_documents

| Column          | Type   | Notes                                               |
|-----------------|--------|-----------------------------------------------------|
| doc_id          | TEXT   | Stable document identifier                          |
| matter_id       | TEXT   |                                                     |
| title           | TEXT   |                                                     |
| doc_date        | TEXT   | YYYY-MM-DD                                          |
| custodian_name  | TEXT   |                                                     |
| source_system   | TEXT   |                                                     |
| category_code   | TEXT   |                                                     |
| responsiveness  | TEXT   | responsive, nonresponsive, or null                  |
| privilege_status| TEXT   | privileged, nonprivileged, or null                  |
| produced_status | TEXT   | produced, not_produced, withheld, or null           |
| issue_tags      | TEXT   | Comma-separated tags                                |
| summary         | TEXT   | Short document description                          |

## privilege_entries

| Column         | Type    | Notes                                                |
|----------------|---------|------------------------------------------------------|
| entry_id       | TEXT    | Stable privilege entry ID                            |
| matter_id      | TEXT    |                                                      |
| category_code  | TEXT    |                                                      |
| custodian_name | TEXT    |                                                      |
| doc_count      | INTEGER | Total documents in the entry                         |
| withheld_count | INTEGER | Documents withheld as privileged                     |
| logged_count   | INTEGER | Documents actually logged on the privilege log       |
| issue_type     | TEXT    | clean, incomplete_log, over_designated, family_mismatch, waived |
| third_party    | INTEGER | 1 if a third party is involved, 0 otherwise          |
| notes          | TEXT    |                                                      |

## qc_findings

| Column           | Type    | Notes                                              |
|------------------|---------|----------------------------------------------------|
| finding_id       | TEXT    | Stable QC finding ID                               |
| matter_id        | TEXT    |                                                    |
| batch_id         | TEXT    |                                                    |
| issue_type       | TEXT    | miscoded_nonresponsive, duplicate_overlay, family_break, metadata_gap, near_duplicate |
| doc_count        | INTEGER |                                                    |
| affected_category| TEXT    | Single category code                               |
| source_ref       | TEXT    | Document ID or other hub record ID                 |
| severity         | TEXT    | low, medium, high, critical                        |
| notes            | TEXT    |                                                    |

## retention_events

| Column                 | Type    | Notes                                            |
|------------------------|---------|--------------------------------------------------|
| event_id               | TEXT    | Stable retention event ID                        |
| matter_id              | TEXT    |                                                  |
| record_type            | TEXT    | e.g. email_archive, box_storage, voice_mail, audit_report |
| event_date             | TEXT    | YYYY-MM-DD of the retention action, or null      |
| hold_date              | TEXT    | Matter hold date, YYYY-MM-DD                     |
| policy_section         | TEXT    | Records schedule reference, or null              |
| retention_period_months| INTEGER | Policy retention period, or null                 |
| volume_count           | INTEGER | Count of affected units, or null                 |
| volume_unit            | TEXT    | boxes, files, mailboxes, exports, reports, days  |
| status                 | TEXT    | policy_destroyed_pre_hold, post_hold_loss, auto_purged, active_system_loss, retained, system_loss, should_exist_missing |
| affected_categories    | TEXT    | Comma-separated category codes                   |
| source_ref             | TEXT    | Records schedule or source reference, or null    |
| notes                  | TEXT    |                                                  |

## remediation_actions

| Column      | Type    | Notes                                             |
|-------------|---------|---------------------------------------------------|
| action_id   | TEXT    | Stable action ID                                  |
| matter_id   | TEXT    |                                                   |
| action_type | TEXT    | remediation action type label                     |
| priority    | TEXT    | P0, P1, P2, or P3                                 |
| severity    | TEXT    | low, medium, high, critical                       |
| owner       | TEXT    | Responsible party label                           |
| target_ref  | TEXT    | Hub record ID the action targets                  |
| due_days    | INTEGER | Days from dashboard delivery                      |
| description | TEXT    |                                                   |
