# Asteria Reconciliation Rules

Use these rules for Asteria Fleet Data Quality Hub tasks. They are reusable patterns inferred from the staged examples; always let the live task data and output template control exact fields, IDs, limits, and ordering.

## Shared Data Handling

- Scope records to the requested `collection_id` and business cutoff or period from `case_scope.json`.
- Read collection snapshots and prefer a `CERTIFIED` snapshot when resolving overlapping raw occurrences. Do not discard provisional-only logical records just because a certified snapshot exists.
- Group raw rows by the public logical ID for transaction, charge, and maintenance tasks:
  - fuel: `transaction_id`
  - freight: `charge_id`
  - maintenance: `event_id`
- For a duplicate logical group, retain the certified occurrence if present. If no certified occurrence exists, retain the single or best provisional occurrence. If a tie remains, use latest `business_updated_at`, then latest `ingested_at`, then lexicographic snapshot ID.
- Report raw counts from all scoped rows. Report logical counts from retained logical groups. Duplicate raw count is `raw_row_count - logical_count`.
- Sort all stable-ID arrays lexicographically unless the contract specifies a rank or panel order.

## Reference Matching

Use active, in-window reference rows for classification:

- A reference row is eligible only when `reference_status == "ACTIVE"`, `valid_from <= business_date`, and `valid_to` is absent or `business_date <= valid_to`.
- Normalize descriptions and alias text case-insensitively. Match aliases as phrases or token-boundary words, not as arbitrary substrings inside longer words.
- If all matched eligible aliases point to one canonical value, the record is recognized as that value.
- If no eligible alias matches, it is unrecognized.
- If eligible aliases match more than one canonical value, it is ambiguous.
- Active rows not yet valid or inactive rows are not usable for classification. Provisional reference rows are not usable for classification.

Reference policy codes:

- `RB-42`: active and valid reference row.
- `RB-17`: inactive, expired, or not-yet-valid reference row at the business cutoff.
- `RB-83`: provisional reference row.

## Source and Ledger Codes

Source basis codes for fuel and freight panels:

- `SB-61`: duplicate logical record retained from the certified authoritative snapshot.
- `SB-24`: single retained certified record.
- `SB-79`: retained provisional-only record.

Ledger disposition codes:

- `LD-72`: valid recognized record whose recognized category or class matches the expected value.
- `LD-31`: valid recognized record whose recognized category or class differs from the expected value.
- `LD-14`: quarantined because the description has no eligible alias match.
- `LD-88`: quarantined because the description has eligible aliases for multiple canonical values.
- `LD-53`: quarantined because a required physical quantity, weight, or distance is nonpositive or otherwise invalid.

Apply ledger disposition precedence in this order: invalid physical measure, unrecognized alias, ambiguous alias, valid mismatch, valid match.

## Fuel Audits

- Match `purchased_description` against `domain=fuel` aliases using the purchase date.
- Quarantine a retained logical transaction if it has no unique recognized fuel type or if `quantity <= 0`.
- `unrecognized_transaction_ids` includes both zero-match and ambiguous fuel descriptions. It does not include a physical-measure-only quarantine when the fuel type is recognized.
- Valid transactions exclude all quarantined transactions. Valid mismatches remain valid and enter normalized totals.
- Normalize volume with `kind=volume` conversion factors into liters.
- Convert spend with certified FX for the transaction date and source currency. Multiply `amount * usd_per_unit`.
- Aggregate fuel totals by recognized fuel type, sorted ascending by `fuel_type`.
- Merchant exception counts are distinct retained logical transactions with either a valid expected-versus-recognized mismatch or a quarantine condition. Rank by `exception_count` descending, then `merchant_id` ascending.

## Freight Audits

- Match `description` against `domain=freight` aliases using the service date.
- Quarantine a retained logical charge if the service class is unrecognized or ambiguous, `billed_weight <= 0`, or `distance <= 0`.
- Quarantine reason counts are mutually exclusive. Use physical-measure reasons for invalid weight or distance; use alias reasons only when physical measures are valid.
- Valid charges exclude quarantines. Valid class mismatches remain valid and enter normalized totals.
- Normalize weight with `kind=weight` factors into kilograms and distance with `kind=distance` factors into kilometers.
- Convert spend with certified FX for the service date and source currency.
- Aggregate service-class totals by recognized service class, sorted ascending.
- Carrier ranking exposure is normalized USD spend on valid mismatched charges only. Rank by mismatch exposure descending, then `carrier_id` ascending. `exception_count` is valid mismatches plus quarantines.

