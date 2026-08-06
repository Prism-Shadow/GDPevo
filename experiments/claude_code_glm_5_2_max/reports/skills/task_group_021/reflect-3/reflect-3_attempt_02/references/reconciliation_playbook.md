# Reconciliation playbook

Detailed, transferable rules for reconciling Asteria Fleet Data Quality Hub collections. Apply the rules that match the record family in the case scope.

## Contacts

### Usable-channel test
A value is usable only if it is present, non-empty after trimming, not a null sentinel, and well-formed.
- **Usable email**: trimmed, lowercased, not in `{'', 'n/a', 'na', 'none', 'null', 'nan', 'nil', 'unknown'}`, and contains `@`.
- **Usable phone**: has at least ~7 digits after stripping non-digits.
Null sentinels (`''`, `'   '`, `'N/A'`, `'none'`, `'NULL'`, etc.) are **not** usable and must not be treated as a clustering key.

### Clustering / entity resolution
- Cluster rows by **usable normalized email** (trim + lowercase; NFKC-normalize). Rows with no usable email are each their own entity — do not cluster them on their shared null/sentinel value.
- A **contested** cluster arises when rows share an identifier (e.g. a phone) but represent different identities (different emails/names). Mark these `CONTESTED_NO_AUTOMERGE`; do not merge. A `master_hint` like `SHARED-HELPDESK` flags this.
- `canonical_person_count` / `canonical_entity_count` = number of resolved entities (including quarantined ones). `merged_duplicate_cluster_count` = clusters with >1 row.

### Survivor and field-level precedence
- The **survivor / master_id** is the row carrying a `master_hint` of the form `MH-xxxx` within the cluster; if none, the lowest row id.
- Canonical **email, phone (digits-only), city, region, consent, record_status** come from the **survivor (master source)**.
- Canonical **name** comes from the **name-authority source** (the HR/partner-portal source), not the survivor: NFKC-normalize, trim, and title-case each word; **preserve Unicode diacritics** (e.g. `Renée`, `Müller`, `Zoë`). Do not take the name from a source that drops diacritics.
- `canonical_phone_digits` = digits-only of the survivor's phone. `canonical_email` = normalized lowercase email. `depot_code` = canonical region.
- Resolution outcomes: `FIELD_LEVEL_PRECEDENCE_APPLIED` (multi-row merge), `SINGLE_SOURCE` (one row, usable contact), `CONTESTED_NO_AUTOMERGE` (shared identifier, different identity), `NO_USABLE_CONTACT` (quarantine).

### Quarantine, readiness, certification
- **Quarantine rows** = rows with no usable email **and** no usable phone. `quarantine_rate` = quarantined rows ÷ canonical entities (round to 4 dp).
- **Readiness-eligible** = active **and** has at least one usable channel. A channel is ready only when consent is `GRANTED`.
- Channel partitions (mutually exclusive over eligible entities): `both` (usable email + phone + GRANTED), `email_only`, `phone_only`, `not_ready` (eligible but no ready channel, i.e. consent not GRANTED).
- Inactive entities with a usable channel are excluded from readiness (blocked-inactive); entities with no usable channel are blocked-no-contact.
- Certification: apply `status_thresholds` from the case scope to the quarantine rate; map via `status_action_map`.

## Transactions (fuel / freight)

### Deduplication
Deduplicate by the business id (`transaction_id` / `charge_id`). When the same id appears in multiple snapshots, **retain the CERTIFIED occurrence**. `raw_row_count` = all in-scope raw rows; `logical_count` = distinct ids; `duplicate_raw_count` = raw − logical.

### Category resolution (alias matching)
1. Restrict aliases to those `ACTIVE` and temporally valid on the record's business date.
2. Tokenize the description (lowercase, alphanumeric tokens) and each alias text.
3. Match aliases as **contiguous token phrases, longest first** (sort by token-count desc, then length desc). When a phrase matches, mark those tokens used and continue.
4. Collect matched `canonical_value`s:
   - 0 matches → **unrecognized**
   - >1 distinct canonical → **ambiguous**
   - exactly 1 → **recognized**
5. A recognized category ≠ `expected_*` → **class mismatch** (but only if the record is otherwise valid).

`unrecognized_transaction_ids` / analogous lists combine zero-match **and** ambiguous ids (per the contract). Reused alias texts redefined over time (e.g. `priority`) resolve to whichever row is ACTIVE and valid on the record date.

