---
name: asterops-data-quality-audits
description: Use this skill for AsterOps task_group_021 data-quality audit tasks that provide input/prompt.txt, input/payloads/answer_template.json, and environment_access.md, and require one JSON answer from the remote AsterOps workbench. Covers CRM contact and campaign audits, fleet fuel purchases, logistics cost events, facilities charges, effective-record handling, alias normalization, ordering, rounding, and output conventions.
---

# AsterOps Data Quality Audits

## Operating Rules

Use only files in the solver attempt directory:

- `input/prompt.txt`
- `input/payloads/answer_template.json`
- `environment_access.md`

Do not inspect local environment source, evaluator files, notes, hidden answers, or other task directories. Get data from the remote workbench named in `environment_access.md`.

The final answer is exactly one JSON object matching the template. Do not include prose outside the JSON.

## Remote Workbench Workflow

1. Read the prompt to identify the target slice: batch, campaign, region/period, wave, scope/period, or other business keys.
2. Read the answer template before computing. It defines required keys, controlled enums, list ordering, precision, and whether extra properties are ignored or forbidden.
3. Read `environment_access.md` and call:
   - `/api/health` only as a sanity check.
   - `/api/catalog` to discover endpoints, allowed filters, fields, and downloads.
4. Query only catalog-listed API filters. The workbench rejects unknown query parameters.
5. Use CSV downloads when the prompt mentions snapshots, exports, shared downloads, reconciliation, stale rows, or legacy rows. APIs represent current state; CSVs may represent monthly/export snapshots.
6. Parse API `quality_notes` as arrays. In CSV downloads, parse JSON-looking `quality_notes` strings before using them.
7. Derive the answer from data and template rules, then validate:
   - Required keys appear in template order.
   - Enum values exactly match template/rule spellings.
   - Required zero-valued enum buckets are present.
   - ID lists are sorted as requested.
   - Empty results are `[]` or `{}` as appropriate, never `null`.

## Output Conventions

- Preserve key order from `required_top_level_keys` and nested required-key lists.
- Sort stable IDs lexicographically ascending unless the template gives a different ordering.
- For grouped rows, sort by the template fields, usually person key, vehicle ID, transaction key, charge ID, event ID, or business key.
- For ranked summaries, sort by metric descending, then stable label ascending for ties. For city retained counts, include up to three cities by retained count descending, then city name ascending.
- Include all required enum keys with `0` when absent.
- Use JSON numbers for counts and amounts. Counts are integers.
- Use `Decimal`, not binary floats, for money and gallons:

```python
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

def cents(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
```

- For logistics currency conversion, convert each included line to USD and round that line to cents before aggregation.
- For USD spend and gallon totals, aggregate with `Decimal` and report rounded to two decimal places where requested.
- Normalize emails with trim plus lowercase. Normalize phones by removing all non-digits while preserving country-code digits. Normalize domains from the retained normalized email after `@`.

## Effective Records

The common `record_status` values are `posted`, `void`, and `amended`.

- Exclude `void` records from operational totals.
- Include valid `amended` records as the current effective record.
- Treat a record referenced by an `amends_*_id` field as superseded when that referenced record is in the target slice or the template explicitly asks for amended targets.
- Do not mix CSV-only legacy rows into current operational totals. Keep them in source-delta or reconciliation audit fields.
- If a record is both stale/superseded and present in a CSV snapshot, classify it as a snapshot/source reconciliation issue rather than a current effective row.
- For duplicate business keys after void, invalid, and amendment handling, count duplicate groups as the template defines. If a task requires closed-form totals, suppress unresolved duplicate candidates from totals unless the prompt/template says to include and only flag them.

## Alias Resolution

Alias tables use lowercase aliases, canonical values, and numeric priorities.

General method:

1. Lowercase and trim the text being matched.
2. Match aliases by substring.
3. Select the highest-priority matched alias. Break priority ties deterministically by alias text.
4. Record all matched aliases in sorted order when the template asks for a trace.
5. If nothing matches, use the template's unknown canonical value when available and count an unmapped issue.

Fleet fuel:

- Match against `product_description`.
- Canonical values come from the fuel alias reference/template: `diesel`, `unleaded`, `premium_unleaded`, `electric`, `hybrid`, `unknown`.
- Count `priority_overlap` when more than one alias matches.
- Count `generic_unleaded_trap` when generic `unleaded` also matches a more specific unleaded alias such as regular, premium, or super unleaded.
- Count `selected_unknown_alias` when the selected alias maps to `unknown`.
- Count `unmapped_description` when no alias matches.

Facilities categories:

- Match against the useful category text, usually `raw_category` plus `description`, because descriptions can reveal the more specific category.
- Select the highest-priority category alias across all matches.
- Use the category enum keys from the template, including `unknown`.
- Count `ambiguous_alias` when more than one category alias matches.

## CRM Contact Audits

Work at two levels: source rows and canonical people.

Source-row rules:

- A source row is suppressed when `contact_status` is `do_not_contact`, `consent_status` is `revoked`, or suppression/revocation notes say so.
- A row is stale or inactive when `contact_status` is `inactive` or quality notes indicate stale status.
- A row has a usable channel when normalized email or normalized phone is nonblank.
- Normalization issue counts are row-level counts over nonblank source values that change after normalization.
- Duplicate source rows are the rows beyond the first inside duplicate `person_key` groups.

Canonical person selection:

1. Group rows by `person_key`.
2. Prefer nonsuppressed, nonstale active rows.
3. Active steward corrections override ordinary source precedence.
4. Otherwise use source precedence: CRM verified before event import before partner roster.
5. Break remaining ties by most recent `source_updated_at`, then stable row ID.

Canonical status:

