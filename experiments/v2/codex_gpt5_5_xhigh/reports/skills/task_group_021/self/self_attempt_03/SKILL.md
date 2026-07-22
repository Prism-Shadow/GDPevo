---
name: asteria-data-quality-reconciliation
description: Reconcile Asteria Fleet Data Quality Hub collections and return strict JSON audit or certification answers. Use when a task references an Asteria hub, TASK_ENV_BASE_URL, environment_access.md, case_scope.json, answer_template.json, source snapshots, contacts, fuel, freight, maintenance events, reference aliases, unit conversions, FX, duplicate reconciliation, quarantine/exception counts, readiness, certification gates, or compact Asteria decision/control codes.
---

# Asteria Data Quality Reconciliation

Use this skill to solve Asteria Fleet Data Quality Hub tasks that provide a prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`.

## Intake

1. Read the prompt, the full case scope, and the full answer template before querying data.
2. Treat `environment_access.md` as the only source for network base URL, allowed endpoints, and query authorization.
3. Return exactly one JSON object matching the answer template. Do not include Markdown, comments, extra keys, or task-local explanations.
4. Preserve all ordering, length, enum, uniqueness, rounding, and `additionalProperties` constraints from the template.
5. Use only stable public IDs present in hub data or supplied by case scope.

## Hub Access

- Prefer `POST /api/query` with header `Authorization: Bearer ...` from `environment_access.md`.
- The query request body uses `{"query":"select ..."}`.
- Inspect `/api/catalog/collections`, `/api/catalog/schema`, and `/api/source-snapshots` first.
- Query logical views exposed by schema:
  - `v_contacts`
  - `v_fuel_transactions`
  - `v_freight_charges`
  - `v_maintenance_events`
  - `v_reference_aliases`
  - `v_unit_conversions`
  - `v_fx_rates`
  - `v_source_snapshots`
- Do not assume a single REST list response contains the full collection. Use SQL aggregation or explicit pagination.

## Source Snapshot Rules

1. Scope rows by `collection_id` and the business cutoff/as-of dates in `case_scope.json`.
2. Use source snapshot metadata to identify snapshot status, business cutoff, creation time, and row counts.
3. For overlapping logical records in certified and provisional snapshots, retain the certified occurrence when present.
4. Retain provisional-only logical records unless the prompt or template says otherwise.
5. Count raw rows before deduplication; count logical records after grouping by the stable logical ID (`transaction_id`, `charge_id`, `event_id`, or resolved contact/person).
6. Compute duplicate raw count as raw occurrence count minus distinct logical count, unless the template defines a narrower duplicate set.
7. For duplicate group outputs, include every logical ID with multiple raw occurrences, sort by logical ID, sort `snapshot_ids` lexicographically, and report the retained snapshot.

## Reference Matching

Use `v_reference_aliases` for fuel and freight classification.

1. Normalize candidate descriptions and aliases case-insensitively.
2. Match aliases as meaningful phrases/tokens, not arbitrary substrings inside unrelated words.
3. Apply reference business-date validity (`valid_from`, `valid_to`) and `reference_status`.
4. Count a zero-match description as unrecognized.
5. Count a description that matches aliases for more than one canonical value as ambiguous.
6. Treat both zero-match and ambiguous classifications as unresolved/quarantined when the template asks for unrecognized or quarantine IDs.
7. Compare recognized canonical value to expected value to compute valid mismatches.
8. Valid mismatches remain in normalized totals unless the prompt says otherwise.

Common alias domains:

- Fuel canonical values: `BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`, `PREMIUM_UNLEADED`, `UNLEADED`.
- Freight canonical values: `EXPRESS`, `HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`.

## Unit, Currency, And Rounding

1. Use `v_unit_conversions` for volume, weight, distance, and odometer conversions.
2. Use the canonical units from case scope or template, usually `L`, `KG`, `KM`, and `USD`.
3. Use certified FX rows in `v_fx_rates` for the business date and currency. Multiply source amount by `usd_per_unit`.
4. Exclude quarantined transactions or charges from normalized totals.
5. Include valid category/class mismatches in normalized totals.
6. Round only at the final requested output precision. Most normalized totals use 2 decimal places; rates may require 4 decimal places.

## Fuel Audit Rules

1. Group raw rows by `transaction_id`.
2. Retain certified occurrence if duplicated; otherwise retain the only occurrence.
3. A transaction is quarantined when quantity is nonpositive/invalid or classification is unresolved.
4. A mismatch is a retained, valid transaction whose recognized fuel type differs from `expected_fuel_type`.
5. `exception_transaction_count` is the distinct logical transactions with a mismatch or quarantine condition.
6. Merchant exception ranking sorts by exception count descending, then `merchant_id` ascending.
7. Focus-asset rollups use retained logical transactions for the requested assets. Report logical count, valid count, mismatch count, quarantine count, exception count, and normalized valid totals.

## Freight Audit Rules

1. Group raw rows by `charge_id`.
2. Retain certified occurrence if duplicated; otherwise retain the only occurrence.
3. A charge is quarantined when service class is unresolved, billed weight is nonpositive/invalid, or distance is nonpositive/invalid.
4. A class mismatch is a retained, valid charge whose recognized service class differs from `expected_service_class`.
5. Quarantine reason counts are not mutually exclusive unless the template says they are; inspect wording carefully.
6. Normalized totals include valid mismatches and exclude quarantines.
7. Carrier ranking exposure is normalized USD on valid mismatches. Sort by mismatch exposure descending, then carrier ID ascending.

## Maintenance Audit Rules

1. Group raw rows by `event_id` for cross-snapshot duplicate detection and source retention.
2. Retain certified occurrence when an event appears in both certified and provisional snapshots.
3. Reject events with missing/unparsable timestamps, invalid odometer values, negative labor, or extreme labor according to the case/template thresholds and evidence.
4. Reconstruct the requested-period history from retained, non-rejected events inside the business period.
5. Detect odometer regressions after unit-normalizing odometers to kilometers and sorting each asset by event time, then event ID as a deterministic tie-break.
6. Report sequence-only regressions separately from invalid-event rejections when the template distinguishes them.
7. Corrected distance is usually the sum across assets of last reliable odometer minus first reliable odometer in reconstructed history.
8. Asset risk rankings follow the ranking policy in case scope exactly, including all tie-breaks.

## Contact Reconciliation Rules

1. Work over all in-scope contact rows for the collection and cutoff.
2. Normalize emails with trim, Unicode NFKC, and lowercase.
3. Normalize phones to digits only; if an 11-digit North American number starts with `1`, drop the leading `1`.
4. Treat blank, null-like, `N/A`, `none`, and `NULL` channel values as unusable.
5. Build person clusters as connected components from strong evidence:
   - same normalized usable email;
   - same normalized usable phone plus corroborating name/source evidence;
   - reliable shared `master_hint` that does not represent a shared helpdesk/contact channel.
6. Do not auto-merge shared phone or shared `master_hint` groups when names/emails identify different people; mark them contested when requested.
7. Choose a stable master/survivor from the retained source evidence using the task's source status, verified flags, business update times, and field-level precedence. Do not invent IDs.
8. Canonical contact fields are field-level decisions, not whole-row copies. Record the source system for each canonical field when requested.
9. Preserve Unicode names; clean whitespace and casing without stripping meaningful diacritics.
10. A contact/person is dispatch-ready only when active, has at least one usable canonical email or phone, and consent is granted.
11. Partition readiness counts mutually exclusively. Typical blockers are non-granted consent, no usable contact channel, and inactive record status.
12. Quarantine rows are source rows with no usable contact channel when the task asks for row-level quarantine.

## Compact Code Panels

Many templates require opaque Asteria codes. Infer them from the reconciled evidence and the enum family.

- `RB-*` reference-policy codes partition reference alias rows by effective active/current, superseded/out-of-window/inactive, and provisional/unapproved states.
- `SB-*` source-basis or source-retention codes partition retained logical records by certified-only, provisional-only, and cross-snapshot duplicate-retained cases.
- `LD-*` ledger-disposition codes partition retained fuel/freight records by valid aligned, valid mismatch, unresolved zero-match classification, ambiguous classification, and invalid physical measure.
- `MS-*` maintenance-source codes partition maintenance events by certified-only, provisional-only, and cross-snapshot duplicate-retained cases.
- `HR-*` history-route codes partition maintenance events by accepted history, rejected invalid event, and sequence/regression handling.
- `IC-*`, `OR-*`, and `FP-*` contact control codes partition identity resolution, outreach/readiness, and field-provenance outcomes.

When a case scope supplies anchored control cases or decision IDs, classify each anchor into its evidence bucket first, then assign the corresponding allowed code consistently across every row in that bucket. Do not guess a code from enum order alone if anchors make the mapping clear.

## Certification And Status

1. Apply status thresholds and action maps from `case_scope.json`.
2. If explicit certification gates are supplied, use them exactly.
3. Typical pattern:
   - no exceptions/quarantine/regressions: `PASS` with release action;
   - exceptions within tolerance: `PASS_WITH_EXCEPTIONS` with review action;
   - gate failure or threshold breach: `HOLD` with block/remediate action.
4. Use the exact key names from the template, such as `next_action`, `action`, or `routing`.

## Output Assembly Checklist

Before finalizing:

1. Validate top-level required keys and forbid extra keys.
2. Check every scoped panel has exactly the requested IDs and order.
3. Sort all stable-ID lists as specified, usually lexicographically.
4. Confirm counts reconcile: raw, logical, duplicate, valid, mismatch, quarantine, readiness partitions, and ranking totals.
5. Confirm normalized totals exclude quarantines and include valid mismatches.
6. Confirm all enum values appear exactly as allowed.
7. Confirm numbers use requested precision and JSON numbers remain numbers, not strings.
