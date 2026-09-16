---
name: apexcloud-retention-ops
description: Build JSON reports from the ApexCloud Retention Operations API. Use this whenever a prompt mentions ApexCloud, renewal risk queues, QBR metric packets, receivables or pipeline reviews, churn validation, or retention boards, even if the report type is only implied.
---

# ApexCloud Retention Ops

Use this skill for structured JSON deliverables built from the ApexCloud Retention Operations API.

## Workflow

1. Read the prompt and the provided answer template together.
2. Treat the template as the schema contract. Copy its keys, nesting, and ordering exactly.
3. Extract the report type, scope list, date range, month buckets, and as-of date before you query anything.
4. Use the task-environment base URL from the prompt or workspace note, then query only the endpoint families the task actually needs.
5. Fill the template with computed values, not placeholders. Choose one concrete enum value wherever the template offers a controlled vocabulary.
6. Reconcile totals, rankings, and sort order against the detailed rows before you finish.
7. Return JSON only.

## Report families

When the prompt is one of the recurring ApexCloud report types, use the matching playbook in [references/report-archetypes.md](references/report-archetypes.md).

## Output discipline

- Respect explicit scope limits. Do not expand beyond the listed account IDs or candidate IDs.
- Keep ranked lists in the order the prompt asks for.
- Use chronological month order unless the prompt says otherwise.
- Keep currency values to 2 decimals, percentages to 1 decimal, counts as integers, and probabilities to the requested precision.
- Preserve controlled labels exactly as written in the prompt or template.
- Use `null` only when the template or prompt explicitly allows it.
- Do not invent source systems, labels, or extra keys.

## Sanity checks

- Does every required field exist in the final object?
- Do summary counts match the detailed lists?
- Are the selected labels valid members of the template vocabulary?
- Did you use the correct source family for each metric?
- Is the final response valid JSON with no markdown fencing or commentary?