- `retained`: canonical row is not suppressed/stale and has email or phone.
- `dropped_unreachable`: canonical row is not suppressed but has no usable email or phone.
- `suppressed`: no usable non-suppressed canonical candidate remains because the person is hard blocked.
- `manual_review`: unresolved stale/inactive/source-conflict cases when the template exposes this status.

For duplicate lineage audits:

- Include duplicate `person_key` groups only unless the template says all people.
- `source_row_ids` and `noncanonical_source_row_ids` are sorted row IDs.
- Use `source_precedence_override` when precedence selects a row other than the newest source row.
- Use `active_steward_correction` when an active steward correction determines the canonical row.

## CRM Campaign Audience Audits

- Filter campaign members by `campaign_id`.
- Reconcile each member to CRM contacts by `person_key`.
- Canonicalize the contact using the CRM rules above.
- Hard-block member rows when member status is `bounced` or `unsubscribed`, contact status/consent is suppressed, or suppression notes apply.
- Put unresolved rows in manual review: duplicate unselected campaign members, missing contact rows, missing contact channel, stale/inactive contacts, and unresolved source conflicts.
- For duplicate campaign members, select one canonical actionable member and put unselected duplicate member IDs in the duplicate/manual-review audit field. Do not double-count a person.
- A retained audience count is a count of unique people, not member rows.
- Segment normalization is text based:
  - contains enterprise and renewal -> `enterprise_renewal`
  - contains strategic and renewal -> `strategic_renewal`
  - contains smb and churn -> `smb_churn_risk`
  - contains partner -> `partner`
  - contains ops and lead -> `ops_lead`
  - otherwise `unknown`
- Domain and segment counts include retained qualified reachable canonical people only.

## Fleet Fuel Audits

- Filter purchases by requested region and period. Period is based on purchase date month.
- Join vehicles by `vehicle_id`; use the vehicle expected fuel and exemption code.
- Current operational totals come from effective API purchase records: exclude void/superseded rows, include valid amended rows, and include zero-gallon rows with zero contribution.
- Compare API and CSV export snapshots by `purchase_id` and `transaction_key` for source-delta fields:
  - API-only current rows are current records missing from the CSV snapshot.
  - CSV-only legacy rows are snapshot rows missing from the current API.
  - CSV-stale rows are snapshot records whose transaction is replaced or whose current API state differs.
  - Disagreement transaction keys are sorted transaction keys with any API/CSV state difference.
- Gallon totals are grouped by selected canonical fuel and rounded to two decimals.
- A mismatch is an effective purchase whose observed canonical fuel differs from the vehicle expected fuel.
- If a vehicle has a business exemption code other than `none`, keep the purchase out of the mismatch queue and report it as a vehicle exception.
- Vendor mismatch counts include only vendors represented in the final mismatch queue, not vehicle exceptions.
- Alias issue counts are based on effective purchase records in the target slice, not void rows or CSV-only rows.
- Operations/load decision audits should distinguish:
  - current API rows loaded into fuel totals,
  - mismatch review owned by regional operations,
  - documented vehicle exceptions,
  - superseded/void records excluded from totals,
  - CSV stale or legacy snapshot rows excluded from totals and owned by source integrations.

## Logistics Cost Event Audits

- Filter cost events by `wave_id`.
- Use quality-rule currency rates for USD conversion and quality-rule units for valid units.
- Invalid events are excluded from corrected totals:
  - negative amount -> `invalid_negative_amount`
  - missing amount -> `missing_amount`
  - unit not in the controlled unit list -> `invalid_unit`
  - currency not in the conversion-rate map -> `invalid_currency`
- Void events are excluded and counted as `void_record`.
- Valid non-USD events are included after conversion and counted as `non_usd_currency`.
- Include valid amended events and list them where the template asks; list superseded event IDs separately.
- Compute `corrected_total_usd`, cost-type totals, and lane totals from included effective events only.
- For top lane, compare included USD totals; tie by lane name ascending.
- `unit_correction_counts` count included effective events by source unit after integrity exclusions.
- `issue_type_counts` are source-event issue counts in the target wave. Include required issue keys with zero.
- `non_usd_sample_event_ids` is the first ten non-USD, non-void source event IDs with an amount, sorted ascending, unless the template says otherwise.

## Facilities Charge Audits

- Filter charges by scope and period. Period is based on charge date month.
- Effective charges are valid posted/amended records after removing void, superseded, invalid, and unresolved duplicate/source-conflict records.
- Negative or missing amounts are `invalid_amount`. Unknown units, when present, are `invalid_unit`.
- Use category aliases to compute canonical category and ambiguous-alias review reasons.
- `category_counts` and `spend_by_category_usd` include effective charges only and include every required category key.
- `review_reason_counts` count target-slice review reasons using the template enum labels and order.
- `top_vendor_by_adjusted_spend` is based on effective adjusted spend only; include that vendor's effective charge IDs sorted ascending.
- `canonical_charge_sample` should be sorted by `charge_id`; include the canonical effective rows requested by the template, usually all effective rows unless a sample size is specified.

## Common Pitfalls

- Do not use train-task identifiers or previous answers as assumptions in a new task. Always derive from that task's prompt, template, API data, and downloads.
- Do not trust recency alone for CRM canonical rows; source precedence and active steward corrections can override newer lower-priority rows.
- Do not count hard-blocked/suppressed contacts as manual review.
- Do not count duplicate member rows as duplicate people more than once; count unique `person_key` values.
- Do not select generic aliases when a higher-priority specific alias also matches.
- Do not include CSV-only or stale snapshot rows in operational totals.
- Do not aggregate logistics foreign currency before line-level cent rounding.
- Do not omit zero-valued required buckets just because no records landed there.
