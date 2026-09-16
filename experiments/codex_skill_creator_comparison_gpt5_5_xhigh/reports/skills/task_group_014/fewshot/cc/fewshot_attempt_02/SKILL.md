---
name: northstar-payer-ops-json
description: Produce strict JSON determinations and operations packets for Northstar Health Plan payer-operations tasks using the shared task environment. Use when the prompt asks for prior authorization or UM review, pharmacy appeal or assistance intake, peer-to-peer closure, payment integrity claim repricing, benchmark selection, or service margin queue summaries that must conform to an input/payloads/answer_template.json schema.
---

# Northstar Payer Operations JSON

## Core Workflow

1. Read `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` before querying anything.
2. Extract the target identifiers, reporting date or period, requester role, answer schema, endpoint base URL, and SQL bearer token from the task files. If the prompt contains a placeholder base URL, use the task environment access note supplied with that task.
3. Query only the documented environment endpoints. Do not inspect task-environment source files, generated databases, SQLite files, manifests, or setup scripts.
4. Start with the exact target IDs from `task_context.json`, then follow linked `case_id`, `member_id`, `policy_id`, `claim_id`, appeal, document, and queue row IDs. Avoid broad table dumps.
5. Build the answer directly from environment records and the template. Do not rely on local memos except for scope, target IDs, dates, definitions, and output constraints.
6. Return exactly one JSON object and no markdown or narrative text.

Use `scripts/northstar_sql.py` for SQL requests when helpful:

```bash
python skill/scripts/northstar_sql.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --token "$SQL_BEARER_TOKEN" \
  --sql "select * from cases where case_id = '...'"
```

Read [references/table-map.md](references/table-map.md) when you need the table list, key columns, or query patterns.

## Evidence Gathering

Use a focused query set based on the work type:

- **Authorization or UM determination**: cases, members, plans, request_lines, policies, policy_criteria, case_criteria, documents, document_facts, authorizations.
- **Pharmacy appeal or assistance**: cases, appeals, drug_trials, case_criteria, documents, document_facts, assistance_screen, authorizations when denial context is needed.
- **Peer-to-peer closure**: cases, request_lines, policies, policy_criteria, case_criteria, documents, document_facts, p2p_events, authorizations.
- **Payment integrity repricing**: claims, claim_lines, members, plans, cases if linked, payment_benchmarks, authorizations if an auth number must be reconciled.
- **Finance or margin queue**: service_margin rows named in task_context and any finance definitions in the local memo.

Prefer SQL for multi-table work because the endpoint returns structured rows. The SQL body key is `sql`, not `query`.

## Business Rules

Apply the rule implied by the task and then set `basis_audit.source_precedence` to the matching template enum.

### Current Clinical Records Over Stale Export

- Treat current clinical documents and their facts as higher precedence than stale exports.
- Use `documents.is_current` and document dates/source summaries to decide evidence versus exclusions.
- Use `case_criteria.result` as the final criterion result unless contradicted by higher-priority current evidence.
- Approve through the nurse route only when the applicable criteria are met and the authorization record supports an approval.
- Put current relied-upon document IDs in `evidence_documents`; put stale, superseded, or non-relied documents in `excluded_documents`.

### Payer Appeal Before Manufacturer Assistance

- Resolve payer appeal eligibility, deadline, route, owner, denial status, and medication failure evidence before assistance screening.
- Split medication trials into documented failures and undocumented or insufficient failures using the `documented` flag plus trial notes.
- Build payer appeal packet requirements before assistance requirements. Order missing items with appeal evidence gaps before assistance information gaps.
- Use assistance_screen for program status and assistance-only missing fields; do not let assistance readiness override an incomplete payer appeal record.

### Effective Benchmark By Plan, Modifier, And Date

- Match each claim line to the payment benchmark by payer/plan type, service domain, CPT, modifier, and service date within the benchmark effective range.
- Treat a null line modifier and a null benchmark modifier as a match. Do not use an empty string for absent modifiers in the answer.
- Prefer the benchmark whose effective window contains the service date and whose source/version is current for the plan. Reject stale or non-applicable schedules.
- Compute line corrected allowed amount as `allowed_amount * units`, rounded to cents.
- Compute line and total recovery from the template's direction. When the corrected allowed total is greater than paid total, use the underpayment amount as a positive value.
- Preserve claim-line order from `claim_lines.line_number`.

### New Patient-Specific P2P Information

- Treat the completed P2P event as the highest-precedence record for final outcome, but verify it against current clinical documents and criteria.
- Set `new_information_changed_review` true only when the event contains new patient-specific facts that materially change the criteria outcome.
- For adverse outcomes, include unresolved criteria and missing modality-specific factors in the order required by the answer template.
- Calculate appeal deadlines from the final adverse determination date and the appeal window stated in the prompt, policy, plan, or memo.

### Margin Threshold Then Charge Sensitivity

- Use only queue row IDs named in `task_context`.
- Compute `total_cost = variable_cost + fixed_cost_allocated`.
- Compute `margin = net_revenue - total_cost`.
- Compute `revenue_to_cost_ratio = net_revenue / total_cost`, rounded to the precision requested by the template.
- Mark `below_threshold` when the ratio is below the task threshold; these rows drive payer contract review.
- Mark `charge_sensitive` from the environment flag; if a row is not below threshold but is charge-sensitive, route it to monitoring.
- Compute `gap_to_120pct` or analogous threshold gap as `(threshold * total_cost) - net_revenue` for the top below-threshold issue, rounded to cents.

### Appeal Deadline Then Clinical Then Payment Integrity

- When a task spans appeal timing, clinical merits, and payment facts, resolve route eligibility and deadlines first, clinical criteria second, and payment integrity facts last.
- Use this precedence only when it is the closest enum in the template or the prompt explicitly combines those domains.

## Basis Audit

Every answer with `basis_audit` needs a concise audit trail:

- `controlling_record_ids`: environment record IDs that directly determine the result. Include records such as appeals, P2P events, claim lines, benchmarks, service-margin rows, current documents, or documented trials.
- `exception_record_ids`: gaps, stale records, rejected benchmarks, missing packet items, unresolved criteria, or unsupported factors that explain denials, pends, exclusions, or route priority.
- `precedence_record_order`: controlling and exception records in business-precedence order, highest priority first. Do not simply alphabetize unless the template says to.
- Use exact IDs from the environment or exact missing item/criterion identifiers from the template. Do not invent IDs.

## Output Discipline

- Follow the template's required top-level keys and nested required keys exactly.
- Use only enum values allowed by the template.
- Use JSON `null` for absent nullable values; do not use empty strings for null modifiers or dates.
- Sort lists only when the template says to sort. Otherwise preserve operational order: queue row order, claim-line order, packet order, or evidence precedence order.
- Round currency to two decimals and ratios to the template precision. Emit JSON numbers, not formatted strings.
- Include optional fields only if the template allows them and they add task-relevant information.
- Before final response, parse the JSON and compare it to the template. If you wrote the answer to a file, run:

```bash
python skill/scripts/template_check.py input/payloads/answer_template.json /tmp/answer.json
```

If evidence is missing or criteria are unclear, return the template's pending, information request, medical-director, or denial route rather than guessing.
