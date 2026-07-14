# AsterOps Data-Quality Skill (fewshot)

Transferable rules distilled from five train task families: CRM contact import audit, fleet fuel mismatch audit, logistics cost integrity audit, campaign audience qualification, and facilities charge cleanup.

---

## Environment

| Setting | Value |
|---|---|
| Base URL | `http://34.46.77.124:9021` |
| Health | `GET {base}/api/health` |
| Catalog | `GET {base}/api/catalog` — lists all endpoints, fields, filters, and download filenames |
| Downloads | `GET {base}/downloads/{filename}` — CSV exports (snapshot, may differ from API) |

Do NOT start a local env, use localhost, or read env source directories. The remote HTTP API is the sole data source. The catalog is your first call — it tells you which endpoints exist and how to filter them.

---

## Data Domains & Endpoints

| Domain | Endpoint | Key Filters |
|---|---|---|
| CRM contact rows | `/api/crm/contact_rows` | `batch_id`, `person_key`, `source_system` |
| CRM campaign members | `/api/crm/campaign_members` | `campaign_id`, `person_key` |
| Fleet purchases | `/api/fleet/purchases` | `period`, `region`, `vehicle_id` |
| Fleet vehicles | `/api/fleet/vehicles` | `active`, `region`, `vehicle_id` |
| Logistics cost events | `/api/logistics/cost_events` | `wave_id`, `event_type` |
| Facilities charges | `/api/facilities/charges` | `scope`, `period` |
| Fuel aliases | `/api/reference/fuel_aliases` | (no filter needed; returns all 15 rows) |
| Category aliases | `/api/reference/category_aliases` | (no filter needed; returns all 13 rows) |
| Quality rules | `/api/reference/quality_rules` | `domain`, `rule_id` |

**CSV download filenames** (from catalog `downloads` array):
`campaign_members_export.csv`, `category_aliases.csv`, `crm_contact_rows_export.csv`, `facilities_charges_export.csv`, `fleet_purchases_export.csv`, `fleet_vehicles_export.csv`, `fuel_aliases.csv`, `logistics_cost_events_export.csv`

CSV exports may contain stale or legacy records not present in the API. The API is the authoritative "current" view.

---

## Universal Business Rules

### 1. Record Lifecycle (all domains)

Every domain uses `record_status` with three values (per QR_EFFECTIVE_RECORDS):
- **`posted`** — normal, active record. Included in effective counts.
- **`void`** — excluded from all effective counts, totals, and aggregations. Tracked in audit lists.
- **`amended`** — a replacement record. Its `amends_*` field points to the superseded record. An amendment takes the place of the original; the original is excluded from effective operations.

**Amendment handling**: When a record has `record_status: "amended"` with `amends_X_id: "ORIG"`, then ORIG is superseded and the amendment is the effective record. In the effective set, exclude the superseded original, include the amendment.

### 2. Canonical Alias Resolution (fuel & category domains)

Alias reference tables have fields: `alias`, `canonical_{fuel|category}`, `priority`, plus optional `notes`.

**Matching**: Case-insensitive comparison between the raw description string (lowercased) and alias entries.

**Priority selection**: When a raw description matches multiple aliases, use the **highest priority** match. The `selected_alias` in audit traces is the alias string that won.

**Priority overlap**: When multiple aliases match with different priorities → record is flagged as `priority_overlap`. If the winning alias has a higher priority than a lower-priority match, it's still a priority_overlap — the resolution was nontrivial.

**Generic unleaded trap**: The alias `"unleaded"` (canonical `unleaded`, priority 50) is generic. Any purchase whose description matches both a specific unleaded alias (priority ≥80, like `"unleaded regular"` or `"regular unleaded"`) AND the generic `"unleaded"` (priority 50) creates a `generic_unleaded_trap`. The trap is recorded regardless of which alias won — when the specific unleaded alias wins, it's a trap because had the generic been selected, the result would be the same (`unleaded`) but the trace would be different.

**Unmapped descriptions**: Descriptions matching no alias → canonical `unknown`. These are flagged as `unmapped_description`.

**Ambiguous unknown match**: When a description matches an alias whose canonical is `unknown` alongside other aliases → `ambiguous_unknown_matches`.

### 3. CRM Source Precedence

When a person has multiple source rows, the canonical row is selected by source precedence (highest first):
1. `crm_verified`
2. `steward_override`
3. `event_import`
4. `partner_roster`

