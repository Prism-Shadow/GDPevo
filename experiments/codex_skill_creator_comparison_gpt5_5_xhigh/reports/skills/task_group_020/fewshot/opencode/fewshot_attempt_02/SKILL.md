---
name: mna-workbench-json
description: Prepare strict JSON outputs for M&A deal-workbench tasks. Use when a user asks for seller or buyer APA/SPA issue registers, deviation matrices, closing/economics packages, committee escalation memos, transition reviews, or any structured M&A analysis that must compare deal-workbench records against playbooks, policies, benchmarks, risk estimates, consents, employees, cap tables, regulatory records, diligence findings, notes, or draft terms.
---

# M&A Workbench JSON

Use this skill to answer deal-workbench tasks that require a JSON-only legal or business output. The core job is to collect current deal evidence, compare draft terms against the applicable playbook or policy, calculate normalized amounts, and fill the provided answer template exactly.

Before deriving issues, read [references/mna_issue_mapping.md](references/mna_issue_mapping.md). Use [scripts/fetch_workbench.py](scripts/fetch_workbench.py) when an HTTP workbench is available and you want a complete evidence snapshot.

## Workflow

1. Read the user prompt and the provided `input/payloads/answer_template.json` before fetching data.
2. Extract the deal ID, client side, deal type, output units, enum values, required fields, ordering rules, and any named playbook or policy IDs from the prompt and template.
3. Resolve the task workbench base URL from the prompt or task environment instructions. Stay inside the allowed workbench endpoints.
4. Fetch enough evidence to support every requested template section: deal record, current terms, playbook rules or policy thresholds, risk estimates, benchmarks, consents, material contracts, regulatory status, employees, cap table, diligence findings, documents, and notes as applicable.
5. Build an evidence table before drafting JSON. For every issue, record the source term IDs, source record IDs, governing rule or threshold, calculation basis, and any risk estimate used.
6. Compare only current applicable draft terms against the client-side rule set. Exclude stale, unrelated, in-policy, or distractor records when the prompt asks for escalations or deviations only.
7. Treat draft silence as an issue when the playbook, policy, prompt, or surrounding deal evidence requires an affirmative provision.
8. Calculate all dollars and percentages from the source-stated basis. If the prompt says to use headline purchase price or equity value unless another basis is stated, do that; otherwise prefer the explicit basis attached to the term, rule, or risk estimate.
9. Assemble the answer directly in the template shape. Use exact enum strings and stable IDs from the workbench. Return JSON only.

## Evidence Collection

Prefer the bundled fetch helper from the skill directory:

```bash
python scripts/fetch_workbench.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --deal-id "$DEAL_ID" \
  --out /tmp/deal_evidence.json
```

Add `--playbook-id` or `--policy-id` when the prompt names them:

```bash
python scripts/fetch_workbench.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --deal-id "$DEAL_ID" \
  --playbook-id "$PLAYBOOK_ID" \
  --policy-id "$POLICY_ID" \
  --out /tmp/deal_evidence.json
```

If read-only SQL is explicitly allowed, use it only to cross-check missing or ambiguous relationships. Do not use SQL to bypass the prompt's evidence boundary. The API records remain the primary source for stable IDs and business labels.

## Derivation Rules

Use the template as the contract for output names, enum spelling, nullability, ordering, and precision. Do not invent fields.

For each candidate issue:

- Use `source_term_ids` only for current draft terms that actually contain the relevant provision.
- Use an empty `source_term_ids` array for missing required terms.
- Put consent, employee, material contract, diligence, regulatory, risk, note, or document IDs in fields meant for source records, blockers, or conditions.
- Classify `draft_below_playbook` when buyer-side protection is too weak or seller-side consideration/protection is below the seller fallback.
- Classify `draft_exceeds_playbook` when the draft imposes more burden or exposure than the client-side fallback allows.
- Classify `missing_required_term` when the required affirmative term is absent from current terms.
- Classify `in_policy` only when the prompt/template asks to include accepted positions; otherwise omit in-policy items from escalation-only outputs.

Common high-priority blockers include required closing consents, material-contract consents, regulatory clearance, financing-condition risk, indemnity/escrow gaps, employee transition gaps, and missing separation protections. Priority order should reflect closing certainty and economic exposure first, then operational continuity, then legal cleanup, unless the template gives a fixed order.

## Calculation Rules

- Convert percentages to dollar amounts as `round(basis_dollars * percent / 100)` and output integer dollars.
- Preserve the prompt's requested percent precision: one decimal, two decimals, whole percent points, or holder percentages to four decimals.
- For buyer shortfalls, calculate fallback or preferred amount minus draft amount when the draft is below the required protection.
- For seller deltas, calculate draft burden minus fallback burden when the draft exceeds the allowed seller fallback.
- For month deltas, use draft months minus fallback months when the draft is too long; use fallback months minus draft months when the draft is too short.
- Sum closing consent exposure only for required closing consents, not notice-only or post-closing covenant items.
- Sum material-contract revenue only for contracts that require consent or are requested as closing conditions. Exclude notice-only or explicitly excluded contracts.
- Aggregate risk exposures from risk-estimate records tied to included issues. Avoid double-counting the same source estimate in multiple summary totals unless the template asks for separate components.
- For holder allocations, allocate each consideration component by fully diluted percentage or as-converted ownership from the cap table, then check that totals reconcile to the deal economics after rounding.

## Final JSON Gate

Before finalizing:

- Parse the answer with `jq .` or Python `json.load`.
- Check every required template key is present, including nested keys whose value is `null`, `[]`, or `{}`.
- Check IDs are stable source IDs from the workbench or template-approved synthetic IDs.
- Check summary counts equal the included arrays.
- Check totals equal their component sums and use the correct basis.
- Check the final response contains only the JSON object, with no Markdown fence or explanatory prose.
