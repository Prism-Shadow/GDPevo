# Enum Usage Guide

How to select the correct enum value for each categorical field based on hub evidence. This guide covers enums that appear across multiple archetypes; template-specific enums are documented in the answer template itself.

## General Principle

When mapping hub evidence to an enum value:
1. Read the evidence record from the hub (retention event, QC finding, privilege log entry, custodian source, etc.)
2. Match the evidence to the most specific applicable enum value
3. If no value fully matches, prefer the most specific still-reasonable value
4. If nothing fits, use the catch-all (`"other"`, `"unknown"`, `"not_applicable"`) rather than fabricating

## Severity / Risk Level Assignment

Use the hub record's inherent risk, not the volume of data affected. A single privileged document inadvertently produced to the government may be `critical` even if the document count is 1.

### `critical`
**When**: The issue creates immediate legal jeopardy — spoliation risk, privilege waiver to adversaries, inability to comply with a production obligation, or destruction of records after a litigation hold was in effect.

**Hub signals**: `post_hold_loss` retention events, `third_party_waiver` privilege log entries where the third party is the government or an adverse party, documents coded `responsive` and `not_produced` with no log entry.

### `high`
**When**: Material production or preservation gap without immediate legal jeopardy, or a gap that requires disclosure to the requesting authority.

**Hub signals**: Uncollected custodian sources covering high-priority categories, `should_exist_missing` events for required records, `miscoded_responsive` QC findings with high document counts in key categories.

### `medium`
**When**: Gap exists but remediation is available — an archive can be searched, a source can still be collected, or documents can be recoded.

**Hub signals**: `available_archive` retention events, `not_collected` sources with retrievable data, `incomplete_log` privilege entries that can be supplemented.

### `low`
**When**: Administrative deviation, policy non-compliance without data loss, or minor coding issues.

**Hub signals**: `over_designation` privilege findings (documents logged as privileged but should be produced — the log exists, just too aggressively), `protocol_noncompliant` findings with no data impact.

---

## Issue Type Assignment

### `preservation_failure` / `post_hold_loss`
Records destroyed after a litigation hold was in effect.
- **Hub signal**: Retention event with `event_date` > `hold_date` and `event_type` indicating destruction
- **NOT** when destruction was policy-compliant and pre-hold

### `collection_gap` / `personal_source_gap`
A custodian source was not collected.
- **Hub signal**: Custodian source with `collection_status: "not_collected"` or `"partial"`
- **Personal variant** when source is a personal device, personal email, or personal messaging account

### `responsiveness_miscode`
A document coded non-responsive that should have been coded responsive.
- **Hub signal**: QC finding with `finding_type: "miscoded_responsive"` or current coding `nonresponsive` with recommended coding `responsive`

### `privilege_log_gap`
Documents withheld from production without corresponding privilege log entries.
- **Hub signal**: Privilege log entry with `logged: false` and `produced_status: "withheld"`, or documents `withheld` with no privilege log record at all
- **Count**: `withheld_count` is total withheld, `logged_count` is with log entries, `unlogged_count` = `withheld_count - logged_count`

### `privilege_miscoding` / `miscoded_privilege`
Privilege coding errors — either privileged documents coded non-privileged (exposure risk) or non-privileged documents coded privileged (over-designation).
- **Hub signal**: QC finding with privilege-related finding type, or privilege log entries with coding contradictions
- **Over-designation**: Document is logged as privileged but evidence suggests it should not be — production impact is `underproduced`
- **Under-designation**: Document is not logged but contains privileged content — production impact is `privilege_exposure`

### `third_party_waiver`
Privilege waived through disclosure to a third party.
- **Hub signal**: Privilege log entry with `waived: true` and a `third_party` value, or documents produced that contain communications with third parties
- **Severity depends on the third party**: disclosure to government/adversary is `critical`, disclosure to a vendor under a common-interest agreement may be `medium` or `low`

