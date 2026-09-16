---
name: apexcloud-retention-ops
description: Build exact JSON-only reports from the ApexCloud Retention Operations API. Use when a prompt mentions ApexCloud retention data, task environment API calls, account metrics, billing, support tickets, NPS, A/R aging, opportunities, HR summary, event performance, churn exports, renewal risk queues, QBR packets, receivables reviews, retention boards, or any similar structured business output that must match an answer template and controlled label vocabulary.
---

# ApexCloud Retention Ops

Use this skill for the staged ApexCloud reporting tasks.

## Workflow

1. Read the prompt and the answer template first. Treat the template as the contract for keys, nesting, item order, and allowed enum values.
2. Identify the report family and requested slice. Read [references/api_patterns.md](references/api_patterns.md) when the prompt combines multiple data sources or the endpoint mapping is not obvious.
3. Fetch only the needed records from the local task environment described in `environment_access.md`.
4. Build a local fact table from the live data, then calculate the requested rankings, summaries, or validation metrics.
5. Keep every controlled label exactly as written in the prompt or template. Do not invent synonyms or widen the vocabularies.
6. Normalize the final JSON:
   - currency: 2 decimals
   - percentages: precision requested by the prompt
   - probabilities: 3 decimals when requested
   - counts and scores: integers unless the template says otherwise
7. Verify the result before returning it:
   - item count matches the prompt
   - ranks and sort order match the instructions
   - totals reconcile with item-level values
   - nulls, booleans, and strings match the template types
   - no extra prose, markdown, or code fences

## Output discipline

Return only the JSON object. If the template includes policy or model codes, choose from the template's allowed values and do not invent new ones.
