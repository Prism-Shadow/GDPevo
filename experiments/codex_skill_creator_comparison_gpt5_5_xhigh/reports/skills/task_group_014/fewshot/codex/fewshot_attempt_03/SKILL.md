---
name: northstar-payer-ops
description: Produce strict JSON answers for Northstar Health Plan payer-operations tasks that use the shared task environment, task_context.json, and answer_template.json. Use for prior authorization determination summaries, pharmacy appeals and manufacturer assistance intake, payment integrity claim repricing, peer-to-peer authorization closure, and therapy margin queue analysis requiring case, policy, document, rate schedule, appeal, or SQL evidence.
---

# Northstar Payer Ops

## Core Workflow

Use this skill to solve Northstar payer-operations tasks by deriving a single schema-conforming JSON object from the task files and the running environment.

1. Read the prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`.
2. Resolve the environment base URL and SQL token from the prompt/context. If the base URL is a placeholder, read the staged environment access file supplied with the task.
3. Inspect the template before reasoning. Preserve required keys, enum values, date formats, numeric precision, list ordering rules, and whether extra fields are allowed.
4. Query only permitted environment endpoints or SQL. Do not inspect local databases, generated data files, manifests, setup scripts, test answers, or environment source.
5. Build the answer from current operational records, then validate the object against the template. Return JSON only.

For endpoint details, schema notes, reusable SQL patterns, and domain checklists, read [references/northstar_environment.md](references/northstar_environment.md). For a small standard-library helper that fetches endpoint or SQL evidence, use [scripts/northstar_fetch.py](scripts/northstar_fetch.py).

## Evidence Collection

Prefer `GET /api/cases/{case_id}` when the task has a case-like business ID. The case endpoint returns the case joined with member, provider, plan, request lines, criteria, documents, document facts, authorizations, appeals, assistance screens, drug trials, claims, and P2P events when present.

Use SQL for focused table work, especially:

- `service_margin` rows listed in `task_context.finance_memo.queue_row_ids`
- `claims`, `claim_lines`, and `payment_benchmarks` for repricing
- filtered appeal, assistance, trial, criteria, document, or fact lookups when the case endpoint is insufficient

Always constrain SQL by task-specified IDs, dates, payer/plan, service domain, CPT, modifier, or row IDs. Avoid broad dumps unless first inspecting table names or columns.

## Decision Rules

Apply the task template first; these rules fill common Northstar fields.

- Current clinical evidence takes precedence over stale exports. Use `documents.is_current = 1` and criterion-supporting facts as evidence; put stale or irrelevant case documents in excluded or exception fields when the template asks.
- Criteria results usually come from `case_criteria.result` for the required criterion IDs, normalized to the template's enum values. Verify gaps and facts before copying a result.
- Authorization summaries use the active authorization record for status, approved units, dates, CPTs, modifier, denial reason, and letter/next action.
- Pharmacy appeals use appeal path, expedited flag, deadline, owner, required packet notes, current documents, drug trials, and assistance screen. Documented trials go in documented failures; undocumented or insufficient trials go in gap fields. Payer appeal routing controls before manufacturer assistance status.
- Claim repricing uses the benchmark effective on the service date that matches payer, plan type, service domain, CPT, and modifier, treating null modifier as a real match. Calculate line allowed amount as benchmark allowed amount times units, then sum totals. Recovery is corrected allowed minus paid amount, rounded to cents; set line disposition from the sign of the correction.
- P2P closure uses the completed P2P event plus current criteria and clinical evidence. New information changes review only when it supplies patient-specific facts that materially alter criteria. For adverse final results, calculate the internal appeal deadline from the final adverse determination date using the appeal window specified by the prompt, context, policy, or plan record.
- Therapy margin queues use only the row IDs supplied by the task context. Total cost is variable cost plus fixed allocated cost unless the context gives a different definition. Margin is net revenue minus total cost. Revenue-to-cost ratio is net revenue divided by total cost. Below-threshold actions take priority over charge-sensitive monitoring.

## Basis Audit

Populate `basis_audit` as an operational trace, not a citation list.

- Select `source_precedence` from the template enum according to the workflow: current clinical over stale export, payer appeal before assistance, effective benchmark by plan/modifier/date, new patient-specific P2P information, margin threshold then charge sensitivity, or a task-specific combined precedence.
- Put records that directly determine the result in `controlling_record_ids`, in operational evidence order.
- Put gaps, stale records, missing packet items, unsupported criteria, or rejected benchmark records in `exception_record_ids`.
- Put `precedence_record_order` in source-precedence order, highest priority first. It may be shorter than the union of the other lists when only the decisive precedence trail is needed.

## Final Checks

Before answering:

- Parse the final JSON with `jq` or Python.
- Ensure dates are ISO calendar dates, month fields use `YYYY-MM`, JSON null is used for absent modifiers or absent deadlines when allowed, and booleans are booleans.
- Round currency to two decimals and ratios to the precision requested by the template.
- Preserve required list ordering, such as claim-line order, task-context queue order, ascending document ID, alphabetical medication names, or enum choice order.
- Remove markdown, comments, and narrative text outside the JSON.
