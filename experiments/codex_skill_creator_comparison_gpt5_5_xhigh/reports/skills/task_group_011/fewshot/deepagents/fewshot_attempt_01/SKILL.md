---
name: credit-office-committee-packets
description: Produce committee-ready JSON from the public credit office API for branch regrade reviews, lending allocation packages, credit-union segment posture pages, watch-list stress packets, and competing CRE decisions. Use when the prompt provides a branch_id or segment_id, a TASK_ENV_BASE_URL, benchmark or policy data, and a strict answer template.
---

# Credit Office Committee Packets

Use this skill when the task asks for a strict JSON committee packet built from the public credit office API rather than a narrative summary.

## Workflow

1. Read the prompt and the answer template first.
2. Fetch `/api/manifest` and `/api/policies`.
3. Pull only the public endpoints needed for the packet.
4. Derive every field from the prompt, policy rules, benchmarks, and live branch or segment data.
5. Emit JSON only, with the template's exact keys, ordering, rounding, and enums.

See [API reference](references/api_reference.md) for endpoint details, policy thresholds, and packet patterns.

## Packet Playbooks

### Branch regrade review

- Review the target branch loans at or above the stated current-rating threshold.
- Re-derive final ratings from the available delinquency, DSCR, LTV, and collateral signals using the policy thresholds and dominant-factor rule.
- Aggregate final-rating exposure totals, migration from current rating 3, material downgrades, watch-list action coverage, and the top problem credit.
- Use the FDIC benchmark requested by the prompt and compute variance against the branch ratio with the template's precision.

### Lending allocation package

- Use lending capacity, branch metrics, and sector exposure to size approvals and conditional approvals.
- Keep the priority ranking to approved and conditionally approved applications only.
- Sort decisions, concentration flags, and post-approval concentrations exactly as required.
- Map decline reasons only to the controlled codes in the template.

### Segment posture page

- Compare the target state to the U.S. and the named peer states using the NCUA benchmark table.
- Fill controls, escalation triggers, and the committee interpretation from the allowed enums only.
- Keep the posture consistent with the direction of the state metrics.

### Watch-list stress packet

- Treat adverse-rated loans as the population defined by the prompt.
- Assign CDFI-style risk classes from the policy factor scores.
- Compute the watch-list or CRE stress using the policy formula and flag DSCR breaches at the stated threshold.
- Queue workout actions by severity and exposure, then summarize severe-bucket counts.

### Competing CRE decision

- Compare the two applications using weighted CRE score, stressed DSCR, concentration, and FDIC variance.
- Select the stronger path for the better credit and give the unselected disposition and reason codes.
- Include the concentration view, policy variance, and required conditions from the template.

## Output Rules

- Keep JSON only; do not add narrative, fences, or notes.
- Use only IDs, enums, and reason codes that appear in the prompt, template, policy endpoint, or fetched public data.
- Preserve the template's sort order and numeric precision.
- Do not reuse task-specific final values across runs.
