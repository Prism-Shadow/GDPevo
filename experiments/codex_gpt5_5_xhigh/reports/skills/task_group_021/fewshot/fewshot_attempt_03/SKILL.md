---
name: asteria-data-quality-audit
description: Reconcile Asteria Fleet Data Quality Hub collections and produce contract-exact JSON answers for contact-master readiness, fuel and freight normalization, maintenance-log certification, source-snapshot retention, and opaque Asteria policy/control/ledger code panels. Use when a task mentions Asteria Fleet Data Quality Hub, case_scope.json, answer_template.json, source snapshots, /api/query, overlapping source records, quarantines, canonical contacts, normalized fuel/freight totals, maintenance history metrics, or Asteria compact decision codes.
---

# Asteria Data Quality Audit

## Start

1. Read the prompt, `payloads/case_scope.json`, and `payloads/answer_template.json` before querying data.
2. Read `environment_access.md` for the base URL and query token. Use those values only; do not infer credentials.
3. Query the hub catalog and schema first:

```bash
curl -sS "$BASE/api/catalog/collections"
curl -sS "$BASE/api/catalog/schema"
curl -sS -X POST "$BASE/api/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"select * from v_source_snapshots limit 5"}'
```

The query body key is `query`. Prefer `/api/query` for complete audits because public collection endpoints can be paged and may reject unsupported filters.

## Contract Discipline

- Return exactly one JSON object when requested. Do not include Markdown or commentary.
- Treat the answer template as binding for required keys, allowed enum values, ordering, uniqueness, and numeric precision.
- Sort arrays by the template or case-scope rule. If no rule is supplied, sort stable IDs lexicographically and ranking rows by their stated ranking keys.
- Validate the final JSON shape against the template when it is a JSON Schema. For descriptive templates, check every required key and reject extra top-level keys.
- Recompute all values from the current hub and scope. Do not reuse IDs, counts, totals, names, or rankings from examples.

## Shared Reconciliation Rules

- Scope by `collection_id` and the task cutoff/as-of period. Use the business date field for the family: contacts use `business_updated_at` and snapshot cutoff, fuel uses `purchased_at`, freight uses `service_date`, and maintenance uses `event_time_raw` plus any business period in scope.
- Use `v_source_snapshots` to identify snapshot status, source system, cutoff, and row counts.
- For overlapping logical rows, group by the public logical ID (`transaction_id`, `charge_id`, or `event_id`). Retain the certified occurrence when present; otherwise retain the in-scope provisional occurrence. Count duplicates as raw rows minus distinct logical IDs.
- Build duplicate groups from all logical IDs with more than one raw occurrence. Sort group IDs ascending; sort `snapshot_ids` lexicographically.
- Treat retained rows with a recognized category/class but an expected-versus-recognized mismatch as valid rows unless a quarantine condition also applies.
- Exclude quarantined rows from normalized totals. Include valid mismatches in normalized totals and in mismatch/exposure reporting.
- Round only final reported numeric fields to the precision required by the template.

## Alias Recognition

Use `v_reference_aliases` for fuel and freight descriptions.

- Normalize descriptions and aliases with Unicode NFKC, trim, lowercase, and collapse whitespace.
- Match active aliases as phrase substrings. Respect `valid_from`, `valid_to`, `reference_status`, and the row business date.
- Recognize by distinct canonical value, not raw alias count. Multiple matched aliases that resolve to the same canonical value are one recognized value.
- Zero active canonical matches means unrecognized. More than one distinct active canonical value means ambiguous. Both are quarantine conditions for fuel/freight answer rows.
- For reference-row decision panels, use:
  - `RB-42` for an active, effective, usable reference row.
  - `RB-17` for an inactive, expired, not-yet-effective, or otherwise non-usable time-bound reference row.
  - `RB-83` for a provisional reference row.

## Source And Ledger Codes

For fuel/freight source-retention panels:

- `SB-24`: retained logical row is from a certified, non-duplicate source occurrence.
- `SB-61`: retained logical row is the certified occurrence from a cross-snapshot duplicate.
- `SB-79`: retained logical row exists only in a provisional source occurrence.

For fuel/freight ledger-disposition panels:

- `LD-72`: valid recognized row, expected value matches recognized value.
- `LD-31`: valid recognized row, expected value differs from recognized value.
- `LD-14`: quarantined because no active alias resolves the description.
- `LD-88`: quarantined because aliases resolve the description to multiple distinct canonical values.
- `LD-53`: quarantined because a physical quantity or measure is nonpositive or otherwise invalid. Let invalid measure override mismatch handling.

## Fuel Audits

Use retained rows from `v_fuel_transactions`.

- Recognize `purchased_description` against fuel aliases to produce the actual `fuel_type`.
- Quarantine rows with nonpositive `quantity`, zero active canonical matches, or multiple distinct active canonical values.
- Convert volume with `v_unit_conversions` where `kind = 'volume'`; use the purchase date for effective dating.
- Convert spend to USD with the certified row in `v_fx_rates` for the purchase date and transaction currency. Use the table even for USD.
- `mismatch_transaction_ids` contains valid retained rows where `expected_fuel_type` differs from recognized `fuel_type`.
- The unrecognized/ambiguous ID list requested by fuel contracts contains every retained row with no unique recognized fuel type.
- Merchant exception rows count distinct retained logical transactions with either a valid mismatch or a quarantine condition. Rank by exception count descending, then merchant ID ascending unless the contract says otherwise.
- Focus-asset rollups count retained logical rows for requested assets and sum only valid rows.

