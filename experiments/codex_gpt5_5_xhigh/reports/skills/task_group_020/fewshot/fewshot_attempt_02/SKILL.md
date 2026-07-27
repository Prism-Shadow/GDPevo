---
name: deal-workbench-ma-review
description: Prepare strict JSON M&A legal review outputs from a running deal workbench. Use when a task asks Codex to act as buyer-side, seller-side, or committee M&A counsel, gather deal/workbench records over the provided API, compare draft acquisition terms against playbooks or policy thresholds, quantify deviations, identify closing blockers or missing required provisions, and return an answer conforming exactly to a supplied JSON template.
---

# Deal Workbench M&A Review

Use this skill to complete M&A deal-workbench tasks that require a structured JSON legal package rather than prose.

## Required Inputs

- The user prompt, especially the client side, deal ID, requested work product, rounding rules, and named playbook or policy.
- The task's `input/payloads/answer_template.json`; treat it as the output contract.
- The environment access file for the base URL, allowed endpoints, and SQL token if available.

Do not infer facts from similarly named projects or previous examples. Use only records for the requested deal ID.

## Collect The Workbench Bundle

Prefer API records over the web UI. Use `scripts/collect_workbench_bundle.py` when a base URL is available:

```bash
python3 <skill>/scripts/collect_workbench_bundle.py \
  --base-url "$GDPEVO_ENV_BASE_URL" \
  --deal-id "$DEAL_ID" \
  --query-token "$QUERY_TOKEN" \
  --output /tmp/deal-bundle.json
```

If the prompt names a playbook or policy that is not present on the deal record, pass it explicitly with `--playbook-id` or `--policy-id`.

Gather, when available:

- `/api/deals/<deal_id>` for value base, client side, counterparty, dates, playbook, policy, and links.
- `/api/deals/<deal_id>/terms` for current draft terms, including term IDs, categories, clauses, numeric values, units, basis, and staleness flags.
- `/api/playbooks/<playbook_id>/rules` for preferred and fallback positions.
- `/api/policies/<policy_id>/thresholds` for committee approval thresholds and restricted positions.
- Deal subresources for consents, material contracts, regulatory facts, risk estimates, benchmarks, employees, cap table, diligence findings, documents, and notes.
- `POST /api/query` only for read-only cross-table checks, using the provided token.

Record stable source IDs from API records and carry them into the JSON. Use empty arrays for missing draft terms when the template requires source-term arrays.

## Analyze The Deal

1. Parse the answer template first. Preserve its top-level shape, field names, enum values, ordering instructions, null conventions, and requested rounding.
2. Determine the correct value base for each calculation. Use the deal's headline value unless the prompt, term, playbook rule, policy threshold, or template states a different basis.
3. Normalize draft terms by category. Ignore stale terms unless the prompt asks for stale records; exclude in-policy or distractor terms when the requested package is limited to deviations or committee escalations.
4. Compare each relevant draft term against the applicable buyer playbook, seller playbook, or committee policy:
   - Buyer-side reviews usually flag draft positions below buyer fallback/preferred protection, missing closing conditions, missing escrow/holdback mechanics, insufficient survival, incomplete materiality scrape, missing HSR condition, and inadequate consent/material-contract blockers.
   - Seller-side reviews usually flag buyer overreach above seller fallback/preferred limits, missing seller-protective terms, financing or closing-certainty risk, excessive escrow or cap, transition-service exposure, employee continuity/PTO issues, tax allocation gaps, and missing governing law/forum provisions.
   - Committee packages should include only current out-of-policy or restricted terms requiring approval and should list stale, in-policy, or non-committee items only if the template asks for exclusions.
5. Treat required playbook provisions absent from the draft as issues when the surrounding deal data shows the term is needed, such as HSR records, required consents, employee transfer facts, material contracts, tax allocation requirements, D&O tail, or transition services.
6. Use benchmarks as support, not as substitutes for playbook or policy thresholds. Classify benchmark position relative to median and upper quartile when the template requests it.
7. Use risk estimates for modeled exposure totals. Include only exposure categories requested by the template; do not double-count the same modeled exposure under multiple issue summaries.

## Calculation Rules

- Currency values: output integer dollars.
- Percentages: output percent points, rounded exactly as the prompt/template requires.
- Months, days, years, counts, and ranks: output integers.
- Holder allocation: multiply upfront cash, stock value, and total value by each holder's fully diluted percentage; round to integer dollars and keep holder percentages at the requested precision.
- Cap, escrow, basket, reverse-fee, holdback, and threshold amounts: multiply the relevant base by the applicable percent.
- Shortfall to fallback/preferred: for buyer-side protection, calculate required amount minus draft amount; for seller-side overreach, calculate draft amount minus allowed fallback amount.
- Consent amount at risk and material-contract revenue: sum only records classified as required pre-closing blockers by the prompt/playbook and the source records.
- Employee PTO liability: sum relevant employee groups or use the direct source value if already aggregated.

## Build The JSON

- Return only valid JSON. No markdown, comments, or explanatory prose.
- Fill every template-required field, even when the value is `null`, an empty array, or an empty object.
- Use stable source IDs from the workbench for terms, consents, contracts, findings, risk estimates, notes, documents, employees, and regulatory synthetic IDs when the template permits them.
- Keep issue arrays sorted according to the template. If the template asks for priority order, order highest negotiation or closing risk first and make ranks match that order.
- Set statuses from the template enums:
  - `missing_required_term` for required provisions absent from current draft terms.
  - `draft_below_playbook` when buyer protection is below required fallback/preferred levels.
  - `draft_exceeds_playbook` when buyer demands exceed seller fallback/preferred limits.
  - `out_of_policy` for policy breaches or restricted committee terms.
  - `in_policy` only when the requested matrix explicitly includes acceptable positions.
- Before finalizing, validate the JSON parses and conforms to the template's required fields and enum constraints.

