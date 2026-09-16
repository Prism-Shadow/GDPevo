---
name: asteria-hub-reconcile
description: Solve Asteria Fleet Data Quality Hub audit and certification tasks that require reconciling contacts, fuel transactions, freight charges, or maintenance events from a running task environment into a strict JSON answer contract. Use when prompts mention the Asteria Fleet Data Quality Hub, source snapshots, contact-readiness, fuel or freight normalization, maintenance-history integrity, reference aliases, FX/unit conversions, or opaque control-code panels.
---

# Asteria Hub Reconcile

Use this skill to produce exact JSON answers for Asteria Fleet Data Quality Hub tasks. Always derive values from the current task payloads and hub data. Do not reuse any prior answer values.

## Inputs

1. Read the user prompt, `payloads/case_scope.json`, and `payloads/answer_template.json`.
2. Read `environment_access.md` for the base URL and allowed endpoints.
3. Inspect `/api/catalog/collections` and `/api/catalog/schema` to confirm the collection family and field names.
4. Fetch all in-scope rows, source snapshots, and relevant reference data. The REST endpoints use `collection=<collection_id>` and paginate with `offset`; each response has `items`, `limit`, `offset`, and `total`.

Use the bundled exporter when helpful:

```bash
python scripts/asteria_export.py --base-url "$TASK_ENV_BASE_URL" --collection "$COLLECTION_ID" --family contacts --out /tmp/asteria
python scripts/asteria_export.py --base-url "$TASK_ENV_BASE_URL" --collection "$COLLECTION_ID" --family fuel --refs --out /tmp/asteria
python scripts/asteria_export.py --base-url "$TASK_ENV_BASE_URL" --collection "$COLLECTION_ID" --family freight --refs --out /tmp/asteria
python scripts/asteria_export.py --base-url "$TASK_ENV_BASE_URL" --collection "$COLLECTION_ID" --family maintenance --refs --out /tmp/asteria
```

If `/api/query` is authorized in the task environment, use it for aggregation; otherwise page the REST endpoints and compute locally.

## Common Rules

- Use the answer template as the output schema and ordering contract. Return only one JSON object.
- Treat the source snapshot with `snapshot_status == "CERTIFIED"` for the scoped collection as authoritative when resolving duplicated logical IDs.
- For duplicate logical records, keep the certified occurrence when present; otherwise keep the only available non-certified occurrence. Count `duplicate_raw_count` as raw rows minus distinct logical IDs.
- Apply the task cutoff to source snapshots, reference aliases, FX rows, and unit conversions. Prefer certified reference or FX rows that are effective for the business date.
- Sort stable-ID arrays lexicographically unless the template or scope says otherwise. Preserve required rank ordering and numeric precision exactly.
- Keep valid expected-vs-actual mismatches in normalized totals. Exclude quarantined or rejected records from normalized totals.

## Reference And Ledger Codes

Use these reusable code meanings when the answer contract asks for compact codes:

- `RB-42`: active reference alias that is effective for the business date.
- `RB-17`: reference alias not effective for the date because it is inactive, expired, or not yet valid.
- `RB-83`: provisional reference alias.
- `SB-24`: retained from a certified single source occurrence.
- `SB-61`: retained after overlapping occurrences, with the certified source winning.
- `SB-79`: retained from a non-certified/provisional source because no certified occurrence exists.
- `LD-72`: valid ledger row whose recognized category/class matches the expected value.
- `LD-31`: valid ledger row with expected-vs-recognized mismatch.
- `LD-14`: quarantine because no active effective alias matches the description.
- `LD-88`: quarantine because aliases match more than one canonical category/class.
- `LD-53`: quarantine because physical quantity, distance, or weight is invalid.

## Alias Matching

For fuel and freight, match reference aliases against the free-text description:

1. Lowercase and normalize whitespace.
2. Consider only aliases for the relevant domain (`fuel` or `freight`) whose `reference_status` is active and whose valid date range covers the transaction or service date.
3. Use case-insensitive substring matching of `alias_text`.
4. If matches map to zero canonical values, classify as unrecognized.
5. If matches map to multiple canonical values, classify as ambiguous.
6. If exactly one canonical value remains, compare it with the expected field to decide mismatch.

## Fuel Audits

For `v_fuel_transactions`:

- Logical ID: `transaction_id`.
- Business date: date part of `purchased_at`.
- Quarantine when the recognized fuel type is unresolved or `quantity <= 0`.
- Normalize volume to liters using `kind=volume` conversions and amount to USD using certified FX for the purchase date.
- Count valid transactions after duplicate resolution and quarantine removal.
- `mismatch_transaction_ids`: valid logical transactions where recognized fuel type differs from `expected_fuel_type`.
- `unrecognized_transaction_ids`: logical transactions with zero-match or ambiguous descriptions.
- Merchant exceptions: one per logical transaction with a mismatch or quarantine; rank by `exception_count` descending, then `merchant_id` ascending.
- Focus-asset rollups count logical, valid, mismatch, quarantine, exception, liters, and USD for the scoped asset IDs.