### `missing_required_record`
A record that should exist per retention policy or business practice but cannot be located.
- **Hub signal**: Retention event with `event_type: "should_exist_missing"` or custodian source note indicating expected records are absent
- **Different from retention loss**: a retention loss means the record existed and was destroyed; a missing required record means it should exist but there is no evidence it ever did

### `archive_available`
A loss that is mitigated because an archive or backup contains the data.
- **Hub signal**: Retention event with `archive_source_id` set, or custodian source with `archive_status: "available_archive"`
- **Use when**: The primary source is lost but an archive copy exists — risk is reduced but the archive still needs to be searched/collected

---

## Production Impact Assignment

| Evidence | Production Impact |
|---|---|
| Source destroyed, no archive | `source_lost` |
| Source exists but not collected | `source_missing` |
| Responsive documents exist but not produced | `not_produced` |
| Some documents produced, material ones missing | `underproduced` |
| Documents withheld, not on privilege log | `withheld_unlogged` |
| Privileged material may have been produced | `privilege_exposure` |
| Documents need recoding before production | `recode_needed` |
| Record should exist but cannot be found | `missing_record` |
| Archive contains the data | `source_available` |
| No impact on current production | `no_production_impact` |

---

## Category Status Assignment

Map the worst issue affecting each category:

| Category's Issues | Category Status |
|---|---|
| Post-hold loss events affect this category | `preservation_loss` |
| Required records are missing for this category | `missing_required_record` |
| Personal sources not collected for this category | `personal_source_gap` |
| Source gap exists but archive is available | `source_gap_with_archive_available` |
| Archive source exists for this category | `archive_available` |
| Privilege log has gaps for documents in this category | `privilege_log_gap` |
| Responsive documents miscoded in this category | `responsiveness_gap` |
| Privilege corrections needed (recoding) affecting production | `underproduced_privilege_corrections` |
| Both preservation loss and missing records | `mixed_preservation_and_missing_record` |
| No open issues | `no_open_gap` |
| Category not fully produced but no blocking issue | `complete` / `incomplete` (template-dependent) |

When a category has multiple issue types, choose the most severe status. Severity order: `preservation_loss` > `missing_required_record` > `personal_source_gap` > `privilege_log_gap` > `responsiveness_gap` > `source_gap_with_archive_available` > `archive_available` > `no_open_gap`.

---

## Source Status Assignment

| Hub Custodian Source Evidence | Source Status |
|---|---|
| Source confirmed destroyed or irrecoverable | `destroyed` / `lost` |
| Source identified but collection never attempted | `not_collected` |
| Source has an archive or backup available | `available_archive` |
| Source was collected fully | `collected` (not typically listed in gap outputs) |
| Source partially collected | `partial` |
| Source should exist but there is no evidence of it | `should_exist_missing` |
| Insufficient information | `unknown` |
| Field not applicable to this finding/risk | `not_applicable` |

---

## Owner Assignment

Assign the owner that can actually execute the recommended action:

| Action | Typical Owner |
|---|---|
| Collect a device or forensically recover data | `forensics` / `client_it` |
| Recode and produce documents | `review_qc` / `review_vendor` / `ediscovery_vendor` |
| Supplement privilege log | `privilege_team` / `privilege_counsel` |
| Waiver assessment | `privilege_counsel` / `outside_counsel` |
| Disclose to government | `outside_counsel` |
| Locate missing records | `records_management` / `records_vendor` / `client_legal` |
| Search or collect from archive | `ediscovery_vendor` / `records_vendor` |
| Compliance audit | `compliance_audit` |
| Escalate to counsel | `litigation_counsel` / `outside_counsel` |
| Monitor only | `legal_operations` / `outside_counsel` |

---

## Volume Unit Assignment

| What Is Being Counted | Volume Unit |
|---|---|
| Physical records in storage boxes | `boxes` |
| Email messages | `emails` |
| Individual documents | `documents` |
| Retention period in days | `days` |
| Retention period in months | `months` |
| Individual records (database rows, log entries) | `records` |
| Custodian sources (devices, accounts) | `sources` |
| A single report or assessment | `report` |
| Not applicable | `not_applicable` |
