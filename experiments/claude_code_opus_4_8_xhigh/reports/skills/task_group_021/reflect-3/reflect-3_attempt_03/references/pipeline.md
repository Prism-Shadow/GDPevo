# Per-family pipeline checklist

A concrete order of operations to implement after reading `case_scope.json` and
`answer_template.json`. Compute in code from a full local pull of the
collection; the query interface caps at 2000 rows, and each collection fits.

## Shared preamble
1. Load connection details from `environment_access.md` (see `hub_client.py`).
2. `GET /api/catalog/schema`; confirm the view's columns.
3. Read `v_source_snapshots` for the collection. Identify the **CERTIFIED**
   snapshot → `authoritative_snapshot_id`, `authoritative_row_count`,
   `snapshot_status`.
4. Pull the whole collection view for the `collection_id`.
5. Apply the business cutoff on the *business date* column (not `ingested_at`).
6. Dedup by the stable business ID, retaining the certified occurrence →
   `raw_row_count`, `logical_count`, `duplicate_raw_count`, duplicate groups.

## Contacts (partner onboarding / field-service roster)
- Normalize email (NFKC/strip/lower, drop placeholder tokens; usable ⇔ `@`+dot)
  and phone (digits; usable ⇔ ≥ 7 digits).
- Union-find clusters: merge by usable email; merge by usable phone **excluding**
  shared phones (`master_hint=SHARED-HELPDESK`, or phone with ≥2 distinct emails).
  Never merge on name.
- Quarantine rows = no usable channel. `canonical count` = number of clusters,
  **including** quarantine singletons. `merged/duplicate clusters` = size > 1.
- Region/depot rollup counts every canonical entity; it must sum to the
  canonical count.
- Readiness partition: eligible = ACTIVE + usable channel; ready/dispatchable =
  eligible + consent GRANTED; produce the template's bucket shape; buckets sum
  to their denominator.
- Focus/anchor rows: report member_row_ids (sorted, deduped), the survivor/
  master row, canonical fields with per-field `*_source_system`, and
  `resolution_outcome`. Derive per-field precedence + canonical-consent from the
  probe rows; keep them consistent globally.
- Contested identifier = anchor's usable identifier shared across people.

## Fuel / freight transactions
- Build alias lookup for the domain: ACTIVE + valid at the record's business
  date; greedy longest whole-token match → {0=unrecognized, 1=recognized,
  ≥2=ambiguous}.
- Flags: invalid measure(s) ≤ 0; quarantined = unrecognized/ambiguous/invalid;
  valid = recognized-unique + measures > 0; mismatch = valid + recognized ≠
  expected.
- Check: valid+quarantine=logical; mismatch⊥quarantine; reason buckets sum to
  quarantine.
- Normalized totals over valid records: units via `v_unit_conversions`, USD via
  CERTIFIED `v_fx_rates` at the business date; group by recognized class; round
  per contract; group counts sum to valid count.
- Merchant/carrier ranking: exposure/exception measure desc, ID asc, top-N;
  include component counts.

## Maintenance events
- Retained record per `event_id` (certified). Population = both snapshots
  deduped (certified-only counts are wrong).
- Issue flags: missing/invalid timestamp, invalid (null/negative) odometer,
  negative labor, extreme labor (> full-day threshold). invalid_event_ids =
  union (deduped); valid = logical − invalid.
- Odometer regression on per-asset time-ordered valid events (reading < prior);
  reported separately, not invalid.
- Corrected distance = Σ over assets (last − first reliable odometer → km).
- Asset risk ranking: rejected desc, regression desc, asset_id asc.

## Codes & status (last)
- Map each scoped ID to its data-derived disposition, then to a code in the
  family's allowed enum; one distinct code per distinct disposition.
- Apply scope thresholds / certification gate / status→action map. If none is
  given, derive the release/close decision from the scope's stated rule.

## Final validation
- Validate the object against `answer_template.json` (keys, enums, patterns,
  lengths, ordering, `multipleOf`).
- Re-check every rollup/partition sum and the `valid+quarantine=logical`
  identity.
- Output only the JSON object.