### Validity, mismatch, quarantine
- **valid** = recognized (1 category) **and** physical measures usable (quantity/weight/distance > 0, convertible unit).
- **mismatch** = valid **and** recognized ≠ expected. (Quarantined records are never mismatches.)
- **quarantine** = not valid: unrecognized/ambiguous class, nonpositive/unconvertible weight or distance (fuel also: nonpositive quantity). Freight `quarantine_reason_counts` breaks this down by `ambiguous_alias` / `invalid_distance` / `invalid_weight` / `unrecognized_alias`.
- `exception` = mismatch + quarantine (disjoint). Mismatches count toward merchant/carrier exception ranking; quarantine does too.

### Normalization
- Volume/weight/distance → canonical unit via `v_unit_conversions` (fuel: `US_GAL`/`IMP_GAL`→`L`; freight: `LB`→`KG`, `MI`→`KM`).
- Amount → USD via `v_fx_rates`: **CERTIFIED** rate for the record's business date and currency, applied to **all currencies including USD** (USD ≈ 1.0); fall back to PROVISIONAL only if CERTIFIED absent.
- Normalized totals sum over **valid** records only (exclude quarantined; **include valid mismatches**), grouped by **recognized** category. Round money/quantities to 2 dp (`ROUND_HALF_UP`).

### Rankings
- Merchant (fuel): top N by `exception_count` desc, then merchant id asc. Each row: `merchant_id, exception_count, mismatch_count, quarantine_count`.
- Carrier (freight): top N by `mismatch_spend_usd` (sum of USD on valid mismatch charges) desc, then carrier id asc. Each row: `rank, carrier_id, mismatch_count, mismatch_spend_usd, quarantine_count, exception_count`. Sort by the **unrounded** sum, then round for display.

### Decision panels (codes)
- Reference rows: one per scoped alias id, with a reference-policy code inferred from the alias's status/validity (active+valid vs provisional vs inactive/expired vs future-dated).
- Source-retention / source-basis: one per scoped transaction/charge id, inferred from the retained source (duplicate vs certified-only vs provisional-only).
- Ledger-disposition / routing: one per scoped id, inferred from the record's ledger treatment (clean valid vs valid mismatch vs unrecognized vs ambiguous vs invalid measure).
Use only the enum values the contract allows.

## Maintenance

### Integrity issues (over deduplicated logical events)
- `missing_timestamp` = `event_time_raw` null/empty.
- `invalid_timestamp` = non-empty but unparseable.
- `invalid_odometer` = odometer null or ≤ 0.
- `negative_labor` = labor < 0.
- `extreme_labor` = labor above the family's extreme threshold (a tight cluster well above the normal range; identify the threshold from the distribution gap).
- `odometer_regression` = a valid event whose odometer (in KM) is less than the previous valid event's odometer for the same asset, in time order.
Counts are over **deduplicated logical events** (retain CERTIFIED occurrence), not raw rows.

### Invalid vs regression
`invalid_event_ids` = logical events rejected for missing/invalid timestamp, invalid odometer, or invalid labor range. **Sequence-only odometer regressions are NOT invalid** — they are reported in `corrected_metrics` (`regression_event_ids`, `regression_asset_ids`).

### Corrected metrics
- `valid_event_count` = logical events with no integrity issue.
- `total_distance_km` = sum across assets of (last reliable odometer − first reliable odometer), odometers converted to KM via `v_unit_conversions` (`MI`→`KM`). Round to 2 dp.
- `regression_asset_ids` / `regression_event_ids` = assets/events with a sequence regression, sorted lexicographically.
- Asset risk ranking: top N by `rejected_event_count` desc, then `regression_event_count` desc, then asset id asc.

### Certification
Use the case scope's `certification_gate` verbatim when supplied (e.g. odometer-regression status/action). Otherwise apply thresholds to the issue/quarantine rate.

## Output discipline
- One JSON object; every required key; no extra keys; valid enums.
- Sort every list exactly as the contract states (usually lexicographic by id; rankings by the stated keys + tie-breakers).
- Round to the contract's precision (2 dp money/quantities; 4 dp rates). Use `ROUND_HALF_UP`.
- No commentary, no Markdown — only the JSON object.
