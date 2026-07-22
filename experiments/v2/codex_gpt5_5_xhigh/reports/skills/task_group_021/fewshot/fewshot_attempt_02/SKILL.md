---
name: asteria-dq-reconciliation
description: Reconcile Asteria Fleet Data Quality Hub audit and certification tasks. Use when Codex must answer JSON-only Asteria data-quality cases from prompt.txt, case_scope.json, answer_template.json, and environment_access.md for contact-master readiness, fuel ledger normalization, freight accrual close, or maintenance-history integrity using the hub catalog, schema, source snapshots, reference aliases, conversions, FX, and authenticated SQL query endpoint.
---

# Asteria DQ Reconciliation

## Required Workflow

1. Read the task prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`.
2. Use only the base URL, allowed endpoints, and bearer token from `environment_access.md`. Prefer `/api/query` for complete, paginated, and aggregate work.
3. Fetch `/api/catalog/schema` and `/api/catalog/collections` to confirm the family and logical view names.
4. Recompute every answer field from hub data. Do not infer from prior examples or reuse old row IDs, counts, totals, names, emails, cities, or rankings.
5. Build a local scratch calculation in Python or SQL for nontrivial counts. Hand-count only tiny decision panels.
6. Emit exactly one JSON object conforming to the supplied answer template. Preserve required names, numeric precision, uniqueness, and ordering rules.

Use `scripts/query_hub.py` if helpful:

```bash
python skill/scripts/query_hub.py --env environment_access.md "select * from v_source_snapshots limit 5"
```

The query API accepts JSON `{"query": "<SQL>"}` and returns `columns`, `rows`, `row_count`, and sometimes `truncated`. If `truncated` is true or a full row set is required, query with explicit `limit`/`offset` or push aggregation into SQL.

## Common Hub Rules

- Identify the view by collection family: contacts use `v_contacts`, fuel uses `v_fuel_transactions`, freight uses `v_freight_charges`, maintenance uses `v_maintenance_events`.
- Scope rows by `collection_id` and the case cutoff or business period. Use the task's named cutoff field (`business_cutoff`, `cutoff_at`, `as_of`) exactly in output fields when requested.
- Use `v_source_snapshots` to identify snapshots at the cutoff. For fuel, freight, and maintenance, the authoritative snapshot is the `CERTIFIED` snapshot for the collection and cutoff; its `snapshot_id`, `snapshot_status`, and `row_count` feed source-decision fields.
- Collapse overlapping raw rows into one logical record before business calculations:
  - Fuel: group by `transaction_id`.
  - Freight: group by `charge_id`.
  - Maintenance: group by `event_id`.
  - Retain `CERTIFIED` over `PROVISIONAL` over `STALE`; tie-break by latest `business_updated_at`, then latest `ingested_at`, then lexical snapshot ID.
- Report duplicate groups for logical IDs with more than one raw occurrence. Sort logical IDs ascending, sort snapshot IDs lexicographically, and set the retained snapshot from the retained row.
- Normalize text with Unicode NFKC, trim, and case-fold/lowercase. Treat null, empty strings, whitespace, and placeholders such as `N/A` as missing.
- Normalize phone numbers to digits only. Normalize emails to trimmed NFKC lowercase.
- Normalize money by multiplying `amount` by the `CERTIFIED` `v_fx_rates.usd_per_unit` for the transaction or service date and currency. Prefer the latest certified rate published on or before the cutoff if more than one applies.
- Normalize units by joining `v_unit_conversions` on conversion `kind`, source unit, canonical target unit, and business date validity. Round only at the final output precision requested by the template.
- Sort all stable-ID arrays lexicographically unless the template gives a different rule. Rank arrays use the task's primary sort and tie-breaks, then assign ranks after sorting.

## Reference Alias Recognition

Use `v_reference_aliases` for fuel and freight classification.

1. Filter by `domain` (`fuel` or `freight`), business date within `[valid_from, valid_to]`, and `reference_status = 'ACTIVE'` for operational recognition.
2. Match aliases against normalized descriptions as whole words or whole phrases, not arbitrary substrings. A description containing two aliases for the same canonical value is still uniquely recognized; aliases mapping to multiple canonical values are ambiguous.
3. Classify each retained row:
   - exactly one recognized canonical value: usable classification
   - zero recognized canonical values: unrecognized quarantine
   - more than one recognized canonical value: ambiguous quarantine
4. Compare the recognized value to `expected_fuel_type` or `expected_service_class` only after classification succeeds.

Reference decision codes:

- `RB-42`: active reference row that is valid for the relevant business date.
- `RB-17`: inactive, expired, or not-yet-valid reference row.
- `RB-83`: provisional reference row.

## Ledger and Accrual Codes

Source-basis codes for fuel and freight:

- `SB-24`: retained row is from a certified snapshot and has no cross-snapshot duplicate.
- `SB-79`: retained row is from a provisional snapshot and has no certified duplicate.
- `SB-61`: logical record has cross-snapshot duplicates and the retained row won by source priority.

Ledger-disposition codes:

- `LD-72`: valid recognized row with expected class/type matching recognized class/type.
- `LD-31`: valid recognized row with expected class/type different from recognized class/type.
- `LD-14`: no recognized active alias.
- `LD-88`: active aliases resolve to more than one canonical value.
- `LD-53`: invalid physical measure, such as nonpositive fuel quantity, billed weight, or distance.

## Fuel Audit Procedure

1. Retain one row per `transaction_id`.
2. Count raw rows, logical transactions, duplicate raw rows, valid rows, mismatches, unrecognized rows, ambiguous rows, invalid-quantity rows, and distinct exception transactions.
3. Quarantine retained rows with nonpositive/missing `quantity` or non-unique fuel recognition. Quarantined transactions do not enter normalized totals.
4. A valid mismatch is an unquarantined row where recognized fuel type differs from `expected_fuel_type`; include it in normalized totals.
5. Compute normalized liters and USD spend for valid rows, then totals by fuel type sorted by fuel type.
6. For merchant exception ranking, count distinct retained transactions with a mismatch or quarantine. Sort by exception count descending, then merchant ID ascending, and apply the requested limit.
7. For scoped transaction decisions, sort requested transaction IDs and assign `source_basis_code` plus `ledger_disposition_code`.
8. Set status/action from the task threshold or implied gate: no exceptions is `PASS`/`RELEASE`; tolerable exceptions are `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS`; blocking data-quality conditions are `HOLD`/`BLOCK_AND_REMEDIATE`.

## Freight Audit Procedure

1. Retain one row per `charge_id`.
2. Count raw rows, logical charges, duplicate raw rows, valid charges, class mismatches, quarantines, and quarantine reasons.
3. Quarantine retained charges with non-unique service-class recognition, nonpositive/missing billed weight, or nonpositive/missing distance. Quarantined charges do not enter normalized totals.
4. A valid mismatch is an unquarantined charge where recognized service class differs from `expected_service_class`; include it in normalized totals.
5. Compute normalized weight, distance, and USD spend for valid charges. Output one service-class total per class sorted ascending.
6. Carrier accrual exposure is USD spend on valid mismatches only. Rank carriers by mismatch exposure descending, then carrier ID ascending; include mismatch count, quarantine count, and exception count.
7. For decision panels, sort requested IDs and assign reference-row, source-retention, and ledger-routing codes from the shared code rules.
8. Use blocking close status when unresolved classes or invalid measures remain unless the case scope declares a different gate.

## Maintenance Integrity Procedure

1. Retain one row per `event_id`; include all scoped raw rows when reporting raw coverage.
2. Count logical duplicate groups before rejecting invalid events.
3. Reject retained events with any of:
   - missing timestamp
   - unparsable timestamp
   - timestamp outside the business period
   - missing, negative, or unconvertible odometer
   - negative labor hours
   - extreme labor hours greater than 24
4. Issue counts are counts of retained logical events meeting each predicate; an event may contribute to multiple issue counts. `invalid_event_ids` is the unique set rejected for any invalid predicate, sorted lexicographically.
5. Convert odometers to kilometers. On the remaining events, sort per asset by parsed event time, then event ID. An odometer lower than that asset's previous reliable reading is a sequence-only regression.
6. Exclude invalid events and regression events from corrected history metrics. Compute total distance as, for each asset, last reliable odometer minus first reliable odometer; sum across assets and round to the requested precision.
7. Rank assets by rejected invalid-event count, then regression-event count, then asset ID unless the case scope states another policy.

Maintenance decision codes:

- `MS-12`: retained event comes only from the certified snapshot.
- `MS-86`: retained event comes only from a provisional snapshot.
- `MS-47`: retained event is part of a cross-snapshot duplicate group.
- `HR-33`: accepted into corrected history.
- `HR-74`: rejected for invalid timestamp, odometer, or labor predicates.
- `HR-19`: sequence-only odometer regression.

## Contact Reconciliation Procedure

1. Normalize email, phone, and names before clustering. Use strong keys first: normalized email, trusted master hints that identify a person, and matching source-record stems. Use phone-only evidence only when names are compatible; shared service numbers or shared helpdesk hints are not enough to merge distinct names.
2. Keep rows with no usable email or phone as their own quarantined entities unless another strong key links them.
3. Select a stable survivor/master row from the cluster by trusted identity evidence: row with a person-specific `master_hint`, then authoritative identity/compliance source, then verified row, then latest `business_updated_at`, then latest `ingested_at`, then lexical row ID.
4. Select canonical fields at field level, not by copying the survivor blindly:
   - Names and depot/region fields usually come from the operational system of record such as HR, dealer, partner, warranty, or marketing source.
   - Contact and consent fields usually come from identity/compliance sources such as Identity Registry or Compliance Master.
   - When task output asks for source-system provenance, report the source system whose field value was used.
5. Readiness eligibility requires an active canonical record and at least one usable canonical email or phone. A channel is ready only when canonical consent is `GRANTED`.
6. Dispatchable contacts are active, have a usable canonical channel, and have granted consent. Contacts with usable channels but non-granted consent are consent-blocked; inactive contacts with usable channels are inactive exclusions; contacts with no usable channel are no-contact blocks.
7. Region/depot rollups count canonical entities, not raw rows. Duplicate cluster counts count multi-row clusters merged as one person.
8. For requested focus anchors, find the cluster containing the anchor row and output all member row IDs sorted lexicographically, the selected survivor/master, canonical field values, and the resolution outcome.
9. For identifier watchlists and anchored control cases, evaluate only the supplied evidence rows and apply the contact control-code meanings below.

Contact control codes:

- `IC-70`: strong same-entity evidence; auto-merge with field-level precedence.
- `IC-25`: single/distinct identity or shared-channel evidence that is insufficient for merging.
- `IC-90`: contested identifier evidence; do not auto-merge.
- `IC-40`: no usable contact identity; quarantine.
- `OR-35`: active, usable email or phone, and consent granted.
- `OR-80`: active and usable contact exists, but consent is not granted.
- `OR-60`: no usable email or phone.
- `OR-15`: inactive record excluded from outreach despite a usable channel.
- `FP-55`: field-level precedence applied across merged sources.
- `FP-20`: direct/single-source field provenance or contested evidence with no merge.
- `FP-75`: quarantine/no usable field provenance.

## Final Validation

- Validate JSON syntax with `python -m json.tool`.
- Check exact top-level keys and `additionalProperties` constraints from the answer template.
- Recheck all arrays for the specified ordering and uniqueness.
- Recompute summary counts from the same retained-row table used for detail lists; mismatched totals usually indicate a raw-vs-logical counting error.
- Avoid commentary or Markdown in the final answer when the task requests JSON only.
