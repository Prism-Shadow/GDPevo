---
name: northstar-payer-ops
description: Build strict JSON disposition packets for Northstar payer-operations tasks. Use when a task provides staged Northstar inputs and asks for a UM, appeal, peer-to-peer, claim repricing, or finance-queue determination from the shared environment.
---

# Northstar Payer Ops

## Workflow

1. Read the task prompt, `task_context.json`, `answer_template.json`, and `environment_access.md`.
2. Use only the shared Northstar HTTP endpoints and `POST /sql/query`. Do not inspect environment files, SQLite files, manifests, or setup scripts directly.
3. Query the minimum records needed for the task family, keeping source IDs, effective dates, quantities, and statuses.
4. Map the result exactly to the template. Preserve key order, required fields, list ordering, enum values, and numeric/date precision.
5. Build `basis_audit` from the controlling records and the rejected or gap records. Use the template's `source_precedence` value and order records highest priority first.
6. Return one JSON object only. No markdown, comments, code fences, or narrative prose.

## Task Families

- UM / prior auth summaries: review case, member, plan, clinical documents, requested therapy lines, and authorization status.
- Pharmacy appeal packets: review appeal, denial, fill history, packet requirements, and manufacturer-assistance eligibility.
- Claim repricing packets: review claim lines, active benchmark schedule, stale source rejection, and line-level correction amounts.
- Peer-to-peer summaries: review the P2P event, current clinical evidence, unresolved criteria, and appeal deadline rules.
- Finance queue summaries: review queue rows, cost, margin, threshold ratios, and charge-sensitive segments.

## Output Rules

- Follow the template exactly, including any allowed nulls or empty lists.
- Use the template's ordering rules for lists and records. Do not reorder unless instructed.
- Use only template-supported fallback values such as `unclear`, `partial`, `not_applicable`, or `null` when evidence is missing.
- Keep `basis_audit` concrete:
  - `source_precedence`: choose the exact rule named by the template.
  - `controlling_record_ids`: list the records that directly determine the answer.
  - `exception_record_ids`: list stale, excluded, missing, or rejected records.
  - `precedence_record_order`: list all controlling and exception records in highest-priority-first order.
- If the template restricts extra keys, omit anything not listed.
