# Classification Rules

How to turn hub records into the template's enumerated values. The template's own enum lists are always authoritative; where a hub value has no exact match, pick the closest enum member by meaning and stay consistent across the answer.

## 1. Pre-hold vs post-hold (the master distinction)

Compute `hold_date` from the matter record. For each custodian_source / retention_event:

- `event_date` **before** `hold_date` (or `post_hold = 0`) and the loss followed an approved retention policy → **policy-destroyed-pre-hold**: report it as a retention event, risk `low`/`medium`, action `no_action` / `no_action_policy_loss` / `document_system_gap`. It is a *fact*, not a preservation breach.
- `event_date` **on or after** `hold_date` (or `post_hold = 1`) → **post-hold loss**: preservation breach, risk `high`/`critical`, action `disclose_preservation_issue` / `disclose_to_government` and/or `forensic_recovery` / `restore_from_backup` where an archive exists.
- `should_exist_missing` (a record the schedule says should exist but is absent, with no destruction event) → preservation risk regardless of timing; action `locate_missing_record`.

## 2. Issue type mapping

| Hub signal | Template `issue_type` (pick the one in the template's enum) |
|---|---|
| post-hold destruction / loss | `post_hold_loss`, `retention_loss`, `preservation_failure` |
| pre-hold policy destruction | `retention_loss` (with `no_action`) — or omitted if the template only wants open gaps |
| auto-purge / deleted channel / purged custodian mail | `active_system_loss` / `post_hold_loss` |
| personal phone/email/messaging not collected | `personal_source_gap`, `collection_gap`, `personal_email_gap`, `personal_phone_gap` |
| withheld docs with `logged < withheld` | `privilege_log_gap` |
| privileged docs miscoded / over-designated | `privilege_miscoding`, `miscoded_privilege`, `over_designation` |
| responsive docs tagged nonresponsive (or vice versa) | `responsiveness_miscode`, `responsive_miscoding` |
| third-party communication withheld/produced | `third_party_waiver` |
| record that should exist is missing | `missing_required_record`, `should_exist_missing` |
| archive still available | `archive_available` (as a remediation source, not a defect) |
| zero-production batch contradicted by other evidence | `zero_claim_contradiction` |

## 3. Severity / risk_level

- Prefer the hub `severity` when present.
- Otherwise infer: post-hold loss touching a produced/withheld category → `critical`; unlogged privilege on withheld docs → `high`; uncollected personal source → `high`; responsiveness miscoding → `medium`; pre-hold policy loss → `low`; available archive (remediation) → `low`/`medium` as a source, not a defect.

## 4. Status mapping

Map hub `status` to the template's status enum. Common translations:

- open defect / unaddressed → `open`
- fix proposed but not done → `remediation_pending` / `remediation_available`
- violates a protocol/hold → `protocol_noncompliant`
- resolved / produced / collected → `ready` / `closed` / `no_gap` / `cleared`
- archive usable → `remediation_available` (status) and the source gets `available_archive`

Items in a final `critical_findings`/`top_risks`/`issue_ledger` list should generally be non-ready (`open`, `remediation_pending`, `protocol_noncompliant`, `needs_recode`, `should_exist_missing`, `incomplete_log`, `waived`). Ready/closed items usually appear only as context or in `available_archives`/`retained_or_available_sources`.

## 5. Source status mapping

| Hub source state | Template `source_status` |
|---|---|
| destroyed / lost / purged | `lost` / `destroyed` |
| not collected / not_collected | `not_collected` |
| partial collection | `partial` / `partial_collection` |
| collected / preserved | `collected` / `preserved_available` |
| pending collection | `pending` / `collection_pending` |
| archive available | `available_archive` |
| n/a | `not_applicable` / `unknown` |

## 6. Production impact mapping

| Situation | `production_impact` |
|---|---|
| source destroyed/lost | `source_lost` |
| source missing / never collected | `source_missing` / `not_produced` |
| partial source | `partial_source_missing` / `underproduced` |
| withheld but unlogged | `withheld_unlogged` |
| third-party privileged produced → waiver | `privilege_exposure` / `privilege_waiver` |
| wrong coding | `recode_needed` |
| required record missing | `missing_record` |
| archive usable / no current defect | `source_available` / `no_production_impact` / `no_current_gap` |
| multiple | `multiple_impacts` (only where the enum has it) |

## 7. Privilege-log math

For each privilege_entries row flagged as an incomplete-log blocker (issue_type = incomplete-log / privilege_log_gap):

- `withheld_count` = docs withheld
- `logged_count` = docs logged on the privilege log
- `unlogged_count` = `withheld_count − logged_count` (≥ 0)

Template metrics that say "from selected incomplete-log blockers only" mean: sum `withheld_count`, `logged_count`, and the computed `unlogged_count` **only** over those blocker rows — not over every privilege entry. Filter first, then sum.

A `third_party = 1` flag on a withheld/produced entry raises a `third_party_waiver` issue and feeds `third_party_waiver_doc_count` / `waived_privilege_doc_count`.

## 8. Category rollup

For each category code in the matter's subpoena-category universe:

1. Gather every finding/event/source/document/privilege entry whose `affected_category` / `category_impacts` / `category_code` includes it.
2. Decide one `category_status`:
   - post-hold loss present → `preservation_loss` / `preservation_risk`
   - should-exist-missing only → `missing_required_record`
   - uncollected personal source, no archive → `personal_source_gap` / `collection_gap`
   - source gap but an archive covers it → `source_gap_with_archive_available`
   - unlogged privilege → `privilege_log_gap` / `withholding_gap`
   - miscoding → `responsiveness_gap` / `underproduced_privilege_corrections`
   - nothing open → `no_open_gap` / `no_current_gap` / `complete`
3. Include the category in the answer only when its status is non-complete (unless the template's field description demands full coverage).
4. Attach `source_refs`/`issue_refs` (the IDs gathered in step 1, sorted ascending) and a `recommended_action` derived from the dominant issue.

## 9. Priority / action assignment

Assign `priority` (P0–P3) and `action_type`/`owner` together:

| Situation | priority | action_type | owner (typical) |
|---|---|---|---|
| Post-hold loss of a produced/withheld category, no archive | P0 | `disclose_to_government` / `disclose_preservation_issue` | outside_counsel / privilege_counsel |
| Third-party privileged docs produced (waiver) | P0 | `waiver_assessment_and_disclosure` | privilege_counsel |
| Unlogged privilege on withheld docs | P1 | `supplement_privilege_log` | privilege_team |
| Uncollected personal device/email/messaging | P1 | `collect_source` / `collect_personal_device` / `collect_personal_email` / `collect_signal_messages` | forensics / client_it |
| Archive available covering a loss | P1/P2 | `search_archive` / `restore_from_backup` / `collect_archive` | ediscovery_vendor / records_management |
| Responsiveness miscoding | P2 | `recode_and_produce` | review_qc |
| Privilege miscoding / over-designation | P2 | `privilege_recode_and_log` / `privilege_re_review` | privilege_team |
| Should-exist-missing record | P2 | `locate_missing_record` | records_management / compliance_audit |
| Pre-hold policy-compliant loss | P3 | `no_action` / `no_action_policy_loss` / `monitor_only` | records_management / legal_operations |

Then re-rank all actions into a single `priority_rank`/`rank` list, 1 = highest, sorted ascending. `target_refs` = the hub record IDs the action addresses (sorted ascending); `category_impacts` / `affected_categories` = the category codes it covers (sorted ascending, uppercase).

## 10. Readiness / production-ready boolean

`production_ready` / `rolling_production_ready` / `*_ready` is `true` **only** when no open critical or high blocker remains across the matter. If any P0/P1 issue is open, the boolean is `false`. Set it last, after the issue ledger and metrics are finalized, so it reflects the actual open-item set.
