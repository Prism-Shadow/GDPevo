---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer-operations tasks that require using a task environment to produce structured JSON for authorization determinations, pharmacy appeals, payment-integrity repricing, peer-to-peer summaries, and UM-finance margin queues. Use when prompts mention Northstar, payer operations, prior authorization, appeal disposition, manufacturer assistance intake, claim repricing, P2P, service margin, or an answer_template.json contract.
---

# Northstar Payer Operations

Use this skill to produce the exact JSON object requested by Northstar payer-operations prompts. The task environment is the source of truth; local prompt payloads define the target IDs, reporting date or period, credentials, and output schema.

## Workflow

1. Read the user prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.
2. Extract the target business ID(s), reporting date/period, requester role, service domain, SQL endpoint, bearer token, and any scoped row IDs.
3. Query only the task environment named in the prompt/context. Do not inspect environment source files, generated data files, SQLite files, manifests, setup scripts, test tasks, or answer files.
4. Anchor every lookup on the target IDs. Prefer targeted SQL with `WHERE` filters over broad dumps. Use business endpoints when they expose the exact case, appeal, policy, document, rate schedule, or portal record needed.
5. Build a working evidence map of cases, request lines, appeals, claims, claim lines, authorization records, documents, policies/criteria, rate schedules, P2P events, assistance facts, and finance rows as applicable.
6. Apply the domain rules in [references/northstar_workflow.md](references/northstar_workflow.md).
7. Return one JSON object only. Match the template's required keys, enum values, numeric precision, date precision, null handling, and ordering rules.

## Environment Access

Use the base URL and token from the task, not hardcoded local paths. If helpful, use [scripts/northstar_env.py](scripts/northstar_env.py):

```bash
python scripts/northstar_env.py tables --base-url "$TASK_ENV_BASE_URL"
python scripts/northstar_env.py get /api/cases/CASE-ID --base-url "$TASK_ENV_BASE_URL"
python scripts/northstar_env.py sql "SELECT * FROM some_table WHERE case_id = 'CASE-ID'" --base-url "$TASK_ENV_BASE_URL" --token "$SQL_BEARER_TOKEN"
```

The helper is only a convenience wrapper around HTTP. It does not know task-specific schemas or answers.

## Output Discipline

- Use the answer template as the contract. Do not add fields unless the template explicitly allows them.
- Preserve template ordering instructions: claim lines in claim-line order, queue rows in scoped row order, CPT lists ascending when requested, medication lists alphabetically when requested, and factor lists in template choice order when requested.
- Emit JSON numbers for currency and ratios, not strings. Round currency to two decimals and ratios to the precision stated in the template.
- Use JSON `null` for absent modifiers or inapplicable dates when the template calls for null.
- Do not include markdown, comments, citations, or narrative outside the JSON.

## Final Check

Before responding, verify:

- All required top-level keys and nested required keys are present.
- Every enum value appears exactly as allowed by the template.
- `basis_audit` names the precedence rule, directly controlling record IDs, exception/gap IDs, and source-precedence order.
- Evidence documents used in the determination are separated from stale, superseded, or excluded records.
- Totals equal the sum of line or row calculations after rounding rules are applied.
