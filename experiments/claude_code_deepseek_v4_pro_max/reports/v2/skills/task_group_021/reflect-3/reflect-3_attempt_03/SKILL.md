# AsterOps Data-Quality Audit Skill

## Environment

All AsterOps data-quality tasks use a shared HTTP API workbench. Start every task by fetching the catalog and relevant data endpoints.

### Catalog and Data Sources

```
GET {BASE_URL}/api/catalog          — list all endpoints, fields, filters, record counts, and available CSV downloads
GET {BASE_URL}/api/health           — environment health and generation timestamp
```

The catalog returns `endpoints` (API surface with field lists and filter params) and `downloads` (CSV export filenames). CSV exports are monthly snapshots; API endpoints return current state. Always fetch **both** when a task mentions reconciliation.

### CSV Downloads

CSV exports are accessed via:
```
GET {BASE_URL}/downloads/{filename}
```
Filenames come from the catalog's `downloads` array. Always read with `csv.DictReader`.

### Reference Data

Always fetch these before computing answers:
- `GET {BASE_URL}/api/reference/quality_rules` — controlled enums, currency rates, valid units
- `GET {BASE_URL}/api/reference/fuel_aliases` — product-description-to-canonical-fuel mapping with priority
- `GET {BASE_URL}/api/reference/category_aliases` — raw-category-to-canonical-category mapping with priority

---

## General Business Rules

### Record Status Handling (applies to all domains)

Every record-oriented API has a `record_status` field. The quality rule `QR_EFFECTIVE_RECORDS` defines three values:

| Status | Meaning | Action |
|--------|---------|--------|
| `posted` | Normal source row | **Include in effective set** |
| `void` | Explicitly voided | **Exclude** from effective set; list in `void_*_ids` |
| `amended` | Amendment record (the replacement) | **Include in effective set**; the record it amends (via `amends_*_id`) is superseded and excluded |

An amended record with non-empty `amends_*_id` field **is** the current/correct version. The record it points to is the superseded original — exclude the original from the effective set and list it in `superseded_*_ids`.

When a void record is also amended by another record, it goes into **both** `void_*_ids` and `superseded_*_ids`.

### Source Precedence for Duplicate Resolution (CRM)

For CRM person records, canonical row selection uses source-system precedence:

1. `crm_verified` (highest)
2. `event_import`
3. `partner_roster`
4. `steward_override` (lowest)

**Exception**: When a `steward_override` row has `steward_corrected` in its `quality_notes`, it wins via `active_steward_correction` regardless of normal precedence.

To determine `precedence_override_person_keys`: compare the source-precedence pick against the newest-by-`source_updated_at` pick — include the person_key when they differ.

### Suppression Rules (CRM contacts and campaign members)

Rows are **suppressed** (excluded before canonical selection) when:
- `contact_status` is `do_not_contact`
- `consent_status` is `revoked`

For campaign audience tasks, members are **hard blocked** when:
- `member_status` is `bounced` or `unsubscribed`
- The person's CRM contact has **all** rows suppressed (do_not_contact or revoked on every source row)

### Duplicate Campaign Member Handling

When the same `person_key` appears in multiple campaign member rows for the same campaign:
- The **highest-scoring** member (by `score`) is kept as qualified (if reachable)
- **All lower-scoring** duplicate members go to `needs_manual_review_ids`

---

## Normalization Rules

### Email
- Trim outer whitespace
- Convert to lowercase
- Use empty string `""` when no email is available

### Phone
- Strip all non-digit characters
- Preserve country-code digits present in the source
- Use empty string `""` when no phone is available

### Normalization-Change Detection
A row's nonblank email **or** phone "changes under normalization" if the normalized value differs from the raw value. This is a per-row boolean: count the row once even if both email and phone change.

---

## Domain-Specific Rules

### 1. CRM Contact Import Audit

**Effective contacts**: All source rows in the target batch, minus suppressed rows (do_not_contact, revoked_consent). Suppressed row IDs go in `suppressed_contact_ids`.

**Canonical contacts**: For each person_key, select one canonical row from non-suppressed rows using source precedence. Output every person_key present in the batch in `canonical_contacts` (including suppressed ones with `contact_status: "suppressed"`).

