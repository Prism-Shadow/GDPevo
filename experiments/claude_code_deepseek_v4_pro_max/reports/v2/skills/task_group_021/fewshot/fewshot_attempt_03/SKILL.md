# AsterOps Data-Quality Audit Skill (Fewshot)

You are solving AsterOps data-quality audit tasks across five families: CRM contact imports,
fleet fuel purchases, logistics cost events, CRM campaign audiences, and facilities charges.
All tasks share a common environment, API-surface conventions, and cross-cutting rules.

## Environment

Base URL: `http://34.46.77.124:9021`

Use the catalog to discover endpoints and downloads:
- `GET /api/catalog` — lists all endpoints, fields, filters, record counts, and CSV download paths

Key endpoints (discover exact fields/filters from catalog, not hardcoded here):
- `/api/crm/contact_rows` — filter by `batch_id`, `person_key`, `source_system`
- `/api/crm/campaign_members` — filter by `campaign_id`, `person_key`
- `/api/fleet/purchases` — filter by `region`, `period`, `vehicle_id`
- `/api/fleet/vehicles` — filter by `region`, `active`, `vehicle_id`
- `/api/logistics/cost_events` — filter by `wave_id`, `event_type`
- `/api/facilities/charges` — filter by `scope`, `period`
- `/api/reference/quality_rules` — controlled enums, currency rates, valid units
- `/api/reference/fuel_aliases` — priority-ordered fuel alias → canonical fuel mapping
- `/api/reference/category_aliases` — priority-ordered category alias → canonical category mapping

CSV downloads (from `/downloads/` path listed in catalog):
- `fleet_purchases_export.csv` — monthly fleet snapshot for source-delta comparison
- `logistics_cost_events_export.csv` — logistics snapshot
- `facilities_charges_export.csv` — facilities snapshot
- `campaign_members_export.csv`, `crm_contact_rows_export.csv`
- `fuel_aliases.csv`, `category_aliases.csv`

**API vs CSV pattern**: For fleet and facilities tasks, fetch BOTH the API (current) and the
CSV export (monthly snapshot). Reconcile differences for the source_delta_audit section.

## Cross-Cutting Business Rules

### Record Status Handling (all task families)

| status    | Meaning | Effective? |
|-----------|---------|------------|
| `posted`  | Normal record | Yes, unless superseded |
| `void`    | Voided / cancelled | No — excluded from effective set; counted in issue/quality flags |
| `amended` | Replacement for another record | Yes — replaces the record it amends |

**Amendment chain**: if record A has `amends_X_id` = "B", then B is **superseded** and A is
the **effective** record for that business key. Superseded records are excluded from
effective totals but tracked in audit lists.

### Currency Conversion (logistics tasks)

Rates from `QR_CURRENCY` quality rule:
- CAD → USD: × 0.74
- EUR → USD: × 1.08
- GBP → USD: × 1.27
- USD → USD: × 1.00

**Rounding rule**: convert each individual event's amount first, round to 2 decimal places
(cents), THEN sum for totals. Do NOT sum raw amounts and convert the total.

### String Normalization (CRM tasks)

- **Email**: trim outer whitespace, lowercase. Store as empty string `""` if no email.
- **Phone**: strip ALL non-digit characters (`[^0-9]`). Preserve any leading country-code
  digits present in the source. Store as empty string `""` if no phone.
- **Domain**: the lowercase substring after `@` in the normalized email.
- **City**: as-is from the source data. No normalization.
- **Segment** (campaign): trim whitespace, lowercase raw_segment, then keyword-match to
  canonical enum: "enterprise" → `enterprise_renewal`, "strategic" → `strategic_renewal`,
  "smb" or "churn" → `smb_churn_risk`, "partner" → `partner`, "ops" → `ops_lead`,
  else → `unknown`.

### Contact Reachability & Suppression (CRM tasks)

A contact row is **suppressed** (excluded from retained set) if:
- `contact_status` = `"do_not_contact"`, OR
- `consent_status` = `"revoked"`

