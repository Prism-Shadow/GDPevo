---
name: skill
description: Solve Northstar payer-operations tasks that require reading task_context and answer_template files, querying the shared environment, and returning exact JSON for UM nurse reviews, pharmacy appeals, claim repricing, peer-to-peer summaries, and margin-queue analyses.
---

# Northstar Payer Ops

## Workflow

1. Read the prompt, `task_context.json`, and `answer_template.json` together.
2. Identify the task family, target record IDs, reporting date or period, output contract, and any prompt-specific restrictions on local file inspection.
3. Use only the documented environment endpoints. Prefer `POST /sql/query` for joins, filters, and rollups; use case, policy, document, appeal, rate-schedule, portal, claim, or queue endpoints when they expose the controlling record directly.
4. Treat task-context memos as routing hints, not evidence. Build the answer from current controlling records only.
5. Follow the template exactly. Preserve required key order, nested key order, enum spellings, list ordering rules, and null handling. Round numbers only to the precision requested by the template.
6. Keep the output JSON-only. Do not add markdown, commentary, or extra keys unless the template explicitly allows them.

## Common Task Families

- UM nurse review: resolve case status, authorization details, therapy criteria, evidence documents, and excluded documents.
- Pharmacy appeal: resolve appeal path, deadline, prior medication failures, packet gaps, and assistance readiness.
- Claim repricing: resolve benchmark source, stale source rejection, line-level corrections, totals, and resubmission route.
- Peer-to-peer summary: resolve final outcome, PET criteria, unresolved factors, alternative modality, and appeal deadline if adverse.
- Margin queue: resolve per-row ratios, threshold flags, charge sensitivity, top issue, and the gap to 120 percent of cost.

## Audit And Calculation Rules

1. Use the exact criteria keys from the template. Do not rename them or infer extra ones.
2. Keep identifier lists in the ordering requested by the template. Use source order only when the template requires it; otherwise use operational precedence.
3. Fill `basis_audit` with the controlling records, exception or gap records, and the precedence trail in highest-priority-first order.
4. Choose the source-precedence rule that matches the decision:
   - `current_clinical_records_over_stale_export`
   - `payer_appeal_before_manufacturer_assistance`
   - `effective_benchmark_by_plan_modifier_and_date`
   - `new_patient_specific_p2p_information`
   - `margin_threshold_then_charge_sensitivity`
   - `appeal_deadline_then_clinical_then_payment_integrity`
5. Keep intermediate calculations in working precision, then serialize only the rounded values required by the template.
6. Use `null` only where the template permits it, such as absent modifiers or an unavailable deadline.
