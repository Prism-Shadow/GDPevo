# AsterOps Data-Quality Audit Skill

## Environment

All tasks use a shared AsterOps workbench exposing REST APIs and CSV downloads. Start every task by calling `GET /api/catalog` to discover available endpoints, their field schemas, filter parameters, and record counts. Also fetch `GET /api/reference/quality_rules` — it contains currency conversion rates, controlled vocabularies (record statuses, consent/contact statuses, valid units), and domain-specific rules that govern data validation.

Download CSVs via `GET /downloads/<filename>` using the filenames listed in the catalog's `downloads` array. CSVs represent monthly snapshot exports and may diverge from the live API — always reconcile the two when a task mentions a monthly export or snapshot.

## Record Lifecycle: Void, Amendment, and Effective Sets

The `QR_EFFECTIVE_RECORDS` quality rule defines three record statuses:

| Status | Meaning | Action |
|--------|---------|--------|
| `posted` | Normal record | Include in effective set |
| `void` | Deleted/invalidated record | Exclude from effective set |
| `amended` | Replacement for an earlier record | Include in effective set; the record it amends (via `amends_*_id`) is **superseded** and excluded |

To build the effective set for any domain:
1. Exclude all `void` records.
2. Exclude all records whose ID appears as an `amends_*_id` on another record (these are superseded).
3. Amendment records themselves remain in the effective set.

When a record is void in the API but appears as `posted` in a CSV export, treat the CSV version as **stale** — the API is the current source of truth.

## Source Precedence for CRM Contacts

When multiple contact rows share a `person_key`, select one canonical row using **source precedence** (not newest-first):

```
steward_override > crm_verified > event_import > partner_roster
```

If a person has a `steward_override` row with quality note `steward_corrected`, that row is the canonical. The `source_precedence_override` lineage decision applies when source precedence picks a different row than choosing the newest by `source_updated_at`. Use `active_steward_correction` when the steward row is both the newest and the highest-precedence row in a duplicate group.

Rows with `contact_status = "do_not_contact"` or `consent_status = "revoked"` are **suppressed at the row level**. When selecting a canonical for a person who has both suppressed and non-suppressed rows, pick from the non-suppressed pool only. The person is suppressed only if ALL their rows are suppressed.

## Field Normalization Rules

**Email**: Trim outer whitespace, then lowercase. Store as empty string `""` when no email exists.

**Phone**: Strip all non-digit characters. Preserve any country-code digits present in the source (e.g., `+1-312-555-0166` → `13125550166`). Store as empty string `""` when no phone exists.

**Segment mapping** (campaign `raw_segment` to canonical segment): Match case-insensitive keywords in priority order — `enterprise` → `enterprise_renewal`, `strategic` → `strategic_renewal`, `smb` or `churn` → `smb_churn_risk`, `partner` → `partner`, `ops` → `ops_lead`. Fallback is `unknown`.

## Alias Resolution (Fuel and Category)

Reference alias tables (`/api/reference/fuel_aliases`, `/api/reference/category_aliases`) map free-text descriptions to controlled enums. Each alias has a `priority` integer; when a source value matches multiple aliases, select the one with the **highest priority**.

**Matching strategy**: Match the source value against alias strings using **case-insensitive exact match** (lowercase both sides and compare equality). The source field to match depends on the domain — for fleet purchases use `product_description`, for facilities charges use `raw_category`.

When a source value matches no alias, classify it as `unknown` and flag it as unmapped.

## Currency Conversion

Use the deterministic rates from the `QR_CURRENCY` quality rule. The environment exposes rates as a JSON object mapping currency codes to USD multipliers:

| Currency | USD Rate |
|----------|----------|
| USD | 1.00 |
| CAD | 0.74 |
| EUR | 1.08 |
| GBP | 1.27 |

**Rounding rule**: Convert each individual record's amount to USD and round to **cents** (2 decimal places) before summing. Then round all aggregate totals to 2 decimal places.

## Data Validation and Invalid Records

