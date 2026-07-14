# AsterOps Data-Quality Audit Skill

This skill covers the five AsterOps data-quality task families: CRM contact imports, fleet fuel purchases, logistics cost events, CRM campaign audiences, and facilities maintenance charges.

---

## Environment

### Base URL
```
GDPEVO_ENV_BASE_URL=http://34.46.77.124:9021
```
Use this remote URL for all API calls and downloads. Do not use localhost or any local env setup.

### API Catalog
`GET /api/catalog` — Returns all available endpoints, their fields, filters, and record counts, plus a list of downloadable CSV snapshots.

### API Endpoints (all support GET with optional query-param filters)

| Endpoint | Key Filter(s) | Records |
|---|---|---|
| `/api/crm/contact_rows` | `batch_id`, `person_key`, `source_system` | 164 |
| `/api/crm/campaign_members` | `campaign_id`, `person_key` | 91 |
| `/api/fleet/purchases` | `period`, `region`, `vehicle_id` | 235 |
| `/api/fleet/vehicles` | `active`, `region`, `vehicle_id` | 74 |
| `/api/logistics/cost_events` | `event_type`, `wave_id` | 276 |
| `/api/facilities/charges` | `period`, `scope` | 169 |
| `/api/reference/category_aliases` | — | 13 |
| `/api/reference/fuel_aliases` | — | 15 |
| `/api/reference/quality_rules` | — | 4 |

### CSV Downloads
Available at `/downloads/<name>` (no `/api/` prefix):
- `campaign_members_export.csv`
- `crm_contact_rows_export.csv`
- `fleet_purchases_export.csv`
- `fleet_vehicles_export.csv`
- `logistics_cost_events_export.csv`
- `facilities_charges_export.csv`
- `category_aliases.csv`
- `fuel_aliases.csv`

CSV exports are **snapshots** that may be stale compared to the current API state. Use them only when the task explicitly requires CSV-vs-API reconciliation.

### Health Check
`GET /api/health` — Returns `{"status": "ok", "generated_at": "..."}`.

---

## Cross-Cutting Business Rules

### 1. Record Lifecycle (applies to all task families)

Every domain uses the same record-status model:

| Field | Values | Meaning |
|---|---|---|
| `record_status` | `posted`, `void`, `amended` | Normal, deleted, or a replacement record |
| `amends_X_id` | empty or points to superseded record | The amendment replaces the referenced record |

**Effective-record algorithm** (same across fleet, logistics, facilities):
1. Exclude all records with `record_status = "void"`.
2. Identify superseded records: any record whose ID appears in another record's `amends_X_id` field is superseded — **unless** it is itself an amendment.
3. Exclude superseded records. Keep amended records (they are the replacements).
4. Remaining posted records (not void, not superseded) form the **effective set**.

**Pitfall**: A void record that is also referenced by `amends_X_id` should be excluded as void, not double-counted as superseded. The amendment is retained.

### 2. Source Precedence (CRM tasks)

When multiple contact rows share the same `person_key`, pick the **canonical** row by source-system precedence:

```
crm_verified > event_import > partner_roster > steward_override
```

Within the same source system, prefer the row with the **newest** `source_updated_at` date.

**Precedence override detection**: Compare the source-precedence pick against simply picking the newest row overall. If they differ, the person_key belongs in `precedence_override_person_keys`.

### 3. Contact Suppression Rules (CRM tasks)

A source contact row is **suppressed** (excluded from canonical consideration) when:
- `contact_status = "do_not_contact"`, OR
- `consent_status = "revoked"`

**Pitfall**: Suppress at the row level, not at the person level. A person_key with 3 rows where 1 is do_not_contact still has 2 active rows to pick from.

Rows that are suppressed but still have a usable normalized email or phone go into `suppressed_reachable_row_ids`.

### 4. Contactability / Reachability (CRM tasks)

A canonical person is **reachable** if, after normalization, either `email` or `phone` is non-empty (OR logic). If both are empty, the person is `dropped_unreachable`.

In campaign-audience tasks, a member with no matching contact row at all goes to `needs_manual_review`.

