---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer operations tasks that require reviewing the shared task environment and returning strict JSON. Use for utilization management determinations, pharmacy appeals and manufacturer assistance intake, peer-to-peer summaries, payment integrity claim repricing, and UM-finance margin queue analysis when prompts reference Northstar, payer operations, authorization cases, appeals, claims, P2P events, service-margin queues, answer_template.json, or TASK_ENV_BASE_URL.
---

# Northstar Payer Ops

## Core Rule

Use the task environment as the source of truth. Do not inspect local database files, generated data files, manifests, setup scripts, evaluator code, or test answers. Read the prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`; then query the environment and return only one JSON object matching the template.

## Environment Access

Resolve `<TASK_ENV_BASE_URL>` from the prompt, task context, or environment access note. Use business endpoints when convenient and SQL for joins or calculations. The SQL endpoint is `POST /sql/query` and expects JSON shaped as `{"sql": "select ..."}` with the bearer token specified by the task.

Use [scripts/northstar_sql.py](scripts/northstar_sql.py) to run SQL without rewriting HTTP boilerplate:

```bash
python3 scripts/northstar_sql.py --base-url "$TASK_ENV_BASE_URL" --token "$TOKEN" \
  "select * from cases where case_id = '...'"
```

Start every unfamiliar task by fetching `/api/tables` or querying table schemas. Typical tables are `cases`, `members`, `plans`, `providers`, `request_lines`, `policies`, `policy_criteria`, `case_criteria`, `documents`, `document_facts`, `authorizations`, `appeals`, `drug_trials`, `assistance_screen`, `p2p_events`, `claims`, `claim_lines`, `payment_benchmarks`, and `service_margin`.

## Work Sequence

1. Extract the target business IDs, reporting date or period, requester role, allowed endpoints, token, and output contract from the prompt and payloads.
2. Read the answer template before querying. Treat required keys, enum choices, ordering rules, numeric precision, date format, null handling, and whether extra fields are allowed as binding.
3. Query the minimum complete record set for the task type:
   - UM authorization: case, member, plan, provider, request lines, active policy and criteria, case criteria, current documents and facts, stale or excluded documents, and authorization record.
   - Pharmacy appeal: appeal, case, denial and deadline fields, requested drug, policy criteria, documented and undocumented medication trials, packet documents, and assistance screen.
   - Payment integrity claim: claim, claim lines ordered by source line order, member/plan context, authorization number, and payment benchmarks effective for payer, plan type, service domain, CPT, modifier, and service date.
   - Peer-to-peer: case, request line, active policy criteria, clinical evidence, completed P2P event, authorization/final status, and any plan appeal-window facts needed for adverse outcomes.
   - Margin queue: only the row IDs or period explicitly scoped by `task_context`; use service margin rows and the finance definitions supplied in the payload.
4. Reconcile source precedence before filling fields. Prefer current clinical records over stale exports; payer appeal disposition before manufacturer assistance; effective benchmark records by plan, modifier, and date over legacy schedules; new patient-specific P2P facts over prior review only when they materially change criteria; margin threshold findings before charge-sensitive monitoring.
5. Perform required calculations from source rows, then round only at the output boundary:
   - Claim repricing: calculate corrected allowed amount per line from the selected benchmark times units; sum paid and corrected totals; compute the correction or recovery amount as directed by the template; use `null` for absent modifiers.
   - Margin queues: `total_cost = variable_cost + fixed_cost_allocated`, `margin = net_revenue - total_cost`, `revenue_to_cost_ratio = net_revenue / total_cost`, and gap to threshold equals `(threshold * total_cost) - net_revenue` for the top below-threshold issue.
   - Appeal deadlines and P2P deadlines: use the date fields and calendar-window rules in the environment or prompt; output ISO `YYYY-MM-DD`.
6. Populate every template field exactly. Preserve required ordering: source line order for lines, task-context row order for scoped queues, alphabetical order where requested, choice order where requested, ascending IDs where requested.
7. Build `basis_audit` whenever present:
   - `source_precedence`: choose one of the template's precedence enums that matches the controlling business rule.
   - `controlling_record_ids`: list environment records that directly determine the disposition, calculation, deadline, or routing in operational evidence order.
   - `exception_record_ids`: list stale records, missing documents, unresolved criteria, unsupported factors, or threshold/route gaps in business gap order.
   - `precedence_record_order`: list the records or gap identifiers in highest-priority source-precedence order, not merely every record retrieved.
8. Validate the final object locally before answering: parse as JSON, compare required keys against the template, check enum values, check numeric precision, and remove all prose or markdown.

## Output Discipline

Return JSON only. Do not include explanations, citations, markdown fences, comments, or fields not allowed by the template. If evidence conflicts, resolve by the stated precedence rule and reflect the conflict in `basis_audit`; do not guess from stale or unrelated records.