**Contact status values**:
- `retained` — has usable email or phone
- `dropped_unreachable` — canonical row has no email AND no phone
- `suppressed` — all rows for this person_key are suppressed
- `manual_review` — needs human decision

**Source lineage audit**: Include every person_key with >1 source row in the batch. `source_row_ids` lists ALL rows including suppressed ones. `noncanonical_source_row_ids` lists all source rows except the selected canonical. `lineage_decision` is `source_precedence_override` unless a steward actively corrected (`active_steward_correction`).

**Quality flag definitions**:
- `raw_row_count` — total rows in batch
- `canonical_person_count` — distinct person_keys
- `duplicate_person_groups` — person_keys with >1 row
- `duplicate_source_rows` — extra rows beyond the first in each duplicate group
- `missing_channel_rows` — rows with empty email AND empty phone
- `suppression_rows` — rows with do_not_contact or revoked_consent
- `email_normalization_rows` — rows where nonblank email changes under normalization
- `phone_normalization_rows` — rows where nonblank phone changes under normalization
- `stale_or_inactive_rows` — rows with quality note `stale_status` or `contact_status: inactive`

**City retained counts**: Top 3 cities by retained count descending, then alphabetically ascending for ties.

### 2. Fleet Fuel Purchase Audit

**Scoping**: Filter API purchases by `region` and `period` (YYYY-MM). Also fetch the CSV export and filter identically.

