---
name: asteria-quality-reconciliation
description: Reconcile Asteria Fleet Data Quality Hub tasks for contacts, fuel, freight, and maintenance audits. Use when a task provides a case scope, answer contract, source snapshots, operational records, reference aliases/conversions/FX, and asks for canonical entities, duplicate retention, quarantine/exception counts, normalized totals, ranking panels, compact control codes, or release/certification decisions.
---

# Asteria Quality Reconciliation

## Required Workflow

1. Read the prompt, case scope, answer contract, and environment access supplied with the task.
2. Inspect the catalog/schema before querying records. Identify the collection family (`contacts`, `fuel`, `freight`, or `maintenance`), business cutoff/as-of time, requested focus IDs, output precision, and ordering rules.
3. Pull all in-scope source rows for the scoped collection. Keep raw rows for raw counts, then build a retained logical record set for calculations.
4. Use source snapshot metadata to identify the authoritative basis. Prefer certified/authoritative rows when overlapping logical records exist; otherwise retain the latest available row by business update and ingestion time. Report duplicate groups from all overlapping raw occurrences, not only the retained row.
5. Build the answer directly from the answer contract. Preserve exact key names, enum values, list lengths, sort orders, uniqueness rules, and numeric precision.

## Ledger Audits

Use this for fuel-purchase and freight-charge collections.

- Resolve logical records by stable transaction/charge ID before counting valid, mismatch, or quarantined records.
- Classify descriptions with applicable active reference aliases for the business date. Match aliases case-insensitively on phrase/word boundaries. Apply longest-phrase dominance so a specific alias such as a multi-word phrase is not made ambiguous only because it contains a shorter alias.
- After longest-phrase dominance, treat zero canonical matches as unrecognized and multiple canonical values as ambiguous. Treat nonpositive required physical measures as invalid. These are quarantine conditions.
- Treat expected-versus-recognized category/class mismatches as valid exceptions, not quarantines. Include valid mismatches in normalized totals and ranking exposure.
- Exclude quarantined logical records from normalized totals.
- Normalize physical measures with the unit conversion reference rows valid for the business date. Convert money with certified FX for the record business date. Round only at the output boundary to the contract precision.
- Rank exception merchants/carriers exactly as specified in the scope or template. Use distinct retained logical records for counts.
- For compact decision-code panels, derive a small state table from the scoped rows and apply it consistently:
  - reference rows: applicable active reference, inactive/out-of-window reference, provisional reference;
  - source rows: retained authoritative row, retained non-authoritative row, overlapping duplicate retained from the authoritative basis;
  - ledger rows: valid match, valid mismatch, invalid measure, unrecognized alias, ambiguous alias.

## Contact Reconciliation

Use this for partner-contact and field-roster collections.

- Normalize email with Unicode NFKC, trim whitespace, and lowercase. Normalize phone to digits only. Normalize names by trimming and collapsing whitespace while preserving Unicode.
- Build candidate identity clusters by unioning rows that share strong evidence: normalized email, normalized phone, or stable master hint. If the shared evidence connects clearly different names or people, keep the cluster contested for reporting instead of silently treating it as a clean merge.
- Do not merge rows solely on a missing channel, blank identifier, or a common operational placeholder.
- Select canonical fields field-by-field, not necessarily from a single survivor row. Prefer verified/certified and fresher business evidence, then source-specific field authority implied by the prompt. Keep the public survivor/master ID stable and deterministic.
- Quarantine source rows with no usable email and no usable phone. Count canonical entities separately from quarantined source rows as required by the contract.
- A dispatch/readiness-eligible canonical person/entity must be active and retain at least one usable email or phone. A channel is ready only when consent is granted. Partition readiness categories so they are mutually exclusive and sum to the eligible population or depot total required by the template.
- For depot/region rollups, count canonical entities, not raw rows. Use the canonical depot/region field and sort by the contract.
- For contact control codes, assign codes by condition family and apply the same condition-to-code mapping across all panels:
  - identity: single-source identity, clean auto-merge, contested identifier/no auto-merge, no usable identity/contact evidence;
  - outreach: ready with both channels, email-only ready, phone-only ready, blocked by consent/no contact/inactive status;
  - field provenance: single-source field, field-level precedence/conflict resolution, verified authoritative field.

## Maintenance History Audits

Use this for maintenance-event collections.

- Resolve overlapping events by public event ID, retaining authoritative/certified evidence when present. Still report every cross-snapshot duplicate group with all snapshot IDs.
- Reject events from corrected history when required time is missing/unparseable, odometer is nonpositive/unusable, labor is negative, or labor is beyond the task’s valid range. Count each issue independently when one event has multiple issue types.
- Convert odometers to the canonical distance unit before sequence checks.
- Within each asset, sort retained valid events by parsed event time, then event ID. Mark odometer regressions when an event drops below the previous reliable odometer. Report sequence regressions separately from hard-invalid event IDs.
- Compute corrected distance per asset from reliable non-regression readings only, using last reliable odometer minus first reliable odometer, then sum across assets and round to the requested precision.
- Build asset risk rankings from rejected-event counts first, regression-event counts second, then the specified stable ID tie-break.
- For maintenance code panels, map source codes by retained source basis and duplicate status, and map history route codes by accepted history, rejected hard-invalid event, or sequence regression.

## Final Checks

- Validate that every required scoped ID appears exactly once in its panel and that no unrequested IDs appear in fixed-length panels.
- Recompute summary counts from the same retained/quarantine sets used for detail arrays.
- Ensure sorted arrays follow the contract, especially duplicate-group IDs, scoped decision IDs, ranked arrays, and row-ID sets.
- Return only the JSON object requested by the task.