### 5. Normalization Rules (CRM tasks)

**Email**: Trim outer whitespace, then lowercase. Example: `" Opted@example.COM "` → `"opted@example.com"`.

**Phone**: Remove all non-digit characters. Preserve country-code digits. Example: `"+1-312-555-0166"` → `"13125550166"`.

Rows whose **nonblank** raw email or phone value differs from its normalized form belong in `normalization_changed_row_ids`.

### 6. Alias Resolution (fleet fuel + facilities category)

**Matching**: Case-insensitive exact match of the source description to alias entries.

**Priority**: Sort matching aliases by `priority` descending. The highest-priority alias wins.

**Issue flags**:
| Condition | Flag |
|---|---|
| Multiple aliases tied at the same top priority | `priority_overlap` |
| The generic `"unleaded"` alias (priority 50) matches AND a more specific unleaded alias (e.g. `"unleaded regular"`, priority 80) also matches | `generic_unleaded_trap` — select the more specific one |
| Selected alias maps to `canonical_fuel = "unknown"` | `selected_unknown_alias` |
| No alias matches the description at all | `unmapped_description` — classify as `unknown` fuel/category |

**Pitfall**: `"Unleaded regular"` matches both `"unleaded regular"` (priority 80) and `"unleaded"` (priority 50). The higher priority wins; this is the correct behavior. The `generic_unleaded_trap` flag is for auditing that the fallback-to-generic path was avoided.

### 7. Fuel Alias Reference

| Alias | Canonical Fuel | Priority |
|---|---|---|
| renewable diesel b20 | diesel | 98 |
| renewable diesel | diesel | 95 |
| b20 | diesel | 93 |
| diesel | diesel | 90 |
| premium unleaded | premium_unleaded | 92 |
| super unleaded | premium_unleaded | 91 |
| regular unleaded | unleaded | 80 |
| unleaded regular | unleaded | 80 |
| unleaded | unleaded | 50 |
| ev fast charge | electric | 97 |
| ev charge | electric | 95 |
| electric | electric | 80 |
| hybrid service fuel | hybrid | 88 |
| fuel service | unknown | 10 |
| misc fuel | unknown | 5 |

### 8. Category Alias Reference

| Alias | Canonical Category | Priority |
|---|---|---|
| diesel fuel | fuel | 95 |
| fuel | fuel | 90 |
| preventive maintenance | maintenance | 95 |
| repair | maintenance | 85 |
| freight | freight | 90 |
| linehaul | freight | 88 |
| accessorial | accessorial | 92 |
| detention | accessorial | 90 |
| damage claim | claim | 95 |
| claim | claim | 90 |
| regulatory fee | tax_fee | 88 |
| tax | tax_fee | 80 |
| misc | unknown | 10 |

### 9. Fleet Vehicle Fuel Matching

For each effective purchase:
1. Resolve `product_description` → `canonical_fuel` via alias matching.
2. Look up the vehicle's `expected_fuel`.
3. If `canonical_fuel != expected_fuel`:
   - If `exemption_code != "none"` → **exception** (not a mismatch)
   - Otherwise → **mismatch**
4. Zero-gallon purchases are still effective and count toward totals.

### 10. Currency Conversion (logistics)

Fixed USD conversion rates from quality rule `QR_CURRENCY`:

| Currency | USD Rate |
|---|---|
| USD | 1.00 |
| CAD | 0.74 |
| EUR | 1.08 |
| GBP | 1.27 |

Convert each source amount: `usd = round(amount × rate, 2)`. Aggregate after conversion.

### 11. Invalid Data Detection (logistics, facilities)

| Condition | Issue Type |
|---|---|
| `amount < 0` | `invalid_negative_amount` |
| `amount` is null/empty/missing | `missing_amount` |
| `unit` not in valid set | `invalid_unit` |
| `currency` not in known rates | `invalid_currency` |

Valid logistics units: `kg`, `lb`, `mile`, `shipment`, `claim`.

**Invalid records are excluded from effective counts and totals.**

### 12. Segment Mapping (campaign audiences)