If two rows have the same source system, the one with the most recent `source_updated_at` wins.

**Precedence override**: If the selected row differs from what would be selected by simply picking the newest `source_updated_at` row regardless of source, that person_key is a precedence override.

### 4. Contact Suppression / Blocking

A person or campaign member is blocked/suppressed when:
- `contact_status: "do_not_contact"` (any row or the canonical row)
- `consent_status: "revoked"` (any row or the canonical row)
- Campaign member `member_status: "bounced"` or `"unsubscribed"`

Suppressed rows that still have a usable (non-empty after normalization) email or phone are flagged as `suppressed_reachable_row_ids`.

### 5. Contact Reachability

A person is **unreachable** (dropped) when, after normalization of the canonical row:
- Normalized email is empty string **AND**
- Normalized phone (digits only) is empty string

### 6. Normalization Rules

| Field | Rule |
|---|---|
| email | Trim outer whitespace, lowercase. Empty string if no email. |
| phone | Remove ALL non-digit characters. Preserve country code digits present in source. Empty string if no phone. |
| domain | Extract from canonical email: everything after `@`, lowercased. |
| city | As-is from canonical row. |
| Normalization changed | A row is `normalization_changed` if its non-blank email or phone value changes under the normalization rules. |

### 7. Currency Conversion (logistics domain)

Per QR_CURRENCY, use deterministic rates:

| Currency | USD Rate |
|---|---|
| USD | 1.00 |
| CAD | 0.74 |
| EUR | 1.08 |
| GBP | 1.27 |

**Conversion method**: `usd_amount = round(source_amount * rate, 2)` — round to cents BEFORE aggregation. Then sum the rounded values for totals.

### 8. Valid/Invalid Data Detection (logistics & facilities)

**Invalid records** (excluded from effective set, listed in invalid IDs):
- `amount < 0` → `invalid_negative_amount`
- `unit` NOT in the controlled unit enum (`kg`, `lb`, `mile`, `shipment`, `claim`) → `invalid_unit`
- Missing/null `amount` → `missing_amount`
- `currency` not recognized → `invalid_currency`

Records with invalid data are excluded even if `record_status` is `posted`. They are NOT effective.

### 9. Vehicle Fuel Mismatch (fleet domain)

Compare the purchase's **canonical fuel** (determined via fuel alias resolution) against the vehicle's **`expected_fuel`** from the vehicle registry.

- **Match** → no review needed.
- **Mismatch** AND vehicle `exemption_code == "none"` → `mismatch_review` (owner: `regional_ops`).
- **Mismatch** AND vehicle `exemption_code != "none"` → `exception_documented` (owner: `none`, `metric_effect: "included_exception_not_mismatch"`). These are **exceptions**, not mismatches.
- **Zero gallons** → tracked in `zero_gallon_purchase_ids` but still effective.

**Exception purchase IDs** are those kept out of the mismatch queue because of vehicle exceptions or amendment handling — NOT because the fuel matches.

### 10. Source Delta Reconciliation (API vs CSV)

When a task involves both API data and CSV exports:

- **`api_only_current`**: Purchase IDs in API but NOT in CSV (e.g., fresh amendments created after the CSV snapshot).
- **`csv_only_legacy`**: Purchase IDs in CSV but NOT in API (legacy records from old source systems, like `legacy_monthly_export`).
- **`csv_stale`**: Same purchase ID appears in both, but CSV shows `posted` while API shows `void` or `amended` — the CSV is a stale snapshot.
- **`source_disagreement_transaction_keys`**: Transaction keys where API and CSV records differ.

CSV records that are csv_only_legacy or csv_stale are **excluded from operational totals**.

### 11. Duplicate Detection

- **Person duplicates** (CRM): Person keys with more than one source row in the batch → duplicate group. Count groups, not rows. `duplicate_source_rows` = total source rows in duplicate groups minus the number of groups (the "extra" rows beyond the first per group).
- **Business key duplicates** (logistics): Business keys with more than one non-void, non-invalid effective candidate.
- **Campaign member duplicates**: Person keys appearing in more than one campaign member row → needs manual review.

### 12. Quality Notes / Annotations

