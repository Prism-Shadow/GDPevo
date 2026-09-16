# Opaque control codes

Control codes are fixed-enum, domain-specific values. The answer template's enum constraints define the allowed values per field. Assign codes using the rules below. Never invent new code values.

## Code families overview

| Family | Prefix | Domains |
|---|---|---|
| Identity | IC-XX | contacts |
| Outreach | OR-XX | contacts |
| Field Provenance | FP-XX | contacts |
| Reference Policy | RB-XX | fuel, freight |
| Source Basis | SB-XX | fuel, freight |
| Ledger Disposition | LD-XX | fuel, freight |
| Maintenance Source | MS-XX | maintenance |
| History Route | HR-XX | maintenance |

## Contacts codes

### IC (identity) codes

Available: `IC-25`, `IC-40`, `IC-70`, `IC-90`

Assignment rules:
- `IC-70` — multi-source cluster where fields from at least two different source systems contribute canonical values (FIELD_LEVEL_PRECEDENCE_APPLIED)
- `IC-25` — single-source cluster or a cluster whose evidence rows are all from the same source system
- `IC-90` — multi-source cluster where the canonical values show conflicting signals (e.g., different names across systems that could not be reconciled, or a contested identifier case)
- `IC-40` — cluster where all rows are quarantined (no usable contact channel from any source)

When examining anchored control cases with multiple evidence rows, look at the cluster those rows belong to and assign the code based on the cluster's composition.

### OR (outreach) codes

Available: `OR-15`, `OR-35`, `OR-60`, `OR-80`

Assignment rules:
- `OR-35` — entity is active, has contact, and consent is GRANTED (dispatchable/ready)
- `OR-80` — entity is active, has contact, but consent is not GRANTED (PENDING, DENIED, or UNKNOWN)
- `OR-60` — entity has no usable contact channel (quarantined)
- `OR-15` — entity is INACTIVE (even if contact and consent exist)

For readiness partitions:
- `both`, `email_only`, `phone_only` → `OR-35`
- `not_ready` (active, has channel, consent not GRANTED) → `OR-80`
- For inactive exclusions → `OR-15`

### FP (field provenance) codes

Available: `FP-20`, `FP-55`, `FP-75`

Assignment rules:
- `FP-55` — canonical values come from multiple source systems (mixed provenance)
- `FP-20` — canonical values all come from a single source system
- `FP-75` — canonical values cannot be determined because all rows are quarantined

## Fuel and freight codes

### RB (reference policy) codes

Available: `RB-17`, `RB-42`, `RB-83`

Assignment rules for reference aliases:
- `RB-42` — the alias is present in the reference table, its `reference_status` shows it was active well before the cutoff, and it maps unambiguously to one canonical value
- `RB-17` — the alias was published recently (close to the cutoff date) and reflects a new or updated mapping
- `RB-83` — the alias is present but its status indicates it is deprecated, stale, or no longer current as of the cutoff

To determine which code, inspect the alias row's `valid_from`, `valid_to`, `published_at`, and `reference_status` fields relative to the task cutoff.

### SB (source basis) codes

Available: `SB-24`, `SB-61`, `SB-79`

Assignment rules for transactions/charges:
- `SB-61` — the transaction's retained row comes from the CERTIFIED snapshot and appears only there (single-source)
- `SB-24` — the transaction's retained row comes from the CERTIFIED snapshot but the same transaction_id also exists in the PROVISIONAL snapshot (duplicate resolved to certified)
- `SB-79` — the transaction's retained row comes from the PROVISIONAL snapshot (this applies when the transaction does not appear in the certified snapshot at all)

### LD (ledger disposition) codes

Available: `LD-14`, `LD-31`, `LD-53`, `LD-72`, `LD-88`

Assignment rules:
- `LD-72` — clean transaction: recognized category matches expected category, no issues, valid
- `LD-31` — transaction has a category mismatch but is otherwise valid (goes to normalized totals)
- `LD-14` — transaction is unrecognized/ambiguous (fuel: description has zero or multiple matches)
- `LD-53` — transaction is quarantined for invalid quantity/weight/distance
- `LD-88` — transaction is quarantined for unrecognized/ambiguous alias (freight) or for unrecognized description that also has an invalid physical measure

For freight, use the same LD logic:
- `LD-72` — valid with no mismatch
- `LD-31` — valid with class mismatch
- `LD-14` — quarantined: unrecognized_alias
- `LD-53` — quarantined: invalid_weight or invalid_distance
- `LD-88` — quarantined: ambiguous_alias or multiple reasons including ambiguous

## Maintenance codes

### MS (maintenance source) codes

Available: `MS-12`, `MS-47`, `MS-86`

Assignment rules:
- `MS-12` — event originates from "Mobile Work Orders" source system
- `MS-47` — event originates from "Maintenance ERP" source system
- `MS-86` — event originates from "Legacy Maintenance Export" source system

Determine the source system by checking which snapshot (`snapshot_id`) the retained event comes from. The snapshot's `source_system` field (from `/api/source-snapshots`) tells you the originating system. Alternatively, query the event row and check the `snapshot_id` to infer the source.

### HR (history route) codes

Available: `HR-19`, `HR-33`, `HR-74`

Assignment rules:
- `HR-74` — event is in the CERTIFIED snapshot and is clean (not rejected, not regressed)
- `HR-33` — event is in the CERTIFIED snapshot but has a data quality issue (rejected or in a regression)
- `HR-19` — event is only in the PROVISIONAL snapshot (not in the certified snapshot)

When an event appears in both snapshots, use the retained CERTIFIED occurrence for the HR decision.
