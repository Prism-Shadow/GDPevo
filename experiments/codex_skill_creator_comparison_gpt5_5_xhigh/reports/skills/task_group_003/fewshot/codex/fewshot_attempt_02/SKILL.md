---
name: support-console
description: Resolve structured support-console tasks from staged payloads and task-environment API evidence, including offline ticket triage, contact-center case routing, queue-quality reviews, enterprise export complaint packages, and mobile-data recovery. Use when prompts mention the support-console API, the task-environment base URL, support records, or an exact JSON answer template.
---

# Support Console

Use this skill for staged support-console tasks that require reconciling payloads with API evidence and returning exact JSON.

## Workflow

1. Read the prompt, every file in `payloads/`, and the answer template first.
2. Query the task-environment API for only the IDs and dates named in the payload.
3. Follow [references/task-map.md](references/task-map.md) for the family-specific record order and decision cues.
4. Preserve input order, use template enums exactly, and compute summary fields from the item decisions.
5. Return JSON only.

## Guardrails

- Do not invent IDs, owners, outage IDs, charges, or permissions.
- Use `NO_ACTION` only when the template allows a filler step.
- Round currency and quantities to the template precision.
- If evidence is missing, inspect the next linked record type rather than guessing.
- For response-package tasks, follow the naming rules in the requirements file instead of copying sample text.
