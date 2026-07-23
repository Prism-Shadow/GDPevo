# Hub → Answer Enum Mappings

Templates differ in their exact enum strings — **always read the task's
`answer_template.json` `enums` block** and use those literal strings. The mappings below
are the consistent hub→enum translations observed across matters. When a template's enum
lacks a value shown here, pick the closest enum member present.

## Retention status
| Hub `status` | Answer `retention_status` / `source_status` |
|---|---|
| `policy_destroyed_pre_hold` | `policy_destroyed_pre_hold` |
| `post_hold_loss` | `post_hold_loss` |
| `post_hold_partial_recovery` | `post_hold_loss` |
| `system_loss` | `active_system_loss` (comm) / `destroyed` (source) |
| `auto_purged` | `auto_purged` |
| `should_exist_missing` | `should_exist_missing` |
| `retained` | `preserved_available` |
| `available` | `available_archive` |

## Privilege issue → issue_type / correction_type / privilege_status
| Hub `issue_type` | issue_type | correction_type | privilege_status |
|---|---|---|---|
| `incomplete_log` | `privilege_log_gap` | `supplement_log` | `incomplete_log` |
| `over_designated` | `privilege_miscoding` | `downgrade` | `over_designated` |
| `third_party_waiver` | `third_party_waiver` | `waiver_assessment` | `waived` |
| `miscoded_privilege` (qc) | `privilege_miscoding` | `privilege_recode` | `incomplete_log` |
| `family_mismatch` / `clean` | (noise — exclude) | — | — |

## QC issue → issue_type
| Hub qc `issue_type` | Answer `issue_type` |
|---|---|
| `miscoded_nonresponsive` | `responsiveness_miscode` / `responsive_miscoding` |
| `zero_claim_contradiction` | `responsiveness_miscode` (or `zero_claim_contradiction` if in enum) |
| `miscoded_privilege` | `privilege_miscoding` |
| `family_break`, `near_duplicate`, `metadata_gap`, `duplicate_overlay`, `date_normalization` | (noise — exclude) |

## Source status
| Hub `status` | Answer `source_status` |
|---|---|
| `lost` | `lost` / `destroyed` |
| `not_collected` | `not_collected` |
| `partial_collection` | `partial` / `partial_collection` |
| `available` | `available_archive` |
| `collected` / `in_review` | (usually noise unless signal) |

## Production impact (derive from source/doc state)
| Situation | `production_impact` |
|---|---|
| Source lost / wiped / destroyed post-hold | `source_lost` |
| Source not collected | `source_missing` |
| Source available (archive) | `source_available` |
| Privileged doc withheld but not logged | `withheld_unlogged` |
| Privilege waiver / third-party disclosure | `privilege_exposure` |
| Miscoded doc (needs recode) | `recode_needed` |
| Responsive doc not produced / zero-claim | `not_produced` / `underproduced` |
| No gap | `no_production_impact` |

## Risk level (preservation risk — NOT remediation severity)
| Hub retention status / situation | `risk_level` |
|---|---|
| `policy_destroyed_pre_hold` | `low` (policy-compliant) |
| `post_hold_loss` | `high` (or `critical` for large/irreparable losses) |
| `should_exist_missing` | `medium` |
| `system_loss` / `auto_purged` | `medium` |
| `archive_available` | `medium` |
| Over-designation / miscoding | `medium` (or `high` if severity high) |

## Owner (hub → enum; pick the member present in THIS template's `owner` enum)
| Hub owner | Likely enum member |
|---|---|
| `Forensics` | `forensics` (direct) — else `ediscovery_vendor` — else `client_it` |
| `Review Operations` | `review_qc` / `review_operations` / `review_vendor` |
| `Privilege Team` | `privilege_team` |
| `Legal Hold Team` | `client_legal` / `privilege_counsel` |
| `Vendor Team` | `ediscovery_vendor` |
| `Records Management` | `records_vendor` |
| `Compliance Audit` | `compliance_audit` |
| `Matter Associate` | (noise owner — exclude the action) |

## Action type (hub `action_type` → answer `action_type` enum)
| Hub action_type | Target state | Answer action_type |
|---|---|---|
| `supplemental_collection` | lost/destroyed source | `forensic_recovery` / `disclose_preservation_issue` |
| `supplemental_collection` | not-collected personal source | `collect_personal_device` / `collect_source` |
| `supplemental_collection` | archive | `collect_archive` / `search_archive` |
| `privilege_rework` | incomplete log | `supplement_privilege_log` |
| `privilege_rework` | over-designation | `privilege_recode_and_log` / `recode_and_produce` |
| `privilege_rework` | third-party waiver | `waiver_assessment_and_disclosure` |
| `qc_remediation` | miscoded privilege/responsiveness | `qc_remediation` (if present) / `recode_and_produce` / `quality_control_review` |
| `retention_exception_review` | post-hold loss | `disclose_preservation_issue` |
| `retention_exception_review` | should-exist-missing | `locate_missing_record` |
| `retention_exception_review` | system loss | `restore_from_backup` / `document_system_gap` |
| `retention_exception_review` | policy-destroyed-pre-hold | `no_action_policy_loss` |
| `custodian_followup` / `load_file_cleanup` / `sampling_review` | (noise — exclude) | — |

## Priority / severity
- `priority`: copy hub `priority` verbatim (`P0`/`P1`/`P2`/`P3`).
- `priority_rank` / `rank`: integer, 1 = highest. Order: P0 < P1 < P2 < P3; within a tier
  follow ascending hub `action_id`.
- `severity`: copy hub `severity` when the field asks for severity (distinct from risk_level).

## Dates
- `cutoff_date` = matter `hold_date` (YYYY-MM-DD). Do not null it when a hold_date exists.
- `event_date`, `hold_date`: copy verbatim from the hub.