The `quality_notes` array on records provides audit annotations. Common values and their meanings:
- `"duplicate_person"` — this row is one of multiple rows for the same person
- `"revoked_consent"` — consent has been revoked → suppression
- `"suppressed"` — do-not-contact → suppression
- `"stale_status"` — inactive contact → possible staleness
- `"missing_channel"` — no email and no phone → unreachable indicator
- `"case_email"` — email has case issues → normalization will change it
- `"steward_corrected"` — steward fixed the data → source lineage decision
- `"fresh_source"` — new row from a fresh source
- `"invalid_negative_amount"` — negative amount → invalid event
- `"invalid_unit"` — unit not recognized → invalid event
- `"detention"`, etc. — advisory notes (counted as `advisory_note`)

### 13. Segment Mapping (campaign domain)

Campaign members have a `raw_segment` field. Map to canonical segments:
- Contains `"enterprise"` or `"renewal"` in combination → `enterprise_renewal`
- Contains `"strategic"` → `strategic_renewal`
- Contains `"smb"` or `"churn"` → `smb_churn_risk`
- Contains `"partner"` → `partner`
- Contains `"ops"` → `ops_lead`
- Otherwise → `unknown`

Trim and lowercase the raw_segment before classification.

---

## Output Conventions

### Sorting Rules (apply everywhere unless template says otherwise)

| Data type | Sort order |
|---|---|
| ID lists (purchase IDs, event IDs, charge IDs, member IDs) | Ascending string sort |
| Object arrays keyed by person | Ascending by `person_key` |
| Object arrays keyed by event/purchase/charge | Ascending by the primary ID field |
| Object arrays keyed by transaction | Ascending by `transaction_key` |
| Object arrays keyed by vehicle | Ascending by `vehicle_id`, then `observed_fuel` |
| Enum value arrays inside objects | Template enum order (NOT alphabetical) |
| `city_retained_counts` | Top by count desc, then city name asc (top 3) |

### Required Keys & Ordering

The answer template (`payloads/answer_template.json`) defines required top-level keys in order. Preserve that exact key ordering in the output JSON. Required keys inside nested objects must also be present exactly as listed.

### Numeric Precision

- All counts → integers only, no decimal places.
- All USD amounts → exactly 2 decimal places (rounded to cents).
- Gallon totals → 2 decimal places.
- Currency conversion rounding → apply rounding per-line before summing.

### Enums (Controlled Values)

Always use the exact enum values from the answer template. Never invent new enum values. Common enums:

**Fuel class**: `diesel`, `unleaded`, `premium_unleaded`, `electric`, `hybrid`, `unknown`

**Contact status**: `retained`, `dropped_unreachable`, `suppressed`, `manual_review`

**Canonical source**: `crm_verified`, `event_import`, `partner_roster`, `steward_override`

**Lineage decision**: `source_precedence_override`, `active_steward_correction`

**Cost type**: `freight`, `accessorial`, `tax_fee`, `claim`

**Units**: `kg`, `lb`, `mile`, `shipment`, `claim`

**Record status**: `posted`, `void`, `amended`

**Member status**: `registered`, `attended`, `no_show`, `bounced`, `unsubscribed`

**Contactability status**: `qualified_reachable`, `blocked_or_suppressed`, `needs_manual_review`

**Reconciliation status**: `api_current_replaces_stale_csv`, `csv_only_legacy`, `csv_extra_legacy`, `csv_stale_status`

**Issue types (logistics)**: `invalid_negative_amount`, `missing_amount`, `invalid_unit`, `invalid_currency`, `void_record`, `amended_record`, `duplicate_business_key`, `non_usd_currency`, `advisory_note`

**Review reasons (facilities)**: `duplicate`, `invalid_amount`, `invalid_unit`, `missing_contact_channel`, `suppressed_contact`, `ambiguous_alias`, `superseded`, `source_conflict`

**Ops action**: `mismatch_review`, `exception_documented`, `source_snapshot_review`, `superseded_record`, `no_ops_review`

**Owner**: `regional_ops`, `source_integrations`, `none`

**Metric effect**: `included_in_fuel_totals`, `included_exception_not_mismatch`, `excluded_from_totals`

**Source action**: `current_api_loaded`, `csv_snapshot_excluded`

**Decision reason (fleet)**: `expected_fuel_mismatch`, `vehicle_exception`, `superseded_by_api`, `csv_stale_record`, `csv_only_legacy`, `api_current_amendment`

**Alias audit reason**: `priority_overlap`, `generic_unleaded_trap`, `selected_unknown_alias`, `unmapped_description`

---

## Task Family Workflows