`consent_status = "unknown"` does NOT block retention — only `"revoked"` does.

A person is **reachable** if their canonical row has a non-empty normalized email OR
non-empty normalized phone.

A person is **retained** if they are not suppressed AND are reachable AND their
canonical row has `contact_status = "active"`.

A person is **dropped_unreachable** if their canonical row is not suppressed but has
neither a usable email nor a usable phone.

### Source Precedence (CRM duplicate resolution)

When multiple contact rows exist for the same `person_key`, pick the canonical row by:

1. Highest source precedence: `crm_verified` > `steward_override` > `event_import` > `partner_roster`
2. If precedence is tied: newest `source_updated_at` (string comparison — later date wins)

Non-selected rows in duplicate groups are tracked as noncanonical.

### Alias Resolution / Fuel & Category Mapping

For fleet fuel purchases and facilities charges, match the product description or raw
category against the priority-ordered alias reference tables.

**Fuel alias resolution**:
1. Match case-insensitively the `product_description` against all fuel aliases.
2. If multiple aliases match, select the one with the **highest priority** number.
3. Use the alias's `canonical_fuel` as the observed fuel class.
4. If zero aliases match, classify as `"unknown"`.
5. Flag purchase in alias_priority_purchase_ids if more than one alias matched.
6. Flag purchase in generic_unleaded_trap_purchase_ids if the generic `"unleaded"` alias
   (priority 50) matched alongside any higher-priority unleaded alias.

**Category alias resolution** (facilities):
1. Match `raw_category` against category aliases (case-insensitive).
2. Highest priority match wins.
3. No match → `"unknown"`.

### Vehicle Fuel Mismatch (fleet tasks)

For each effective purchase, compare the **observed fuel** (from alias resolution) against
the vehicle's **expected_fuel** (from `/api/fleet/vehicles`).

- If observed ≠ expected AND the vehicle has `exemption_code = "none"` → **mismatch**.
  Add to `mismatch_purchase_ids` and `vehicle_review_queue`.
- If observed ≠ expected AND the vehicle has a non-none `exemption_code` (e.g.
  `field_generator`, `rental_substitution`) → **business exception**. Add to
  `exception_purchase_ids` but NOT to mismatch queue.
- Inactive vehicles (`active = false`): purchases for inactive vehicles are still
  evaluated — the vehicle record exists and its expected_fuel still applies.

### Invalid / Excluded Records

**Logistics invalid events** (excluded from all effective calculations):
- `amount` is negative → `invalid_negative_amount`
- `amount` is missing/null → `missing_amount`
- `unit` is not one of the controlled units (`kg`, `lb`, `mile`, `shipment`, `claim`) → `invalid_unit`
- `currency` is not a recognized currency code → `invalid_currency`

**Facilities invalid charges** (excluded from effective calculations):
- Void records
- Negative amounts
- Missing amounts

### Source Delta Reconciliation (fleet tasks)

Compare API results (current) against CSV export (monthly snapshot) by transaction_key:

- `api_only_current`: purchase_id in API but NOT in CSV → new record
- `csv_only_legacy`: purchase_id in CSV but NOT in API → legacy-only record
- `csv_stale`: same transaction_key appears in both API and CSV but with different
  purchase_ids AND the CSV record's status differs from current API state
- `source_disagreement`: same transaction_key with materially different data between
  sources (different purchase_id, amount, or status)
- CSV records excluded from operational totals: all csv_only_legacy + csv_stale records

## Output Conventions

### Ordering

ALL ID lists and object arrays must be sorted **ascending** (lexicographic string sort
unless documented otherwise). Specific rules:

- `suppressed_contact_ids`, `suppressed_contact_ids`: ascending by row_id / member_id
- `canonical_contacts`: ascending by `person_key`
- `source_lineage_audit`: ascending by `person_key`
- `vehicle_review_queue`: ascending by `vehicle_id`, then by `observed_fuel`
- `mismatch_purchase_ids`, `exception_purchase_ids`: ascending by purchase_id
- `alias_resolution_trace`: ascending by purchase_id
- `transaction_reconciliation`: ascending by `transaction_key`
- `invalid_event_ids`, `void_event_ids`: ascending by event_id
- `canonical_charge_sample`: ascending by `charge_id`
- `canonical_member_sample`: ascending by `person_key`

