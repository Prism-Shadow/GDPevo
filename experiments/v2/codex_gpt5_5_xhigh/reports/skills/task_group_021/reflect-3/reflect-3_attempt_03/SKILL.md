---
name: asteria-fleet-data-quality
description: Reconcile Asteria Fleet Data Quality Hub audit tasks and produce strict JSON answers from a task prompt, case scope, answer contract, source snapshots, aliases, conversions, FX, contacts, fuel/freight transactions, and maintenance events. Use when asked to certify or audit Asteria fleet contact readiness, partner/contact mastering, fuel or freight normalization, accrual/ledger routing, source-retention panels, or maintenance-history integrity.
---

# Asteria Fleet Data Quality

## Core Workflow

1. Read the prompt, `case_scope`, `answer_template`, and the supplied environment access file before querying data.
2. Use the catalog and schema to identify the relevant logical views, stable business keys, source-snapshot fields, reference rows, unit conversions, and FX fields.
3. Pull the complete in-scope dataset. Check pagination or truncation explicitly; do not rely on sample rows.
4. Resolve source snapshots before calculating business metrics:
   - Filter snapshots by the requested collection and cutoff/as-of period.
   - Prefer certified authoritative evidence for overlapping logical records.
   - When a logical record appears in multiple snapshots, retain the authoritative occurrence and report the duplicate group from all raw occurrences.
   - When a logical record exists only in a non-authoritative snapshot, keep it with a distinct source-basis disposition rather than dropping it silently.
5. Build the answer from the output contract, not from memory. Preserve required key names, enum values, ordering, uniqueness, numeric precision, and `additionalProperties` restrictions.
6. Validate all count partitions: raw vs logical vs duplicate rows, valid plus quarantined records, mutually exclusive readiness buckets, exception counts, and ranked limits.

## Contact Reconciliation

Normalize contact fields before clustering:

- Email: Unicode NFKC, trim, lowercase; treat blank, `n/a`, `null`, and `none` as unusable.
- Phone: treat blank/null placeholders as unusable, then keep digits only.
- Names: trim and collapse whitespace for comparison, but preserve the best display spelling in output.

Use strong identity evidence. Merge rows on exact usable email, stable source/master identifiers, or phone only when corroborated by the same person evidence and not a shared line. Do not merge on name alone. Treat shared service-desk/helpdesk numbers, unrelated emails, or weak name-only repeats as contested or separate people unless the task gives an explicit merge anchor.

For canonical fields, choose per field rather than selecting one whole-row survivor. Prefer source evidence by certified status, source reliability for that field, verified flags, and business recency. Keep the source-system provenance required by the contract for name, contact, city/depot, consent, or other canonical fields.

Readiness rules:

- A person/entity is dispatchable or channel-ready only when active, has at least one usable canonical email or phone, and consent is granted.
- Active records with usable contact but non-granted consent are blocked by consent.
- Active records with no usable channel are quarantined or blocked by no contact.
- Inactive records with usable channels are excluded/blocked as inactive, not counted as ready.
- Depot or region rollups are over canonical people/entities, including blocked or quarantined entities when the contract asks for total population.

Opaque contact-control codes should be inferred from anchored control cases and then applied consistently by control family:

- Identity states commonly distinguish confirmed multi-source identity, acceptable single-source identity, contested/shared identifiers, and no usable identity evidence.
- Outreach states commonly distinguish ready/granted outreach, pending/non-final consent, denied consent, and inactive/no-contact exclusion.
- Field-provenance states commonly distinguish field-level precedence across sources, verified/single-source provenance, and weak or unusable provenance.

Keep codes opaque; do not expand their names unless the task provides expansions.

## Fuel And Freight Audits

Group raw rows by the public logical transaction or charge ID. Retain one occurrence per logical ID using the snapshot rule, but keep all raw occurrences for duplicate reporting.

Recognize fuel types or freight service classes with reference aliases:

- Use aliases whose domain matches the task and whose validity window includes the business date.
- Prefer active reference rows for recognition. Treat inactive, future-effective, expired, or provisional aliases as policy decisions unless the task explicitly allows them for recognition.
- Match aliases case-insensitively with token boundaries. Avoid substring false positives such as an alias embedded inside a longer word.
- Multiple alias hits mapping to the same canonical value are a single recognized category/class.
- Zero canonical matches is unrecognized; more than one canonical value is ambiguous.

Quarantine logic:

- Fuel: quarantine unresolved category or nonpositive quantity.
- Freight: quarantine unresolved class, nonpositive billed weight, or nonpositive distance.
- Valid category/class mismatches are exceptions but still enter normalized totals.
- Quarantined records do not enter normalized physical or spend totals.

Normalization:

- Convert physical measures with the supplied unit conversion rows for the relevant kind.
- Convert spend using certified FX for the transaction/service date and source currency.
- Sum with full precision and round only final reported numeric fields to the contract precision.
- Produce one total row per required canonical category/class, sorted exactly as the contract says, even when a count is zero.

Rankings:

- Merchant exception rankings usually sort by exception count descending, then stable ID ascending.
- Carrier accrual rankings usually sort by valid mismatch spend descending, then carrier ID ascending.
- Count exceptions as distinct retained logical records, not raw duplicate rows.

Opaque fuel/freight decision codes should be assigned by evidence category, using the scoped decision panel to map allowed code values consistently:

- Reference policy: active and effective reference, inactive/expired/future reference, or provisional reference.
- Source retention: retained authoritative single occurrence, authoritative retained over duplicate occurrence, or non-authoritative-only occurrence.
- Ledger routing: valid matched record, valid mismatch, unresolved/ambiguous class/category, invalid physical measure, or other contract-specific exception state.

## Maintenance History Audits

Group maintenance rows by public event ID and retain one occurrence using the snapshot rule. Report every event ID that appears in multiple snapshots with all source snapshot IDs and the retained snapshot.

Hard invalid events include missing or unparsable event time, invalid odometer range, negative labor, and extreme labor according to task thresholds or clearly anomalous values. Sequence-only odometer regressions are not hard invalid unless the contract says so; report them separately in corrected metrics.

For corrected history:

- Parse event time and filter to the requested business period.
- Convert odometer readings to the canonical unit before comparisons.
- Sort valid events by asset, event time, then event ID.
- Flag an odometer regression when a reading decreases from the preceding reliable reading for the same asset.
- Compute total corrected distance as the sum over assets of last reliable odometer minus first reliable odometer.
- Rank asset risk by rejected event count, then regression count, then asset ID unless the scope gives a different sort.

Opaque maintenance codes should be mapped from retained source basis and history route:

- Source codes distinguish authoritative/certified events, provisional-only events, and duplicate-retained events.
- History-route codes distinguish accepted history, hard-rejected events, and sequence-only regression handling.

## Output Validation

Before returning JSON:

- Re-read the answer contract and ensure every required key is present and no extra keys are present.
- Sort every list by the stated stable-key ordering.
- Deduplicate every ID list after retaining logical records.
- Confirm totals reconcile with detail lists and count partitions.
- Confirm numeric precision after rounding.
- Confirm status/action pairs follow the scope thresholds or gate rules.
- Return only the JSON object.
