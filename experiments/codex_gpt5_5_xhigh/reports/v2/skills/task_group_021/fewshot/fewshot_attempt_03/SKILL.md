---
name: asterops-data-quality-audit
description: Solve AsterOps task_group_021 data-quality audit tasks that use a remote workbench, an input answer_template.json, API records, reference rules, and CSV downloads. Use for CRM contact loads, CRM campaign audiences, fleet fuel purchase audits, logistics cost-event integrity audits, and facilities charge cleanup tasks that require strict JSON outputs, effective-record decisions, alias normalization, source reconciliation, controlled enums, ordering, and rounding.
---

# AsterOps Data Quality Audit

## Core Workflow

1. Read the task prompt, `input/payloads/answer_template.json`, and `environment_access.md` from the current solver directory.
2. Treat the answer template as authoritative for required keys, key order, enum values, list ordering, precision, and whether extra fields are allowed.
3. Extract the target slice from the prompt, such as `batch_id`, `campaign_id`, `region` plus `period`, `wave_id`, or `scope` plus `period`.
4. Use only the remote workbench. Get the base URL from `environment_access.md`, verify `/api/health`, then call `/api/catalog` to discover endpoints, filters, fields, and CSV download names.
5. Pull JSON from relevant APIs and, when the template asks about source deltas or snapshot reconciliation, pull the matching CSV from `/downloads/<filename>`.
6. Build the answer from parsed data, not from ad hoc text inspection. Use JSON and CSV parsers, normalize missing values to empty strings or nulls consistently, and keep numeric work in `Decimal` or integer cents where money is involved.
7. Emit one JSON object only. Do not include prose, comments, Markdown fences, or unrequested fields when `additional_properties` is false.

Useful commands:

```bash
BASE="$(sed -n 's/^GDPEVO_ENV_BASE_URL=//p' environment_access.md)"
curl -fsS "$BASE/api/health"
curl -fsS "$BASE/api/catalog"
curl -fsS "$BASE/api/reference/quality_rules"
curl -fsS "$BASE/downloads/<filename>"
```

## Template Conventions

- Preserve required top-level key order when the template specifies it.
- Use controlled enum strings exactly as listed in the template or reference API.
- Include all required enum/object keys even when the value is `0`, `[]`, or an empty object, unless the template says to include only positive keys.
- Sort ID lists lexicographically ascending unless the template specifies another order.
- For lists of objects, sort by the specified fields, commonly `person_key`, `member_id`, `purchase_id`, `event_id`, `charge_id`, `vehicle_id`, `transaction_key`, or `business_key`.
- For issue lists with enum arrays, order issue types by the template enum order, not alphabetically.
- For top-N summaries, sort by count or amount descending and use the template's tie-breaker, often name ascending.
- JSON numbers should be numbers, not strings. Round to the requested precision; trailing zeros are not required unless the evaluator explicitly expects strings.

## Remote Data Surfaces

Use `/api/catalog` each time rather than assuming every task uses every endpoint. Common surfaces are:

- CRM contacts: `/api/crm/contact_rows`, usually filtered by `batch_id`, `person_key`, or `source_system`.
- CRM campaign members: `/api/crm/campaign_members`, usually filtered by `campaign_id` or `person_key`.
- Fleet purchases: `/api/fleet/purchases`, usually filtered by `region`, `period`, or `vehicle_id`.
- Fleet vehicles: `/api/fleet/vehicles`, usually filtered by `region`, `active`, or `vehicle_id`.
- Logistics cost events: `/api/logistics/cost_events`, usually filtered by `wave_id` or `event_type`.
- Facilities charges: `/api/facilities/charges`, usually filtered by `scope` and `period`.
- References: `/api/reference/quality_rules`, `/api/reference/fuel_aliases`, and `/api/reference/category_aliases`.
- Downloads: CSV exports listed by the catalog. Use them for snapshot/source reconciliation, not as a substitute for current API records unless the prompt says so.

## Effective Record Rules

- A `posted` row is normally an effective current record.
- An `amended` row with `amends_*_id` replaces the referenced original. Include the amendment in effective totals and report the referenced original in superseded/excluded fields when requested.
- A `void` row is excluded from effective totals. If a void row is also replaced by an amendment, report it under all audit categories requested by the template, such as void and superseded.
- Do not count superseded originals in effective counts or totals.
- Exclude invalid rows from totals when they have disqualifying values such as negative amount, missing amount, invalid unit, or invalid currency. Still count and list them in issue audits.
- Group duplicates by the business key named by the task: `person_key` for people, `business_key` for charge/cost records, or `transaction_key` for purchase source reconciliation.

## Normalization Rules

- Email: trim outer whitespace and lowercase. Use `""` when no canonical email exists.
- Phone: remove every non-digit character and preserve any country code digits present. Use `""` when no canonical phone exists.
- Email domain: derive from the normalized email after `@`, lowercase, and count only retained/qualified people.
- Aliases: lowercase and trim source text before matching. Match all aliases contained in the source text, select the highest-priority alias, and keep matched alias evidence when the template asks for a trace.
- Money: use integer cents or `Decimal`. For logistics currency conversion, multiply each line by the reference USD rate and round that line to cents before aggregation.
- Gallons and non-money measures: sum effective records, then round final totals to the template precision unless the template gives a line-level rule.

