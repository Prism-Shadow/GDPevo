---
name: ma-deal-workbench
description: Analyze M&A deal workbench records for buyer-side or seller-side APA, SPA, merger agreement, transition, closing readiness, committee escalation, and deviation-matrix tasks. Use when a prompt provides a TASK_ENV_BASE_URL or deal APIs with draft terms, playbooks or policies, consents, regulatory facts, employees, cap tables, material contracts, diligence findings, risk estimates, benchmarks, documents, or notes and requires exact schema-conformant JSON.
---

# M&A Deal Workbench

## Core Rule

Produce the requested JSON from the current task's deal workbench records and answer template only. Do not reuse values from prior examples, train records, similarly named deals, or memory. Return no prose outside the JSON.

Read `references/reasoning-rules.md` before analyzing any substantive deal task. Use `scripts/workbench_snapshot.py` when a quick API snapshot would reduce missed records.

## One-Pass Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Capture the deal ID, client side, agreement type, playbook or policy ID, output sections, required units, enum values, sorting instructions, and whether in-policy items should be included or excluded.
2. Resolve `<TASK_ENV_BASE_URL>` from the task environment or prompt. Fetch every endpoint listed in the prompt, then fetch common supporting endpoints when relevant: deal record, terms, playbook or policy rules, risk estimates, employees, consents, regulatory, benchmarks, notes, cap table, material contracts, diligence findings, and documents.
3. Build a source map keyed by stable workbench IDs. Separate current draft terms from stale terms, superseded notes, non-committee distractors, notice-only consents, and records for other deals.
4. Compare current draft terms and draft silence against the side-specific playbook or committee policy. Treat absent protective terms as issues when the prompt, playbook, or surrounding deal facts require an affirmative provision.
5. Calculate all amounts from the base named by the prompt or source record. If the source gives no different basis, use the deal headline purchase price or equity value as directed. Round currency to integer dollars and percentages/months exactly as the template requires.
6. Populate only fields allowed by the template. Use template enum strings verbatim. Use `null` for not applicable numeric fields, `0` for real zero values, and `[]` for no stable source IDs.
7. Validate the output shape, ordering, counts, totals, and JSON syntax before final response.

## Evidence Collection

Prefer API records over inference. The optional helper writes a JSON snapshot while tolerating missing routes:

```bash
python skill/scripts/workbench_snapshot.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --deal-id "$DEAL_ID" \
  --playbook-id "$PLAYBOOK_ID" \
  --out /tmp/deal-workbench-snapshot.json
```

If read-only SQL is available, use it only for cross-table checks or to find records not exposed through documented routes. Keep API and prompt facts authoritative when records conflict.

## Output Discipline

- Preserve the template's top-level shape and stable identifiers.
- Use stable source IDs from the workbench. For missing required terms, set term ID arrays to empty and cite document, regulatory, consent, or diligence source IDs where the template provides a place for them.
- Follow requested ordering. If none is specified, order issue arrays by the template's stable issue IDs or a clear counsel workflow, and order priority arrays from highest negotiation or closing risk to lowest.
- Count only included issues in issue totals. Count unique business outcome categories when the template asks for business outcome count.
- Sum only exposure components the prompt or template asks to include. Do not add non-quantified risks, excluded components, or benchmark values to exposure totals.
- Emit valid JSON only. Do not include markdown fences, citations, or explanation.
