---
name: asteria-fleet-dq-audit
description: Solve Asteria Fleet Data Quality Hub reconciliation, normalization, and certification tasks. Use for prompts mentioning the Asteria Fleet Data Quality Hub, source snapshots, authoritative snapshots, duplicate logical records, contact readiness, fuel or freight transaction audits, maintenance history integrity, quarantine rows, compact internal control codes, or strict JSON answer contracts.
---

# Asteria Fleet Data Quality Hub Audits

Use this skill to produce the single JSON answer required by an Asteria Fleet Data Quality Hub task. The examples behind this skill are data-quality audits over live hub records; do not solve from memory or from the payload names alone.

## Required Inputs

Read these files from the task workspace before querying the hub:

- `prompt.txt`: identify the business domain, relevant endpoints, cutoff/as-of date, and any special inclusion rules.
- `payloads/case_scope.json`: authoritative scope, focus IDs, decision panels, ranking limits, thresholds, and ordering rules.
- `payloads/answer_template.json`: exact output shape. It may be JSON Schema or a custom contract with `field_contract`.
- `environment_access.md`: base URL, credentials, and allowed endpoint list for the running hub.

Return only one JSON object. Do not include Markdown, commentary, or extra keys.

## Hub Access

Prefer the read-only `/api/query` service when credentials are available, because these tasks require full-population counts and aggregates. The bundled helper is [scripts/asteria_query.py](scripts/asteria_query.py). In commands, replace `<skill-dir>` with the directory containing this `SKILL.md`.

```bash
python <skill-dir>/scripts/asteria_query.py catalog --access environment_access.md
python <skill-dir>/scripts/asteria_query.py schema --access environment_access.md
python <skill-dir>/scripts/asteria_query.py query --access environment_access.md --sql 'select * from v_source_snapshots limit 5'
```

If `environment_access.md` names a query credential, pass it exactly as a header:

```bash
python <skill-dir>/scripts/asteria_query.py query --access environment_access.md \
  --header 'X-Query-Token: <value>' \
  --sql 'select count(*) as n from v_contacts'
```

Use direct GET endpoints only after confirming their filter and pagination shape from the current hub. Do not assume a collection fits in one page.

Known logical views from the hub schema:

- `v_contacts`
- `v_fuel_transactions`
- `v_freight_charges`
- `v_maintenance_events`
- `v_reference_aliases`
- `v_unit_conversions`
- `v_fx_rates`
- `v_source_snapshots`

## General Workflow

1. Parse the answer contract into a checklist of required fields, array lengths, enum values, precision, and ordering. Treat it as stricter than the prose prompt.
2. Select the scoped collection and cutoff/as-of values from `case_scope.json`, not from examples or endpoint defaults.
3. Inspect `v_source_snapshots` for that collection. Choose the authoritative snapshot as of the cutoff by snapshot status and recency: prefer `CERTIFIED`, then `PROVISIONAL`, then `STALE`; within a status, use the latest eligible business cutoff/created/ingested time not after the task cutoff/as-of. Retain the selected snapshot ID in the answer when requested.
4. Pull every in-scope raw row across the relevant snapshots. Count raw rows before de-duplication.
5. Reconstruct logical records by the stable public identifier for the domain:
   - Contacts: row/person cluster keys from `master_hint`, shared source identity, or case-scope anchors.
   - Fuel: `transaction_id`.
   - Freight: `charge_id`.
   - Maintenance: `event_id`/logical event ID.
6. For duplicate logical records, keep one retained row for business metrics. Prefer the authoritative snapshot, then better snapshot status, then more recent `business_updated_at`, then more recent `ingested_at`. Still report duplicate groups and duplicate raw counts from all raw occurrences.
7. Apply validation and quarantine rules before totals. Quarantined records never enter normalized totals; valid mismatches do enter totals.
8. Compute requested full-population metrics, focus panels, rankings, and rollups from retained logical records. Avoid sampling and avoid deriving counts from visible ID patterns unless confirmed by records.
9. Infer compact codes from row state and reconciliation outcome. Do not assign a code from the public ID string.
10. Validate the final object against the template: required keys only, enum values only, sorted arrays, exact numeric precision, and cross-count reconciliations.

## Normalization Rules

- Dates: use the business date named by the task (`business_cutoff`, `cutoff_at`, `as_of`, or business period). Exclude records outside the declared period when the prompt says to.
- Emails: trim, Unicode-normalize with NFKC, and lowercase.
- Phones: keep digits only.
- Contact usability: a usable contact has at least one nonempty normalized email or phone. Dispatch/channel readiness also requires active status and granted consent.
- Units: use `v_unit_conversions` effective on the business date. Convert only after retaining the logical record.
- Currency: use `v_fx_rates` effective on the transaction/service date and the task base currency. Multiply by `usd_per_unit` for USD reports.
- Rounding: follow the template; common totals use 2 decimals, quarantine rates use 4 decimals.
- Reference aliases: normalize description/alias text consistently; match effective alias rows for the domain and business date. Zero matches are unrecognized, one match is recognized, more than one canonical match is ambiguous.

