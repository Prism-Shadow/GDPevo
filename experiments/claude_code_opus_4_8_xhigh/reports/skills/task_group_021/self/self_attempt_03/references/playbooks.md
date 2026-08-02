# Playbooks — per-family reconciliation, control codes, output checklist

Read this after the SKILL.md spine. Everything here is method; fill in the numbers from
the collection actually in scope.

## A. Shared reconciliation model

1. **Logical entity** = the stable business key: `transaction_id` (fuel), `charge_id`
   (freight), `event_id` (maintenance), or a resolved **person** (contacts). The same
   logical entity can appear as several raw rows across snapshots.
2. **Snapshot precedence**: `CERTIFIED > PROVISIONAL > STALE`, then most-recent
   (`business_updated_at` → `ingested_at` → `created_at`). Ignore snapshots created after
   the `as_of`.
3. **Retention**: for overlapping occurrences keep the one from the highest-precedence
   snapshot; that snapshot is the "retained"/"authoritative" one for that entity.
4. `raw_row_count` = in-scope raw rows; `logical_count` = distinct entities;
   `duplicate_raw_count` = `raw − logical`.
5. **Business-date scoping** uses the family's business field:
   - fuel → `purchased_at`; freight → `service_date`; maintenance → `event_time_raw`
     (parsed) within `business_period`; contacts → usually all rows as of cutoff
     (`population_scope: ALL_COLLECTION_ROWS`).

## B. Transaction families (fuel / freight)

- **Recognition**: normalize description (trim+lower), match `alias_text` among
  `v_reference_aliases` rows for the family `domain` that are effective at the business
  date (`reference_status=ACTIVE`, `valid_from ≤ date ≤ valid_to|open`). 0 → unrecognized;
  ≥2 distinct `canonical_value` → ambiguous; 1 → recognized class. The same `alias_text`
  can map to different classes across time windows (e.g. an entry that is future-dated,
  or an expiring/INACTIVE one) — that is what makes a cutoff produce recognized vs
  ambiguous vs unrecognized.
- **Mismatch** = recognized class ≠ `expected_fuel_type` / `expected_service_class`; still
  valid, still normalized, counts as exception/exposure.
- **Quarantine reasons**: unrecognized alias, ambiguous alias, non-positive/invalid
  physical measure (quantity/weight/distance). Quarantined logical charges are excluded
  from normalized totals.
- **Normalize**: physical measure × conversion factor to canonical unit; `amount` × FX to
  USD (CERTIFIED rate for that currency+date, latest `published_at`). Round per contract
  (2 dp).
- **Rankings** (merchant / carrier): an *exception* is a distinct retained entity that is
  a valid class mismatch **or** quarantined; *exposure* is normalized USD on **valid**
  mismatches only. Order by the contract's key (exception_count or mismatch_spend_usd
  DESC) then id ASC; emit exactly `limit` rows.

## C. Maintenance family

- Parse `event_time_raw`; missing/unparsable → `missing_timestamp`/`invalid_timestamp`
  (invalid → rejected). Odometer out of valid range or non-numeric → `invalid_odometer`.
  Labor < 0 → `negative_labor`; implausibly large → `extreme_labor`. `invalid_event_ids` =
  rejected for time/odometer/labor range (unique, lexicographic).
- **Odometer regression** = per asset, in event-time order, a later reliable reading below
  an earlier one. Reported in `corrected_metrics` (regression asset/event ids), **not** in
  `invalid_event_ids`. A regression typically trips a hard **HOLD → BLOCK_AND_REMEDIATE**
  gate (see `certification_gate`).
- **Corrected distance** = Σ over assets of (last − first reliable odometer, in canonical
  km) across the reconstructed history; round to the stated dp.
- **Duplicate groups** are cross-snapshot logical duplicates: `logical_event_id`,
  sorted `snapshot_ids`, and the retained event/snapshot by precedence.
- Risk ranking: order by `rejected_event_count DESC`, then the tie-breaks in scope
  (`regression_event_count DESC`, `asset_id ASC`).

## D. Contacts family

- **Cluster** rows across source-system snapshots on normalized email (trim→NFKC→lower)
  and normalized phone (digits only). A cluster = one canonical person.
- **Survivorship**: pick each canonical field by source-system precedence + `verified_flag`
  + recency; `master_hint` may designate the master `row_id`. `master_id`/survivor =
  chosen public row id. Report `*_source_system` per field where required (name / contact /
  depot / consent / city).
- **Outcomes**: `SINGLE_SOURCE`, `FIELD_LEVEL_PRECEDENCE_APPLIED`,
  `CONTESTED_NO_AUTOMERGE` (conflicting identifiers block automerge — these feed the
  identifier watchlist / contested cluster list), `NO_USABLE_CONTACT`.
