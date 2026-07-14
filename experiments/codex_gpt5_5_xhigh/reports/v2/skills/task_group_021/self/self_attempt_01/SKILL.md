---
name: asterops-quality-audits
description: Use for AsterOps data-quality workbench tasks that require auditing CRM contacts or campaign members, fleet fuel purchases, logistics cost events, or facilities vendor charges from a remote TASK_ENV_BASE_URL and returning strict JSON matching an answer_template. Covers catalog discovery, effective-record handling, CRM canonicalization, alias priority resolution, API/CSV reconciliation, currency and gallon rounding, ordering, normalization, and audit-field conventions.
---

# AsterOps Quality Audits

## Operating Workflow

1. Read only the attempt-local prompt, answer template, and `environment_access.md`. Use `GDPEVO_ENV_BASE_URL` as `<TASK_ENV_BASE_URL>`.
2. Query `/api/health` and `/api/catalog` first. Use the catalog to discover endpoint fields, filters, and download filenames.
3. Fetch the target slice through APIs using the prompt keys: `batch_id`, `campaign_id`, `wave_id`, `region` + `period`, or `scope` + `period`.
4. Fetch reference endpoints needed by the task:
   - `/api/reference/quality_rules` for CRM enums, record statuses, logistics units, and currency rates.
   - `/api/reference/fuel_aliases` for fleet fuel canonicalization.
   - `/api/reference/category_aliases` for facilities category canonicalization.
5. Use CSV downloads only when the prompt or template asks for source/export reconciliation. Treat the current API as authoritative for operational totals unless the task explicitly says otherwise.
6. Build a small reproducible calculation, then emit exactly one JSON object matching the template. Do not include prose around the JSON.

Do not inspect environment source code, grading or hidden files, prior outputs, or files outside the solver attempt directory.

## Output Discipline

- Preserve required top-level key order and nested item key order from the answer template.
- Use controlled enum strings exactly as listed. Include every required enum-keyed total with `0` when absent.
- Sort IDs lexicographically ascending unless the template gives another order. Sort object lists by the template fields, such as `person_key`, `purchase_id`, `event_id`, `charge_id`, `vehicle_id`, or `transaction_key`.
- Count integers as integers. Do not emit decimal counts.
- Use `Decimal` for money and conversions. For logistics, convert each line to USD and round that line to cents before aggregation. For facilities USD spend, round adjusted line amounts to cents before summing when calculations are not already cent-exact.
- For gallon totals, sum effective records by canonical fuel and round final totals to two decimal places.
- JSON numbers may be written with two decimal places where practical; keep them numeric, not quoted strings, unless the template says string.
- Include empty lists or empty objects for required fields with no matches.
- If a row qualifies for multiple audit lists, include it in each applicable list unless the template says the lists are mutually exclusive.

## Effective Records

Use this pattern for records with `record_status` and `amends_*` fields:

- `void` rows are non-effective and excluded from totals.
- A row whose ID appears in another row's `amends_*` field is superseded and excluded from totals.
- `amended` rows are effective replacements when otherwise valid.
- A void row can also be superseded; report it in both audit categories if both fields exist.
- Invalid value exclusions are separate from ordinary void/superseded exclusions. Common invalids are missing amount, negative amount, invalid currency, and unit outside the quality-rule unit enum.
- Detect duplicate `business_key` groups after amendment and invalid handling. Count and audit them; do not silently pick an arbitrary winner unless the template gives a winner rule.

## CRM Contact Rules

- Normalize email as `trim().lower()`. Normalize phone as digits only, preserving any country code digits. Use `""` when unavailable.
- A source row is suppressed when `contact_status == "do_not_contact"` or `consent_status == "revoked"`. Suppressed rows with any normalized email or phone are still "suppressed reachable" for audit fields.
- `contact_status == "inactive"` is stale/inactive, not suppressed. Prefer active rows; keep inactive rows in stale/manual-review counts when requested.
- `consent_status == "unknown"` is not a suppression by itself.
- A missing-channel row has both normalized email and phone empty.
- Source precedence for canonical contact selection is: `steward_override`, `crm_verified`, `partner_roster`, `event_import`. Prefer active, non-suppressed candidates; use source precedence before recency, and recency as a tie-breaker within the same source/status.
- An active `steward_override` row can correct an older suppressed or inactive row for the same `person_key`. Audit this as an active steward correction when the template has lineage fields.
- For contact-import audits, choose one canonical row per `person_key`. If no non-suppressed candidate remains, mark the canonical person suppressed. If the selected candidate has no usable channel, mark it dropped/unreachable. Retained counts and city counts include retained canonical people only.
- Quality flag counts usually apply to all raw rows in the target batch, not just retained rows. `duplicate_source_rows` means rows beyond the first inside duplicate `person_key` groups.