Records are **invalid** (excluded from effective totals) when they have:
- **Negative amount**: `amount < 0`
- **Missing amount**: `amount` is null/absent
- **Invalid unit**: `unit` is not in the controlled unit list from `QR_COST_UNITS` (logistics: `kg`, `lb`, `mile`, `shipment`, `claim`)
- **Invalid currency**: currency code not in the rates table

These are distinct from void/superseded records. Track both in separate lists. Issue-type counts span ALL in-scope records (not just the effective set).

## API and CSV Reconciliation

When a task references a "monthly export snapshot" or similar, compare the live API results against the corresponding CSV download:

- **API-only records**: Present in the API but absent from the CSV (e.g., amendment records created after the snapshot).
- **CSV-only records**: Present in the CSV but absent from the API (e.g., legacy source system records).
- **CSV-stale records**: Records that are `void` or superseded in the API but still appear as `posted` in the CSV.
- **Disagreement transaction keys**: Transaction keys whose records differ between API and CSV (different status, different amounts, or different record sets).

The API is authoritative for operational totals; CSV-only and CSV-stale records are excluded from operational metrics.

## Campaign Audience Reconciliation

When reconciling campaign members to CRM contacts:

1. **Blocked/suppressed**: Members with `member_status` of `bounced` or `unsubscribed`, OR whose canonical contact has `contact_status = "do_not_contact"` or `consent_status = "revoked"`.
2. **Needs manual review**: Non-canonical duplicate members (same `person_key`, multiple campaign member rows). For duplicates, select the canonical member by `member_status` priority (`attended` > `registered` > `no_show` > `bounced` > `unsubscribed`), then by higher `score`.
3. **Qualified reachable**: Not blocked, not needing review, and has at least one usable contact channel (non-empty normalized email or phone).

The `qualified_reachable_count` counts **unique people** (distinct `person_key` values), not campaign member rows.

## Output Conventions

### Ordering
- All ID lists (row IDs, event IDs, charge IDs, purchase IDs, member IDs): **ascending alphanumeric**.
- Person key lists: **ascending**.
- Canonical contact samples and lineage entries: sort by `person_key` ascending.
- Vehicle review queue entries: by `vehicle_id` ascending, then `observed_fuel` ascending.
- Transaction reconciliation entries: by `transaction_key` ascending.
- Invalid event issue types within a record: follow the template's enum declaration order: `invalid_negative_amount`, `missing_amount`, `invalid_unit`, `invalid_currency`.

### Numeric Precision
- All counts: integers (no decimal places).
- All USD amounts: exactly 2 decimal places.
- Gallon totals: round to 2 decimal places.

### Required Keys
Always include every key listed in the answer template's `required_*_keys` arrays — even when the value is 0, an empty list, or an empty object. The output must match the template's declared shape exactly.

### Enums
Use only the controlled values declared in each template's `allowed_values` or `controlled_enums` sections. Never invent new enum values.

## Common Pitfalls

1. **Source precedence vs newest-first**: The default canonical selection rule for CRM contacts is source precedence, not picking the newest row. Check whether precedence changes the outcome vs. newest-first for the `precedence_override` audit field.

2. **Row-level vs person-level suppression**: A `do_not_contact` row does not necessarily suppress the entire person — look for steward corrections or other active rows for the same `person_key`.

3. **Duplicate row counting**: "Duplicate source rows" means rows **beyond the first** in each duplicate person-key group. A group of 3 rows contributes 2 to the duplicate count.

4. **Void vs invalid**: Void records are excluded because of their `record_status`. Invalid records are excluded because of bad data values (negative/missing amount, bad unit, bad currency). They are tracked in different lists.

5. **Amendment direction**: The record with `amends_*_id` set IS the effective replacement. The record whose ID appears as someone else's `amends_*_id` is the superseded original.

6. **Alias matching is exact**: `"Diesel generator fill"` does NOT match alias `"diesel"` — the strings must be identical after lowercasing. This produces unmapped descriptions that need separate tracking.

7. **Rounding aggregation order**: Convert and round each record individually, then sum. Do not sum raw amounts and convert/round once at the end.

8. **CSV snapshot staleness**: Treat the API as authoritative. CSV records that disagree with the API are excluded from operational totals and flagged in reconciliation.