### CRM Contact Import Audit (Family 1 — train_001 pattern)

1. Fetch contact rows for the batch via `/api/crm/contact_rows?batch_id={id}`.
2. Group rows by `person_key`. Each group with >1 row is a duplicate group.
3. For each person, select the canonical row by source precedence (crm_verified > steward_override > event_import > partner_roster), ties broken by newest `source_updated_at`.
4. Normalize email and phone for every canonical row.
5. Classify each person:
   - `suppressed`: canonical row has `do_not_contact` status OR `revoked` consent.
   - `dropped_unreachable`: not suppressed, but no email AND no phone after normalization.
   - `retained`: has a usable channel and is not suppressed.
6. For duplicate groups, build source_lineage_audit entries:
   - If the canonical row is NOT the one with the newest `source_updated_at` (ignoring source precedence), then `lineage_decision: "source_precedence_override"`.
   - If the selected row has `quality_notes` containing `"steward_corrected"`, then `lineage_decision: "active_steward_correction"`.
7. Build decision_audit: precedence override person keys, suppressed-but-reachable rows, normalization-changed rows.
8. Build quality_flags: count raw rows, canonical persons, duplicate groups, extra duplicate rows, missing channel rows, suppression rows, email normalization changes, phone normalization changes, stale/inactive rows.
9. Build city_retained_counts from retained canonical contacts only (top 3 cities).

### Fleet Fuel Mismatch Audit (Family 2 — train_002 pattern)

