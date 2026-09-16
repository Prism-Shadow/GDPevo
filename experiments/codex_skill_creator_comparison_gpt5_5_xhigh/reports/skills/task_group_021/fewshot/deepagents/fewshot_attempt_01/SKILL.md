---
name: asteria-fleet-data-quality
description: Reconcile Asteria Fleet Data Quality Hub collections and produce strict JSON audit or certification answers for contact readiness/contact mastering, fuel purchases, freight charges, and maintenance history. Use when a task mentions Asteria Fleet Data Quality Hub, source snapshots, answer_template.json, case_scope.json, contact control codes, fuel/freight normalization, maintenance integrity, or internal decision-code panels.
---

# Asteria Fleet Data Quality

## Workflow

1. Read the task prompt, `payloads/case_scope.json`, and `payloads/answer_template.json`. Treat the template as the output contract: required keys, exact names, enum values, precision, and ordering rules override intuition.
2. Read runtime access details from `environment_access.md`. Use only the listed endpoints. Do not invent data or use prior task answers.
3. Fetch the catalog, schema, source snapshots, and all rows for the scoped `collection_id`. The REST endpoints use `collection` for collection filters, `domain` for aliases, `kind` for unit conversions, and `currency` for FX. They page with `limit` and `offset`.
4. Prefer row-level calculations over shortcut inference. Reconcile duplicates, classify exceptions, compute totals, then fill the decision-code panels from the same evidence.
5. Return only the final JSON object. Before finalizing, check every array is sorted as specified, every count is internally consistent, and every rounded number uses the contract precision.

Use `scripts/fetch_hub_bundle.py` to collect a complete local JSON bundle for a scoped collection:

```bash
python skill/scripts/fetch_hub_bundle.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --family fuel \
  --collection "$COLLECTION_ID" \
  --out /tmp/asteria-bundle.json
```

Families are `contacts`, `fuel`, `freight`, and `maintenance`.

## Shared Reconciliation

- Scope rows by the case dates: collection ID, cutoff/as-of timestamp, and any business-period bounds. Use source snapshots to identify the authoritative retained source, normally a `CERTIFIED` snapshot when one exists; otherwise retain the best available non-final snapshot.
- For duplicated logical records, group by the public stable ID: contact row clusters by normalized identity/contact evidence, fuel by `transaction_id`, freight by `charge_id`, and maintenance by `event_id`. Count raw rows before retention and logical records after retention.
- For duplicate groups in transactional and maintenance tasks, retain the authoritative snapshot occurrence; report all snapshot IDs lexicographically where the contract asks for them.
- Match aliases by normalized, case-insensitive containment of `alias_text` in the description field. Use only reference rows effective on the business date or cutoff and with an eligible active status. Zero matching canonical values is unrecognized; more than one matching canonical value is ambiguous.
- Convert units with `/api/reference/conversions`: fuel volume to liters, freight weight to kilograms, freight/maintenance distance to kilometers. Convert money with `/api/reference/fx`, preferring `CERTIFIED` rates for the business date and treating USD as factor 1.
- Round only at the final contract field: usually 2 decimals for normalized quantities and spend, 4 decimals for rates, and exact integers for counts.

## Decision Codes

Apply compact codes by condition, not by ID.

- Reference rows: `RB-42` active and effective for the scoped date; `RB-17` inactive, retired, future-effective, or otherwise not effective for the date; `RB-83` provisional/non-final reference evidence.
- Fuel/freight source basis: `SB-24` single authoritative/certified retained occurrence; `SB-61` duplicate logical record retained from the authoritative/certified occurrence; `SB-79` single non-authoritative/provisional retained occurrence.
- Fuel/freight ledger disposition: `LD-72` valid recognized class/type matches expected; `LD-31` valid recognized class/type differs from expected; `LD-14` no recognized alias; `LD-88` multiple recognized canonical aliases; `LD-53` invalid physical measure such as nonpositive quantity, weight, or distance.
- Maintenance source: `MS-12` single authoritative/certified event; `MS-47` duplicate event retained from authoritative/certified; `MS-86` single provisional/non-authoritative event.
- Maintenance history route: `HR-33` accepted into corrected history; `HR-19` sequence-only odometer regression excluded from corrected history; `HR-74` rejected for missing/unparsable timestamp, invalid odometer, negative labor, or extreme labor.
- Contact identity: `IC-70` clean automerged duplicate person; `IC-25` shared usable identifier/channel that does not justify a merge; `IC-90` contested identity/watchlist cluster with unresolved same-name or identifier conflict; `IC-40` no usable-contact identity quarantine.
- Contact outreach: `OR-35` active, usable channel, consent granted; `OR-80` active and usable channel but consent not granted; `OR-60` no usable email or phone; `OR-15` inactive exclusion.
- Contact field provenance: `FP-55` field-level precedence applied across merged source rows; `FP-20` single-source or no field conflict; `FP-75` quarantined/no usable-contact record.

## Contacts

- Normalize email with Unicode NFKC, strip, and lowercase. Normalize phone to digits only. Normalize names with Unicode NFKC, trimmed whitespace, collapsed internal spaces, and casefolding for comparison; preserve display Unicode in canonical names.
- Automerge rows only when strong contact evidence links compatible identities, such as the same normalized email or phone with compatible names. Do not automerge rows that have no usable email or phone. Treat shared channels or hints across different names as contested/shared-channel evidence, not as an automatic merge.
- Prefer source-specific field precedence over whole-row precedence. Identity/compliance sources usually win master ID, contact, consent, and onboarding city fields; HR/depot sources usually win name and depot/region fields for roster tasks. Fall back to verified rows, rows with `master_hint`, latest `business_updated_at`, then stable row ID.
- A canonical person is dispatchable/channel-ready only when active, has at least one usable email or phone, and consent is `GRANTED`. Partition readiness counts so dispatchable/consent-blocked/no-contact/inactive buckets sum to the canonical population requested by the template.
- For focus rows, find the canonical cluster containing the anchored row, list all member row IDs sorted lexicographically, choose the same master/survivor used by the cluster, and report canonical fields from the selected field-level sources.
- Certification/release decisions come from the case thresholds when present. Without explicit thresholds, hold when contested identifiers or required dispatch/contact blockers remain; otherwise pass or pass with exceptions according to the prompt's action map.

## Fuel And Freight

- Retain one row per logical transaction/charge before all exception and total calculations. Duplicates contribute to raw and duplicate counts, not normalized totals.
- Fuel valid records require positive quantity and exactly one recognized fuel type. Freight valid records require positive weight, positive distance, and exactly one recognized service class.
- Mismatches are valid retained records whose recognized fuel type or service class differs from the expected field. Quarantines are invalid measure, unrecognized alias, or ambiguous alias records. Quarantined records do not enter normalized totals; valid mismatches do.
- Build exception lists from distinct retained logical IDs. Sort ID lists lexicographically. Rank merchants/carriers by the template's metric and tie breakers; carrier mismatch exposure is normalized USD spend on valid mismatches only.

## Maintenance

- Use source snapshots to identify the authoritative snapshot and row count. Duplicate groups are all event IDs appearing in more than one snapshot.
- Reject retained events with missing/unparsable event time, invalid odometer, negative labor, or extreme labor. Treat very large labor values as extreme when they are outside a plausible single-event range.
- Convert odometer readings to kilometers before sequence checks. For each asset, sort retained, non-rejected Q1 events by event time and stable event ID. A reading lower than the prior reliable reading is an odometer regression: report it separately and exclude it from corrected history metrics.
- Corrected distance is the sum across assets of last reliable odometer minus first reliable odometer after rejected and regression events are excluded.