**Tiebreaker**: where the template specifies a secondary sort (e.g., `vehicle_review_queue`
sorts by vehicle_id then observed_fuel), apply it consistently.

### Numeric Precision

- All **counts**: integers (no decimal places)
- All **USD amounts**: exactly 2 decimal places, rounded to cents
- **Gallon totals**: 2 decimal places
- Zero values: use `0` (integer) for counts, `0.00` or `0.0` for decimals (match the
  template's precision — if a fuel class has 0.0 gallons, write `0.0`)

### Enum Values

Always use the exact enum strings from the answer template. Never invent new values.
Key enum sets:

- `canonical_source`: `crm_verified`, `event_import`, `partner_roster`, `steward_override`
- `contact_status`: `retained`, `dropped_unreachable`, `suppressed`, `manual_review`
- `lineage_decision`: `source_precedence_override`, `active_steward_correction`
- `fuel_class`: `diesel`, `unleaded`, `premium_unleaded`, `electric`, `hybrid`, `unknown`
- `reconciliation_status`: `api_current_replaces_stale_csv`, `csv_only_legacy`, `csv_extra_legacy`, `csv_stale_status`
- `category` (facilities): `fuel`, `maintenance`, `freight`, `accessorial`, `claim`, `tax_fee`, `unknown`
- `review_reason`: `duplicate`, `invalid_amount`, `invalid_unit`, `missing_contact_channel`, `suppressed_contact`, `ambiguous_alias`, `superseded`, `source_conflict`
- `issue_type` (logistics): `invalid_negative_amount`, `missing_amount`, `invalid_unit`, `invalid_currency`, `void_record`, `amended_record`, `duplicate_business_key`, `non_usd_currency`, `advisory_note`
- `segment`: `enterprise_renewal`, `strategic_renewal`, `smb_churn_risk`, `partner`, `ops_lead`, `unknown`
- `member_status`: `registered`, `attended`, `no_show`, `bounced`, `unsubscribed`
- `contactability_status`: `qualified_reachable`, `blocked_or_suppressed`, `needs_manual_review`

### Required Keys

All keys declared in the answer template's `required_keys` or `required_top_level_keys`
MUST be present in the output, even if their value is `0`, `0.00`, `[]`, or `{}`.
Missing a required key will fail evaluation.

### city_retained_counts

Include up to the **top 3** cities by count descending, then city name ascending for ties.
Include only cities with positive retained counts (≥ 1).

### canonical_charge_sample / canonical_member_sample

These are samples of the effective retained records. Only include retained/reachable
records (not suppressed, blocked, or needing review). Sort by the specified key.

## Task-Specific Recipes

### Task 1: CRM Contact Import Audit

1. Fetch contact rows by `batch_id`.
2. Group by `person_key`. Identify duplicate groups (2+ rows per person_key).
3. For each person: apply source precedence, check suppression, check reachability.
4. Build `canonical_contacts` with the resolved person-level decisions.
5. For duplicate groups: produce `source_lineage_audit` entries. Only include non-suppressed
   rows in `source_row_ids`. Lineage decision is `source_precedence_override` when crm_verified
   is selected over a newer lower-precedence row; `active_steward_correction` when
   steward_override is the selected source.
6. Count quality_flags: `raw_row_count` = all rows fetched; `canonical_person_count` =
   distinct person_keys; `duplicate_person_groups` = person_keys with 2+ rows;
   `duplicate_source_rows` = sum of (rows_per_group - 1) across groups;
   `missing_channel_rows` = rows with empty email AND empty phone;
   `suppression_rows` = rows with do_not_contact or revoked;
   `email_normalization_rows` = rows whose nonblank email changes under normalization;
   `phone_normalization_rows` = rows whose nonblank phone changes under normalization;
   `stale_or_inactive_rows` = rows with contact_status "inactive".
7. `precedence_override_person_keys`: person_keys where source precedence selects a
   different row than "newest by source_updated_at" would.
8. `suppressed_reachable_row_ids`: suppressed rows that still have a usable email or phone.

### Task 2: Fleet Fuel Purchase Audit

1. Fetch purchases by `region` + `period` from API.
2. Fetch vehicles by `region` from API.
3. Fetch CSV export; filter to matching region/period.
4. Resolve amendments: for each transaction_key, if an amended record amends another,
   the amended record is effective and the older is superseded.
5. Resolve fuel aliases for each effective purchase.
6. Cross-reference with vehicles to detect mismatches (exemption_code="none" → mismatch;
   non-none exemption when fuels differ → exception).
7. Compute `gallons_by_canonical_fuel`: sum gallons per fuel class across effective
   purchases. Rounded to 2 decimal places.
8. Compute `vendor_mismatch_counts`: count mismatch purchases by vendor (only vendors
   with ≥ 1 mismatch).
9. Source delta: compare API vs CSV by transaction_key.
10. `purchase_count_evaluated`: count of effective purchases included in fuel totals.
11. `alias_resolution_trace`: include entries only for purchases with nontrivial alias
    resolution (multiple matches, generic unleaded trap, or complex mapping).
    `matched_aliases` lists ALL aliases that matched; `audit_reasons` flags why the
    resolution was noteworthy.

### Task 3: Logistics Cost Event Integrity Audit

1. Fetch cost events by `wave_id`.
2. Identify invalid events (negative amount, invalid unit, etc.) → exclude from effective.
3. Filter out void events → exclude from effective.
4. For remaining effective events: convert each amount to USD using QR_CURRENCY rates,
   round to cents, then aggregate.
5. Compute `cost_type_totals_usd` by `event_type`.
6. Compute `unit_correction_counts` by `unit` for effective events.
7. `top_lane_by_cost`: the lane with highest total converted USD. If tie, pick the
   first by lane name ascending.
8. `non_usd_sample_event_ids`: first 10 non-USD event_ids among non-void events with an
   amount, sorted ascending by event_id.
9. `issue_type_counts`: count issues across ALL events in the wave (not just effective).
   `non_usd_currency` counts non-void events with currency ≠ USD.
   `advisory_note` counts events with non-empty quality_notes.
10. `amended_event_ids_used`: amendment records that replace an earlier record in the
    effective set.
11. `duplicate_business_key_count`: after amendment resolution, count business_keys
    appearing 2+ times among effective events.

### Task 4: CRM Campaign Audience Summary

1. Fetch campaign members by `campaign_id`.
2. For each unique `person_key` among members, fetch their CRM contact rows.
3. Resolve contact duplicates per person using standard CRM source precedence rules.
4. Classify each campaign member:
   - `bounced` or `unsubscribed` → `blocked_or_suppressed`
   - Contact row is suppressed (do_not_contact / revoked) → `blocked_or_suppressed`
   - Duplicate person (same person_key in multiple campaign members): the member with
     the highest `score` is the canonical candidate; the other(s) → `needs_manual_review`.
     If scores tie, prefer higher-status member (attended > registered > no_show).
5. For retained canonical members: check reachability (has email OR phone after
   normalization). If reachable → `qualified_reachable`. Otherwise mark appropriately.
6. `domain_counts`: count by lowercase email domain for qualified_reachable members only.
   Include only domains with positive counts.
7. `segment_counts`: count by canonical segment for qualified_reachable members only.
   All six keys required, use 0 where absent.
8. `canonical_member_sample`: only qualified_reachable members. For duplicate persons,
   use the canonical (highest-score) member.
9. `duplicate_person_keys`: person_keys appearing in multiple campaign member rows.

### Task 5: Facilities Charges Spend Audit

1. Fetch charges by `scope` + `period` from API.
2. Resolve amendments: if charge A amends charge B, B is superseded, A is effective.
3. Remove invalid records (void, negative amount, etc.).
4. Resolve `raw_category` against category aliases (priority-based matching). If only
   one alias matches and it has very low priority or maps to "unknown", flag as
   `ambiguous_alias`. If multiple aliases match, pick highest priority.
   If `raw_category` doesn't match any alias, use `"unknown"`.
5. Compute `category_counts` and `spend_by_category_usd` for effective charges.
6. `top_vendor_by_adjusted_spend`: vendor with highest total `amount` across their
   effective charges. Include all their charge_ids sorted ascending.
7. `review_reason_counts`: count per review reason across effective charges.
   `superseded` counts superseded records. `source_conflict` counts records where
   the API data disagrees with the CSV export for the same business_key.
8. `canonical_charge_sample`: effective charges, sorted by charge_id. At minimum include
   charges with nontrivial review reasons, plus enough clean charges to demonstrate
   coverage. (The gold answers include 5 sample entries.)

## Common Pitfalls

1. **Amendment chains**: always check `amends_X_id` fields. If a posted record is
   superseded by an amended record, the posted record is NOT in the effective set.
2. **Void AND superseded**: a record can be both (e.g., void with an amendment that
   replaces it). It appears in both `void_X_ids` and `superseded_X_ids`.
3. **Empty vs null**: treat missing/empty email and phone fields as `""`. A person
   with `""` for both email and phone is unreachable.
4. **Normalization detection**: a phone like `"3125550144"` is already normalized —
   stripping non-digits produces the same string. Do NOT count it as changed.
   Only count rows where the normalized value differs from the raw value.
5. **Phone country codes**: preserve leading digits. `"+1-312-555-0166"` → `"13125550166"`,
   NOT `"3125550166"`.
6. **Fuel alias case-insensitivity**: "Renewable Diesel B20" matches "renewable diesel b20".
   But the `selected_alias` in trace should use the EXACT alias string from the reference
   (lowercase as stored), not the purchase's original casing.
7. **Gallons precision**: sum raw gallon values then round to 2 decimal places.
   Do not round intermediate values.
8. **CSV filtering**: when filtering CSV exports for a specific region/period, filter on
   both `region` and `purchase_date` prefix. The CSV may contain records from other scopes.
9. **Currency conversion ordering**: convert each event's amount individually to USD cents,
   THEN sum. Converting the sum gives a different (wrong) result due to rounding.
10. **Duplicate counting**: `duplicate_person_groups` counts person_keys with 2+ rows.
    `duplicate_source_rows` counts the EXTRA rows (total rows in groups - number of groups).
11. **Suppressed rows in lineage**: suppressed rows (do_not_contact, revoked) are excluded
    from `source_lineage_audit.source_row_ids`. Only non-suppressed duplicate rows
    participate in lineage.
12. **Zero-gallon purchases**: purchases with 0 gallons are still effective (they contribute
    to `gallons_by_canonical_fuel` as 0.0). Track them in `zero_gallon_purchase_ids`
    separately.
13. **Vehicle review queue granularity**: each (vehicle_id, observed_fuel) combination is
    a separate entry, even if the same vehicle has mismatches on different fuel types.
14. **API pagination**: the APIs do not appear to paginate; all results are returned in
    a single response. Fetch once with the filter.
15. **Answer template is authoritative**: if there's a conflict between the prompt text
    and the answer_template.json, the template's required keys, enums, and precision
    rules take precedence.

## Data Flow Pattern

For every task, follow this sequence:

1. **Read the answer template** — understand required keys, enums, and ordering.
2. **Fetch from API** — use the catalog to find the right endpoint and filters.
3. **Fetch reference data** — quality rules, aliases, vehicles, contacts as needed.
4. **Fetch CSV exports** — for fleet and facilities tasks, get the CSV snapshot.
5. **Resolve amendments** — identify effective vs superseded records.
6. **Apply business rules** — normalization, precedence, alias resolution, currency.
7. **Aggregate & count** — compute totals, counts, and flag lists.
8. **Sort everything** — apply ascending sort to all lists.
9. **Validate against template** — ensure all required keys present, enums correct,
   precision matches.
