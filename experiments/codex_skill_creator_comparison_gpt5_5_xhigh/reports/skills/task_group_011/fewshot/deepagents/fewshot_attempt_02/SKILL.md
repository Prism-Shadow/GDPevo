---
name: credit-office-committee-json
description: Solve public credit-office committee JSON tasks that use TASK_ENV_BASE_URL, answer templates, branch records, loans, applications, sector exposures, policies, FDIC benchmarks, or NCUA benchmarks. Use when asked to produce branch rating migrations, lending allocations, CRE comparisons, watch-list stress packets, or credit-union segment posture pages as JSON only.
---

# Credit Office Committee JSON

## Workflow

1. Read the prompt, the matching `answer_template.json`, and any endpoint names it mentions.
2. Fetch data only from the runner-provided `TASK_ENV_BASE_URL` public API.
3. Identify the packet type, then follow the matching section in [references/calculations.md](references/calculations.md).
4. Preserve template key order, enum spelling, list ordering, and numeric precision.
5. Return one JSON object only.

## Packet Types

### Branch Rating Migration

- Regrade the loans at or above the prompt threshold.
- Recompute final ratings from objective factors only, then summarize downgrades, NPA variance, and watch-list coverage.

### Lending Allocation

- Score each pending application with the published weighted CDFI rubric.
- Approve only what fits capacity and concentration rules.
- Build the post-approval concentration view from branch sector exposures and latest total loans.

### Credit-Union Segment Posture

- Use the segment record, NCUA benchmark row, and peer comparisons.
- Choose the posture, controls, escalation triggers, and interpretation directly from the data.

### Watch-List Stress

- Treat the prompt’s adverse-rating floor as the watch-list population.
- Compute the +200bp DSCR stress, queue workout actions, and summarize severe buckets.

### Competing CRE Decision

- Compare the two CRE requests with weighted score, stressed coverage, branch CRE concentration, and FDIC variance.
- Select one path and assign controlled reason codes to the unselected request.

## Output Rules

- Match the schema exactly.
- Use only allowed enums and identifiers.
- Sort grouped IDs alphabetically unless the template says otherwise.
- Round only at the end.

## Reference

- Read [references/calculations.md](references/calculations.md) before calculating.
- Use [scripts/credit_office_toolkit.py](scripts/credit_office_toolkit.py) for shared fetch and math helpers.
