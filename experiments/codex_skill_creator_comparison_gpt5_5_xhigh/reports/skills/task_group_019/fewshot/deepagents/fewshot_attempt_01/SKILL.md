---
name: licensing-json-review
description: Build structured JSON answers for licensing-environment review tasks that use TASK_ENV_BASE_URL data. Use for contractor eligibility batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues involving policies, applications, bonds, insurance, license history, violations, correspondence, inspections, settlements, privileges, incidents, site evidence, answer_template.json schemas, determinations, controls, verification gaps, or ranked queues.
---

# Licensing JSON Review

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: required keys, allowed enum values, ordering rules, date rules, and exact casing all come from it.
2. Extract target identifiers, target locations, review dates, boundary dates, queue size, and any special focus areas from the prompt.
3. Fetch only the records needed for those targets from `<TASK_ENV_BASE_URL>`. Use the helper if useful:

```bash
python skill/scripts/fetch_licensing_records.py --base-url "$TASK_ENV_BASE_URL" --family contractor --ids C-...
python skill/scripts/fetch_licensing_records.py --base-url "$TASK_ENV_BASE_URL" --family liquor --ids L-...
python skill/scripts/fetch_licensing_records.py --base-url "$TASK_ENV_BASE_URL" --family renewal --ids AL-...
```

4. Parse embedded JSON strings such as `details_json` and `controls_json` before applying rules.
5. Compute each field from records and policies. Do not reuse example answer values or infer from identifier patterns.
6. Emit only the JSON object requested by the template. Sort arrays exactly as the template says, use empty arrays when nothing applies, and make summaries reconcile with item-level decisions.

## Family Routing

- **Contractor eligibility**: applications, policies, bonds, insurance, license history, violations, correspondence, and inspections. Read [decision rules](references/decision-rules.md#contractor-eligibility).
- **Restricted liquor review**: liquor applications, settlements, privileges, incidents, site evidence, and liquor policies. Read [decision rules](references/decision-rules.md#restricted-liquor-review).
- **Alcohol renewal queue**: licensees, alcohol violations, renewal rules, release boundary, and successor matches. Read [decision rules](references/decision-rules.md#alcohol-renewal-queue).

## Data Access Notes

Prefer targeted GET calls. SQL may be listed but unavailable; if a SQL POST returns an authorization error, continue with GET endpoints. Known useful filter keys:

- Contractor applications, bonds, insurance: `application_id`.
- Contractor violations, correspondence, inspections: `related_application_id`.
- Contractor license history: `license_id`, usually from `prior_license_id`.
- Liquor applications: `application_id`.
- Liquor settlements, incidents, site evidence: `location_id`.
- Liquor privileges: `license_class`.
- Alcohol licensees and violations: `license_no`.

## Output Checks

Before finalizing, verify:

- Top-level keys exactly match the template.
- Every enum value is allowed by the template and uses the template's spelling.
- Per-item arrays are de-duplicated and sorted when required.
- Batch counts, high-risk lists, policy-impacted lists, stale/unverified correspondence lists, post-boundary exclusions, and board-review lists are derived from the returned items.
- Dates are in `YYYY-MM-DD`.
