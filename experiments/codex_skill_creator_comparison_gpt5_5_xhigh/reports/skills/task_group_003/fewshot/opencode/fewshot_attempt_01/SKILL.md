---
name: support-console-resolver
description: "Resolve support-console ticket, queue, mobile, and enterprise incident prompts into exact JSON. Use this whenever a task provides support-console payload files plus an answer template and asks for classified decisions, action routing, summary counts, or incident response fields, even if it does not mention the support console explicitly."
---

# Support Console Resolver

Use this skill when the task is a support-console batch job: the prompt gives you payload files plus an answer template, and the final deliverable is strict JSON.

## Operating rule

Treat the answer template as the contract. Preserve the requested order, fill every required field, and return JSON only.

## Workflow

1. Read the prompt, the answer template, and every payload file together.
2. Identify the schema family by its top-level keys.
3. Use the support-console API to fetch only the records needed to resolve each item.
4. Cross-check the payload IDs against the records before deciding.
5. Write one decision per input row or item in the template order. Do not re-sort unless the template explicitly says to preserve ascending `case_id` order.
6. Recompute any summary block from the final decisions.
7. Return a single JSON object with no prose, fences, or commentary.

## How to choose actions

- Use direct evidence from the console records, not just the free-text complaint.
- Prefer the smallest action that actually fits the record state.
- Treat local device toggles, carrier-side updates, billing recovery, outage waits, and escalation as different outcomes, not interchangeable ones.
- Mark failures only when the template's rules make the case ineligible, invalid, or unsalvageable in the current workflow.

## Family playbook

Read [references/support-console-playbook.md](references/support-console-playbook.md) for the specific field-mapping rules for ticket triage, mobile recovery, queue classification, and enterprise incident responses.

## Final checks

- Preserve the template's required ordering and enum spelling.
- Use the exact numeric formatting the schema asks for.
- Use empty strings, zeroes, or false only when the schema expects them.
- Never invent extra keys.
- Never add markdown around the final JSON.