## Maintenance Audits

- Retain duplicate maintenance events with the shared snapshot rule. Duplicate groups report all snapshot IDs sorted lexicographically and the retained snapshot ID.
- Maintenance source codes mirror source retention:
  - `MS-47`: duplicate event retained from the certified authoritative snapshot.
  - `MS-12`: single retained certified event.
  - `MS-86`: retained provisional-only event.
- Reject an event for missing timestamp, unparsable timestamp, invalid odometer, negative labor, or extreme labor. Keep separate issue counts by reason.
- Treat sequence-only odometer regressions separately from invalid events: they are not part of `invalid_event_ids`, but they are listed in regression arrays and excluded from corrected history metrics.
- History route codes:
  - `HR-33`: event is accepted into corrected history.
  - `HR-19`: event is excluded as an odometer regression.
  - `HR-74`: event is rejected for intrinsic invalidity.
- Reconstruct corrected distance by asset after filtering intrinsic invalids and regression events: sort reliable retained events by parsed event time, convert odometers to the requested unit, and sum `last_reliable - first_reliable` per asset.
- Asset risk ranking counts rejected invalid events and regression events per asset, then applies the sort policy in `case_scope.json`.

## Contact and Roster Reconciliation

Normalize for matching:

- Email: Unicode NFKC, trim, lowercase. Blank, `n/a`, `none`, `null`, and missing values are unusable.
- Phone: strip to digits. Placeholder strings and empty digit strings are unusable.
- Names: Unicode NFKC, trim, collapse spaces, compare case-insensitively for matching; preserve source spelling for canonical display when required.

Resolve people with union-find style clustering:

- Merge rows that share a strong usable email, phone, or explicit `master_hint`.
- Treat rows with no usable email or phone as quarantined/no-contact rows unless a stronger task-specific identifier links them.
- Watchlist or control cases may describe contested identifier clusters. Do not automerge rows that share only a weak or contested identifier without a usable email, phone, or master hint.

Choose canonical fields with field-level precedence:

- Prefer source-of-record systems over operational feeds. Typical authoritative systems are `Identity Registry` or `Compliance Master` for master/contact/consent fields and `HR Directory` or `Compliance Master` for name, depot, city, and region fields.
- Prefer verified rows over unverified rows, then later `business_updated_at`, then later `ingested_at`.
- Use the selected row ID from the highest-precedence source as the survivor or master ID when the contract asks for one.

Readiness:

- A usable channel is a usable canonical email or phone.
- Dispatchable or ready means active, has at least one usable channel, and consent is `GRANTED`.
- Consent-blocked means active and has a usable channel but consent is not granted.
- No-contact means no usable canonical email or phone.
- Inactive-blocked means inactive with a usable channel.
- For channel partition outputs, keep buckets mutually exclusive: both ready channels, email only, phone only, and not ready.

Contact control codes:

- Identity:
  - `IC-70`: duplicate rows were confidently automerged into one canonical person or entity.
  - `IC-25`: single resolved identity or non-contested retained identity.
  - `IC-90`: contested identifier cluster or no-automerge identity conflict.
  - `IC-40`: quarantined identity with no usable contact basis.
- Outreach:
  - `OR-35`: active, usable channel, consent granted.
  - `OR-80`: active, usable channel, consent not granted or unknown.
  - `OR-60`: no usable contact channel.
  - `OR-15`: inactive exclusion.
- Field provenance:
  - `FP-55`: canonical result used field-level precedence across multiple sources.
  - `FP-20`: single-source or aligned-source result with no material precedence conflict.
  - `FP-75`: unreliable or quarantined field provenance.

## Status Decisions

- If `case_scope.json` provides thresholds and an action map, compute the status from those values exactly.
- Otherwise use the task's explicit gate if present.
- Use `HOLD` and the block/remediate action when unresolved quarantines, contested identifiers, regression gates, or required integrity failures remain.
- Use `PASS_WITH_EXCEPTIONS` only when the task explicitly allows release with bounded exceptions.
- Use `PASS` only when the relevant exception and quarantine counts are zero.
