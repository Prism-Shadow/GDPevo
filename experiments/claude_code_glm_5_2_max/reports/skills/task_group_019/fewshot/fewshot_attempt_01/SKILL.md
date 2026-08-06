---
name: licensing-board-structured-review
description: Structured licensing-board review tasks over a networked data environment. Fetch records from REST endpoints (contractor, liquor, and alcohol licensing plus policies/rules), apply the board's policy baseline, and return exactly one JSON object conforming to the task's answer_template.json. Covers contractor batch eligibility reviews, restricted liquor-license staff packages, and alcohol renewal manual-review queues. Read this BEFORE fetching any endpoint or drafting output.
---

# Licensing-Board Structured Review

You are acting as a licensing-board examiner/analyst. Every task gives you:

- a **prompt** naming the target entities (a batch of applications, a single application + location, or a set of licenses), a review or release-boundary date, and which endpoints to use;
- an **answer template** at `input/payloads/answer_template.json` — the authoritative schema for THIS task;
- an **environment access file** (`environment_access.md`) giving the base URL and the auth token for SQL.

Your job: fetch the relevant records from the licensing environment, apply the board's policy/rules, and return exactly one JSON object matching the template.

## Universal method

Run these steps for every task, regardless of type.

1. **Read the prompt.** Extract: the task framing, the target entity IDs and count, any target location, the review or release-boundary date, and any focus hints (e.g., "hotel lounge controls, camera evidence, late-night monitoring"). The endpoints the prompt lists identify the task type.
2. **Read `input/payloads/answer_template.json` and treat it as authoritative.** Extract: required top-level keys, every field's type, the EXACT `allowed_values` enum for each field, required list lengths, ordering rules (ascending lexical, by date, by rank, "any order", etc.), and the "no extra keys / no prose" instruction. The enum vocabularies DIFFER between tasks that look identical — never reuse a prior task's code list from memory. Build your output skeleton directly from this template.
3. **Read `environment_access.md`** for the base URL and the `X-Task-Token` value. See `environment.md`.
4. **Fetch the rule baseline first.** GET `/api/policies` for every task; additionally GET `/api/renewal/rules` for renewal-queue tasks. These define currency thresholds, policy-impact comparisons, and the violation→next-step/risk mappings you must apply. Do not invent thresholds.
5. **Fetch the business endpoints** for the task type (see `playbooks.md`). When a REST endpoint would force many round-trips (joining violations to licenses, aggregating correspondence, counting per application), use `POST /api/sql` with read-only `SELECT` queries instead. See `environment.md` for SQL usage.
6. **Derive per-entity decisions from evidence + rules.** For each target, gather all evidence, then map each finding to the CLOSEST allowed code in the template's enum list. Emit only codes that appear in the template's `allowed_values`. Where the template implies a 1:1 pairing (e.g., deficiency ↔ required action), produce the matching paired value for each.
7. **Compute summary/aggregate fields** from the per-entity decisions — counts, sorted id lists, excluded ids, etc. The summary MUST be consistent with the entity-level decisions.
8. **Emit exactly one JSON object** matching the template. Respect every ordering rule. Use empty arrays where nothing applies. No prose, no markdown, no comments, no keys not in the template.
9. **Run the pre-submit checklist** below.

## Task types

Identify the type from the prompt's endpoints and framing, then follow the matching playbook in `playbooks.md`:

- **Type A — Contractor batch eligibility review.** A batch of contractor application IDs; contractor endpoints + policies + SQL. Output: per-application determination/deficiency/action/risk/policy-impact + a summary. Prompt mentions "Contractors Licensing Board", "application batch", "eligibility".
- **Type B — Restricted liquor-license staff package.** One application + one location; liquor endpoints + policies + SQL. Output: posture, same-premises flag, covered risks, verification gaps, standard vs location-specific controls, 90-day plan, escalation triggers. Prompt mentions "restricted liquor license", "staff package", a location ID.
- **Type C — Alcohol renewal manual-review queue.** A set of license IDs and a release-boundary date; alcohol + renewal/rules + SQL. Output: a ranked queue of N entries + a summary. Prompt mentions "renewal", "manual-review queue", "release boundary".

## Output discipline

- **Conform exactly.** Only keys listed in the template. Only enum values from the template's `allowed_values`. Required list lengths must match (e.g., exactly N queue entries, exactly the target application count).
- **Ordering is scored.** Apply each field's ordering rule: ascending lexical for id/code lists; by date then id for matched violation ids; ranks 1..N with no gaps for queues; operational sequence for 90-day plans where specified. Where the template says "any order", still deduplicate ("use each code at most once").
- **Empty arrays, not null.** When no code/action/id applies, use `[]`.
- **No extra material.** No prose, no narrative memo, no citations, no markdown, no comments — even if the prompt invites explanation. Return only the JSON object.
- **Currency uses the task's date.** Judge "current/expired" against the review or boundary date stated in the prompt (or the policy's current date), not today's date.
- **policy_impacted** means a deficiency/flag exists solely because the CURRENT policy baseline applies and the PRIOR baseline would not have created it — compare current vs prior in `/api/policies`.

## Pre-submit checklist

- [ ] Output is a single JSON object; no prose/markdown/comments outside it.
- [ ] Every required top-level key is present; no extra keys.
- [ ] Every enum value is from the template's `allowed_values` (you read THIS task's template, not a remembered one).
- [ ] List lengths match the template (target entity count; queue size; ranks 1..N with no gaps).
- [ ] Every ordering rule applied; duplicates removed where required.
- [ ] Empty arrays used where nothing applies.
- [ ] Summary fields are consistent with the per-entity decisions (counts add up; id lists match the decisions).
- [ ] For queues: post-boundary records excluded and listed; close/uncertain matches flagged and listed; board-review licenses listed.
- [ ] Currency decisions use the task's review/boundary date.

## Supporting files

- `environment.md` — how to reach the environment, the token-header rule, the endpoint catalog, and SQL usage.
- `playbooks.md` — decision logic for each of the three task types.