Map `raw_segment` to canonical segments. Trim whitespace first. Normalization: match case-insensitively after collapsing separators.

| Raw Pattern | Canonical Segment |
|---|---|
| `Renewal - Enterprise`, `Enterprise Renewal Duplicate`, `Enterprise`, standalone `renewal` (no strategic/enterprise modifier) | `enterprise_renewal` |
| `renewal / strategic` | `strategic_renewal` |
| `SMB churn risk`, `SMB` | `smb_churn_risk` |
| `Partner` (with optional trailing space) | `partner` |
| `Ops-lead` (with optional hyphen or space variation) | `ops_lead` |
| Unrecognized | `unknown` |

### 13. Campaign Member Blocking and Deduplication

**Hard-blocked member_status values**: `bounced` and `unsubscribed` members are immediately blocked. They go into `blocked_or_suppressed_ids` (and `suppressed_or_bounced_member_ids` in the decision audit).

**Deduplication rule**: When a `person_key` has multiple campaign members:
1. Exclude blocked members first.
2. Among remaining members, prefer by status: `attended > registered > no_show`.
3. The highest-priority member is canonical; all others go to `needs_manual_review` (and `duplicate_member_manual_review_ids`).

**Member-to-contact reconciliation**: Each campaign member must find a matching contact row by `person_key`. If no contact row exists at all → `needs_manual_review`. If the canonical contact for that person is suppressed (do_not_contact or revoked consent) → `blocked_or_suppressed_ids`. If the canonical contact has `quality_notes` containing `"suppressed"` → also blocked.

**Canonical contact_status values**: After determining the canonical row for a person_key, assign one of:
- `retained` — reachable (has email or phone), not suppressed
- `dropped_unreachable` — no email AND no phone after normalization
- `suppressed` — the canonical row itself is do_not_contact or revoked (rare; usually suppressed rows are excluded before canonical selection)
- `manual_review` — the contact has unresolved data-quality issues that need human judgment

### 14. Quality Notes Codes (CRM)

The `quality_notes` field in contact rows is a string array. Known codes:

| Code | Meaning |
|---|---|
| `case_email` | Email uses mixed case — normalization will change it |
| `duplicate_person` | This person_key has multiple source rows |
| `missing_channel` | No email and no phone — unreachable |
| `suppressed` | Row is do_not_contact |
| `revoked_consent` | Consent has been revoked |
| `fresh_source` | Normal record |
| `stale_status` | Row has inactive contact_status |
| `steward_corrected` | Row was corrected by a steward (steward_override source) |

Use these to cross-validate your algorithm but do not rely on them as the sole signal — detect conditions from actual field values.

### 15. Quality Flags Counting (CRM contact import audits)

The `quality_flags` section counts source-level issues. Count from actual field values, not solely from quality_notes:

| Flag | How to Count |
|---|---|
| `raw_row_count` | Total rows in the filtered batch |
| `canonical_person_count` | Distinct person_keys after suppression |
| `duplicate_person_groups` | Person_keys with >1 active row |
| `duplicate_source_rows` | Sum of (group_size - 1) across duplicate groups |
| `missing_channel_rows` | Rows where both email AND phone are blank after trimming |
| `suppression_rows` | Rows with do_not_contact OR revoked consent |
| `email_normalization_rows` | Rows with nonblank email whose normalized form differs from trimmed raw |
| `phone_normalization_rows` | Rows with nonblank phone whose normalized form differs from trimmed raw |
| `stale_or_inactive_rows` | Rows with contact_status = `inactive` |

### 16. CSV vs API Reconciliation (fleet purchases)

When the task requires comparing API data against the CSV export snapshot:

| Category | Meaning |
|---|---|
| `api_only_current_purchase_ids` | In API, not in CSV |
| `csv_only_legacy_purchase_ids` | In CSV, not in API |
| `csv_stale_purchase_ids` | In both, but `record_status` differs between API and CSV |
| `csv_records_excluded_from_operational_totals` | CSV records excluded because they're stale or superseded in API |
| `source_disagreement_transaction_keys` | Transaction keys where API and CSV differ in any meaningful field (record_status, amounts, descriptions, vendor, or purchase-ID composition) |

