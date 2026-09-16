---
name: licensing-json-review
description: Use this skill for structured licensing-environment JSON tasks involving contractor application eligibility batches, restricted liquor-license staff packages, or alcohol renewal manual-review queues. Use it when the prompt mentions TASK_ENV_BASE_URL, licensing API endpoints, answer_template.json, policy-backed deficiency or control codes, or renewal queue ranking.
compatibility: Requires ordinary file and network access in the task workspace. SQL access is optional; REST endpoints are sufficient.
---

# Licensing JSON Review

Use this skill when a task asks for a licensing decision, staff package, or renewal queue as JSON that must match `input/payloads/answer_template.json`.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` before querying data.
   Extract the target IDs, target location, review date or release boundary, queue size, required top-level keys, allowed enum codes, and all ordering rules.
2. Resolve the task environment base URL from the prompt or environment instructions. Fetch `/api/policies` first and parse each `details_json`.
3. Fetch only records needed for the target IDs when the endpoint supports filters. Repeated query parameters may return only the first value, so loop over targets unless SQL is available and authorized.
4. Treat `POST /api/sql` as optional. If it rejects the request or no token is available, use the REST endpoints and filter locally when an endpoint lacks the needed filter.
5. Build a small evidence table before writing JSON: one row per target, with the policy applied, source records used, output codes selected, and any excluded records with reasons.
6. Apply the domain rules in [references/licensing_rules.md](references/licensing_rules.md). Use the local answer template as the authority whenever schema names, code casing, or ordering differ.
7. Return only the JSON object. Do not include prose, markdown, citations, comments, or extra keys.

## Endpoint Joins

- Contractor applications, bonds, and insurance usually filter by `application_id`.
- Contractor violations, correspondence, and inspections join by `related_application_id`; license history may require filtering locally by `license_id`, applicant, trade, or prior-license clues.
- Liquor applications filter by `application_id`; settlements, incidents, and site evidence join by `location_id`; privileges are commonly fetched once and filtered by `license_class`.
- Alcohol renewal licensees filter by `license_no`; violations filter by `license_no`. If a licensee has `successor_to`, also fetch violations for the predecessor license and mark the match confidence accordingly.

## Validation

Before finalizing:

- Ensure every required top-level key exists and no unrequested keys are present.
- Sort arrays exactly as the template says; if the template says "any order", still keep a stable, sensible order.
- Use empty arrays for no applicable codes.
- Derive summary counts and ID lists from the item-level decisions, not independently.
- Check that every output code is in the template's allowed enum values. If the rule guide suggests a code that is unavailable in the current template, omit it or use the template's nearest explicit equivalent only when the mapping is unambiguous.
