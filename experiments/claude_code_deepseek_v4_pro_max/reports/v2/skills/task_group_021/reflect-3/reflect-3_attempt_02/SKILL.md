# AsterOps Data-Quality Audit Skill

## Environment & Data Access

All tasks share a remote AsterOps workbench exposing REST APIs and downloadable CSV snapshots.

**Base URL**: use the `<TASK_ENV_BASE_URL>` provided in the task prompt.

**Always call these endpoints first:**
- `GET /api/health` — confirm the environment is live.
- `GET /api/catalog` — lists every available API endpoint, its fields, filters, and record counts, plus the list of downloadable CSV exports.

**Data fetching pattern:**
- Use API endpoints with query-string filters (e.g. `?batch_id=...`, `?region=north&period=2026-07`, `?wave_id=...`, `?scope=...&period=...`) to retrieve the in-scope slice.
- Download CSVs from `/downloads/<filename>` when a task references "shared CSV downloads" or when source-delta reconciliation is required.
- Always treat API data as the **current** source of truth; CSV exports are **monthly snapshots** that may be stale.

---

## Record Lifecycle: Void / Amended / Superseded

Every task family uses the same record-status model (from quality rule `QR_EFFECTIVE_RECORDS`):

| status     | meaning |
|------------|---------|
| `posted`   | normal active record |
| `void`     | permanently excluded, never counts toward totals |
| `amended`  | replacement record; its `amends_*_id` field points to the original |

**Effective-record rule:** A record is _effective_ when it is NOT void and NOT superseded by an in-scope amendment. The amendment record replaces the original for all aggregations (gallons, spend, counts).

**Cross-scope amendments:** An amendment whose `amends_*_id` points to a record _outside_ the filtered scope is still effective within scope — there is no in-scope record to supersede.

---

## Source Precedence & Duplicate Resolution

### Contact Row Precedence (CRM tasks)

When multiple source rows exist for the same `person_key`, select the canonical row by this order:

1. `crm_verified`
2. `event_import`
3. `partner_roster`
4. `steward_override`

**Steward correction override:** A row with `source_system = "steward_override"` AND `"steward_corrected"` in its `quality_notes` list wins over source precedence. When steward correction is active, the lineage decision is `"active_steward_correction"`; otherwise it is `"source_precedence_override"`.

**Precedence-override person keys:** A duplicate person key belongs in `precedence_override_person_keys` when the source-precedence choice differs from the newest-row (by `source_updated_at`) choice, **unless** steward correction is active — steward-corrected persons are excluded from this list.

### Duplicate Campaign Members

When multiple campaign members share the same `person_key`:
- The member with the **highest score** is the canonical retained member.
- Lower-scoring duplicate members go to `needs_manual_review_ids`.

---

## Suppression Rules (CRM / Campaign Tasks)

**Row-level suppression:** A source row is suppressed when `contact_status = "do_not_contact"` OR `consent_status = "revoked"`. Suppressed rows are listed in `suppressed_contact_ids` (sorted ascending).

**Person-level suppression:** A person is suppressed ONLY when **every** one of their contact rows is suppressed. If at least one row is non-suppressed, the person is NOT suppressed.

**Campaign member blocking:** A campaign member is hard-blocked when:
- `member_status` is `"unsubscribed"`, OR
- The person's contacts are all suppressed (person-level suppression).

**Manual review:** A campaign member needs manual review when:
- `member_status` is `"bounced"` (and the person is not person-suppressed), OR
- The member is a lower-scoring duplicate for the same `person_key`.

---

## Contact Normalization

**Email:** Trim outer whitespace, then lowercase. Use `""` when no email exists.

**Phone:** Remove every non-digit character. Preserve any country-code digits present in the source. Use `""` when no phone exists.

**Normalization tracking:** A source row's email or phone "changes under normalization" when the raw value is nonblank AND the normalized value differs from the raw value. Count these per-row for `email_normalization_rows` and `phone_normalization_rows` quality flags.

---

## Alias Resolution Patterns

### Fuel Aliases (Fleet)

The `/api/reference/fuel_aliases` and `fuel_aliases.csv` provide alias→canonical-fuel mappings with integer priority (higher = more specific). The alias matching uses **case-insensitive substring** matching: an alias matches a product description when the alias string appears inside the lowercased description. When multiple aliases match, the one with the highest priority wins.

**Alias issue types:**
- `priority_overlap` — more than one alias matched
- `generic_unleaded_trap` — the generic alias `"unleaded"` matched alongside a more specific unleaded alias (e.g. `"unleaded regular"` or `"premium unleaded"`)
- `selected_unknown_alias` — the winning alias maps to `unknown` fuel
- `unmapped_description` — no alias matched the description at all

