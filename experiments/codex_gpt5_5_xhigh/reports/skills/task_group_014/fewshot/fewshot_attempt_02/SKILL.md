---
name: skill
description: Northstar payer-operations structured JSON review tasks that query the shared environment and return strict dispositions for UM nurse reviews, pharmacy appeals and assistance intake, claim repricing, peer-to-peer review, or margin queue analysis. Use when a task bundle includes a Northstar case, claim, queue, appeal, or P2P record plus a task-specific answer template.
---

# Northstar Structured Reviews

## Overview
Use this skill to turn a Northstar task bundle into strict JSON that matches the supplied answer template. The bundle usually includes a prompt, task context, an answer template, and an environment access note.

## Workflow
1. Read `prompt.txt`, `task_context.json`, and `answer_template.json`.
2. If `environment_access.md` is present, use it only to obtain the base URL and bearer token for the shared environment.
3. Use the shared environment endpoints or `POST /sql/query` to pull only the records needed to answer the template.
4. Treat `answer_template.json` as the contract. The prompt explains the business question; the template defines the output shape.
5. Return JSON only. Do not add prose, markdown, comments, or extra keys.

## Identify the family
- `authorization` plus PT criteria and document lists -> UM nurse determination.
- `appeal_id`, `drug`, and `assistance` -> pharmacy appeal and manufacturer assistance intake.
- `claim_id`, `benchmark_source`, and `lines` -> claim repricing / payment integrity.
- `p2p_id`, PET criteria, and `missing_pet_factors` -> peer-to-peer review.
- `period`, `rows`, and a threshold ratio -> margin queue analysis.

## Shared rules
- Match field names, nesting, and enum values exactly.
- Preserve required ordering rules from the template.
- Use ISO calendar dates and cents-rounded currency when required.
- Use `null` only when the schema allows it.
- Keep list order exactly as requested by the schema or source record order.
- If the template forbids extra fields, omit everything not named in the schema.
- Keep `basis_audit` records in precedence order: controlling records first, then exceptions or exclusions.

## Family-specific handling
### UM nurse review
- Fill `authorization`, `criteria_results`, `evidence_documents`, `excluded_documents`, `determination_letter`, and `next_action`.
- Prefer current clinical records over stale exports.
- Put the records that directly control the outcome into `controlling_record_ids`.

### Pharmacy appeal and assistance
- Split failures into documented vs insufficient evidence.
- Keep appeal packet items before assistance items.
- Use the assistance status that matches the drug/program fit and the missing fields actually absent.

### Claim repricing
- Use the effective benchmark source and version for the claim context.
- Recalculate each line in claim-line order, then the totals and recovery amount.
- Mark stale rate sources as rejected in `stale_source_rejected`.

### Peer-to-peer review
- Resolve `PET-IND` and `PET-FACTOR`, then list only unresolved criteria.
- Record whether new patient-specific information materially changed the review.
- If adverse, include the internal appeal deadline.

### Margin queue
- Keep rows in the queue row order from the context.
- Flag below-threshold and charge-sensitive rows according to the template rules.
- Identify the top issue and the gap to 120 percent of cost.

## Audit trail
- Use actual record IDs from the environment.
- Put controlling IDs first in `precedence_record_order`, then exceptions and stale or excluded records.
- Do not invent audit IDs or reuse task labels as record IDs.
