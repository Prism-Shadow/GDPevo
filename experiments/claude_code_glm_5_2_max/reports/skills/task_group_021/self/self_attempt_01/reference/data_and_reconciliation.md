# Data model, reference data & reconciliation

## The 8 queryable views
Field names below are the stable shape; always confirm against `/api/catalog/schema` (whose `meaning` text documents each field) in case a field shifts.

- **v_contacts** — contact / person rows (partner onboarding, field-service roster, dealer / marketing contacts). Fields include collection_id, row_id, snapshot_id, source_system, source_record_id, person_or_org_name, email, phone, city, region, country, consent_status, record_status, verified_flag, business_updated_at, ingested_at, master_hint.
- **v_fuel_transactions** — fuel purchase rows (transaction_id, asset_id, merchant_id, fuel description, volume, unit, amount, currency, expected fuel category, snapshot_id, …).
- **v_freight_charges** — freight charge lines (charge_id, carrier_id, lane_id, service_date, weight, distance, amount, currency, expected service class, alias, snapshot_id, …).
- **v_maintenance_events** — maintenance log events (event_id, asset_id, timestamp, odometer, labor, snapshot_id, …).
- **v_reference_aliases** — alias→canonical mapping. Fields: domain, alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status, published_at. Maps a raw text (fuel description, freight service-class alias) to one canonical value (fuel_type / service_class). **0 matches = unrecognized; >1 match = ambiguous.**
- **v_unit_conversions** — unit factors. Fields: kind, from_unit, to_unit, factor, valid_from, valid_to, precision. Convert a raw unit to the canonical unit (volume→L, weight→KG, distance→KM) by multiplying by `factor`.
- **v_fx_rates** — currency→USD. Fields: rate_date, currency, usd_per_unit, rate_status, published_at. Convert an amount to USD by multiplying by `usd_per_unit` for the matching currency and rate_date.
- **v_source_snapshots** — snapshot metadata (same fields as the `/api/source-snapshots` items).

## Snapshots & overlap resolution
A collection has multiple snapshots (different source systems / ingest times). Every domain row carries a `snapshot_id`. Overlapping logical records (same logical ID appearing across snapshots) are resolved by **retaining the row from the authoritative snapshot** (`snapshot_status` = CERTIFIED, matching the business cutoff) and treating the other occurrences as duplicates. Report duplicate groups with their `snapshot_ids` and the retained `snapshot_id`.

## Reconciliation logic (universal)
1. **Raw rows** = all rows for the collection across all snapshots, respecting the business cutoff / as-of.
2. **Logical records** = raw rows with cross-snapshot duplicates collapsed to the authoritative occurrence. `duplicate_raw_count` = raw − logical.
3. **Category / class resolution** (fuel / freight): map each row's text via `v_reference_aliases` to a canonical value. `expected` = the row's declared expected class; `recognized` = the alias-mapped canonical.
   - mismatch = expected ≠ recognized (and recognized is a single, valid canonical).
   - unrecognized = 0 canonical matches.
   - ambiguous = >1 canonical match.
4. **Quantity validity**: nonpositive or unparseable volume / weight / distance / odometer; invalid or missing timestamp; invalid labor (negative / extreme) → invalid. Quarantine the invalid + unrecognized + ambiguous rows per the domain's quarantine definition.
5. **valid** = logical − quarantined. **exception** = distinct logical records that are a valid mismatch OR quarantined.
6. **Normalize**: convert quantity to the canonical unit via `v_unit_conversions.factor`; convert amount to USD via `v_fx_rates.usd_per_unit` for the matching currency / rate_date.
7. **Normalized totals**: sum over VALID records only (quarantined excluded). Valid mismatches are valid — they stay in totals. Round per contract (2 dp for measures & USD).

## Canonicalization (contacts)
- email: trim, Unicode NFKC, lowercase.
- phone: digits only (kept as a string).
- name: Unicode-preserving display form.
- city / region / depot: canonical value; track which source_system supplied each field (field-level precedence) and report the `*_source_system`.
- Merge multi-row clusters into one canonical person / entity; pick a survivor / master row_id (e.g. via `master_hint` or source precedence). `member_row_ids` = all rows in the cluster, deduplicated and lexicographically sorted.
- **Readiness**: an entity is readiness-eligible only if it is ACTIVE and has ≥1 usable email or phone. A channel is ready only if `consent_status` = GRANTED. Inactive entities are excluded (not ready). Watchlist identifier cases that cannot be auto-merged remain **contested**.

## Certification math
- `quarantine_rate` = quarantined_rows / canonical_entities, rounded to 4 dp (or per contract).
- status via case_scope thresholds: ≤ `pass_max_quarantine_rate` → PASS; ≤ `pass_with_exceptions_max_quarantine_rate` → PASS_WITH_EXCEPTIONS; else HOLD. (Some domains use an explicit `certification_gate`.)
- action = `status_action_map[status]` (HOLD → BLOCK_AND_REMEDIATE, PASS → RELEASE, PASS_WITH_EXCEPTIONS → REVIEW_EXCEPTIONS).