### Category Aliases (Facilities)

The `/api/reference/category_aliases` and `category_aliases.csv` map `raw_category` values to canonical categories. Match the **lowercased raw_category exactly** against the lowercased alias. Aliases with higher priority win ties, but exact-match resolution typically produces zero or one match per raw category value.

---

## Currency Conversion (Logistics)

Rates come from quality rule `QR_CURRENCY`:

| Currency | USD Rate |
|----------|----------|
| USD      | 1.00     |
| CAD      | 0.74     |
| EUR      | 1.08     |
| GBP      | 1.27     |

**Conversion rule:** For each effective event, multiply `amount × rate`, round to **2 decimal places** (cents), then sum for totals. Report all USD values with exactly two decimal places.

---

## Invalid Records & Exclusion

### Logistics Cost Events

A candidate event is **invalid** (excluded from effective set) when any of these hold:
- `amount < 0` → `invalid_negative_amount`
- `amount` is null/missing → `missing_amount`
- `unit` is not in `{kg, lb, mile, shipment, claim}` → `invalid_unit`
- `currency` is not in `{USD, CAD, EUR, GBP}` → `invalid_currency`

Invalid events go into `invalid_event_ids` (ascending) with their issue types in `invalid_event_issue_types`. Issue types within each event follow the template enum order: `invalid_negative_amount`, `missing_amount`, `invalid_unit`, `invalid_currency`.

---

## Output Ordering & Sorting Rules

These conventions apply across all task families:

| Field type | Sort order |
|------------|------------|
| ID lists (`*_ids`, `*_purchase_ids`, etc.) | Ascending string sort |
| Person keys | Ascending string sort |
| Event/charge IDs in arrays | Ascending string sort |
| Canonical contacts / member samples | Ascending by `person_key` |
| Vehicle review queue | Ascending `vehicle_id`, then ascending `observed_fuel` |
| City retained counts | Top 3 by count descending, then city name ascending for ties |
| Top N selections | By metric descending, then name/key ascending for ties |
| Transaction reconciliation | Ascending `transaction_key` |
| Operations load decision audit | Ascending `purchase_id` |

---

## Source Delta & Reconciliation (Fleet / Multi-Source Tasks)

When both API and CSV data are available for the same scope:

1. **api_only_current** — record IDs present in the API but absent from the CSV export.
2. **csv_only_legacy** — record IDs present in the CSV but absent from the API.
3. **csv_stale** — record IDs present in both sources where the CSV `record_status` differs from the API `record_status`.
4. **source_disagreement_transaction_keys** — transaction keys whose purchase-ID sets differ between API and CSV.
5. **csv_records_excluded_from_operational_totals** — CSV records that the API marks as void or superseded.

Transaction reconciliation uses statuses: `api_current_replaces_stale_csv`, `csv_only_legacy`, `csv_extra_legacy`, `csv_stale_status`.

---

## Segment Mapping (Campaign)

Map `raw_segment` to canonical segment by lowercased keyword:

| raw_segment contains | canonical_segment |
|---------------------|-------------------|
| `enterprise`        | `enterprise_renewal` |
| `strategic`         | `strategic_renewal` |
| `smb` or `churn`    | `smb_churn_risk` |
| `partner`           | `partner` |
| none of the above   | `unknown` |

---

## Common Pitfalls

1. **Person vs row suppression** — do NOT suppress a person just because one of their rows is `do_not_contact`. Check ALL rows.
2. **Steward correction trumps source precedence** — when `"steward_corrected"` appears in quality_notes, that row is canonical regardless of its source system.
3. **Steward-corrected persons are NOT in precedence_override** — the steward actively chose the row, so there is no "precedence" question to flag.
4. **Cross-scope amendments** — an amendment record that amends an out-of-scope record is still effective within scope. Do not treat the out-of-scope original as superseded within scope.
5. **Void records in CSV** — the CSV snapshot may still show `posted` for records the API has since voided. Trust the API for effective-record determination.
6. **Rounding before aggregation** — convert each individual line to USD cents (round to 2dp) before summing. Do not sum raw amounts and round only at the end.
7. **Normalization scope** — only count normalization changes for rows whose raw value is nonblank AND differs from the normalized value. Blank-to-blank is not a change.
8. **Top-N tiebreaking** — when selecting top entities by a numeric metric, break ties by the entity's name/key in ascending order.
9. **Required keys with zero values** — when the answer template lists required keys for a count/spend object, include every key even when the value is 0 or 0.0.
10. **Rely on the catalog** — always fetch `/api/catalog` first to discover available endpoints, filters, and record counts before querying.
