---
name: apexcloud-retention-ops
description: Build ApexCloud retention-ops JSON deliverables from the public task-env API and churn CSV exports. Use when asked for customer risk queues, QBR packets, receivables and pipeline reviews, retention action boards, or churn validation/ranking from the staged ApexCloud environment.
---

# ApexCloud Retention Ops

## Start

1. Identify the deliverable family from the prompt: risk queue, QBR packet, receivables review, action board, or churn validation/ranking.
2. Read the prompt template first, then mirror its key order exactly.
3. Use [references/apexcloud_rules.md](references/apexcloud_rules.md) for field precedence, joins, and rollup rules.
4. Use [scripts/apexcloud_ops.py](scripts/apexcloud_ops.py) when a normalized draft will save time.

## Data precedence

- Use billing snapshots for ARR when the prompt asks for current ARR, exposure, or ARR at risk.
- Use exact normalized legal-name matching for A/R aging links. Do not fuzzy-match similar subsidiaries or noise rows.
- Exclude spam, duplicate, and cancelled tickets from clean support counts and SLA math.
- Treat SLA as met only when both first response and resolution SLA are true.
- Use the latest non-retracted NPS response inside the window.
- Sum only open opportunities inside the requested window for open pipeline.
- Keep CRM ARR separate from billing ARR unless the prompt explicitly asks for CRM exposure.

## Output rules

- Return JSON only unless the prompt explicitly asks for something else.
- Preserve the template shape and key order.
- Round currency to 2 decimals, percentages to 1 decimal, counts as integers, and probabilities to 3 decimals.
- Sort rows the way the prompt asks: score desc, customer name asc, month asc, or rank asc.
- Fill policy-code fields last. Choose the code whose label matches the rule you actually used.

## Task families

### QBR packet

- Build monthly revenue from the account metrics endpoint.
- Recompute support ticket counts and SLA compliance from clean tickets, not from raw monthly ticket totals.
- Derive the ticket trend from the month sequence in the prompt.
- Use the prompt's source enums for revenue, support tickets, SLA compliance, and NPS.

### Receivables and pipeline review

- Start from A/R aging rows with overdue in the older buckets.
- Link A/R rows to CRM accounts only by exact normalized legal name.
- Sort overdue followups by `customer_name` ascending.
- Summarize pipeline from opportunities in the requested window, separating open, won, and lost.
- Pull HR and event context from the requested summary endpoints and aggregate across regions when needed.

### Risk queue and action board

- Score accounts from renewal timing, overdue balance, NPS, SLA, usage trend, tenure, and open expansion pipeline.
- Use `collections_followup` when overdue receivables dominate.
- Use `technical_recovery` when support or product health dominates.
- Use `renewal_save` when renewal timing is the main risk.
- Use `nurture_monitor` only when the account is low risk.

### Churn validation and ranking

- Fit on `train.csv`, validate on `validation.csv`, then rank only the requested candidates.
- Use the heuristic fallback in the helper script if you do not have a stronger model.
- Keep the validation summary simple: row counts, feature count, accuracy, band, and tenure direction.

## When the environment is awkward

- If a per-account billing or A/R URL returns `not_found`, fall back to the collection endpoint and filter in memory.
- If the prompt gives a fixed follow-up calendar, map actions to those dates directly.

