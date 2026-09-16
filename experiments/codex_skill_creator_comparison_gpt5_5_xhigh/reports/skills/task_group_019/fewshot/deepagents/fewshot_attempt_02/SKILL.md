---
name: licensing-record-review
description: Structured licensing review from task-environment records. Use when solving contractor application eligibility batches, restricted liquor-license staff packages, or alcohol renewal manual-review queues that require fetching policy and licensing endpoints from TASK_ENV_BASE_URL and returning strict JSON matching an answer_template.json schema.
---

# Licensing Record Review

## Core Workflow

Use the prompt and `input/payloads/answer_template.json` as the output contract. Return only the JSON object requested by the template; do not include prose, citations, comments, or unrequested keys.

1. Identify the review family from the prompt and endpoints:
   - Contractor batches: contractor applications, bonds, insurance, license history, violations, correspondence, inspections.
   - Restricted liquor reviews: liquor applications, settlements, privileges, incidents, site evidence.
   - Alcohol renewal queues: alcohol licensees, alcohol violations, renewal rules.
2. Fetch every endpoint named in the prompt. Add `?limit=500` or a larger limit to GET requests; default responses can be capped. Use `POST /api/sql` only when the environment provides a usable token or credentials.
3. Filter records to the target application IDs, license numbers, location IDs, and directly related prior/successor identifiers. Keep distractor rows out of calculations unless they are linked by an explicit relationship such as `prior_license_id`, `related_application_id`, or `successor_to`.
4. Parse JSON-in-string fields such as `details_json` and `controls_json` before reasoning.
5. Apply the family reference:
   - Contractor: read [references/contractor.md](references/contractor.md).
   - Restricted liquor: read [references/liquor.md](references/liquor.md).
   - Renewal queues: read [references/renewal.md](references/renewal.md).
6. Normalize final arrays to the template's required ordering. Sort and dedupe coded arrays unless the template says to preserve operational sequence.
7. Validate consistency: summary counts and ID lists must match item-level decisions; ranks must be consecutive; dates must use `YYYY-MM-DD`; empty coded fields must be empty arrays.

## Evidence Helper

Use [scripts/fetch_evidence.py](scripts/fetch_evidence.py) to fetch and locally group endpoint records without writing task-specific logic:

```bash
python skill/scripts/fetch_evidence.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --family contractor \
  --targets C-EXAMPLE-001,C-EXAMPLE-002 \
  --output evidence.json
```

For liquor reviews, pass `--targets` for application IDs and `--locations` when the prompt gives location IDs. For renewal queues, pass `--targets` for license numbers or `--prefixes` for a target range prefix. Review the generated evidence file before deciding; the script is a fetch/filter aid, not an answer generator.

## Guardrails

Do not hardcode staged record IDs, staged application decisions, or staged final answer values. Derive each answer from the current prompt, current template, policy rows, and fetched records. If an allowed code name differs across templates, map by meaning to an allowed value and omit findings that have no corresponding allowed output field.
