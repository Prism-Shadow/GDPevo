# Noise vs Material Record Identification

Every hub table for a matter contains a handful of **material** (escalated, production-impacting) records buried among many **decoy/noise** records. Getting this split right is the single biggest scoring lever, because findings/categories are matched by their stable-ID sets — a wrong split fails most checks.

## Primary signal: the record ID and note

**Material records** have a *descriptive, named* ID and a note that states a concrete escalated fact:
- `SRC-ALLOY-KLINE-SIGNAL` — "Signal messages were identified in custodian interview but not collected."
- `PRIV-NORTH-LOG-GAP` — "Only 365 of 840 withheld privileged documents are logged."
- `RET-HARB-EHS-POST` — "Two boxes destroyed after the hold date."
- `QC-ALLOY-ZERO-CLAIM` — "Category F zero-production claim contradicted by two responsive bid emails."
- `SRC-GRAY-HALE-LAPTOP` — "Laptop replaced post-hold and wiped on 2023-12-01."

**Decoy records** have a *generically-numbered* ID (`<MATTER>-001`, `-002`, …) and a note containing one of these noise phrases:

| Noise phrase (in `notes`) | Meaning |
|---|---|
| "Entry included to create similar labels across matters" | decoy — exists only to mimic material records |
| "Privilege sample has ordinary review variance" | decoy — normal review noise |
| "Review team marked this item for follow-up but not immediate remediation" | decoy — not escalated |
| "Potential issue requires category-level context before escalation" | decoy — not escalated |
| "No production-impacting issue has been escalated yet" | decoy — no impact |
| "Entry creates a similar label but has no unresolved production impact" | decoy — no impact |
| "Quality-control sample is noisy but not dispositive without source comparison" | decoy — inconclusive |
| "Review manager requested re-sampling before escalation" | decoy — not escalated |
| "Finding is similar to escalated records in another matter" | decoy — not this matter's escalation |
| "Corrected in later overlay but retained for audit trail" | decoy — already corrected |
| "Vendor tracker and legal hold tracker use slightly different record labels" | decoy — label discrepancy only |
| "Source map entry has minor metadata normalization issues" | decoy — metadata only |
| "Collection status differs between custodian tracker and vendor load report" | decoy — tracker discrepancy |
| "Requires matter-level filtering because similar issue labels appear across matters" | decoy — cross-matter label noise |
| "Retention entry is relevant only after comparing hold date and policy period" | usually decoy — check dates; if pre-hold and policy-compliant, it is not an open gap |
| "Potential issue was remediated by archive collection" | remediated — not an open gap (may point to an available archive) |
| "Routine action included as realistic operational noise" (remediation_actions) | noise action — exclude |

When a note states a real loss with dates/counts ("destroyed after the hold date", "wiped on <date>", "covers X of Y withheld", "X boxes destroyed", "forwarded to <third party>"), the record is material.

## Confirmation signal: remediation_actions

The most reliable cross-check: list the `target_ref` of every remediation action whose `description` is **not** "Routine action included as realistic operational noise". Those `target_ref`s are exactly the material records for the matter. If your material set from notes matches this set, you are confident. If a record is targeted by a non-noise action, include it; if a record is only referenced by noise actions (or by a bare category-code target), exclude it.

## Per-table material defaults

- **custodian_sources**: personal-device sources (`personal_phone`, `personal_email`, `personal_messaging`, `laptop`) that are `lost`/`not_collected` with `post_hold=1`; board/sharepoint sources scoped but not collected; archive sources tagged `archive_available`/`remediation_source`. Routine `network_share`/`mailbox`/`teams_export`/`contract_repository` sources are decoys.
- **privilege_entries**: only escalated `incomplete_log` (unlogged > 0) and `third_party_waiver` (third_party=1 with a named recipient) entries. `over_designated`/`family_mismatch`/`clean` are noise unless escalated by note.
- **qc_findings**: only findings with a concrete escalated note (miscoded responsiveness/privilege, zero-claim contradiction). `family_break`/`near_duplicate`/`duplicate_overlay`/`metadata_gap`/`date_normalization` are noise unless escalated.
- **retention_events**: `post_hold_loss`, escalated `should_exist_missing`, and escalated system/auto-purge losses. `policy_destroyed_pre_hold` is a compliant loss (include as an event but mark no-action/policy-loss). `retained`/`available` are not gaps. Remediated/system-loss-with-noise-note are not open gaps.
- **remediation_actions**: exclude the "operational noise" actions and bare-category-code targets.

## Affected categories

A category has an open gap only if a material record impacts it (via its `category_impacts`/`affected_categories`). Build the union of categories across all material records for `categories_with_open_gaps` / `categories_with_open_risk` and its count. A category with no material record is `no_open_gap`/`ready` (or omitted, per the template).