## Domain Procedures

### Contacts And Rosters

Cluster source rows into canonical people or partner contacts. Multi-row clusters usually need field-level precedence, not whole-row selection. Determine the source system for each canonical field and report it when requested.

Use these readiness partitions:

- Dispatchable/ready: active, usable email or phone, and consent is `GRANTED`.
- Blocked consent/not ready: active, usable channel, but consent is not granted.
- Blocked no contact/quarantine: no usable email or phone.
- Blocked inactive/inactive exclusion: inactive record with otherwise usable contact evidence.

For focus people or clusters, return exactly the scoped anchors in the requested order, with member row IDs sorted lexicographically. For watchlists/control cases, evaluate the supplied evidence rows and preserve sorted evidence IDs.

### Fuel And Freight

Resolve the actual category/service class through effective reference aliases. Compare recognized actual value to the expected source value:

- Valid matched: recognized actual equals expected.
- Valid mismatch: recognized actual differs from expected; include in normalized totals and mismatch rankings.
- Quarantine: unresolved class/category, ambiguous alias, unrecognized alias, nonpositive or invalid quantity/weight/distance.

Normalize physical measures and spend only for valid retained records. Build merchant/carrier exception rankings from distinct retained logical records, ordered by the prompt's primary metric and tie breaks.

### Maintenance

After retaining logical events, reject events with missing/unparseable timestamps, timestamps outside the scoped period, invalid odometer values, negative labor, or extreme labor. Sort reliable events by asset and event time. Mark odometer regressions as sequence issues, report their event and asset IDs separately, and exclude regression events from corrected distance metrics when the contract distinguishes them from invalid events.

The corrected distance metric is typically the sum across assets of last reliable odometer minus first reliable odometer in the reconstructed period, converted to the requested unit.

## Compact Code Semantics

Prefer explicit code-bearing fields if the hub exposes them. Otherwise infer the compact code from the reconciled condition:

Identity/contact codes:

- `IC-25`: single-source or uniquely resolved identity.
- `IC-70`: merged identity where multiple source rows resolve to one entity with field precedence.
- `IC-90`: contested identifier or no-automerge identity conflict.
- `IC-40`: quarantined identity/contact with no usable contact evidence.

Outreach/readiness codes:

- `OR-35`: ready or dispatchable: active, usable channel, consent granted.
- `OR-80`: active with usable channel but not outreach-ready because consent is pending, denied, unknown, or otherwise not granted.
- `OR-60`: no usable contact channel.
- `OR-15`: inactive exclusion.

Field provenance codes:

- `FP-20`: single-source/direct retained fields or no cross-source field conflict.
- `FP-55`: field-level precedence applied across multiple source rows.
- `FP-75`: quarantined or unusable field state.

Reference-policy codes:

- `RB-42`: effective recognized reference/alias row with one canonical mapping.
- `RB-17`: ambiguous or conflicting reference mapping.
- `RB-83`: unrecognized, inactive, expired, or otherwise non-effective reference row.

Source-retention/source-basis codes:

- `SB-61`: retained occurrence from an authoritative duplicate group.
- `SB-24`: retained single occurrence from the primary ledger/ERP-style source.
- `SB-79`: retained single occurrence from a secondary feed/mobile/legacy-style source.

Ledger/history routing codes:

- `LD-72`: valid matched transaction/charge routed normally.
- `LD-31`: valid expected-versus-actual mismatch.
- `LD-14`: quarantine caused by unrecognized/zero-match class or category.
- `LD-88`: quarantine caused by ambiguous class or category.
- `LD-53`: quarantine caused by invalid physical quantity, weight, distance, or other numeric measure.
- `HR-33`: maintenance event accepted into corrected history.
- `HR-74`: maintenance event rejected for invalid source fields.
- `HR-19`: maintenance event routed as an odometer regression.

Maintenance source codes:

- `MS-47`: Maintenance ERP source.
- `MS-12`: Mobile Work Orders source.
- `MS-86`: Legacy Maintenance Export source.

These mappings are reusable decision rules. Still verify them against current records and allowed enums in the task contract.

## Status Decisions

Use thresholds and action maps from `case_scope.json` when present. Otherwise:

- `PASS`/`RELEASE`: no material exceptions and all required gates pass.
- `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS`: exceptions are allowed by the task thresholds.
- `HOLD`/`BLOCK_AND_REMEDIATE`: unresolved quarantine, contested identity, odometer regression gate failure, or exception rate above allowed thresholds.

Use the exact status/action key names from the answer template; some domains call the action field `routing` or `next_action`.

## Final Checks

Before returning JSON:

- Sort arrays exactly as specified, often lexicographically by public stable ID or by rank.
- Confirm counts reconcile: raw rows, logical records, duplicate raw rows, valid records, quarantines, mismatches, and readiness partitions should balance under the task definitions.
- Confirm quarantined records are excluded from normalized totals and included in exception counts when required.
- Confirm every requested focus ID, decision ID, anchor, and control case is present exactly once.
- Confirm no train-task counts, public IDs, collection IDs, or answer rows have been copied from this skill into the solution.
