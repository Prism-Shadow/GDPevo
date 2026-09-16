---
name: asteria-hub-audit
description: Solve Asteria Fleet Data Quality Hub certification and reconciliation tasks that ask for strict JSON answers from contact, fuel, freight, or maintenance collections. Use this when a prompt mentions Asteria Fleet, the shared Data Quality Hub, overlapping source snapshots, canonical contacts, fuel/freight normalization, maintenance-history integrity, opaque control codes, or an answer_template.json contract.
---

# Asteria Hub Audit

Use this skill to produce contract-shaped JSON for Asteria Fleet Data Quality Hub tasks. The common pattern is: read the scoped payloads, fetch all rows for the named collection, retain the authoritative logical record across snapshots, compute exceptions and normalized aggregates, then emit only the JSON object requested by `payloads/answer_template.json`.

## Quick Start

Run the bundled helper for a first-pass answer:

```bash
python /work/skill/scripts/asteria_hub_audit.py \
  --task-dir /path/to/task/input \
  --env /path/to/environment_access.md \
  --pretty
```

The task directory is the one containing `prompt.txt` and `payloads/`. The helper supports the observed contact, fuel, freight, and maintenance audit families. Treat its output as a computed draft: compare it to `answer_template.json`, check ordering and precision, and manually inspect any field the prompt emphasizes.

## Hub Access

Read `environment_access.md` for `base_url`. For row endpoints, use the public GET API with these filters:

- Contacts: `/api/contacts?collection=<collection_id>&offset=<n>`
- Fuel: `/api/transactions/fuel?collection=<collection_id>&offset=<n>`
- Freight: `/api/transactions/freight?collection=<collection_id>&offset=<n>`
- Maintenance: `/api/maintenance/events?collection=<collection_id>&offset=<n>`
- Snapshots: `/api/source-snapshots?collection=<collection_id>&offset=<n>`
- Reference aliases: `/api/reference/aliases?domain=fuel|freight`
- Unit conversions: `/api/reference/conversions?kind=volume|weight|distance`
- FX rates: `/api/reference/fx?offset=<n>`

Each response is paged with `items`, `total`, `limit`, and `offset`; fetch until `len(items_seen) == total`. Use `/api/catalog/schema` to confirm view fields. Do not assume `limit` or `collection_id` query parameters work on row endpoints; the portable filter is `collection`.

## Common Reconciliation Rules

Pick the authoritative snapshot from `/api/source-snapshots`: prefer `snapshot_status == "CERTIFIED"` for the scoped collection. Collapse raw rows by the public stable ID (`row_id` clusters for contacts after identity resolution, `transaction_id`, `charge_id`, or `event_id`). For duplicate transaction, charge, or event IDs, retain the authoritative/certified occurrence and report the duplicate group when the contract asks for it.

Keep all stable-ID arrays sorted exactly as the schema says. Use the answer template as the source of required keys, enum values, array lengths, and numeric precision. Return JSON only.

## Contact Audits

Normalize email with Unicode NFKC, trim, and lowercase. Normalize phone to digits only. Merge contact rows when they share a normalized email, or when they share both phone digits and normalized name. Do not merge on phone or `master_hint` alone; shared helpdesk numbers can indicate contested evidence rather than one person.

For canonical contact fields:

- Choose the master/survivor row from the row with `master_hint` when present, then by authoritative contact-source priority.
- Prefer `Identity Registry` or `Compliance Master` for email, phone, and consent.
- Prefer HR/portal/claims sources for display name; preserve Unicode and normalize casing.
- Prefer HR or Compliance sources for city/region/depot fields.
- Quarantine source rows with no usable email and no usable phone.

Readiness partitions are canonical-person partitions:

- Dispatchable/ready: active, has a usable channel, and consent is `GRANTED`.
- Blocked consent/not_ready: active, has a usable channel, but consent is not granted.
- Blocked no contact: no usable canonical channel.
- Blocked inactive: inactive with a usable channel.

Contact control codes:

- `IC-70`: durable duplicate cluster was auto-merged.
- `IC-40`: single no-contact quarantine identity.
- `IC-90`: contested same-name/no-durable-identifier evidence or conflicting multi-row identity evidence.
- `IC-25`: normal single-source or distinct-person evidence that should not auto-merge.
- `OR-35`: dispatchable/ready.
- `OR-80`: usable channel but blocked by consent.
- `OR-60`: no usable contact.
- `OR-15`: inactive exclusion.
- `FP-55`: field-level precedence was applied across merged rows.
- `FP-75`: no usable field provenance because the row is quarantined.
- `FP-20`: ordinary single-source field provenance.

## Fuel And Freight

Use reference aliases effective on the business date of each row. Only `ACTIVE` aliases whose `valid_from`/`valid_to` cover the row date participate in recognition. Match aliases case-insensitively with word boundaries; then discard shorter matches that overlap a longer matched phrase so `bio diesel` is not also classified as plain `diesel`. A row is:

- Zero-match quarantine when no active effective alias matches.
- Ambiguous quarantine when matches produce more than one canonical value.
- Physical quarantine when quantity, billed weight, or distance is nonpositive.
- Valid mismatch when it has exactly one recognized class and that class differs from the expected class.

Exclude quarantined rows from normalized totals. Include valid mismatches in totals. Convert units per `/api/reference/conversions`, rounding each converted measure to the conversion row's `precision` before aggregation. Convert spend with the certified FX rate for the row date and round each row's USD spend to cents before aggregation.

Fuel/freight codes:

- Reference policy: `RB-42` active and effective, `RB-17` inactive or not effective at cutoff, `RB-83` provisional.
- Source basis/retention: `SB-61` retained from a duplicate raw group, `SB-24` single certified row, `SB-79` single non-certified row.
- Ledger route/disposition: `LD-53` invalid physical measure, `LD-14` zero-match alias, `LD-88` ambiguous alias, `LD-31` valid mismatch, `LD-72` valid match.

For fuel merchant rankings, sort by exception count descending, then merchant ID ascending. For freight carrier rankings, sort by valid mismatch USD exposure descending, then carrier ID ascending; quarantined charges count as exceptions but do not add exposure.

## Maintenance

Deduplicate by `event_id`, retaining the authoritative/certified event. Field rejects are:

- Missing timestamp.
- Unparseable timestamp.
- Nonpositive odometer.
- Negative labor hours.
- Labor hours greater than 24.

After removing field rejects, convert odometers to km and sort events by asset, event time, then event ID. Mark an event as an odometer regression when its converted odometer is lower than the previous reliable reading for that asset; exclude regression events from `valid_event_count`.

Maintenance codes:

- Source: `MS-47` duplicate retained from multiple snapshots, `MS-12` single certified row, `MS-86` single non-certified row.
- History route: `HR-74` field reject, `HR-19` odometer regression, `HR-33` accepted history row.

For asset risk rankings, `rejected_event_count` includes both field rejects and sequence regressions; sort by rejected count descending, regression count descending, then asset ID ascending.

Manually verify `corrected_metrics.total_distance_km`. The reusable calculation is the sum by asset of last reliable converted odometer minus first reliable converted odometer, rounded to two decimals. This is the one aggregate most sensitive to legacy conversion and rounding choices, so inspect it before finalizing maintenance answers.
