# Asteria Data Quality Hub Audit Workflow

## Hub Records

Use `/api/catalog/schema` to choose the logical view or REST endpoint:

- contacts: `/api/contacts`, view `v_contacts`
- fuel transactions: `/api/transactions/fuel`, view `v_fuel_transactions`
- freight charges: `/api/transactions/freight`, view `v_freight_charges`
- maintenance events: `/api/maintenance/events`, view `v_maintenance_events`
- source snapshots: `/api/source-snapshots`, view `v_source_snapshots`
- aliases: `/api/reference/aliases`, view `v_reference_aliases`
- unit conversions: `/api/reference/conversions`, view `v_unit_conversions`
- FX rates: `/api/reference/fx`, view `v_fx_rates`

For business collections, filter REST calls with `collection=<collection_id>`. For references, filter aliases with the business `domain`, conversions with `kind`, and FX with `currency` if useful. Do not assume a page-size above the returned `limit`; loop through offsets.

## Snapshot And Source Resolution

Load source snapshots for the collection and cutoff. Treat rows from snapshots after the business cutoff as out of scope unless the task explicitly says otherwise.

For transaction and maintenance families, group duplicate raw rows by the public logical ID (`transaction_id`, `charge_id`, or `event_id`). The retained row is the certified occurrence if present. If no certified occurrence exists, retain the provisional occurrence. If multiple occurrences have the same snapshot status, use the newest business update and then newest ingest time as tie-breakers.

Reusable source-basis codes:

- `SB-61`: retained logical record had both certified and provisional source evidence, with certified retained.
- `SB-24`: retained logical record was certified-only.
- `SB-79`: retained logical record was provisional-only.

Maintenance source codes follow the same retained-source pattern:

- `MS-47`: retained certified row from a duplicate certified/provisional group.
- `MS-12`: certified-only retained event.
- `MS-86`: provisional-only retained event.

## Reference Alias Decisions

Normalize descriptions by trimming, lowercasing, and matching alias text as whole meaningful phrases, not arbitrary substrings inside unrelated words. Apply reference validity as of the business date: `valid_from <= date`, `valid_to` empty or `date <= valid_to`, and `reference_status` must be active for normal use.

Reference-policy codes:

- `RB-42`: active, effective reference row that resolves to exactly one canonical value.
- `RB-17`: inactive, expired, not-yet-effective, or otherwise unusable reference row.
- `RB-83`: provisional or ambiguous reference evidence that should not be treated as an authoritative one-to-one rule.

For fuel and freight descriptions, a retained transaction is unrecognized when no active effective alias maps the description to one canonical value. It is ambiguous when multiple canonical values match. Include both unrecognized and ambiguous IDs in any "unrecognized" or quarantine set if the template defines that set broadly.

## Financial Normalization

For fuel, recognize the fuel type from effective fuel aliases and compare it with `expected_fuel_type`. Convert quantity to the canonical volume unit using conversion rows whose validity covers the business date. Convert spend to USD using the certified FX rate for the transaction date and currency; if the source currency is already USD, use 1.0.

For freight, recognize the service class from effective freight aliases and compare it with `expected_service_class`. Convert billed weight and distance to the canonical units from the case scope. Convert spend to USD using certified FX rates by service date.

Quarantine financial rows with unresolved class/category, ambiguous class/category, nonpositive physical quantity/weight/distance, or any task-specific invalid physical measure. Quarantined rows do not enter normalized totals. Valid mismatches do enter normalized totals and mismatch exposure rankings.

Ledger routing codes:

- `LD-72`: valid retained record with recognized class/category matching expected class/category.
- `LD-31`: valid retained record whose recognized class/category differs from the expected class/category.
- `LD-14`: quarantined because the description has no recognized class/category.
- `LD-88`: quarantined because the description maps to multiple class/category candidates.
- `LD-53`: quarantined because physical measures are invalid, such as nonpositive fuel quantity, billed weight, or distance.

Round normalized totals to the decimal places required by the answer template, usually two decimals for currency and physical quantities. Derive exception counts from distinct retained logical IDs, not raw duplicate rows.

## Contact Canonicalization And Readiness

Normalize email by Unicode NFKC, trimming, and lowercasing. Normalize phone to digits only. A usable contact channel is a nonempty normalized email or phone.

Build identity clusters as connected components using strong identifiers first: `master_hint`, normalized email, normalized phone, and stable source-record relationships. Do not merge solely on display name when stronger identifiers conflict. Mark shared helpdesk-style identifiers as contested when the same phone, hint, or operational identifier connects clearly different people.

Choose canonical fields by field-level source precedence, not by a single row for all fields. Typical patterns:

- Compliance or identity registry systems are strongest for stable IDs, canonical contact fields, consent, and verified contact values.
- HR-style systems are strongest for person names and depot/region assignment.
- Operational portals and dispatch systems are useful supporting evidence but lose ties to verified authoritative systems.
- Within the same source tier, prefer verified rows, then newest business update, then newest ingest time.

For partner-contact survivor or roster master IDs, choose the row representing the strongest retained identity source. Focus cluster member IDs must be unique and lexicographically sorted.

Readiness rules:

- Dispatchable or channel-ready: canonical person/entity is active, has at least one usable channel, and consent is granted.
- Blocked consent or not-ready: active with a usable channel but consent is not granted.
- Blocked no-contact or quarantine: no usable canonical channel.
- Blocked inactive or inactive exclusion: inactive person/entity with a usable channel.

Outreach codes:

- `OR-35`: active, usable channel, consent granted.
- `OR-80`: active, usable channel, consent not granted.
- `OR-60`: no usable contact channel.
- `OR-15`: inactive exclusion.

Identity codes:

- `IC-70`: same-person automatic merge with field-level precedence applied.
- `IC-25`: contested identifier that should not be automerged.
- `IC-40`: single quarantined/no-usable-contact identity outcome.
- `IC-90`: multi-row identity exception that is not a normal automatic merge, such as same-name/no-channel or same-name conflicting-channel evidence requested as an anchored case.

Field-provenance codes:

- `FP-55`: multiple sources contributed and field-level precedence selected canonical values.
- `FP-20`: single-source or retained-source evidence without quarantine.
- `FP-75`: quarantined/no-usable-contact provenance outcome.

## Maintenance Integrity

Deduplicate maintenance events by `event_id` and retain certified over provisional. Report every duplicate group with sorted snapshot IDs and the retained snapshot.

Reject events from corrected history metrics when they have missing or unparsable event time, invalid odometer, negative labor, or extreme labor. Count each issue independently if a row has multiple defects, but list each rejected event ID only once. Convert odometer readings to kilometers using conversion rows.

Odometer regression is a sequence issue, not a rejected-event condition by itself: after removing rejected events, sort events per asset by event time and identify readings lower than the previous reliable reading. Report regression asset IDs and event IDs sorted lexicographically unless the template says otherwise.

Corrected distance is the sum over assets of last reliable odometer reading minus first reliable odometer reading in the reconstructed period, rounded to the required precision.

History-route codes:

- `HR-33`: valid accepted maintenance history event with no sequence regression.
- `HR-19`: valid event that participates in an odometer-regression finding.
- `HR-74`: rejected event due to field validity failures.

## Certification And Status

Use status thresholds and action maps from `case_scope.json` when present. If the scope gives a direct gate for a defect class, apply it exactly. Otherwise, use the template and prompt wording: any unresolved quarantine, contested identifier, odometer regression, or close-blocking financial exception usually prevents a clean release. Always pair the status with the action or routing enum specified in the answer contract.
