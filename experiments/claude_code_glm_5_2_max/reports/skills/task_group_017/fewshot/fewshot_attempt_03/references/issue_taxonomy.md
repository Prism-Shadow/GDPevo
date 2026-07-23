# Issue Taxonomy & Field Mapping

How to detect material issues from hub data and map each one to the template's fields. This
is generic — the per-task `answer_template.json` decides the exact field names and enum
values, so adapt the labels to that template's enums.

## Domains and how to find them

### 1. Preservation / retention loss
- **Source lost / destroyed:** `custodian_sources` with `status` indicating lost or
  destroyed, or `retention_events` with a loss status. Distinguish:
  - **Pre-hold policy destruction** — destroyed before the hold date per a documented
    retention policy (`policy_section` set, event before `hold_date`). Low risk; action is
    typically `no_action_policy_loss` / `no_action` / `monitor_only`, owner
    `records_management`.
  - **Post-hold loss** — lost on or after the hold date (`post_hold = 1` or event_date ≥
    hold_date). Critical/high; action `disclose_preservation_issue` /
    `disclose_to_government`, owner `outside_counsel`.
- **Should-exist / missing required record** — a record that should exist for a category
  but is absent (`should_exist_missing`). Action `locate_missing_record`, owner
    `compliance_audit`.
- `production_impact` → `source_lost` (lost) or `missing_record` (should-exist).

### 2. Collection gaps
- `custodian_sources` with `status = not_collected` (personal phone, personal email,
  personal messaging, board shared drive, etc.). `production_impact = source_missing`.
- Action `collect_source` / `collect_personal_device` / `collect_personal_email` /
  `collect_signal_messages`, owner `client_it` / `forensics` / `ediscovery_vendor`.

### 3. Privilege log gaps
- `privilege_entries` where `withheld_count - logged_count > 0` → documents withheld but
  not logged.
- `document_count = withheld_count`; `logged_count` as recorded; `unlogged_count =
  withheld_count - logged_count`.
- `production_impact = withheld_unlogged`. Action `supplement_privilege_log`, owner
  `privilege_team`.

### 4. Privilege waiver / third-party exposure
- `privilege_entries` with `third_party = 1` (third-party recipient defeats or risks
  privilege). `production_impact = privilege_exposure`.
- Set `third_party` to the recipient description where the field exists; else `null`.
- Action `waiver_assessment_and_disclosure`, owner `privilege_counsel`.
- These are typically fully logged (`logged_count = withheld_count`, `unlogged = 0`) but
  still a waiver risk.

### 5. Privilege miscoding / over-designation
- `qc_findings` (and `privilege_entries`) showing privileged docs coded nonprivileged, or
  non-privileged docs over-designated as privileged (e.g. "business-only counsel copy").
- `production_impact = privilege_exposure` or `recode_needed`.
- Action `privilege_recode_and_log` / `qc_remediation` / `privilege_recode`, owner
  `review_qc` / `privilege_team`.

### 6. Responsiveness miscoding / zero-production claims
- `review_documents` miscoded (responsive doc marked nonresponsive, or vice versa) and/or
  `qc_findings` with a responsiveness issue type, and/or `production_stats.zero_claim_reason`
  on a category that actually has responsive documents.
- `production_impact = not_produced` / `underproduced` / `recode_needed`.
- Action `recode_and_produce`, owner `review_qc` / `review_vendor` / `review_operations`.

### 7. Communication / system gaps
- `retention_events` with `active_system_loss` (e.g. Teams channel data deleted) or
  `auto_purged` (e.g. voicemail auto-delete). Record `cutoff_date` / `purge_window_days`.
- Action `document_system_gap`, owner `it_messaging` (or closest enum). Medium risk; often
  partially remediable if an archive exists.

### 8. Available archives / retained sources
- `custodian_sources` / `remediation_actions` flagged as available archive or retained
  source. These **limit irretrievable loss** for their affected categories — record
  `limits_loss_for_categories` / `limits_irretrievable_loss_for_categories`.
- Action `collect_archive` / `search_archive`, owner `ediscovery_vendor`.
- If the task's matter has no available archive, the `retained_or_available_sources` /
  `available_archives` list is `[]` and `available_archive_count = 0`.

## Severity / risk ranking (generic)

critical > high > medium > low. Typical assignment:
- **critical:** post-hold source loss / destruction affecting multiple categories.
- **high:** privilege waiver exposure, privilege log gaps, privilege miscoding, uncollected
  personal sources, responsiveness miscodes that block production.
- **medium:** active-system / auto-purge communication gaps (archive may recover), over-
  designation downgrades.
- **low:** pre-hold policy-compliant destruction.

## Owner / action mapping (choose the closest template enum)

| Situation | action_type (representative) | owner (representative) |
|---|---|---|
| Source lost post-hold / must tell government | `disclose_preservation_issue` / `disclose_to_government` | `outside_counsel` |
| Forensic recovery of lost device | `forensic_recovery` | `ediscovery_vendor` / `forensics` |
| Uncollected source / board drive | `collect_source` | `client_it` |
| Uncollected personal phone/email/messaging | `collect_personal_device` / `collect_personal_email` / `collect_signal_messages` | `forensics` |
| Responsiveness miscode / zero-claim | `recode_and_produce` | `review_qc` / `review_vendor` |
| Withheld-unlogged privilege | `supplement_privilege_log` | `privilege_team` |
| Third-party waiver | `waiver_assessment_and_disclosure` | `privilege_counsel` |
| Privilege miscoding | `privilege_recode_and_log` / `privilege_recode` / `qc_remediation` | `review_qc` |
| Over-designation downgrade | `qc_remediation` / `downgrade` | `privilege_team` |
| Missing required record | `locate_missing_record` | `compliance_audit` |
| Communication/system gap | `document_system_gap` | `it_messaging` |
| Available archive | `collect_archive` / `search_archive` | `ediscovery_vendor` |
| Pre-hold policy loss | `no_action_policy_loss` / `no_action` / `monitor_only` | `records_management` |

Always pick a value that **exists in the template's enum** for that field; enum names differ
across task variants.

## Category roll-up

For each category with open issues, choose a single `status` / `readiness_status` and
`production_impact` from the dominant (highest-severity) issue:

- Preservation loss dominates → `preservation_loss` / `preservation_risk`, impact `source_lost`.
- Missing required record → `missing_required_record`, impact `missing_record`.
- Personal source uncollected, archive available → `source_gap_with_archive_available`, impact `source_missing`.
- Personal source uncollected, no archive → `personal_source_gap`, impact `source_missing`.
- Collection gap (no personal-source angle) → `collection_gap`, impact `source_missing`.
- Privilege log gap → `privilege_log_gap`, impact `withheld_unlogged`.
- Privilege waiver + miscoding on same category → `underproduced_privilege_corrections`, impact `privilege_exposure`.
- Responsiveness miscode / zero-claim → `responsiveness_gap` / `incomplete`, impact `underproduced` / `not_produced`.
- Archive present and no other gap → `archive_available`, impact `source_available`.
- Multiple distinct blockers → `not_ready_multiple_blockers` / `multiple_impacts` (readiness variants).
- No open issue → omit the category (unless the template asks for all).

`issue_refs` / `blocking_refs` / `source_refs` for a category = union of record IDs from all
its open issues, sorted ascending. `open_issue_count` = number of open issue records summed
into the category.
