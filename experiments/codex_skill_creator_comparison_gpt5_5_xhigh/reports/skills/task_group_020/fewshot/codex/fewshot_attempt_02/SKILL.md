---
name: ma-deal-workbench-review
description: Analyze M&A deal workbench tasks that require counsel-side JSON outputs using TASK_ENV_BASE_URL/API records, playbooks or policies, issue matrices, closing packages, committee escalations, transition reviews, consents, employees, regulatory records, benchmarks, risk estimates, and schema-conformant answer_template.json responses.
---

# M&A Deal Workbench Review

## Core Workflow

Use this skill when a task asks for buyer-side or seller-side counsel analysis from an M&A deal workbench and requires JSON matching an `answer_template.json`.

1. Read the prompt and `input/payloads/answer_template.json` first. Extract the deal ID, client side, deal type, requested package type, applicable playbook or policy IDs, required ordering, units, enum values, and whether in-policy terms should be included or excluded.
2. Collect deal records from `TASK_ENV_BASE_URL` using the routes named in the prompt. A helper is available:

   ```bash
   python skill/scripts/fetch_workbench.py "$TASK_ENV_BASE_URL" "$DEAL_ID" --playbook-id "$PLAYBOOK_ID" --policy-id "$POLICY_ID" --output workbench_records.json
   ```

   Omit unknown optional IDs. Use direct API calls for any prompt-specific endpoint not covered by the helper.
3. Compare only records for the exact deal ID. Do not use similarly named projects, stale terms, or records from other deals.
4. Treat current draft terms as the draft position. Treat playbook rules and policy thresholds as the required, preferred, fallback, or committee-approved positions.
5. Fill the template exactly and return only valid JSON. Use stable source IDs from the workbench. Do not add narrative outside the JSON.

## Record Review

Load enough sources to support every requested section:

- `deals`: party names, project name, target, transaction type, headline value or equity value, signing and meeting dates, currency, playbook or policy references.
- `terms`: current draft positions, clause references, status, term IDs, percentages, dollar caps, baskets, survival periods, escrow or holdback terms, consent conditions, closing conditions, covenants, governing law, and transition terms.
- `playbooks` or `policies`: preferred positions, fallback positions, approval thresholds, restricted changes, required affirmative terms, permitted exceptions, and committee routing.
- `risk-estimates`: modeled exposure ranges and risk categories. Use these for exposure totals only when the task asks for modeled exposure.
- `employees`: employee groups, continuing employee counts, service credit, PTO/accrual liability, WARN or retention issues, and employee IDs when the schema asks for them.
- `consents` and `material-contracts`: required closing consents, notice-only items, post-closing covenants, counterparty names, amounts at risk, annual revenue, and material-contract blocker IDs.
- `regulatory`: HSR or other approval requirements, clearance status, outside dates, remedy covenants, hell-or-high-water obligations, and regulatory closing conditions.
- `benchmarks`: median, upper quartile, sample size, and position classification for terms that need market support.
- `diligence-findings`, `documents`, and `notes`: gaps, draft silence, issue context, unresolved agents or releases, special indemnities, privacy findings, transition disruption, and distractor flags.

See [references/issue_workflow.md](references/issue_workflow.md) for reusable issue classification and calculation rules.

## Issue Selection

Start from the issue IDs, redline IDs, blocker types, and enum values in the answer template. Build an issue only when one of these is true:

- The current draft term deviates from the relevant playbook, policy, preferred position, fallback position, or approval threshold.
- A required protective provision is absent and the deal data shows the provision is needed.
- The prompt asks for all covered positions, including accepted or in-policy positions.
- The template has a dedicated required output section for the issue, blocker, redline, condition, or summary metric.

Exclude records that are stale, expressly non-current, in-policy when the prompt asks only for escalations, or unrelated to the requested package.

## Status and Side Logic

Use the template's exact enum strings. Apply these meanings consistently:

- `missing_required_term`: no current draft term exists for a provision required by the prompt, playbook, policy, or surrounding deal data.
- `draft_below_playbook`: the draft gives less protection than the client's buyer-side required or fallback position.
- `draft_exceeds_playbook`: the draft imposes more burden or exposure than the client's seller-side required or fallback position.
- `out_of_policy`: the draft violates a policy threshold or restricted term that requires approval.
- `in_policy`: the draft satisfies the required position and the prompt or template still asks to report it.

For buyer-side tasks, gaps usually require adding or strengthening buyer protections. For seller-side tasks, buyer-favorable conditions, long survival, excessive escrow, broad termination rights, transition burdens, or unrestricted covenants usually require deletion, narrowing, or fallback caps. Committee-escalation tasks usually include only current out-of-policy or restricted terms unless the prompt says otherwise.

## Calculations

Use integer dollars unless the template specifies otherwise. Preserve source-provided amounts when an API record states a dollar value. Otherwise calculate percentage amounts from the correct source basis:

- Use the prompt's specified basis first.
- If the record states a basis, use that basis.
- Otherwise use the deal's headline purchase price, headline value, equity value, or upfront cash field that matches the template label.

Round percentages to the precision required by the prompt. Convert percentage points with:

```text
amount = round(value_basis * percent_points / 100)
```

Calculate deltas from the client-side fallback unless the template asks for preferred:

- Buyer shortfall: `fallback_or_preferred_amount - draft_amount`.
- Seller excess: `draft_amount - fallback_or_preferred_amount`.
- Month excess or shortfall follows the same client-side direction.
- Aggregate negotiation delta is the sum of dollar deltas requested by the template, not a sum of unrelated exposure ranges.
- Aggregate modeled exposure is the sum of included risk-estimate components only; list excluded components when the schema asks.
- Required consent amount at risk and material-contract revenue totals should include only required closing conditions or material-contract blockers, not notice-only or post-closing items.

For cap-table allocations, use fully diluted percentages or as-converted shares from the source record. Allocate each consideration component separately, round to integer dollars, and ensure totals reconcile to the source economics when the template requires a complete allocation.

## Output Discipline

Before finalizing:

- Validate the JSON parses with `python -m json.tool`.
- Compare every key, enum, null, boolean, array, and ordering rule against `answer_template.json`.
- Use `null` for unknown or not applicable scalar values and `[]` for empty arrays unless the template directs a different sentinel.
- Keep stable source IDs in the fields intended for IDs. Put human-readable names only in fields intended for names.
- Do not invent missing evidence. If a value is not in the workbench and cannot be calculated from stated data, use the template's unknown or not-found value.
- Do not include train-task deal IDs, party names, dollar amounts, percentages, dates, or reconstructed answer records in the output.
