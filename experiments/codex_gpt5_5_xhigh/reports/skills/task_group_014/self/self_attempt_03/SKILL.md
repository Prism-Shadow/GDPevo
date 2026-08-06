---
name: northstar-payer-ops
description: Structured JSON disposition and correction packets for Northstar payer-operations tasks. Use when a prompt provides task_context.json and answer_template.json and asks for UM determination, pharmacy appeal, claim repricing, peer-to-peer, or finance queue processing against the shared Northstar environment.
---

# Northstar Payer Ops

Use this skill to turn a Northstar task context into a schema-matched JSON packet.

1. Read `task_context.json` and `answer_template.json` first.
2. Extract the target IDs, dates, requested work type, environment base URL, token, and memo constraints.
3. Query the shared Northstar environment only. Prefer SQL for joins and filtering; use business endpoints when they expose the needed record directly. Do not inspect local databases, manifests, generated data, or setup scripts unless the prompt explicitly allows it.
4. Gather only the records needed to decide the packet. Pull current case, claim, appeal, authorization, policy, document, P2P, assistance, rate schedule, or queue rows as required by the template.
5. Apply the family-specific playbook in [playbooks.md](references/playbooks.md) before resolving conflicts or gaps.
6. Build JSON that matches the template exactly. Preserve required key order when the template implies one, respect enum spellings and list ordering, use ISO dates, round currency to cents, use `null` for absent modifiers, and return JSON only.
7. Populate `basis_audit` with the precedence label, ordered record trail, controlling record IDs, and exception record IDs.
8. Add no extra keys unless the template explicitly allows them.
