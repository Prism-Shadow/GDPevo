---
name: asteria-hub-reconciler
description: Reconcile and audit Asteria Fleet Data Quality Hub tasks. Use when a task asks Codex to read an Asteria case scope and answer contract, query the Fleet Data Quality Hub, reconcile overlapping source records for contacts, fuel transactions, freight charges, or maintenance events, compute quality or ledger metrics, assign compact internal decision/control codes, and return exact JSON only.
---

# Asteria Hub Reconciler

## Required Inputs

Read the task prompt, every file under `payloads/`, and `environment_access.md` before querying the hub. Treat `answer_template.json` as the output contract even when it is not formal JSON Schema. Do not reuse any previous task's IDs, counts, totals, rankings, or completed panels.

Use `environment_access.md` as the only source for network access. It supplies the base URL, allowed endpoints, and bearer token for `/api/query`.

## Querying

Prefer `/api/catalog/schema`, `/api/catalog/collections`, and the authenticated `/api/query` view layer over guessed endpoint filters. The query service accepts JSON of the form `{"query":"select ... from v_source_snapshots limit 5"}` and returns `columns`, `rows`, `row_count`, and `truncated`.

Use the bundled helper when useful:

```bash
python skill/scripts/query_asteria.py environment_access.md --objects \
  'select * from v_source_snapshots where collection_id = "..." order by snapshot_id'
```

Use `v_source_snapshots` to identify in-scope snapshots at or before the business cutoff. Use `CERTIFIED` snapshots as authoritative when present; retain the certified occurrence when a logical row appears in both certified and provisional snapshots. Retain a provisional occurrence only when no certified occurrence exists for that logical ID. Count raw rows before de-duplication and logical rows after de-duplication.

Page large extracts with `limit` and `offset`, or push aggregation into SQL, whenever `truncated` is true or the collection is larger than one response.

## Common Answer Discipline

Build the result from the current task's case scope and live records:

- Follow all required keys, fixed lengths, enum sets, numeric precision, and ordering rules in `answer_template.json`.
- Sort stable-ID arrays and scoped panels exactly as the contract says, usually lexicographically or by the specified rank.
- Normalize emails by trimming, Unicode normalizing when needed, and lowercasing. Normalize phones to digits only.
- Exclude quarantined fuel and freight records from normalized totals. Valid category/class mismatches still count in normalized totals unless the prompt says otherwise.
- Round final reported numbers only at the contract boundary. Keep intermediate calculations unrounded.
- Return exactly one JSON object and no Markdown or commentary.

## Compact Code Semantics

Use the current answer contract's enum set, but map the recurring Asteria compact codes by semantic state:

- Reference policy: `RB-42` means active/applicable reference evidence; `RB-17` means inactive, superseded, not-yet-effective, or otherwise not authoritative at the cutoff; `RB-83` means provisional reference evidence.
- Source basis and retention: `SB-24` means a single retained certified row; `SB-61` means a certified row retained as the duplicate winner; `SB-79` means a retained provisional row.
- Ledger disposition and routing: `LD-72` means valid accepted row with no category/class mismatch; `LD-31` means valid expected-versus-recognized mismatch; `LD-14` means unrecognized zero-match category/class; `LD-88` means ambiguous multi-match category/class; `LD-53` means invalid physical measure or conversion.
- Maintenance source: `MS-12` means a single retained certified row; `MS-47` means a certified duplicate winner; `MS-86` means a retained provisional row.
- Maintenance history route: `HR-33` means accepted valid history event; `HR-74` means rejected invalid event; `HR-19` means sequence-only odometer regression.
- Contact identity: `IC-25` means single/no-merge identity evidence; `IC-40` means no-usable-contact quarantine; `IC-70` means merged duplicate identity; `IC-90` means contested or weak duplicate identity that should not be auto-merged.
- Contact outreach: `OR-35` means active, usable channel, consent granted; `OR-80` means active and contactable but blocked by non-granted consent; `OR-60` means no usable channel; `OR-15` means inactive exclusion.
- Contact field provenance: `FP-20` means single-source or direct retained field evidence; `FP-55` means field-level precedence across merged sources; `FP-75` means unusable or quarantined field evidence.

## Reference Matching

For fuel and freight alias recognition, match aliases case-insensitively as whole business phrases or clear contained phrases from `v_reference_aliases`, constrained by domain and business date. A recognized category/class requires exactly one active applicable canonical value. No active match is unrecognized; matches to more than one active canonical value are ambiguous.

Classify reference-row decision codes by semantic state, then emit the corresponding code symbol allowed by the current answer contract.