**Effective purchases**: Start with all scoped records. Remove void. Remove any record superseded by an amendment (another record's `amends_purchase_id` points to it). Amendment records themselves (status `amended`) are included. The CSV export is the monthly snapshot; the API is current state.

**Fuel alias matching**: Match product description to fuel aliases using **substring** matching (case-insensitive: check if alias is a substring of the lowered description). Among multiple matches, select the **highest priority** alias. The alias's `canonical_fuel` is the resolved fuel.

**Alias issue classification**:
- `priority_overlap` — more than one alias matches the description
- `generic_unleaded_trap` — the generic `unleaded` alias matches alongside a more specific unleaded alias (`unleaded regular`, `regular unleaded`, `premium unleaded`, `super unleaded`)
- `selected_unknown_alias` — the winning alias maps to `unknown` fuel
- `unmapped_description` — no alias matches the description (fuel resolves to `unknown`)

**Mismatch detection**: Compare canonical fuel against vehicle `expected_fuel`. If they differ AND the vehicle has a non-`none` `exemption_code`, it's a vehicle exception (not a mismatch). Otherwise it's a mismatch.

**Gallons by fuel**: Sum `gallons` across effective purchases for each canonical fuel class. Round to 2 decimal places.

**Source delta reconciliation**: Compare API (current) vs CSV (snapshot):
- `api_only_current` — purchase IDs only in API
- `csv_only_legacy` — purchase IDs only in CSV
- `csv_stale` — same ID in both but `record_status` differs
- `disagreement_transaction_keys` — transaction keys with different purchase-ID sets between API and CSV

**Zero-gallon purchases**: Purchases with `gallons = 0` are still effective and contribute to counts. List them in `zero_gallon_purchase_ids`.

### 3. Logistics Cost Event Audit

**Effective events**: Exclude void events and invalid events. There is no separate "superseded" concept for this domain (amended events are rare; check `amends_event_id`).

**Invalid events** (excluded with their issue types):
- `invalid_negative_amount` — amount < 0
- `missing_amount` — amount is null/missing
- `invalid_unit` — unit not in QR_COST_UNITS controlled list (`kg`, `lb`, `mile`, `shipment`, `claim`)
- `invalid_currency` — currency not in QR_CURRENCY rates

**Currency conversion**: Use the deterministic rates from `QR_CURRENCY` quality rule:
- USD × 1.0
- CAD × 0.74
- EUR × 1.08
- GBP × 1.27

Convert each effective event's amount to USD, **round to 2 decimal places (cents)**, then sum for totals. All USD outputs must have exactly 2 decimal places.

**Duplicate business keys**: Count business keys with >1 non-void, non-invalid effective candidate.

**Issue type counting**:
- `void_record` — count of void events in scope
- `amended_record` — count of amendment events (status `amended` or non-empty `amends_event_id`)
- `non_usd_currency` — count of effective events with currency ≠ USD
- `advisory_note` — count of events with `quality_notes` entries that are NOT invalidity markers
- Invalid-issue counts come from the invalid events

**Non-USD sample**: First 10 non-USD effective event IDs in ascending order.

### 4. Campaign Qualified Audience Summary

**Reconciliation flow**:
1. Fetch campaign members for the target campaign_id
2. Fetch CRM contacts for the matching batch_id
3. For each campaign member, look up the contact by `person_key`
4. Determine canonical contact row via source precedence (steward_corrected wins)
5. Classify each member as blocked, manual_review, or qualified_reachable

**Segment mapping**: Normalize `raw_segment` (trim, lowercase) and map to controlled values:
- Contains "enterprise" → `enterprise_renewal`
- Contains "strategic" → `strategic_renewal`
- Contains "smb" or "churn" → `smb_churn_risk`
- Contains "partner" → `partner`
- Contains "ops" → `ops_lead`
- Otherwise → `unknown`

**Domain counts**: From the canonical email domain (lowercase, after `@`) of **qualified reachable members only**. Include only domains with positive counts.

**Segment counts**: Count by canonical segment for **qualified reachable members only**. All six required keys must be present, using 0 for absent segments.

**Canonical member sample**: Only qualified reachable members. Populate `canonical_contact_row_id` with the `row_id` of the selected canonical CRM contact row.

### 5. Facilities Charge Audit

**Category alias matching**: Match `raw_category` to category aliases using **exact case-insensitive** matching (not substring). Unmatched raw categories resolve to `unknown`.

**Review reasons** (assign per charge):
- `ambiguous_alias` — raw_category matches multiple aliases (substring matching context; rare with exact matching)
- `superseded` — charge was replaced by an amendment (the void/original record gets this; count it in `review_reason_counts`)
- `source_conflict` — the charge's `description` text suggests a different category than the resolved canonical category
- `duplicate` — same `business_key` appears more than once in the scope (across all statuses)

**Superseded handling**: A void charge that is amended by another charge goes in `superseded_charge_ids`. The amendment record is effective.

**Top vendor**: Vendor with highest total `adjusted_spend_usd` among effective charges.

---

## Output Formatting Rules

### Ordering
- ID lists: **ascending** (lexicographic for string IDs like `CR_SPR_001`)
- Object arrays: sort by the primary key specified in each template (e.g., `person_key`, `event_id`, `charge_id`)
- Enum values in arrays: use template-declared enum order for issue types

### Numeric Precision
- Counts: integers only, no decimals
- USD amounts: exactly 2 decimal places (round each line-item conversion to cents before aggregation)

### Required Keys
- Objects with declared `required_keys` must include **all** keys even when value is 0 or empty list
- `additional_properties` is allowed unless the template explicitly sets it to `false`

### Top-Level Key Ordering
Follow the `required_top_level_keys` order from the answer template. The evaluator may check key ordering.

---

## Common Pitfalls

1. **Don't fetch only filtered API data** — always fetch the full dataset and filter client-side to catch edge cases in server-side filtering.
2. **Suppressed rows still appear in source_row_ids** of lineage audits — they are excluded from canonical selection but not from duplicate evidence.
3. **Steward override with steward_corrected wins** over normal source precedence — check quality_notes before applying the standard ranking.
4. **Currency conversion rounding** — round each event's converted USD amount to cents BEFORE summing. Don't sum raw amounts then round.
5. **Exact vs substring alias matching** — depends on domain. Fuel aliases use substring; category aliases use exact match.
6. **CSV vs API primacy** — the CSV export is a monthly snapshot; the API reflects current state. Both are needed for delta reconciliation.
7. **Zero-gallon/zero-amount records** — they are still effective and counted. They contribute to counts but not to gallon totals.
8. **Amendment status means "this IS the amendment"** — not "this was amended." The record with status `amended` is the replacement; the original is superseded.
9. **Duplicate campaign members** — highest score wins, not first-seen or alphabetical.
10. **normalization_changed** — a row is counted once if EITHER email or phone changes, not separately for each.
