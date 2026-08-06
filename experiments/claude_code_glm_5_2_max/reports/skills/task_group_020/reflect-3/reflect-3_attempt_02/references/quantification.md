# Quantification Conventions

These conventions apply across every deal-workbench task. Apply them uniformly so dollar totals are comparable and enums match.

## Units
- **Currency: integer USD.** Round to the nearest dollar (`int(round(x))`). Never cents, never floats in money fields.
- **Percent points: numbers.** Precision is per-template — read the template's `units` block (e.g. "percent_points: number rounded to two decimal places" vs "to one decimal place"; holder percentages may be "to four decimals").
- **Months: integers.**
- Use `null` (not `0`, not `""`) for a field that does not apply to an issue. Use `0` only when zero is the factual answer (e.g. a draft reverse-break-fee of 0%).

## Choosing the dollar basis
**Default: the deal's `headline_value` (total deal value).** But a term/rule/policy may state a different `basis` — honor it:

- A reverse-break-fee or termination-fee rule with `basis: "equity value"` → compute on the equity-value base. The deal record's `stock_value` is the equity portion, BUT some drafts state the fee "of equity value" while meaning the full deal headline. Always verify: if the draft text gives both a percent AND a dollar ("X% of equity value, equal to $Y"), recover the base as `Y / (X/100)` and use **that** base for both the draft amount and the threshold amount so the delta is consistent.
- An indemnity-cap or escrow rule with `basis: "purchase price"` → compute on `headline_value`.
- A financing/reverse-break-fee rule with `basis: "enterprise value"` → use the deal headline value when no separate EV is published (APA deals often have `stock_value: 0`).
- For SPA holder allocation, split consideration into the cash pool (`upfront_cash`) and stock pool (`stock_value`) and allocate each holder pro-rata by their cap-table percentage.

## Cap-table percentages are fractions
`fully_diluted_pct` is a **fraction** (e.g. `0.092`), not a percent (`9.2`), despite the name. The holders' values sum to 1.0. Use the fractions directly at the precision the template requests, and allocate holder cash/stock amounts as `fraction × pool`, rounded to integer dollars.

## Stable IDs
Use workbench IDs **verbatim**: `term_id`, `consent_id`, `contract_id`/material-contract id, `employee_id`, `finding_id`, `estimate_id`, `benchmark_id`. For a term that is genuinely missing from the draft, use an empty array `[]` for `source_term_ids`. Only synthesize an ID when a template explicitly authorizes it (e.g. a synthetic regulatory-clearance blocker id).

## Status / risk / action derivation
- Status comes from comparing the draft numeric_value to the playbook preferred/fallback or policy threshold on the matching basis/unit (see SKILL.md classification table).
- Risk rating defaults to the playbook `risk_default`; for policy items, weight the breach magnitude and any matching risk-estimate category.
- Recommended action mirrors the playbook `required_action` (escalate / revise / add / accept) or, for policy items, approve / approve_with_conditions / reject.

## Exposure totals
- Sum `exposure_low` across the categories the template includes; do the same for `exposure_high`. Some templates include all three risk-estimate categories (closing certainty, indemnity leakage, transition disruption); others exclude transition disruption. Include only what the template's `included_exposure_components` (or equivalent) names.
- Benchmark "position" is judged on the **metric the benchmark measures** (e.g. general-representation survival months), not a different metric, even when the draft reports a related-but-different figure (e.g. fundamental-rep survival).

## Output shape
One JSON object, template-conformant, no prose, no markdown fences. Arrays sorted per the template (usually `issue_id` ascending, or by a `priority_order`/`priority_rank` you also emit).