## CRM Campaign Audience Rules

- Join campaign members to CRM contact rows by `person_key`; when the contact endpoint supports `batch_id`, first try the campaign ID as the batch ID, then fill gaps by `person_key`.
- Hard-block campaign members with `member_status` of `bounced` or `unsubscribed`, or whose canonical CRM contact is suppressed. Keep these separate from manual-review rows.
- A qualified reachable audience member is a unique person with an actionable member status, an active non-suppressed canonical contact, and at least one normalized email or phone.
- Deduplicate campaign members by `person_key`. Prefer actionable status in the order `attended`, `registered`, `no_show`, then higher `score`, then lower `member_id`. Put noncanonical duplicate member IDs in manual-review audit fields when requested.
- Normalize segments by lowercase/trimmed keyword matching: enterprise renewal, strategic renewal, SMB churn risk, partner, ops lead, otherwise `unknown`.
- Domain counts use the lowercase domain from the retained canonical email only. Do not invent a domain for phone-only reachable people.

## Fleet Fuel Rules

- Use current `/api/fleet/purchases` records for the target `region` and `period` to compute fuel totals, mismatch queues, and effective purchase counts.
- Resolve `product_description` by case-insensitive substring matching against fuel aliases. Keep all matched aliases, select the highest `priority`, and use deterministic alphabetical tie-breaking if needed.
- `priority_overlap` means more than one alias matched. `generic_unleaded_trap` means generic `unleaded` also matched a more specific unleaded alias such as regular, premium, or super unleaded.
- If the selected alias maps to `unknown`, record an unknown-alias issue. If no alias matches, canonical fuel is `unknown` and the row is unmapped.
- Compare observed canonical fuel with the vehicle `expected_fuel`. Purchases on vehicles with an `exemption_code` other than `none` are business exceptions, not mismatch-queue items, but still remain in fuel totals if effective.
- Zero-gallon effective purchases remain in the evaluated set and audit list; they add `0.00` to gallons.
- For source reconciliation, compare the current API slice to the monthly CSV export by `purchase_id` and `transaction_key`. API-only amendments are current records; CSV-only legacy rows and stale CSV rows are excluded from operational totals and belong in snapshot/source-review fields.

## Logistics Cost Rules

- Use `/api/logistics/cost_events?wave_id=...` and the logistics quality rules.
- Exclude void, superseded, and invalid events from corrected USD totals. Invalid events include negative amount, missing amount, unit outside the controlled unit list, or currency absent from the conversion map.
- Valid non-USD events are not invalid. Convert them with `QR_CURRENCY` rates.
- Round each event's converted USD amount to cents before summing totals by wave, cost type, and lane.
- `non_usd_currency` counts/sample fields usually consider non-void events with an amount and non-USD currency, even though valid non-USD events are included after conversion.
- `advisory_note` covers non-exclusion quality notes, such as descriptive notes that are not invalid, void, amendment, duplicate, or currency issues.
- For top-lane fields, aggregate corrected effective USD by `lane`; break ties by lane name ascending unless the template says otherwise.

## Facilities Charge Rules

- Use `/api/facilities/charges?scope=...&period=...` for the target slice.
- Resolve category by matching aliases case-insensitively against both `raw_category` and `description`. Select the highest-priority alias.
- If matched aliases point to more than one canonical category, record `source_conflict`. If multiple aliases match the same category, record `ambiguous_alias`. A `misc` alias mapping to `unknown` is a valid unknown category, not automatically invalid.
- Exclude invalid charges and superseded charges from spend totals. Common invalids are missing or negative amounts; treat non-USD as invalid unless the prompt provides conversion rules.
- Category counts, spend by category, top vendor, and canonical charge samples use effective charges only.
- Sort canonical charge samples by `charge_id`. Sort each charge's `review_reasons` by the enum order or by label when the template says label order.
