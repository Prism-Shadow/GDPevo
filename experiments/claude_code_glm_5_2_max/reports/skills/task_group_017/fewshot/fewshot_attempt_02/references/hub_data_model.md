# Hub Data Model

Grounded in `GET /api/schema` of the Investigation Review Hub. The hub exposes 9 tables,
one per evidence endpoint. All evidence in an answer must trace back to records in these
tables for the target `matter_id`. This is structural, generic information — it contains no
matter-specific answer values.

## matters → `GET /api/matters`
| column | type |
|---|---|
| matter_id | TEXT |
| name | TEXT |
| agency | TEXT |
| investigation_type | TEXT |
| issued_date | TEXT |
| hold_date | TEXT |
| lead_partner | TEXT |
| description | TEXT |
| status | TEXT |

Use: confirm the matter, its `hold_date` (the preservation pivot for retention
classification), agency, and investigation type.

## subpoena_categories → `GET /api/subpoena-categories`
| column | type |
|---|---|
| matter_id | TEXT |
| category_code | TEXT |
| title | TEXT |
| date_start | TEXT |
| date_end | TEXT |
| request_text | TEXT |
| topic_tags | TEXT |

Use: the universe of legal category codes for the matter. Every `category_impacts` /
`affected_categories` value must be one of these codes. `topic_tags` is a delimited string.

## production_stats → `GET /api/productions`
| column | type |
|---|---|
| matter_id | TEXT |
| batch_id | TEXT |
| batch_date | TEXT |
| category_code | TEXT |
| produced_count | INTEGER |
| withheld_count | INTEGER |
| responsive_count | INTEGER |
| nonresponsive_count | INTEGER |
| status | TEXT |
| zero_claim_reason | TEXT |
| notes | TEXT |

Use: per-batch, per-category production rollup. A non-null `zero_claim_reason` that
contradicts a `produced_count`/`responsive_count` of zero signals a responsiveness defect
(zero-claim contradiction). `withheld_count` here feeds privilege metrics.

## custodian_sources → `GET /api/custodian-sources`
| column | type |
|---|---|
| source_id | TEXT |
| matter_id | TEXT |
| custodian_name | TEXT |
| role | TEXT |
| source_type | TEXT |
| source_label | TEXT |
| status | TEXT |
| event_date | TEXT |
| post_hold | INTEGER |
| category_impacts | TEXT |
| issue_tags | TEXT |
| notes | TEXT |

Use: custodian source inventory. `status` (lost / not_collected / partial / collected /
destroyed / available) and `post_hold` flag drive preservation-failure and collection-gap
findings. `source_type` (personal_phone, personal_messaging, laptop, email, cloud_mail,
teams_archive, offsite_records, etc.) drives personal-source-gap findings. `category_impacts`
and `issue_tags` are delimited strings.

## review_documents → `GET /api/documents/search`
| column | type |
|---|---|
| doc_id | TEXT |
| matter_id | TEXT |
| title | TEXT |
| doc_date | TEXT |
| custodian_name | TEXT |
| source_system | TEXT |
| category_code | TEXT |
| responsiveness | TEXT |
| privilege_status | TEXT |
| produced_status | TEXT |
| issue_tags | TEXT |
| summary | TEXT |

Use: document-level review coding. `responsiveness` (responsive/nonresponsive) mismatches
and `produced_status` anomalies anchor responsiveness-miscode and zero-claim findings.
`privilege_status` anomalies anchor privilege miscoding.

## privilege_entries → `GET /api/privilege-log`
| column | type |
|---|---|
| entry_id | TEXT |
| matter_id | TEXT |
| category_code | TEXT |
| custodian_name | TEXT |
| doc_count | INTEGER |
| withheld_count | INTEGER |
| logged_count | INTEGER |
| issue_type | TEXT |
| third_party | INTEGER |
| notes | TEXT |

Use: privilege log. `withheld_count` − `logged_count` = unlogged (log gap) when positive.
`issue_type` distinguishes log gap, waiver, miscoding, over-designation. `third_party = 1`
flags third-party-waiver exposure. This table is the primary source for privilege metrics.

## qc_findings → `GET /api/qc-findings`
| column | type |
|---|---|
| finding_id | TEXT |
| matter_id | TEXT |
| batch_id | TEXT |
| issue_type | TEXT |
| doc_count | INTEGER |
| affected_category | TEXT |
| source_ref | TEXT |
| severity | TEXT |
| notes | TEXT |

Use: QC issues. `issue_type` (responsiveness miscode, privilege miscode, etc.) and
`severity` anchor QC-anchored findings. `source_ref` links the QC finding back to the
document/source it concerns — include it in `source_refs`.

## retention_events → `GET /api/retention-events`
| column | type |
|---|---|
| event_id | TEXT |
| matter_id | TEXT |
| record_type | TEXT |
| event_date | TEXT |
| hold_date | TEXT |
| policy_section | TEXT |
| retention_period_months | INTEGER |
| volume_count | INTEGER |
| volume_unit | TEXT |
| status | TEXT |
| affected_categories | TEXT |
| source_ref | TEXT |
| notes | TEXT |

Use: retention/preservation events. Classify by `status` and by comparing `event_date` to
`hold_date`: a loss before `hold_date` governed by a `policy_section` is a policy-compliant
pre-hold loss (low risk, no remediation beyond documentation); a loss at/after `hold_date`
is a post-hold preservation risk (high/critical, disclose). `volume_count`/`volume_unit`
(box/day/month/record counts) feed volume metrics. `affected_categories` is a delimited
string. `source_ref` may point to an available archive that limits the loss.

## remediation_actions → `GET /api/remediation-actions`
| column | type |
|---|---|
| action_id | TEXT |
| matter_id | TEXT |
| action_type | TEXT |
| priority | TEXT |
| severity | TEXT |
| owner | TEXT |
| target_ref | TEXT |
| due_days | INTEGER |
| description | TEXT |

Use: candidate remediation actions. `target_ref` points at the hub record the action
remediates; map `action_type`, `priority`, `owner`, and `due_days` onto the contract's enums
when assembling the action plan.

## SQL endpoint
`POST /api/query` with the `X-API-Key` header value taken from `environment_access.md`.
Read-only. Use for counts and joins across the tables above (e.g. total withheld minus
logged for a matter, distinct affected categories, source counts by status). Always send
the header. Prefer REST for per-record detail; use SQL for rollups and metric derivation.
