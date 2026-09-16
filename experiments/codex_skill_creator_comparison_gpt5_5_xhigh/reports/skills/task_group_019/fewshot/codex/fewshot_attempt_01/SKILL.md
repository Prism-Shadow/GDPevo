---
name: licensing-review-json
description: Produce structured JSON answers for licensing-environment examiner tasks that use TASK_ENV_BASE_URL endpoints and answer_template.json, including contractor eligibility batches, restricted liquor license staff packages, and alcohol renewal manual-review queues. Use when asked to fetch licensing records, apply policy records, map deficiency/risk/monitoring codes, build summaries, and return only schema-conformant JSON.
---

# Licensing Review JSON

## Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Extract the domain, target IDs, target location IDs, review or release dates, queue size, required ordering, and every allowed enum value.
2. Read the environment instructions for the base URL and allowed endpoints. Replace `<TASK_ENV_BASE_URL>` with that base URL. Use SQL only when the environment explicitly allows it and it works; otherwise use the listed GET endpoints.
3. Fetch the full relevant records before deciding. The optional helper can gather and filter records without external dependencies:

```bash
python3 skill/scripts/fetch_records.py --base-url http://task-env:9019 --domain contractor --ids C-001 C-002
python3 skill/scripts/fetch_records.py --base-url http://task-env:9019 --domain liquor --ids L-001 --location-ids LOC-001
python3 skill/scripts/fetch_records.py --base-url http://task-env:9019 --domain renewal --ids AL-001 AL-002
```

4. Read [references/rules.md](references/rules.md) for the domain-specific decision mappings before writing the final JSON.
5. Build the response directly from the template. Include only required keys unless the template permits optional fields. Use empty arrays when nothing applies.
6. Validate the final object: required top-level keys, enum values, item counts, ordering, summary counts, and sorted ID lists must match the template. Return only JSON, with no prose or markdown.

## Domain Routing

- Use the contractor section when the prompt references State Contractors Licensing Board applications, bonds, insurance, license history, contractor violations, correspondence, or inspections.
- Use the liquor section when the prompt references restricted liquor-license applications, settlements, privileges, incidents, site evidence, same-premises history, controls, first-90-day plans, or escalation triggers.
- Use the renewal section when the prompt requests a ranked alcohol renewal manual-review queue from licensees, violations, and renewal rules.

## Output Discipline

- Prefer current policy records from `/api/policies` or `/api/renewal/rules` over assumptions.
- Normalize code names to the exact enum spelling in the active template. Similar schemas use different names for the same concept.
- Sort arrays exactly as the template says. If the template says any order is accepted, use a stable, policy-logical order and never duplicate codes.
- Make batch summaries mechanically consistent with item-level decisions.
