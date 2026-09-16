---
name: asteria-hub-quality-audits
description: Solve Asteria Fleet Data Quality Hub reconciliation and certification tasks that provide case_scope.json, answer_template.json, and environment_access.md. Use for contact-master/readiness, fuel or freight normalization, maintenance-history integrity, source-snapshot reconciliation, quarantine/mismatch reporting, decision-code panels, rollups, rankings, and strict JSON-only answers.
---

# Asteria Hub Quality Audits

Use this skill when a task asks for an Asteria Fleet Data Quality Hub audit or certification answer. The task will supply a prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`.

## Core Workflow

1. Read the prompt, `case_scope.json`, and the full `answer_template.json` before querying data.
2. Treat `answer_template.json` as the output contract. Preserve required keys, exact enum values, array lengths, uniqueness, numeric precision, and ordering rules from schema descriptions.
3. Read `environment_access.md` for the base URL, credentials, and allowed endpoints. Never call a judge endpoint.
4. Query `catalog/collections` and `catalog/schema` first to identify the collection family, logical view names, field meanings, and source systems.
5. Pull all in-scope rows. Collections can exceed one response page; page until the returned total is exhausted. If `/api/query` is available, use the logical views directly and filter by `collection_id`, cutoff/as-of time, and business period from `case_scope.json`.
6. Reconcile overlapping snapshots before computing metrics. Pick the authoritative in-scope snapshot by status and cutoff evidence, with `CERTIFIED` preferred over `PROVISIONAL`, and retain that snapshot's occurrence for duplicate logical IDs when present. Report duplicate groups from the full raw in-scope row set.
7. Compute every answer field from reconciled rows, reference tables, unit conversions, and FX rates. Do not estimate from row IDs or generator patterns when data can be queried.
8. Fill scoped panels exactly for IDs listed in `case_scope.json`; sort panels and ID lists by the contract, usually lexicographic or ascending stable ID.
9. Before finalizing, verify counts reconcile: raw minus duplicate raw rows equals logical records; valid plus quarantine/rejected categories match logical records where applicable; readiness partitions sum to their totals; status/action values match the scope's gates or action map.
10. Return only the final JSON object.

## Source And Snapshot Rules

Use these logical keys after filtering to the requested collection and cutoff:

- Contacts: `row_id` is the raw public row. Use `master_hint`, stable source identifiers, normalized email/phone, and identity evidence to cluster canonical people or partner contacts.
- Fuel: `transaction_id` is the logical transaction.
- Freight: `charge_id` is the logical charge.
- Maintenance: `event_id` is the public event; duplicate reporting may describe it as the logical event ID.

For each logical key with multiple raw rows, record the sorted distinct `snapshot_id` set. Retain the row from the authoritative snapshot. If the authoritative row is absent, prefer the highest status available, then latest business update/ingest evidence.

Use snapshot metadata for reported source decisions: collection ID, as-of/cutoff, authoritative snapshot ID, snapshot status, authoritative row count, scoped raw row count, duplicate raw count, and logical count.

## Reference Matching

For fuel and freight tasks, resolve `purchased_description` or `description` through `v_reference_aliases`.

- Restrict aliases to the relevant domain and business date: `valid_from <= date`, `valid_to` empty or after date, and `published_at` no later than the audit cutoff.
- Normalize comparison text consistently: trim, casefold/lowercase, collapse whitespace, and ignore punctuation only when the alias evidence supports it.
- Exactly one active matching alias gives the recognized canonical category/class.
- Zero matches are unrecognized. More than one active canonical match is ambiguous.
- Valid mismatches are records with a recognized class/category different from the expected class/category. They remain in normalized totals.
- Quarantines are unresolved aliases or invalid physical measures. They do not enter normalized totals.

For code panels using compact codes, read [decision-codes.md](references/decision-codes.md).

## Normalization

Use `v_unit_conversions` effective on the business date and the canonical units requested in `case_scope.json`.

- Fuel volume: convert to liters and round final reported values to the requested precision.
- Freight weight and distance: convert to kilograms and kilometers.
- Maintenance odometer: convert to kilometers before sequence checks and distance metrics.
- FX: use the effective published rate for the record currency and business date. USD amounts should remain unchanged when the currency is already USD.

Keep full precision internally. Round only final numeric outputs, normally to two decimal places unless the template says otherwise.

## Contact Audits

Normalize contact fields before clustering and readiness checks.

- Email: trim, Unicode-normalize if needed, and lowercase.
- Phone: digits only.
- Usable contact: at least one normalized email or phone.
- Dispatch/channel ready: active record, usable contact, and granted consent.
- Blocked consent/not ready: active with usable contact but non-granted consent.
- No-contact quarantine: no usable email or phone.
- Inactive exclusion: inactive person with usable contact.

Cluster only when identity evidence supports one canonical person. Do not auto-merge contested identifier watchlist cases. Canonical person/entity counts include quarantined people unless the answer contract explicitly excludes them.

For field-level canonical values, use source-system precedence plus verification and recency evidence. In the observed Asteria contact families, registry/compliance systems are strongest for contact and consent fields, while HR-like systems are strongest for workforce names and depot/region fields. Still verify against the collection's source systems and row evidence.

## Fuel And Freight Audits

Build retained logical records, then classify each record:

- `valid_clean`: recognized expected category/class, valid physical measures.
- `valid_mismatch`: recognized but differs from expected; included in normalized totals and mismatch lists.
- `quarantine_unrecognized`: no unique alias match.
- `quarantine_ambiguous`: multiple canonical alias matches.
- `quarantine_measure`: nonpositive or invalid quantity, weight, distance, or equivalent physical field.

For fuel, aggregate valid records by canonical fuel type and focus asset. Merchant exception counts are distinct logical transactions with either a mismatch or quarantine.

For freight, aggregate valid records by canonical service class. Carrier accrual exposure is valid mismatch spend, sorted by exposure descending and carrier ID ascending unless the template says otherwise. Carrier exception count is distinct retained charges that are valid mismatches or quarantined.

## Maintenance Audits

Filter maintenance events to the requested collection, business period, and as-of cutoff, then deduplicate by logical event ID.

Reject events for missing/unparsable time, invalid odometer range, negative labor, or extreme labor. Report unique rejected event IDs sorted lexicographically. Sequence-only odometer regressions are not part of that rejected ID list unless the template says so.

For corrected history:

- Sort valid events per asset by parsed event time, then stable event ID.
- Convert odometer readings to kilometers.
- Detect regressions when a later reliable reading is less than the previous reliable reading for the same asset.
- Exclude regression events from corrected valid history metrics when the task treats regressions as non-reliable.
- Compute total corrected distance as the sum over assets of last reliable odometer minus first reliable odometer.

For risk rankings, apply the exact sort policy in `case_scope.json`, usually rejected count descending, then regression count descending, then asset ID ascending.

## Status Decisions

Use explicit thresholds, gates, and action maps from `case_scope.json` first.

Common patterns:

- Contact certification with quarantine-rate thresholds can pass with exceptions when the rate is nonzero but within the scoped exception threshold.
- Roster release should hold when contested identifier cases remain or required dispatch readiness gates fail.
- Fuel/freight finance close should hold when any hard exception, quarantine, or unresolved mismatch gate remains.
- Maintenance certification should hold when the scope declares odometer regression as a hold gate and regressions are found.

Use the action/routing field name from the template (`action`, `next_action`, or `routing`) and the mapped value from the case scope when present.
