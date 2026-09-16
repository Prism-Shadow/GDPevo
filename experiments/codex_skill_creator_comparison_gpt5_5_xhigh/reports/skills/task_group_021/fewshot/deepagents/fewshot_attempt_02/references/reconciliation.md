# Asteria Reconciliation Rules

Use this reference when the task asks for source survivor decisions, exception counts, normalized totals, or compact internal control codes.

## Hub Access

- Read `environment_access.md` for `base_url`.
- Page GET endpoints with `limit` and `offset`.
- Collection-scoped endpoints use `collection=<collection_id>`, not `collection_id`.
- Reference aliases use `domain=fuel` or `domain=freight`.
- Unit conversions use `kind=volume`, `kind=weight`, or `kind=distance`.
- Prefer the public GET endpoints. Use `/api/query` only when the environment explicitly supplies working query credentials.

## Source Retention

- For fuel, freight, and maintenance, group rows by the public logical ID (`transaction_id`, `charge_id`, or `event_id`).
- Retain the occurrence from the authoritative `CERTIFIED` snapshot when present.
- If no authoritative occurrence exists, retain a certified singleton; otherwise retain the latest available non-certified row.
- Report duplicate groups whenever a logical ID has multiple raw occurrences. Sort group IDs ascending and snapshot IDs lexicographically.
- Source-basis codes: `SB-61` duplicate retained from the authoritative snapshot; `SB-24` certified singleton; `SB-79` non-certified singleton.
- Maintenance-source codes: `MS-47` duplicate retained from the authoritative snapshot; `MS-12` certified singleton; `MS-86` non-certified singleton.

## Alias Classification

- Use only alias rows whose `reference_status` is `ACTIVE` and whose valid date window contains the transaction or charge business date.
- Match aliases case-insensitively after Unicode NFKC normalization.
- Match aliases as word/phrase tokens, not arbitrary substrings.
- Drop shorter matches contained inside longer matches before deciding ambiguity. This prevents phrases such as "premium unleaded" or "bio diesel" from also matching their shorter child aliases.
- A retained row is recognized only when the remaining matched aliases resolve to exactly one canonical value.
- Reference-policy codes: `RB-42` active and effective; `RB-17` inactive or outside the date window; `RB-83` provisional.

## Financial Ledgers

- Fuel quarantine reasons: unrecognized alias, ambiguous alias, or nonpositive/missing quantity.
- Freight quarantine reasons: unrecognized alias, ambiguous alias, nonpositive/missing billed weight, or nonpositive/missing distance.
- Valid rows exclude all quarantined logical rows. Valid category/class mismatches remain valid and must enter normalized totals.
- Mismatch means the recognized canonical value differs from the expected public field.
- Ledger-disposition codes: `LD-72` valid match; `LD-31` valid mismatch; `LD-14` unrecognized alias; `LD-88` ambiguous alias; `LD-53` invalid physical measure or quantity.
- Convert physical measures per row using the reference factor and round each converted row measure to the conversion row's `precision`.
- Convert spend per row by multiplying amount by the certified same-date FX rate and rounding the row USD amount to cents.
- Aggregate rounded row values, then round output totals to the precision requested by the answer contract.
- Carrier/merchant exception counts are distinct retained logical rows with a mismatch or quarantine condition.

## Contacts

- Normalize emails with Unicode NFKC, trimming and lowercasing.
- Normalize phones to digits only.
- Treat rows with no usable email and no usable phone as quarantine/no-contact rows; do not merge them by name alone.
- Merge duplicate contact rows by strong identifiers: equal normalized email, or equal phone digits plus equal normalized name. Do not merge by shared phone alone.
- Use field-level source precedence. Contact and consent fields usually favor Identity Registry or Compliance Master; name and depot/region fields usually favor the operational owner such as HR Directory, Dealer Portal, Partner Portal, or Warranty Claims. When the answer asks for field provenance, record the source used for each field.
- Dispatchable/ready requires an active canonical record, at least one usable channel, and granted consent.
- Outreach codes: `OR-35` dispatchable/ready; `OR-80` active with usable channel but consent not granted; `OR-60` no usable contact; `OR-15` inactive exclusion.
- Identity codes: `IC-70` auto-merged duplicate identity; `IC-25` retained singleton or weak/shared identifier not auto-merged; `IC-90` contested same-name or watchlist identity evidence that remains separate; `IC-40` no-contact quarantine identity.
- Field-provenance codes: `FP-55` field-level precedence over merged rows; `FP-20` single-source/no field merge; `FP-75` no-contact quarantine.

## Maintenance

- Reject retained events with missing/unparsable timestamps, nonpositive/missing odometer, negative labor hours, or extreme labor hours above 24.
- Count issue flags independently, but list invalid event IDs uniquely and sorted.
- After removing rejected events, sort each asset's events by timestamp then event ID. A current event whose odometer is lower than the prior event is a sequence-only odometer regression.
- Regression events are reported separately and excluded from corrected reliable-event counts and distance history; they are not included in invalid event IDs.
- Corrected distance is the sum over assets of last reliable odometer reading minus first reliable odometer reading, using kilometers.
- History-route codes: `HR-33` accepted into history; `HR-19` sequence-only odometer regression; `HR-74` rejected event.
- Asset risk ranking sorts by rejected count descending, then regression count descending, then asset ID ascending unless the case scope specifies otherwise.

## Certification

- Apply any explicit status/action thresholds from `case_scope.json`.
- When no threshold is supplied, any hard data-quality defect that blocks finance/history/release closure maps to `HOLD` and `BLOCK_AND_REMEDIATE`; otherwise use the task's stated pass/review mapping.
- Emit exactly the keys and ordering requested by `answer_template.json`; do not add diagnostics to the final JSON.
