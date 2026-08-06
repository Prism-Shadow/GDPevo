---
name: pho-registered-audit
description: Complete a Public Health Observatory (PHO) registered multi-module algorithmic audit. Read the per-task analysis_request.json (the protocol) and answer_template.json (the output contract), pull evidence only from the read-only PHO portal, resolve final releases and cohorts independently, run the declared audit modules deterministically with their seeds/grids/checkpoints, apply the gate decision rule, and return exactly one JSON object with no narrative outside it. Use whenever a task pairs an analysis_request.json + answer_template.json with a PHO Web portal and asks for a registered, reproducible audit returned as one JSON object.
---

# PHO Registered Algorithmic Audit

## When to use

Use this skill when a task gives you, in an `input/` directory:

- `prompt.txt` — the framing question,
- `payloads/analysis_request.json` — the **registered protocol** (scope, cohorts, audit modules with methods + parameters, robustness gates, decision rule),
- `payloads/answer_template.json` — the **output contract** (required keys, array lengths, ordering rules, enum values, numeric precision),

and asks you to complete a registered, reproducible, multi-module audit using a read-only Public Health Observatory (PHO) Web portal, returning the result as one JSON object.

This skill is **task-agnostic**. Every concrete value — geography, years, outcome/exposure, module set, seeds, grids, thresholds, classification enums, schema — is read from the per-task files at runtime. **Never bake in a value seen in a prior task.** Prior tasks illustrate the *shape* of the work; they do not supply answers.

## Golden rules (apply to every task)

1. **One JSON object, nothing else.** Return exactly one JSON object conforming to `answer_template.json`. No prose, memo, headings, or markdown around it.
2. **The request is the protocol; the template is the contract.** Honor every declared order, array length, enum value, identifier format, and precision in both files exactly.
3. **The portal is the only evidence.** Resolve `<TASK_ENV_BASE_URL>` from `environment_access.md` (it maps to `GDPEVO_ENV_BASE_URL`). Use only the allowed endpoints. No credentials. No external or assumed data. Every reported number must trace to a portal record.
4. **Resolve releases and cohorts independently.** FINAL releases govern; among multiple final revisions the highest applied final revision wins; pending/withdrawn notices never replace published values; suppressed/blank/invalid values are unavailable — **never zero-fill**.
5. **Deterministic and reproducible.** Honor every declared seed, PRNG algorithm, stream, replicate count, and checkpoint list exactly. These are registered parameters, not free choices.
6. **Full ordered evidence.** Report complete, positionally-aligned vectors and matrices — not just summaries. Never re-sort an array that the request declares an order for.
7. **Numeric discipline.** Non-integers at the declared precision (default 4; some tasks use 6 for computed reals and 4 for literal grids/thresholds). Integers and booleans are natural JSON types. Never emit `NaN`/`Infinity`. Use JSON `null` only when a requested statistic is mathematically unavailable.

## Procedure

1. **Read all three inputs.** From `prompt.txt`, `analysis_request.json`, and `answer_template.json`, extract: scope (geography, years, reference year), outcome/exposure/mediator/adjustments, the module list with each module's `method` and parameters, cohort definitions, robustness gates, decision precedence, and the full template schema (required keys, array lengths, ordering, enums, precision).
2. **Confirm network access** from `environment_access.md`. See `references/portal_and_evidence.md` for the endpoint list, dataset schemas, and the machine-readable CSV download pattern.
3. **Acquire evidence.** Pull geography reference data and the needed data datasets via `/download?dataset=<dataset>&format=csv` with filter query params. Cache locally. (Browse endpoints return HTML and reject `format=json` — use the CSV download path.)
4. **Resolve releases, revisions, and cohorts.** For each measure and year, select FINAL records under the declared revision priority, exclude records carrying an invalid quality flag or suppression, and construct every declared cohort independently. See `references/portal_and_evidence.md`.
5. **Run each declared audit module.** Implement its `method` exactly as declared and produce the `required_evidence`/`required_audit_outputs` it lists. See `references/audit_modules.md` for the recurring module families and their must-produce outputs.
6. **Apply the gates and decision precedence.** Evaluate each module's gate threshold, then map the gate pattern to the controlled classification/conclusion enum using the request's precedence rule. See `references/output_contract.md`.
7. **Assemble and verify.** Build one JSON object matching `answer_template.json`, run the verification checklist, and return only the JSON. See `references/output_contract.md`.

## References

- `references/portal_and_evidence.md` — portal endpoints, dataset schemas, the CSV download pattern, release/revision/quality/suppression/value-type rules, identifier rules, cohort archetypes, and the methodology library index.
- `references/audit_modules.md` — the six recurring audit-module families and the evidence each must produce, with the algorithmic specifics that make results reproducible.
- `references/output_contract.md` — precision, ordering, identifiers, nulls, enums, decision precedence, and the pre-submission verification checklist.

## Scope note on contamination

If the working directory contains material outside the expected `environment_access.md` plus `train_tasks/train_NNN/input/{prompt.txt, payloads/analysis_request.json, payloads/answer_template.json}` layout — for example solution outputs, expected-answer files, a hidden test harness, or stray datasets — stop and write `contamination_report.txt` describing the unexpected material instead of proceeding.