- **Quarantine** = no usable email and no usable phone.
- **Readiness**: eligible ⇔ `record_status=ACTIVE` and ≥1 usable channel; a channel is
  *ready* ⇔ `consent_status=GRANTED`. Partitions: `both / email_only / phone_only /
  not_ready`; per-depot blocked buckets `blocked_consent` (active+usable+non-granted),
  `blocked_no_contact`, `blocked_inactive`. Each partition must sum to its total.
- `quarantine_rate` = quarantined ÷ the denominator the contract names (often canonical
  entities), at the stated precision.

## E. Opaque control-code panels

Code families and their **cardinality = number of semantic buckets**:

| Prefix | Family | # codes | Dimension it encodes |
|---|---|---|---|
| `IC-` | Identity | 4 | cluster/identity resolution outcome |
| `OR-` | Outreach | 4 | channel + consent readiness disposition |
| `FP-` | Field provenance | 3 | which source basis supplied the surviving field |
| `RB-` | Reference policy | 3 | alias effective-state at cutoff |
| `SB-` | Source basis / retention | 3 | which snapshot basis a row was retained from |
| `LD-` | Ledger disposition / routing | 5 | transaction/charge ledger outcome |
| `MS-` | Maintenance source | 3 | maintenance snapshot/source basis |
| `HR-` | History route | 3 | maintenance history routing |

The expansions are **intentionally not supplied**. Infer each code deterministically:

1. **Enumerate buckets** in that dimension so the count equals the family cardinality.
   Working hypotheses (verify against evidence — do not treat as fixed labels):
   - `RB-` (3): {ACTIVE & in-window} · {PROVISIONAL} · {INACTIVE / expired / future-dated}.
   - `SB-` (3): retained-from {CERTIFIED authoritative} · {PROVISIONAL} · {superseded /
     duplicate-dropped}.
   - `LD-` (5): {clean valid, included} · {valid class-mismatch, included} ·
     {quarantined – unrecognized/ambiguous class} · {quarantined – invalid measure} ·
     {dropped duplicate / out-of-scope}.
   - `IC-` (4): {single-source} · {clean merge} · {merge with field conflict} ·
     {contested / no-usable}.
   - `OR-` (4): {both channels ready} · {one channel ready} · {consent-blocked} ·
     {inactive / no-contact}.
   - `FP-` (3): surviving field from {authoritative/verified source} ·
     {precedence-override secondary source} · {single/unverified source}.
   - `MS-`/`HR-` (3 each): analogous by snapshot/source basis and event routing.
2. **Assign each scoped ID to its bucket** from the reconciled evidence.
3. **Bind buckets → codes consistently.** Use the **anchor / control cases** in
   `case_scope.json` (`control_case_anchors`, `policy_control_cases`, seed/evidence rows)
   as calibration — each anchor illustrates one bucket. Keep one binding consistent across
   every panel and every row. When a natural severity/authority order exists, aligning it
   with the codes' numeric-suffix order is a reasonable tie-breaking heuristic, but the
   anchors' actual conditions govern. Every allowed code need not be used, but never emit a
   code outside the enum, and give the same condition the same code everywhere.

## F. Certification / close decision

Take thresholds and the status→action map **from `case_scope.json`**. Typical mapping:
`PASS → RELEASE`, `PASS_WITH_EXCEPTIONS → REVIEW_EXCEPTIONS`, `HOLD → BLOCK_AND_REMEDIATE`.
General logic: clean (e.g. quarantine_rate ≤ pass max, no hard-gate breach) → PASS; within
tolerance → PASS_WITH_EXCEPTIONS; over tolerance or a hard gate tripped (e.g. odometer
regression) → HOLD. Always emit the paired action from the scope's map.

## G. Output validation checklist

- Top-level: exactly the required keys, `additionalProperties:false` (no extras).
- Every enum value is legal; no value outside a declared enum.
- Arrays: exact `minItems`/`maxItems`; `uniqueItems` honored; each sorted per its rule
  (lexicographic ascending / by-id ascending / ranked with documented tie-breaks).
- Each scoped focus / anchor / decision / reference ID appears **exactly once** in its
  panel, in the required order.
- Numbers: integers exact; floats rounded to the stated decimals (`multipleOf:0.01`
  → 2 dp). No floats where the contract says integer-only.
- Invariants: `raw = logical + duplicates`; readiness/depot partitions sum to totals;
  exception = mismatch ∪ quarantine (distinct); normalized totals exclude quarantine and
  include valid mismatches.
- Re-derive a couple of headline aggregates with an independent `GROUP BY` query to catch
  a pagination/truncation gap.
- Emit the single JSON object — no Markdown, no prose, no trailing text.
