---
name: licensing-review
description: Solve structured government licensing review tasks against a shared licensing API. Use for contractor eligibility batches, restricted liquor-license staff packages, alcohol renewal/manual-review queues, or similar prompts that require fetching licensing records, applying policies/rules, and returning schema-exact JSON matching answer_template.json with sorted arrays and consistent summaries.
---

# Licensing Review

Use this skill to produce the final JSON for licensing-review tasks. The common failure modes are incomplete API fetches, mixing standard obligations with location-specific controls, including post-boundary records, and returning JSON that does not exactly match the template.

## Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before fetching data.
2. Extract the target IDs, location IDs, review date or release boundary, target queue size, required endpoints, required keys, allowed enum values, and ordering rules.
3. Read [references/decision_patterns.md](references/decision_patterns.md) for the relevant task family:
   - Contractor application eligibility batch.
   - Restricted liquor-license staff package.
   - Alcohol renewal manual-review queue.
4. Fetch records from the task environment.
   - Use the base URL supplied by the prompt or environment instructions.
   - Prefer targeted query parameters such as `application_id`, `location_id`, or `license_no` when supported.
   - Add `limit=1000` or fetch per target; default endpoint responses may be truncated.
   - Treat `POST /api/sql` as optional. If it returns an auth/token error, continue with the GET endpoints.
   - Parse embedded JSON strings such as `details_json` and `controls_json`.
5. Build an evidence ledger before writing the answer. For every target, list the records and policy/rule rows that support each code, count, risk tier, posture, rank, or summary ID.
6. Assemble only the JSON object requested by the template.
   - Include exactly the required top-level keys unless the template explicitly allows extras.
   - Use empty arrays when nothing applies.
   - Deduplicate arrays.
   - Apply each template's ordering rule; when unspecified, keep operational order for plans and stable lexical order for code arrays.
   - Recompute summaries from the item-level output, not from memory.
7. Validate the final object with the bundled validator:

```bash
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

If the validator reports schema or consistency issues, fix the JSON and run it again.

## Fetch Helper

Use the fetch helper when it saves time or when you need a reproducible record pull:

```bash
python skill/scripts/fetch_records.py --base-url "$TASK_ENV_BASE_URL" --limit 1000 /api/policies /api/contractor/applications
python skill/scripts/fetch_records.py --base-url "$TASK_ENV_BASE_URL" --param application_id=C-EXAMPLE-001 /api/contractor/bonds
python skill/scripts/fetch_records.py --base-url "$TASK_ENV_BASE_URL" --param location_id=LOC-EXAMPLE /api/liquor/incidents
```

The helper is intentionally generic. It does not decide eligibility; it only fetches JSON with explicit parameters and shows the URL used for each endpoint.

## Final Answer Rules

Return only JSON. Do not include markdown fences, citations, explanations, comments, or unrequested keys. Do not copy or reuse values from prior examples unless they are directly supported by the current task records.
