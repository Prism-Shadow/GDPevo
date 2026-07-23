---
name: asteria-data-quality-reconciliation
description: Reconcile Asteria Fleet Data Quality Hub audit tasks that use environment_access.md, payloads/case_scope.json, and payloads/answer_template.json. Use for contact survivorship/readiness, fuel or freight ledger cleanup, maintenance history integrity, source-snapshot retention, alias/reference policy decisions, unit/FX normalization, quarantine/exception reporting, compact control-code panels, and strict JSON-only answer contracts.
---

# Asteria Data Quality Reconciliation

## Start Every Case

1. Read `environment_access.md`, `payloads/case_scope.json`, and `payloads/answer_template.json`.
2. Use only the hub endpoints listed in `environment_access.md`. Prefer authenticated `POST /api/query` for complete data; REST endpoints may be page-limited.
3. Query `v_source_snapshots`, the relevant domain view, `v_reference_aliases`, `v_unit_conversions`, and `v_fx_rates` as needed. Check `truncated`; if true, page explicitly with `limit`/`offset` or narrower queries.
4. Fill exactly the answer template: no extra keys, exact required names, numeric precision, sorted arrays, and JSON only.

Useful query pattern:

```bash
curl -sS -X POST "$GDPEVO_ENV_BASE_URL/api/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"select * from v_source_snapshots where collection_id = '\''<collection_id>'\'' order by snapshot_id"}'
```

## Source Retention

- Identify the authoritative snapshot from `v_source_snapshots`: use the `CERTIFIED` snapshot for the scoped collection/cutoff. Treat `PROVISIONAL` as fill evidence only when a logical record has no certified occurrence. Treat `STALE` as non-authoritative unless the prompt explicitly asks for stale coverage.
- For overlapping logical records, group by the public logical ID:
  - contacts: `row_id` is a source row, not the logical person ID; cluster separately.
  - fuel: `transaction_id`.
  - freight: `charge_id`.
  - maintenance: `event_id`.
- Retain the certified occurrence when present. Otherwise retain the latest non-stale occurrence by business update/ingest timestamp. Report duplicate groups from all raw occurrences, with snapshot IDs sorted lexicographically.
- `raw_row_count` is the in-scope source row count. `logical_*_count` is the count after grouping by logical ID. `duplicate_raw_count` is `raw rows - logical records` unless the contract defines a different duplicate measure.

## Alias Recognition

- Use aliases whose business date is within `valid_from` and `valid_to` when `valid_to` is present. Exclude `PROVISIONAL` aliases from automatic recognition. Closed `INACTIVE` aliases may still be historically applicable inside their valid interval.
- Match aliases case-insensitively with Unicode normalization and token boundaries. Do not let a shorter alias inside a longer matched alias create false ambiguity: keep the longest non-overlapping spans, then collect distinct canonical values.
- Classification:
  - zero recognized canonical values: unrecognized alias/class.
  - more than one distinct canonical value: ambiguous alias/class.
  - exactly one canonical value: recognized; compare it to the expected fuel type or service class for mismatch reporting.
- Count/report unrecognized and ambiguous records as quarantine/unrecognized where the contract says unresolved category/class cannot enter the ledger.

## Normalization

- Use `v_unit_conversions` by `kind` and effective date. Apply the factor to reach the requested canonical unit.
- Use only `CERTIFIED` FX rows from `v_fx_rates` for the transaction/service date and currency. USD spend is `amount * usd_per_unit`.
- Exclude quarantined records from normalized totals. Include valid category/class mismatches in normalized totals unless the prompt says otherwise.
- Round only final reported totals to the template precision, usually 2 decimal places for money, volume, weight, distance, and odometer-derived totals.

## Fuel Purchases

- Work on retained logical transactions from `v_fuel_transactions`.
- Quarantine a retained transaction when its recognized category is zero/ambiguous or quantity is missing/nonpositive.
- `unrecognized_transaction_ids` includes both zero-match and ambiguous-category transactions when the contract describes "no unique recognized category."
- Mismatches are retained transactions with exactly one recognized category different from `expected_fuel_type`; if the contract says valid mismatches, exclude quarantined transactions from the mismatch ID list.
- Normalized liters use `kind='volume'`; normalized spend uses certified FX on `date(purchased_at)`.
- Merchant exception ranking counts distinct retained transactions with a mismatch or quarantine condition. Sort by exception count descending, then merchant ID ascending.

## Freight Charges

- Work on retained logical charges from `v_freight_charges`.
- Quarantine a retained charge when service class is zero/ambiguous, billed weight is missing/nonpositive, or distance is missing/nonpositive.
- `class_mismatch_charge_ids` are valid recognized charges where recognized service class differs from `expected_service_class`.
- `quarantine_reason_counts` should partition quarantined logical charges into `ambiguous_alias`, `unrecognized_alias`, `invalid_weight`, and `invalid_distance`. Prefer alias reasons before physical-measure reasons only when a charge has multiple unresolved conditions; otherwise use the single observed condition.
- Normalize `billed_weight` with `kind='weight'`, `distance` with `kind='distance'`, and spend with certified FX on `service_date`.
- Carrier ranking exposure is normalized USD only from valid service-class mismatches. Sort by mismatch spend descending, then carrier ID ascending. `exception_count` is the union of valid mismatches and quarantines.