## Fuel Audits

Use `v_fuel_transactions`, `v_reference_aliases`, `v_unit_conversions`, `v_fx_rates`, and `v_source_snapshots`.

For each retained logical transaction:

- Recognize the actual fuel category from `purchased_description`.
- Mark a mismatch when recognized category differs from `expected_fuel_type`.
- Quarantine when category recognition is zero-match or ambiguous, or when quantity is nonpositive or cannot be converted to the canonical volume unit.
- Convert volume with the applicable `volume` conversion factor.
- Convert spend to USD with the certified FX rate for the transaction business date and currency.

Use the source-basis and ledger-disposition code semantics above for scoped decision panels.

## Freight Audits

Use `v_freight_charges`, `v_reference_aliases`, `v_unit_conversions`, `v_fx_rates`, and `v_source_snapshots`.

For each retained logical charge:

- Recognize the service class from `description`.
- Mark a class mismatch when recognized class differs from `expected_service_class`.
- Quarantine when class recognition is zero-match or ambiguous, billed weight is nonpositive, distance is nonpositive, or either measure cannot be converted.
- Convert weight and distance with applicable `weight` and `distance` factors.
- Convert spend to USD with the certified FX rate for the service date and currency.
- For exposure rankings, use valid mismatch spend only; add quarantine counts to exception counts when requested.

Use the reference, source-retention, and ledger-routing code semantics above. Invalid weight or distance uses the same ledger-routing semantic class as invalid quantity.

## Maintenance Audits

Use `v_maintenance_events`, `v_unit_conversions`, and `v_source_snapshots`.

For each retained logical event:

- Reject events with missing or unparsable event time, nonpositive or unconvertible odometer, negative labor, or extreme labor according to the task's implied or stated rule.
- Treat cross-snapshot duplicates as one duplicate group per logical event ID and retain the certified occurrence when available.
- Detect odometer regressions after removing rejected events: per asset, sort by parsed event time and event ID, convert odometer values to the canonical unit, and flag events where the value decreases from the prior reliable reading.
- Compute corrected distance as the sum across assets of last reliable odometer minus first reliable odometer for the scoped period.
- Rank risky assets by the case-scope sort policy using rejected-event and regression-event counts.

Use the maintenance source and history-route code semantics above for scoped event panels.

## Contact Reconciliation

Use `v_contacts` and `v_source_snapshots`.

Cluster contact rows by strong shared identifiers and task anchors:

- Treat normalized email, phone digits, explicit `master_hint`, and compatible source record evidence as strong signals.
- Do not auto-merge contested identifiers that connect different people through a shared operational value such as a helpdesk phone unless the surrounding rows support one identity.
- Mark no-usable-contact rows when both normalized email and phone are absent.

Resolve canonical fields by field-level source precedence inferred from the collection's source systems and verified flags. In the Asteria contact collections, the most governed identity/registry/master source often supplies canonical contact fields and master IDs, while HR/compliance-style sources often supply names, depot/region, or city. Confirm by comparing same-person clusters in the current collection; do not assume one global precedence for every field.

Readiness rules:

- Dispatchable or ready requires an active canonical person with at least one usable email or phone and granted consent.
- Block consent when active with a usable channel but consent is not granted.
- Block no-contact when no usable canonical channel exists.
- Block inactive when inactive but otherwise contactable.

Use the contact identity, outreach, and field-provenance code semantics above for focus decisions, anchored controls, readiness partitions, quarantines, and inactive exclusions.

## Status Decisions

Use explicit thresholds, gates, and status-action maps from `case_scope.json` first. If a task supplies no thresholds, use the task wording and computed exceptions conservatively:

- `PASS` only when no reportable exceptions remain.
- `PASS_WITH_EXCEPTIONS` when exceptions are allowed for release or review by the scope.
- `HOLD` when quarantine, unresolved identity contest, odometer regression, invalid physical measures, or other blocking conditions violate the gate.

Map actions through the case scope when present; otherwise use the conventional mapping: pass releases, pass-with-exceptions reviews exceptions, and hold blocks for remediation.

## Validation Checklist

Before final output:

- Compare raw row counts to source snapshot row counts or direct collection counts.
- Check that raw count equals retained logical count plus duplicate raw count for duplicate-aware audits.
- Check that valid plus quarantine counts match retained logical counts for ledger audits.
- Check every requested focus or decision panel ID appears exactly once.
- Check partition totals, rankings, duplicate-group ordering, and enum values against `answer_template.json`.
- Validate the final JSON parses and contains no extra keys.