## CRM Contact Loads

- Work within the target `batch_id`.
- Suppress source rows where `contact_status` is `do_not_contact` or `consent_status` is `revoked`.
- A person with no usable normalized email and no usable normalized phone is unreachable unless a harder status such as suppressed applies.
- Group source rows by `person_key` and choose one canonical source row per person.
- Do not choose the newest row blindly. Source precedence and quality notes can override recency. In the train pattern, `crm_verified` can beat a newer `event_import`, and an active steward correction can repair a stale or suppressed row for the same person.
- Count duplicate person groups as `person_key` groups with more than one source row. Count duplicate source rows as rows beyond the first inside those groups.
- Retained-contact counts include only canonical people with retained status. Suppressed and dropped-unreachable canonical people may still need to appear in canonical audit arrays if the template requests all canonical decisions.
- Count normalization-change rows at the source-row level: a nonblank email or phone counts if its normalized value differs from the source value.

## CRM Campaign Audiences

- Filter campaign members by `campaign_id`, then join to CRM contact rows by `person_key`.
- Count qualified reachable audience as unique retained people, not campaign member rows.
- Hard-block campaign members with statuses such as bounced or unsubscribed, and members whose canonical contact is suppressed, revoked, or do-not-contact.
- Put duplicate or ambiguous member rows that require human resolution in manual-review fields rather than counting them as qualified.
- For duplicate campaign members for one person, retain the best qualified member only when the data supports it; list noncanonical duplicate member IDs as manual review if requested.
- Map raw segments to template enums by normalized keywords: enterprise renewal, strategic renewal, SMB churn risk, partner, ops lead, otherwise unknown. Include every required segment key with zero when absent.
- Build domain and segment counts from retained qualified reachable people only.

## Fleet Fuel Purchase Audits

- Filter purchases by target `region` and `period`, and join vehicles by `vehicle_id`.
- Resolve `product_description` with fuel aliases. Multiple matches are normal; select the highest-priority alias and record priority-overlap traces when requested.
- Treat generic `unleaded` plus a more specific unleaded alias as a generic-unleaded trap when the template tracks it.
- Effective purchases include current `posted` and `amended` rows except voided or superseded originals. Zero-gallon effective purchases remain in evaluated counts and audit lists, but add zero to gallon totals.
- Compare observed canonical fuel to the vehicle `expected_fuel`. A mismatch goes to review unless the vehicle has a business exemption code. Exempted mismatches are documented separately and excluded from the mismatch queue.
- Reconcile API records to the monthly CSV snapshot by `purchase_id` and `transaction_key`. Current API amendments replace stale CSV/original rows; CSV-only legacy rows are excluded from operational totals but listed in source-delta audits.
- Gallon totals are by canonical fuel enum and rounded to two decimals when requested. Include all required fuel enum keys with zero values.

## Logistics Cost-Event Audits

- Filter by target `wave_id`.
- Use quality-rule currency rates and valid unit enums from `/api/reference/quality_rules`.
- Exclude void, superseded, and invalid records from corrected cost totals. Invalid examples include negative amount, missing amount, invalid unit, and invalid currency.
- Count non-USD source events as requested even when they are later excluded for another reason; follow the template wording for whether void rows are included in that count or sample.
- Convert each included event amount to USD at the line level, round to cents, then aggregate corrected totals, cost-type totals, and lane totals.
- Count unit corrections by included effective events only unless the template says source-row counts.
- Detect duplicate business keys after removing void/superseded/invalid candidates. If amendments exist, use the amendment row and list both amendment IDs used and superseded originals.
- For non-USD samples, use the first requested number of source event IDs in ascending `event_id` order under the template's eligibility rule.

## Facilities Charge Cleanup

- Filter charges by target `scope` and `period`.
- Apply effective-record rules: include current posted/amended charges, exclude voided and superseded originals, and list invalid/superseded IDs as requested.
- Resolve canonical category from `raw_category` using category aliases and highest priority. Use `unknown` when no better controlled category applies.
- Detect ambiguous alias and source-conflict review reasons when the selected category is weak or when independent evidence, such as description aliases, CSV/API disagreement, or source fields, points to a different category.
- Adjusted spend is USD to cents. Sum only effective non-invalid charges.
- Top vendor is based on adjusted effective spend. Include its effective count and sorted charge IDs.
- Canonical charge samples should be sorted by `charge_id` and use review reasons in template enum order.

## Validation Checklist

- The final JSON has exactly the required structure and no prose.
- Required enum/object keys are present even for zero values.
- Counts reconcile to the listed records and effective-set decisions.
- ID lists and object arrays follow the template ordering.
- Monetary values and gallon totals use the correct rounding stage.
- API-vs-CSV differences are represented only in source reconciliation fields, while operational totals use the current effective source unless the prompt says otherwise.
- Hard blocks, manual review, invalid rows, void rows, amendments, superseded originals, and source conflicts are kept in distinct audit buckets instead of being collapsed into one exclusion list.