## Maintenance Events

- Work on retained logical events from `v_maintenance_events`; group duplicate occurrences by `event_id`.
- Reject events with missing timestamp, unparsable timestamp, negative/missing odometer, negative labor, or extreme labor. In the Asteria maintenance sets, extreme labor is the synthetic high outlier value around `120.0` hours; use a practical daily threshold such as `> 24` hours unless the prompt provides one.
- `issue_counts` count retained logical events by reason; a single event may increment multiple issue counts. `invalid_event_ids` is the sorted unique union of events rejected for field validity. Do not include sequence-only odometer regressions in `invalid_event_ids`.
- Convert odometers with `kind='odometer'`. For regression checks, sort valid events by `asset_id`, parsed event time, then event ID. A regression is an event whose odometer is lower than the previous reliable odometer for that asset; flag it and do not update the previous reliable odometer with the regressed reading.
- Corrected distance is the sum over assets of `last reliable odometer_km - first reliable odometer_km` in the reconstructed period. Exclude rejected field-invalid events and sequence regressions from reliable-distance endpoints.
- Asset risk rankings usually sort by rejected event count descending, then regression event count descending, then asset ID ascending, unless case scope overrides.

## Contact Survivorship And Readiness

- Normalize emails with Unicode NFKC, trim, and lowercase. Treat blank, `N/A`, `NA`, `none`, and `NULL` as unusable.
- Normalize phones by removing non-digits; treat blank placeholders as unusable. For North American numbers with a leading `1` country code, compare on the last 10 digits when identifying duplicates, but report the canonical phone as digits only from the selected source value.
- Build person clusters from strong identifiers:
  - Merge rows sharing a normalized usable email.
  - Merge rows sharing a usable phone only when the phone is not a shared/helpdesk-style identifier across multiple distinct names/emails.
  - Do not merge on name alone, noisy/shared `master_hint`, or a phone shared by many different people. Report those as contested/no-automerge when requested.
- Quarantine source rows with no usable email and no usable phone.
- Choose canonical fields by field-level precedence: prefer verified/certified evidence, majority-agreeing values, authoritative identity/compliance sources, then latest business update. Preserve Unicode; normalize display casing only when needed. Report the source system that supplied each canonical field.
- A contact/person is dispatchable or readiness-eligible only when active and retaining at least one usable email or phone. A channel is ready only when consent is `GRANTED`.
- Readiness partitions:
  - `both`: active, consent granted, usable email and phone.
  - `email_only`: active, consent granted, usable email only.
  - `phone_only`: active, consent granted, usable phone only.
  - `not_ready`: active with usable contact but non-granted consent.
  - Inactive people are not readiness-eligible; report them in inactive exclusions or blocked inactive counts when required.

## Compact Code Semantics

Use these reusable mappings unless the current hub evidence clearly contradicts them:

- Reference policy: `RB-83` active/effective authoritative alias; `RB-42` inactive, superseded, future, or otherwise not effective for the business date; `RB-17` provisional/untrusted reference row.
- Source basis/retention: `SB-79` certified singleton retained; `SB-61` duplicate overlap retained from certified over lower-trust occurrence; `SB-24` provisional-only fill retained.
- Ledger disposition: `LD-14` valid match/accrue; `LD-31` valid mismatch/review; `LD-53` unrecognized alias/class quarantine; `LD-72` ambiguous alias/class quarantine; `LD-88` invalid physical measure or quantity quarantine.
- Maintenance source: `MS-86` certified singleton retained; `MS-47` duplicate overlap retained from certified; `MS-12` provisional-only retained.
- Maintenance history route: `HR-74` accepted reliable history event; `HR-33` sequence-only odometer regression; `HR-19` rejected for invalid field values.
- Identity controls: `IC-90` high-confidence automerged identity cluster; `IC-70` unique usable single-source identity; `IC-40` weak/no-identifier or name-only evidence not automerged; `IC-25` contested shared identifier/no automerge.
- Outreach controls: `OR-80` active, consent granted, both email and phone ready; `OR-60` active, consent granted, exactly one channel ready; `OR-35` usable channel but blocked by non-granted consent; `OR-15` no usable outreach path or inactive exclusion.
- Field provenance controls: `FP-75` multi-source field-level precedence applied; `FP-55` accepted single-source field provenance; `FP-20` poor/unusable/quarantined field provenance.

## Status Decisions

- Apply explicit thresholds, action maps, or certification gates from `case_scope.json` first.
- If no explicit map exists: `PASS` only when there are no exceptions; `PASS_WITH_EXCEPTIONS` when only reviewable valid mismatches remain; `HOLD` when quarantines, rejected invalid records, unresolved identifiers, or explicit gate failures remain.
- Use the exact action/routing enum paired with the chosen status: release for pass, review for pass-with-exceptions, block/remediate for hold.

## Final Checks

- Recompute summary counts from the same retained population used for detail arrays.
- Confirm partition counts sum where the template says they must.
- Sort every ID list and ranked array exactly as specified by the answer contract.
- Validate JSON parseability and, when practical, validate against the provided JSON Schema or field contract before returning.