## Freight Audits

For `v_freight_charges`:

- Logical ID: `charge_id`.
- Business date: `service_date`.
- Quarantine when service class is unresolved, `billed_weight <= 0`, or `distance <= 0`.
- Normalize weight to kilograms, distance to kilometers, and amount to USD using certified FX for the service date.
- `class_mismatch_charge_ids`: valid charges where recognized service class differs from `expected_service_class`.
- `quarantine_charge_ids`: all logical charges quarantined for unresolved alias or invalid measures.
- Duplicate groups include all logical IDs with multiple raw occurrences, sorted by `charge_id`, with snapshot IDs sorted lexicographically and the retained snapshot shown.
- Carrier ranking uses normalized USD exposure from valid mismatches only; rank by mismatch spend descending and carrier ID ascending. Include mismatch, quarantine, and total exception counts.

## Maintenance Audits

For `v_maintenance_events`:

- Logical ID: `event_id`.
- Authoritative snapshot: certified snapshot for the collection.
- Duplicate groups are cross-snapshot logical duplicates; retain the certified event when present.
- Reject events with missing or unparsable timestamps, invalid odometer values, negative labor, or extreme labor. Treat odometer regressions as sequence issues, not invalid-event rejections unless another rejection reason applies.
- Convert odometers to kilometers with `kind=distance` conversions.
- Reconstruct history per asset by event time. For corrected distance, use the first and last reliable odometer readings in the business period and omit regression events from the reliable sequence.
- Rank risky assets by the policy in `case_scope.json`, usually rejected count descending, regression count descending, then asset ID ascending.
- Maintenance codes: `MS-12` for certified single-source retained events, `MS-47` for cross-snapshot duplicates resolved to certified, and `MS-86` for non-certified/provisional retained events. Use `HR-33` for accepted history events, `HR-74` for rejected invalid events, and `HR-19` for odometer-regression route events.

## Contact And Roster Reconciliation

For `v_contacts`:

- Normalize email with Unicode NFKC, trimming, and lowercase. Treat blank, `null`, `n/a`, `none`, and similar placeholders as unusable.
- Normalize phone to digits only. Treat blank, `null`, `n/a`, `none`, and similar placeholders as unusable.
- Build identity clusters from strong shared email/phone evidence and compatible names. Do not auto-merge shared helpdesk phones, noisy `master_hint` values, or identifiers reused by multiple distinct names; report those as contested when scoped.
- For three-source operational clusters, the canonical/master row is usually the identity or compliance source row. Use source-specific field precedence: HR Directory can own name and depot, while Identity Registry or Compliance Master can own contact and consent fields. Preserve Unicode in names.
- A quarantine contact row/entity has no usable canonical email or phone.
- Dispatch/readiness eligibility requires `record_status == ACTIVE` and at least one usable canonical email or phone. A channel is ready only when consent is `GRANTED`.
- For contact-readiness partitions, use mutually exclusive buckets: dispatchable/ready, blocked by consent, blocked by no contact, and blocked because inactive.

Contact control codes:

- `IC-70`: strong same-person cluster auto-merged.
- `IC-25`: contested shared identifier or shared contact signal, not safe to auto-merge.
- `IC-40`: no usable contact/identity evidence sufficient only for quarantine handling.
- `IC-90`: evidence supports separate identities or no auto-merge.
- `OR-35`: active usable channel with granted consent.
- `OR-80`: active usable channel but consent is not granted.
- `OR-60`: no usable outreach channel.
- `OR-15`: inactive exclusion.
- `FP-55`: canonical fields came from multi-source field precedence.
- `FP-20`: single-source or no field-level merge needed.
- `FP-75`: quarantined or insufficient field provenance.

## Status Decisions

- If the scope provides threshold and action maps, compute the status from those values.
- For fuel/freight close or reconciliation tasks, any unresolved/quarantined ledger records normally requires `HOLD` and remediation; mismatches without quarantine may still require review if the template offers that state.
- For maintenance tasks, apply the explicit certification gate in `case_scope.json`; odometer regressions usually hold the certification.
- For roster/contact release tasks, unresolved contested identifiers or non-dispatchable required populations normally block release.

## Final Checks

Before answering, validate that:

- Every top-level key required by the template is present and no extra keys are present.
- Counts reconcile with the ID arrays and grouped summaries.
- Duplicate counts equal raw rows minus logical IDs.
- Valid counts equal logical IDs minus quarantined or rejected records.
- Ranked arrays have the requested length and tie-break order.
- Numeric fields use the declared rounding.
- Output is JSON only, with no Markdown or commentary.