## Freight Audits

Use retained rows from `v_freight_charges`.

- Recognize `description` against freight aliases to produce the actual `service_class`.
- Quarantine rows with nonpositive `billed_weight`, nonpositive `distance`, zero active canonical matches, or multiple distinct active canonical values.
- Break quarantine reasons into `unrecognized_alias`, `ambiguous_alias`, `invalid_weight`, and `invalid_distance` when requested. A row can be counted for the applicable reason family required by the contract; keep the logical charge ID unique in the quarantine ID list.
- Convert weight and distance with `v_unit_conversions` (`weight` and `distance`) using the service date.
- Convert spend to USD with the certified `v_fx_rates` row for the service date and currency.
- `class_mismatch_charge_ids` contains valid retained rows where `expected_service_class` differs from recognized `service_class`.
- Carrier ranking exposure is normalized USD from valid class mismatches only; quarantines increase quarantine/exception counts but do not add exposure. Rank by exposure descending, then carrier ID ascending when specified.

## Maintenance Audits

Use retained rows from `v_maintenance_events`.

- Source-decision code mapping:
  - `MS-12`: retained event is certified and has no cross-snapshot duplicate.
  - `MS-47`: retained event is the certified occurrence from a cross-snapshot duplicate.
  - `MS-86`: retained event exists only in a provisional occurrence.
- Reject hard-invalid retained events for missing timestamp, unparsable timestamp, nonpositive odometer, negative labor, or labor greater than 24 hours. Count hard-invalid issue types on retained logical events, not raw duplicate rows.
- Convert odometer readings with `v_unit_conversions` where `kind = 'odometer'`.
- Detect odometer regressions after removing hard-invalid events, sorted by asset and event time. A sequence-only regression is reported separately and is not included in `invalid_event_ids`.
- History-route code mapping:
  - `HR-33`: event remains in the corrected reliable history.
  - `HR-74`: event is hard-invalid and rejected.
  - `HR-19`: event is excluded from distance because it is a sequence-only odometer regression.
- Corrected distance is the sum by asset of last reliable odometer minus first reliable odometer after excluding hard-invalid events and regression events. Round to the requested precision.
- Asset risk rankings count hard-invalid rejections plus regression events by asset and apply the case-scope ranking keys.

## Contact Audits

Use `v_contacts`, source snapshots, and case-scope anchors/watchlists.

- Normalize email with Unicode NFKC, trim, and lowercase. Normalize phone to digits only. Blank email and blank phone mean no usable contact channel.
- Build canonical people by grouping high-confidence duplicate rows. Strong evidence includes shared `master_hint`, matching normalized email, matching phone with compatible name, and the source-system patterns in the collection. Do not merge generic/shared-helpdesk identifiers or conflicting names solely because a phone or email matches.
- Select the stable master/survivor row from the source row carrying the master hint or the identity/compliance source when present; otherwise use the strongest verified certified row.
- Apply field-level precedence rather than whole-row precedence when the contract asks for canonical fields:
  - Identity/compliance sources usually own master/contact/consent fields.
  - HR, portal, warranty, or dealer claim sources usually own display name and region/depot fields.
  - Use the answer contract's requested source-system fields to expose provenance.
- Quarantine source rows or canonical people with no usable email and no usable phone.
- For partner-style readiness, count active canonical entities with at least one usable email or phone as readiness-eligible; a channel is ready only when consent is granted.
- For field-service dispatchability, dispatchable means active, consent granted, and at least one usable canonical channel. Depot partitions should sum to total people: dispatchable, active blocked by consent, no usable contact, and inactive with usable contact.
- Sort member row IDs and quarantine row IDs lexicographically.

Contact control-code mapping:

- Identity: `IC-70` high-confidence merged same identity; `IC-25` single/distinct identity or weak shared-contact evidence that should not merge; `IC-90` contested identifier cluster; `IC-40` no usable-contact quarantine.
- Outreach: `OR-35` active, consent granted, usable channel; `OR-80` active with usable channel but consent not granted; `OR-60` no usable channel; `OR-15` inactive exclusion.
- Field provenance: `FP-55` multi-source field-level precedence applied; `FP-20` single-source or no override needed; `FP-75` unusable/quarantined field result.

## Status Decisions

- Use `case_scope.json` thresholds and action maps whenever present.
- Otherwise return `PASS`/`RELEASE` only when there are no unresolved mismatches, quarantines, contested identifiers, hard-invalid events, or regressions.
- Return `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS` when the task defines an exception threshold and the measured exception rate remains inside it.
- Return `HOLD`/`BLOCK_AND_REMEDIATE` when critical gates fail, such as any maintenance odometer regression gate, unresolved quarantine conditions, or contested identifier clusters requiring remediation.
