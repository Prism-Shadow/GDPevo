---
name: asteria-fleet-dq-audit
description: Solve Asteria Fleet Data Quality Hub reconciliation tasks for contacts, fuel, freight, and maintenance collections.
---

# Asteria Fleet DQ Audit

Use this skill when a task asks for an Asteria Fleet Data Quality Hub audit, reconciliation, certification, close, readiness brief, or decision panel. The task usually supplies a `payloads/case_scope.json`, an `answer_template.json`, a `<TASK_ENV_BASE_URL>`, and sometimes `environment_access.md`.

Return only the JSON object requested by the answer template. Do not include Markdown or commentary in the answer.

## Hub Access

1. Read `payloads/case_scope.json` and `payloads/answer_template.json` first.
2. Read `environment_access.md` only for the base URL and any credentials.
3. Fetch `/api/catalog/collections`, `/api/catalog/schema`, and `/api/source-snapshots?collection=<collection_id>`.
4. Use the family-specific endpoint with fixed pagination. These endpoints accept `collection=<collection_id>` and `offset=<n>`; page size is normally 100 and returned as `limit`.
   - Contacts: `/api/contacts`
   - Fuel: `/api/transactions/fuel`
   - Freight: `/api/transactions/freight`
   - Maintenance: `/api/maintenance/events`
5. For reference data, use:
   - Aliases: `/api/reference/aliases?domain=fuel` or `domain=freight`
   - Unit conversions: `/api/reference/conversions?kind=volume`, `kind=weight`, or `kind=distance`
   - FX: `/api/reference/fx?date=YYYY-MM-DD`
6. `/api/query` is optional. If it requires credentials that are not supplied, use the REST endpoints above.

Choose the authoritative snapshot as the in-scope `CERTIFIED` snapshot for the collection. If a logical record appears in more than one snapshot, retain the row from the authoritative snapshot; otherwise retain the only available row.

## Shared Normalization

Sort every stable-ID list lexicographically unless the template or case scope says otherwise. Sort ranked arrays by the stated rank policy and include explicit `rank` fields when requested.

Normalize email with Unicode NFKC, trim, lowercase, and reject blank placeholders such as `N/A`, `none`, and `NULL`. Normalize phone values to digits only and reject empty or placeholder values.

For money, multiply by the certified FX rate for the business date and currency, round each retained row's USD amount to cents, then sum and round final totals to 2 decimals. Use the FX endpoint even for USD if it supplies a certified USD row.

For physical units, multiply by the unit-conversion factor, round each retained row's normalized measure to the conversion row's `precision`, then sum and round requested output totals to the template precision.

For alias recognition in fuel and freight:
1. Keep only reference aliases with `reference_status == ACTIVE` and whose `valid_from`/`valid_to` range contains the transaction or service date.
2. Match alias text case-insensitively with alphanumeric word boundaries.
3. When multiple matched aliases overlap, discard shorter aliases contained in a longer matched alias before deciding the canonical class.
4. Zero canonical classes is an unrecognized alias. More than one canonical class is ambiguous. Exactly one canonical class is recognized.

Reference policy codes:
- `RB-42`: active and effective reference row.
- `RB-17`: inactive, expired, or not yet effective row.
- `RB-83`: provisional reference row.

Source-basis/source-retention codes for fuel and freight transaction or charge panels:
- `SB-61`: duplicate logical ID retained from the authoritative snapshot.
- `SB-24`: single retained row from the authoritative/certified snapshot.
- `SB-79`: single retained row from a non-authoritative/provisional snapshot.

Ledger disposition/routing codes for fuel and freight:
- `LD-72`: valid recognized class and expected class matches.
- `LD-31`: valid recognized class and expected class differs.
- `LD-14`: quarantined because no active/effective alias uniquely recognizes the description.
- `LD-88`: quarantined because active/effective aliases recognize more than one canonical class.
- `LD-53`: quarantined because a required physical measure is invalid. This takes precedence over alias and mismatch states.

## Contacts

Use contact rules for partner onboarding, field-service roster, dealer, warranty, or similar contact-master tasks.

Entity resolution:
- Auto-merge rows with the same usable normalized email.
- Auto-merge rows with the same usable phone only when the normalized person or organization name also matches.
- Do not auto-merge no-contact rows.
- Do not auto-merge a shared phone or shared `master_hint` when names/emails identify different people; report these as contested when requested.
- A duplicate cluster is a canonical entity with more than one source row.
- Quarantine rows are source rows with no usable email and no usable phone.

Canonical contact fields:
- The survivor/master row is the cluster row with a non-null `master_hint` when one exists; otherwise use the retained/best row by source authority, recency, then stable ID.
- For contact value fields, prefer the survivor row's usable email/phone, then the best usable value in the cluster.
- For field-service style rosters, display name and depot/region usually come from the directory-like source, while contact and consent usually come from the identity/master source.
- For partner-style contact certification, city and city source usually come from the compliance/master source.
- Preserve Unicode display names; normalize emails and phone digits only.

Readiness:
- A canonical entity is readiness-eligible only when active and it retains at least one usable email or phone.
- A channel is ready only when consent is `GRANTED`.
- Partition eligible entities into `both`, `email_only`, `phone_only`, and `not_ready`.
- For dispatchable rosters, dispatchable means active, at least one usable canonical channel, and granted consent.
- Readiness-by-depot partitions must sum to each depot's total canonical person count: dispatchable, blocked consent, blocked no contact, and blocked inactive.

Contact control codes:
- Identity: `IC-70` duplicate auto-merge; `IC-25` contested/shared identifier not automerged; `IC-40` no usable contact identity quarantine; `IC-90` unresolved potential identity collision across evidence rows.
- Outreach: `OR-35` consent granted and usable channel; `OR-80` usable channel but consent not granted or contested; `OR-60` no usable channel; `OR-15` inactive exclusion with a usable channel.
- Field provenance: `FP-55` field-level precedence/merge applied; `FP-20` single-source or no field-precedence conflict; `FP-75` quarantine/no usable field provenance.

