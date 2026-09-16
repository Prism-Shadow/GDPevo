---
name: ma-deal-workbench-json
description: Use for M&A deal workbench tasks that ask counsel to review APA, SPA, merger, transition, closing, economics, policy, or committee issues and return strict JSON from an answer template. Covers fetching deal APIs, comparing draft terms against buyer or seller playbooks and committee policies, identifying missing required provisions, calculating dollar and percentage metrics, classifying risks and closing blockers, and emitting schema-conformant JSON with stable source IDs.
---

# M&A Deal Workbench JSON

## Core Workflow

1. Read the prompt and answer template before fetching records. Extract the `deal_id`, client side or committee role, required playbook or policy if named, required endpoints, units, enum values, output ordering, and any explicit inclusion or exclusion rule.
2. Gather workbench data for the exact `deal_id`. Use the API routes in the prompt first, then fetch adjacent available routes for the same deal when the requested JSON needs them: terms, playbook rules, policy thresholds, benchmarks, risk estimates, cap table, consents, employees, material contracts, regulatory, diligence findings, documents, and notes.
3. Compare only current applicable draft terms against the controlling buyer/seller playbook or committee policy. Treat draft silence as an issue only when the playbook, policy, deal facts, regulatory facts, document record, or notes show an affirmative provision is required.
4. Fill every required field from the template using stable IDs from the workbench. Use an empty `source_term_ids` array for missing terms. Do not invent IDs; create synthetic IDs only when the template or prompt clearly allows them for regulatory or aggregate items.
5. Return only valid JSON. No commentary, markdown, or citations outside the object.

Use [references/workbench-workflow.md](references/workbench-workflow.md) when the task involves legal issue classification, monetary calculations, closing blocker selection, policy escalation, or aggregate metrics.

## Data Collection

Use `scripts/fetch_deal_workbench.py` when you want a repeatable first-pass record dump. From this skill package directory, run:

```bash
python scripts/fetch_deal_workbench.py --base-url "$TASK_ENV_BASE_URL" --deal-id "$DEAL_ID" --playbook-id "$PLAYBOOK_ID" --policy-id "$POLICY_ID" > /tmp/deal.json
```

If the prompt gives no playbook or policy ID, fetch the deal record first and derive it from fields such as `playbook_id`, `seller_playbook_id`, `buyer_playbook_id`, `policy_id`, or similarly named metadata. Keep all subsequent lookups scoped to the same deal.

## Output Discipline

- Match the answer template exactly: object names, arrays, enum strings, nullable fields, and ordering instructions.
- Use integer dollars, integer months, and the prompt/template rounding rule for percentage points. If no rule is supplied, use two decimal places for percent points.
- Calculate dollar amounts from the stated basis. If the rule does not name a different basis, use the deal headline purchase price or equity value as applicable to the task.
- Sort and prioritize according to the template. When no sort is specified, order by counsel workflow priority: closing certainty and required consents, regulatory clearance, headline economics, indemnity/escrow/survival, employee continuity, transition/separation, tax, governing law/forum, then lower-risk cleanups.
- Exclude stale, in-policy, non-current, wrong-deal, or non-requested records unless the template asks to list exclusions.