1. Fetch purchases via `/api/fleet/purchases?region={region}&period={period}`.
2. Fetch vehicles via `/api/fleet/vehicles?region={region}`.
3. Fetch fuel aliases via `/api/reference/fuel_aliases`.
4. Fetch CSV export via `/downloads/fleet_purchases_export.csv`. Filter to matching region and period rows.
5. **Effective set**: Exclude `void` purchases. Superseded records (where another purchase's `amends_purchase_id` points to them) are also excluded from the effective set.
6. **Alias resolution**: For each effective purchase, match `product_description` (lowercased) against fuel aliases (case-insensitive). Select highest-priority match. If multiple matches → priority_overlap. If match includes both specific unleaded and generic unleaded → generic_unleaded_trap.
7. **Vehicle fuel check**: Compare canonical fuel to vehicle's `expected_fuel`. If vehicle has `exemption_code != "none"` and fuel mismatches → exception, not mismatch.
8. **Gallon aggregation**: Sum gallons by canonical fuel class (use ALL 6 fuel classes; 0.0 for classes with no purchases).
9. **Source delta**: Compare API purchase IDs vs CSV purchase IDs for the same region/period. Identify api_only_current, csv_only_legacy, csv_stale.
10. **Transaction reconciliation**: For transactions where API and CSV disagree, record the reconciliation status.
11. **Operations load decision**: For each purchase affected by mismatch, exception, amendment, or source-snapshot issues, record source_action, ops_action, owner, metric_effect, and decision_reasons.

### Logistics Cost Integrity Audit (Family 3 — train_003 pattern)

1. Fetch events via `/api/logistics/cost_events?wave_id={id}`.
2. Fetch quality rules for currency rates and valid units.
3. **Exclude void** records from effective set.
4. **Exclude invalid** records: negative amount → invalid_negative_amount; unit not in {kg, lb, mile, shipment, claim} → invalid_unit.
5. **Currency conversion**: For each effective event, convert amount to USD using the deterministic rates. Round each event's USD amount to cents. Sum rounded values.
6. **Aggregate**: Cost type totals (freight, accessorial, tax_fee, claim), unit counts, top lane by total cost.
7. **Issue counts**: Count each issue type across ALL events (not just effective). `non_usd_currency` counts effective events with non-USD currency. `advisory_note` counts effective events with non-empty `quality_notes`.
8. **Non-USD sample**: First 10 non-void events with an amount and non-USD currency, sorted ascending by event_id.
9. **Amended events**: Events with `record_status: "amended"` that replace earlier events → listed in `amended_event_ids_used`. The original events are in `superseded_event_ids`.

### Campaign Audience Qualification (Family 4 — train_004 pattern)

1. Fetch campaign members via `/api/crm/campaign_members?campaign_id={id}`.
2. Fetch contact rows for the same batch/person_keys via `/api/crm/contact_rows?batch_id={batch}`.
3. **Duplicate members**: Person keys appearing in multiple campaign member rows → duplicate, needs manual review.
4. **Match members to contacts**: For each person_key, find the canonical CRM contact row using source precedence (same as Family 1).
5. **Block/suppress**: Members with bounced/unsubscribed status, OR whose canonical contact has do_not_contact/revoked consent. These are `blocked_or_suppressed`.
6. **Manual review**: Duplicate members (same person_key, different member_id). These are `needs_manual_review`.
7. **Qualified reachable**: Everyone not blocked and not needing manual review, with a usable email or phone.
8. **Segment classification**: Map raw_segment to canonical segment (see Segment Mapping above).
9. **Domain counts**: Extract email domain (lowercase, after @) from retained qualified reachable members.
10. **Canonical member sample**: For each retained qualified reachable person, include one entry per unique person_key with person_key, member_id, canonical_contact_row_id, email, phone_digits, domain, canonical_segment, member_status, contactability_status.

### Facilities Charge Cleanup (Family 5 — train_005 pattern)

1. Fetch charges via `/api/facilities/charges?scope={scope}&period={period}`.
2. Fetch category aliases via `/api/reference/category_aliases`.
3. **Effective set**: Exclude `void` charges. Exclude superseded charges (those pointed to by another charge's `amends_charge_id`).
4. **Invalid charges**: Separate from void/superseded — charges excluded for invalid data values (negative amounts, invalid units, etc.).
5. **Category resolution**: Match `raw_category` (lowercased) against category aliases by highest priority. Unmatched → `unknown`.
6. **Review reasons** (per charge):
   - `ambiguous_alias`: raw_category matched an alias with canonical `unknown` AND other aliases.
   - `superseded`: the charge was superseded by an amendment.
   - `source_conflict`: (if applicable — charges with discrepancies between sources).
   - `duplicate`: duplicate business keys.
7. **Spend aggregation**: Sum `amount` by canonical category for effective charges only.
8. **Top vendor**: By total adjusted spend across effective charges.
9. **Charge sample**: One entry per effective charge, sorted ascending by `charge_id`.

---

## Common Pitfalls

1. **Not excluding void records from effective counts** — `record_status: "void"` means excluded from effective sets, totals, and aggregations. Track them in audit lists but don't count them.

2. **Forgetting amendment handling** — When `record_status: "amended"` and `amends_X_id` is set, the original is superseded. Include the amendment, exclude the original from effective operations.

3. **Mishandling invalid records** — Invalid records (negative amounts, bad units) are excluded from effective sets even if `record_status: "posted"`. They are separate from void records.

4. **Case sensitivity in alias matching** — Fuel and category alias matching is case-insensitive. Lowercase the raw description before comparing.

5. **Phone normalization losing country codes** — Strip non-digit characters but preserve any leading country code digits (e.g., `+1-312-555-0166` → `13125550166`, NOT `3125550166`). The `+` is non-digit and removed, but the `1` country code stays.

6. **Email normalization** — Trim AND lowercase. ` Opted@example.COM ` → `opted@example.com`.

7. **Currency rounding** — Round to cents per-line BEFORE summing. Don't sum raw amounts and round the total.

8. **Template key ordering** — The answer template's `required_top_level_keys_in_order` (or `required_top_level_keys`) defines the exact key order. Preserve it in output.

9. **Enum values from templates** — Use only the allowed values listed in the template. Never invent new enum values or use different casing.

10. **Source delta double-counting** — CSV records that are `csv_only_legacy` or `csv_stale` should NOT be included in operational totals. Only API-current effective records contribute to fuel totals.

11. **Vehicle exception vs. mismatch** — A mismatch where the vehicle has a non-none `exemption_code` is an EXCEPTION (goes to `exception_purchase_ids`), not a mismatch (doesn't go to `mismatch_purchase_ids`).

12. **Duplicate counting** — `duplicate_group_count` counts person KEY groups with >1 row, not individual extra rows. `duplicate_source_rows` counts the extra rows beyond one per group.

13. **Generic unleaded trap scope** — Only applies to effective purchase records. Void purchases don't contribute to alias issue counts.

14. **Zero-gallon purchases** — Still effective and included in totals (they contribute 0 gallons). Track them in `zero_gallon_purchase_ids` but they're NOT excluded from the effective set.

15. **CSV records appearing in API** — When comparing API vs CSV, a purchase can appear in both with different `record_status` values (API void vs CSV posted). This is a `csv_stale` record.