Certification:
- If the case scope supplies quarantine-rate thresholds, compute `quarantine_rate = quarantined_rows / canonical_entities` rounded to 4 decimals and map the resulting status through `status_action_map`.
- If a roster has any contested identifier clusters and no explicit threshold overrides that, use `HOLD` and `BLOCK_AND_REMEDIATE`.

## Fuel Purchases

Retain one row per `transaction_id`. Counts:
- `raw_row_count`: all in-scope source rows.
- `logical_transaction_count`: distinct transaction IDs.
- `duplicate_raw_count`: raw rows minus logical transactions.
- `valid_transaction_count`: retained logical transactions not quarantined.
- `mismatch_count`: valid transactions whose recognized fuel type differs from `expected_fuel_type`.
- `unrecognized_count`: retained logical transactions with zero recognized classes.
- `ambiguous_count`: retained logical transactions with multiple recognized classes.
- `invalid_quantity_count`: retained logical transactions with missing, nonpositive, or nonconvertible quantity.
- `exception_transaction_count`: distinct mismatch or quarantined logical transactions.

Quarantine excludes rows from normalized totals. Valid mismatches stay in normalized totals under the recognized fuel type. Merchant exception ranking is ordered by exception count descending, then merchant ID ascending; count each logical transaction once.

Normalize volume to liters with `kind=volume`. Normalize spend to USD with certified FX for `purchased_at` date.

Reconciliation status without explicit thresholds: use `HOLD`/`BLOCK_AND_REMEDIATE` when any unresolved alias or invalid quantity exists; use `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS` for mismatches only; use `PASS`/`RELEASE` for no exceptions.

## Freight Charges

Retain one row per `charge_id`. Counts:
- `raw_row_count`: all in-scope source rows.
- `logical_charge_count`: distinct charge IDs.
- `duplicate_raw_count`: raw rows minus logical charges.
- `valid_charge_count`: retained logical charges not quarantined.
- `mismatch_count`: valid charges whose recognized service class differs from `expected_service_class`.
- `quarantine_count`: retained charges with unresolved class, nonpositive weight, or nonpositive distance.
- `quarantine_reason_counts`: count ambiguous alias, unrecognized alias, invalid weight, and invalid distance independently.

Duplicate groups include every charge ID with multiple raw occurrences, sorted by charge ID, with sorted unique `snapshot_ids` and the retained snapshot ID.

Quarantine excludes rows from normalized totals. Valid class mismatches stay in normalized totals under the recognized service class. Carrier ranking uses USD exposure from valid mismatches only, sorted by mismatch spend descending and carrier ID ascending; exception count is mismatch plus quarantine count.

Normalize billed weight with `kind=weight`, distance with `kind=distance`, and spend with certified FX for `service_date`.

Close status without explicit thresholds: use `HOLD`/`BLOCK_AND_REMEDIATE` when any unresolved class or invalid physical measure exists; use `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS` for mismatches only; use `PASS`/`RELEASE` for no exceptions.

## Maintenance Events

Use maintenance rules for maintenance-log integrity certification tasks.

Retain one row per `event_id`. Duplicate groups are event IDs appearing in multiple snapshots; list sorted snapshot IDs and the retained event/snapshot IDs.

Issue counts:
- `missing_timestamp`: blank or null `event_time_raw`.
- `invalid_timestamp`: unparsable nonblank `event_time_raw`.
- `invalid_odometer`: missing or negative odometer value.
- `negative_labor`: missing or negative labor hours.
- `extreme_labor`: labor hours greater than 24.
- `odometer_regression`: sequence-only events where a retained, otherwise valid event's normalized odometer is lower than the previous reliable odometer for that asset.

Rejected invalid event IDs are the unique retained event IDs with missing/unparsable time, invalid odometer, negative labor, or extreme labor, sorted lexicographically. Sequence-only regressions are not part of `invalid_event_ids`; report them separately in corrected metrics.

Corrected metrics:
- Start from retained logical events.
- Drop rejected invalid events.
- Convert odometers to kilometers using `kind=distance` conversion precision.
- Per asset, sort by event time and event ID. Mark regression events when the normalized odometer decreases from the previous reliable value.
- `valid_event_count` is logical events minus rejected invalid events minus regression events.
- `total_distance_km` is the sum across assets of the last reliable normalized odometer minus the first reliable normalized odometer, rounded to the requested precision.
- `regression_asset_ids` and `regression_event_ids` are sorted lexicographically.

Maintenance source codes:
- `MS-47`: duplicate event retained from the authoritative snapshot.
- `MS-12`: single retained event from the authoritative/certified snapshot.
- `MS-86`: single retained event from a non-authoritative/provisional snapshot.

History route codes:
- `HR-33`: accepted into corrected history.
- `HR-74`: rejected because of invalid timestamp, odometer, or labor evidence.
- `HR-19`: sequence-only odometer regression.

Asset risk ranking uses the case-scope policy: usually rejected event count descending, then regression count descending, then asset ID ascending.

Certification status follows explicit gates in `case_scope.json`. In the observed pattern, any odometer regression triggers the configured hold/block action.

## Final Validation

Before returning, validate the object against the template contract manually:
- No extra top-level or nested keys when `additionalProperties` or the template contract forbids them.
- Required arrays have exactly the requested scoped IDs and ordering.
- Counts reconcile against the retained logical records and partitions.
- Numeric values use the requested precision as JSON numbers, not strings.
- Final status/action keys use the exact names required by the template, such as `action`, `next_action`, or `routing`.