Reconciliation statuses: `api_current_replaces_stale_csv`, `csv_only_legacy`, `csv_extra_legacy`, `csv_stale_status`.

---

## Output Formatting Conventions

### Sorting (apply AFTER computing values)
- **ID lists**: Ascending string sort (e.g., `charge_id`, `purchase_id`, `event_id`, `member_id`, `row_id`).
- **Object lists**: By the primary key specified in the template, always ascending (e.g., `person_key`, `event_id`, `charge_id`, `purchase_id`).
- **City counts**: Top 3 by count descending, then by city name ascending for ties.
- **Transaction reconciliation**: By `transaction_key` ascending.
- **Alias resolution trace**: By `purchase_id` ascending.
- **Non-USD sample**: First 10 non-void events with a non-USD currency, by `event_id` ascending.
- **Invalid event issue types**: Within each event, order issue types in template enum order: `invalid_negative_amount`, `missing_amount`, `invalid_unit`, `invalid_currency`.
- **Review reasons**: Within each charge, order by enum label ascending.

### Numeric Precision
- **USD amounts**: Exactly 2 decimal places (round to cents).
- **Gallon totals**: Exactly 2 decimal places.
- **Counts**: Integers only, no decimal places.

### Enums
Use the exact enum string values from the answer template. Do not invent new values. Allowed values are listed in each template under `allowed_values`, `controlled_enums`, or `*_enum` fields.

---

## Task-Family Summary

| Family | Key Filter | Core Concept |
|---|---|---|
| CRM contact import | `batch_id` | Suppress bad rows, deduplicate people by source precedence, normalize contacts, assess reachability |
| Fleet fuel purchases | `region` + period | Resolve fuel aliases, detect vehicle/fuel mismatches, handle amendments, reconcile API vs CSV |
| Logistics cost events | `wave_id` | Exclude void/invalid events, convert non-USD to USD at fixed rates, detect duplicates by business key |
| CRM campaign audience | `campaign_id` | Reconcile members to contacts, deduplicate people, block suppressed/bounced, map segments |
| Facilities charges | `scope` + period | Exclude void/superseded charges, resolve category aliases, compute adjusted USD spend |

---

## Common Pitfalls

1. **Double-excluding superseded records**: A void record that is also superseded should only be excluded once. The void exclusion takes precedence.
2. **Including suppressed contacts in canonical selection**: Do-not-contact and revoked-consent rows must be filtered out before picking the canonical row for a person_key.
3. **Phone normalization with country codes**: `+1-312-555-0166` → `13125550166`, not `3125550166`. Keep all digits.
4. **Email normalization with leading/trailing spaces**: Strip BEFORE lowercasing. `" opted+event@example.com"` → `"opted+event@example.com"`.
5. **Generic unleaded trap**: When `"Unleaded regular"` matches both "unleaded regular" and "unleaded", the higher-priority "unleaded regular" wins. This is the correct resolution; the trap flag is for audit traceability.
6. **Alias matching is exact (case-insensitive)**: `"Unleaded regular"` does NOT match `"regular unleaded"`. They are separate alias entries.
7. **Non-USD currencies are NOT invalid**: CAD, EUR, GBP events with valid amounts are legitimate — they just need conversion. Only completely unrecognized currencies are invalid.
8. **Zero gallons is not an error**: Zero-gallon purchases (e.g., EV charging recorded with 0 gallons) are still effective and count toward totals under their canonical fuel.
9. **Inactive contact status is not suppression**: Only `do_not_contact` and `revoked` consent suppress. `inactive` contact_status still allows the row to be canonical.
10. **Amendment records are effective**: A record with `record_status = "amended"` and a non-empty `amends_X_id` IS included in the effective set (it's the replacement). Only the superseded original is excluded.
11. **CSV-as-snapshot staleness**: CSV exports may lag behind API state. Use the API as the authoritative current state and treat CSV deviations as reconciliation items.
12. **Rounding aggregation order**: Convert individual amounts to USD and round to cents BEFORE summing. Do not sum raw amounts and round the total.
