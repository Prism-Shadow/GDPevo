# Hub Data Model

Every GET endpoint returns `{"count": N, "rows": [...]}`. Filter rows by `matter_id` on the client. The SQL endpoint accepts `POST /api/query` with header `X-API-Key: review-key-017` and body `{"sql": "..."}`.

## Tables and columns

### matters
| Column | Type | Notes |
|--------|------|-------|
| matter_id | TEXT | Primary key, e.g. `MTR-CLIENT-AGENCY` |
| name | TEXT | Human-readable matter name |
| agency | TEXT | e.g. `DOJ Antitrust Division`, `SEC Enforcement` |
| investigation_type | TEXT | `grand_jury_subpoena` or `sec_subpoena` |
| issued_date | TEXT | YYYY-MM-DD |
| hold_date | TEXT | YYYY-MM-DD, litigation hold start |
| lead_partner | TEXT | |
| description | TEXT | |
| status | TEXT | `active_review` or `closed_monitoring` |

### subpoena_categories
| Column | Type | Notes |
|--------|------|-------|
| matter_id | TEXT | Filter by this |
| category_code | TEXT | e.g. `R09`, `SEC-1`, `A`, `CR-06` |
| title | TEXT | Human-readable title |
| date_start | TEXT | YYYY-MM-DD |
| date_end | TEXT | YYYY-MM-DD |
| request_text | TEXT | Subpoena request language |
| topic_tags | JSON array of strings | e.g. `["dealer","safety"]` |

### production_stats (GET /api/productions)
| Column | Type | Notes |
|--------|------|-------|
| matter_id | TEXT | Filter by this |
| batch_id | TEXT | Production batch identifier |
| batch_date | TEXT | YYYY-MM-DD |
| category_code | TEXT | Links to subpoena_categories.category_code |
| produced_count | INTEGER | |
| withheld_count | INTEGER | |
| responsive_count | INTEGER | |
| nonresponsive_count | INTEGER | |
| status | TEXT | `produced`, `rolling_review`, `supplement_pending`, `closed`, `zero_claim_contradicted` |
| zero_claim_reason | TEXT | Reason given for zero-production claim |
| notes | TEXT | |

### custodian_sources (GET /api/custodian-sources)
| Column | Type | Notes |
|--------|------|-------|
| source_id | TEXT | Primary key, e.g. `SRC-CLIENT-CUSTODIAN-TYPE` |
| matter_id | TEXT | Filter by this |
| custodian_name | TEXT | |
| role | TEXT | |
| source_type | TEXT | `mailbox`, `personal_messaging`, `teams_archive`, `laptop`, `personal_email`, `mobile_backup`, `network_share`, `contract_repository`, `teams_export` |
| source_label | TEXT | |
| status | TEXT | `collected`, `not_collected`, `partial_collection`, `available`, `lost`, `in_review` |
| event_date | TEXT | YYYY-MM-DD |
| post_hold | INTEGER | 1 if event occurred after hold date, 0 otherwise |
| category_impacts | JSON array of strings | Category codes this source affects |
| issue_tags | JSON array of strings | `collection_gap`, `personal_messaging`, `post_hold_wipe`, `deleted_channel`, `archive_available`, `routine`, `metadata_gap`, `scope_exception`, `sms`, `signal`, `personal_email` |
| notes | TEXT | |

### review_documents (GET /api/documents/search)
| Column | Type | Notes |
|--------|------|-------|
| doc_id | TEXT | Primary key |
| matter_id | TEXT | Filter by this |
| title | TEXT | |
| doc_date | TEXT | YYYY-MM-DD |
| custodian_name | TEXT | |
| source_system | TEXT | |
| category_code | TEXT | Links to subpoena_categories.category_code |
| responsiveness | TEXT | `responsive`, `nonresponsive` |
| privilege_status | TEXT | `privileged`, `nonprivileged`, `not_applicable` |
| produced_status | TEXT | `produced`, `not_produced`, `withheld`, `not_applicable` |
| issue_tags | TEXT | |
| summary | TEXT | |

### privilege_entries (GET /api/privilege-log)
| Column | Type | Notes |
|--------|------|-------|
| entry_id | TEXT | Primary key |
| matter_id | TEXT | Filter by this |
| category_code | TEXT | Links to subpoena_categories.category_code |
| custodian_name | TEXT | |
| doc_count | INTEGER | Total documents in entry |
| withheld_count | INTEGER | Documents withheld as privileged |
| logged_count | INTEGER | Documents actually logged on privilege log |
| issue_type | TEXT | e.g. `log_gap`, `third_party`, `overdesignation` |
| third_party | INTEGER | 1 if third-party involvement, 0 otherwise |
| notes | TEXT | |

### qc_findings (GET /api/qc-findings)
| Column | Type | Notes |
|--------|------|-------|
| finding_id | TEXT | Primary key |
| matter_id | TEXT | Filter by this |
| batch_id | TEXT | |
| issue_type | TEXT | e.g. `zero_claim_contradiction`, `privilege_miscoding`, `responsiveness_miscode` |
| doc_count | INTEGER | |
| affected_category | TEXT | Single category code (not an array) |
| source_ref | TEXT | References another record ID |
| severity | TEXT | `critical`, `high`, `medium`, `low` |
| notes | TEXT | |

### retention_events (GET /api/retention-events)
| Column | Type | Notes |
|--------|------|-------|
| event_id | TEXT | Primary key |
| matter_id | TEXT | Filter by this |
| record_type | TEXT | e.g. `EHS correspondence`, `Teams messages` |
| event_date | TEXT | YYYY-MM-DD or null |
| hold_date | TEXT | YYYY-MM-DD |
| policy_section | TEXT | or null |
| retention_period_months | INTEGER | or null |
| volume_count | INTEGER | or null |
| volume_unit | TEXT | `boxes`, `days`, `months`, `records`, `not_applicable` |
| status | TEXT | `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `active_system_loss`, `should_exist_missing`, `available_archive`, `preserved_available`, `collection_pending` |
| affected_categories | JSON array of strings | Category codes |
| source_ref | TEXT | References a custodian_source.source_id or archive |
| notes | TEXT | |

### remediation_actions (GET /api/remediation-actions)
| Column | Type | Notes |
|--------|------|-------|
| action_id | TEXT | Primary key |
| matter_id | TEXT | Filter by this |
| action_type | TEXT | |
| priority | TEXT | `P0`, `P1`, `P2`, `P3` |
| severity | TEXT | `critical`, `high`, `medium`, `low` |
| owner | TEXT | |
| target_ref | TEXT | References another record ID |
| due_days | INTEGER | |
| description | TEXT | |

## Cross-reference map

| From | Field | To |
|------|-------|----|
| production_stats | category_code | subpoena_categories.category_code |
| custodian_sources | category_impacts | subpoena_categories.category_code |
| review_documents | category_code | subpoena_categories.category_code |
| privilege_entries | category_code | subpoena_categories.category_code |
| qc_findings | affected_category | subpoena_categories.category_code |
| qc_findings | source_ref | review_documents.doc_id or custodian_sources.source_id |
| retention_events | affected_categories | subpoena_categories.category_code |
| retention_events | source_ref | custodian_sources.source_id |
| remediation_actions | target_ref | any record ID from another table |

Note: `category_code` formats vary by matter -- some use plain letters (`A`, `B`), some numeric (`R01`, `R09`), some prefixed (`SEC-1`, `CR-06`, `IP-B`). Always use the codes exactly as they appear in the hub records for the specific matter.
