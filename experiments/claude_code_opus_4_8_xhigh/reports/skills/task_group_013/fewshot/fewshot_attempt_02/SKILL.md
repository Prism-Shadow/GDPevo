---
name: cedar-ridge-intake
description: >
  Solve Cedar Ridge Intake Coordination Portal tasks — read-only healthcare intake/referral/
  transfer/enrollment audits that must return a single JSON object matching a supplied
  answer_template.json. Use when a task points at the Cedar Ridge Intake Coordination Portal
  (an intake portal base URL / <TASK_ENV_BASE_URL>) and asks for a structured JSON audit of a
  roster, referral batch, transfer batch, or program-candidate panel using controlled enum
  values. Covers new-patient access verification, referral readiness / referral-to-chart
  activation, dialysis transfer review, and chronic-care enrollment panels.
---

# Cedar Ridge Intake Coordination Portal tasks

These tasks all follow one shape: a prompt names an entity to audit (a roster, a referral batch,
a transfer batch, or a program-candidate panel) at the **Cedar Ridge Intake Coordination Portal**,
and ships an `input/payloads/answer_template.json` that defines the **exact JSON output shape and
the controlled vocabulary** (enums, reason codes, ordering). Your job is to read the live portal,
apply the deterministic intake rules, and return **one JSON object** that conforms to the template
— JSON only, no prose, unless the prompt says otherwise.

The scoring is exact-match against controlled values, so precision on enums, list ordering, count
keys, and echoed constants matters more than anything.

## Workflow

1. **Read the task fully.** Read `input/prompt.txt` and, byte for byte, the
   `input/payloads/answer_template.json` (and any other payload, e.g. `target_roster.json`). The
   template is the source of truth for: required top-level keys, per-item keys, every allowed
   enum / reason-code / action-code value, ordering rules, and which constants (task_id, batch_id,
   roster_id, program_code, service_line) to echo verbatim. **Never invent a value outside the
   template's allowed set.**

2. **Reach the environment.** Get the base URL from `environment_access.md`
   (`GDPEVO_ENV_BASE_URL`); prompts use the placeholder `<TASK_ENV_BASE_URL>`. Confirm liveness,
   then pull data with the read-only SQL endpoint (`POST /query`, body `{"sql":"SELECT ..."}`) —
   it is far faster than the REST endpoints for whole batches. See
   [references/portal_api.md](references/portal_api.md) for endpoints, the full table schema, and
   stable reference constants (ICD chapter map, dialysis facilities, artifact types).

3. **Identify the archetype** from the template's keys and open the matching rule file:

   | Signal in the template / prompt | Archetype | Rules |
   |---|---|---|
   | `roster_id`, per-patient insurance/prescription/pharmacy/lifestyle/overall risk + registration | **A. Access verification** | [references/access_verification.md](references/access_verification.md) |
   | referral `batch_id`, readiness_status, ICD/coding discrepancies, duplicates, blockers, priority | **B. Referral readiness / chart activation** | [references/referral_readiness.md](references/referral_readiness.md) |
   | transfer `batch_id`, packet completeness/staleness, chair capacity, intake decision | **C. Dialysis transfer review** | [references/transfer_review.md](references/transfer_review.md) |
   | `program_code`, per-candidate eligibility/enrollment/monitoring package | **D. Enrollment panel** | [references/enrollment_panel.md](references/enrollment_panel.md) |

   If a task doesn't match any archetype, treat the rule files as the pattern: pull the batch and
   joined rows, and reverse-engineer the mapping from the template's controlled values and the
   portal data (see "Deriving rules for a new variant" below).

4. **Apply the rules** in the archetype file to every row. Compute each per-item field, then the
   cohort/summary block from those items. Sort every list exactly as the template specifies.

5. **Validate before returning.** Re-check against the template: all required keys present; every
   enum/code value is in the allowed set; every list ordered as required; count objects include
   **all** keys, zero-filled, and the counts equal the number of matching items; echoed constants
   (task_id, batch_id/roster_id/program_code, service_line, requested dates) are exactly right;
   the row count equals the number of entities in the batch/roster/candidate list. Output valid
   JSON with no surrounding text.

## Output conventions (apply everywhere)

- **Echo, don't guess, constants.** task_id (often required to equal the task folder name),
  roster/batch/program ids, and service_line come from the template's `required_value`/`constant`
  or from the roster/referral/program row — copy them exactly, uppercase as stored.
- **Unordered sets vs ordered lists.** When the template calls a list an "unordered set"
  (reason/issue/blocker/action codes), emit it sorted (alphabetical) for stability. When it
  specifies an ordering (ascending by id, alphabetical by code, priority order), follow that
  literally.
- **Count objects are exhaustive and zero-filled.** Every enum key the template lists must appear
  with an integer, including zeros. Cross-check that per-category counts sum to the total.
- **Empty is `[]`, not omitted.** A section with no members (e.g. `ready_to_schedule`,
  `duplicate_groups`) is an empty list, still present.
- **Booleans/nulls as typed.** `first_checkin_days` and similar are integer-or-null; `priority_tier`
  is null for ready referrals; keep JSON types exact.

## Deriving rules for a new variant

The environment holds many more rosters/batches/programs than any one task, and the engine is
deterministic. If you hit a service line, program, modality, or output field the rule files don't
cover: pull that batch plus its joined rows, list the template's controlled values, and infer the
condition→value mapping from the data (e.g. `SELECT DISTINCT chapter FROM icd_codes WHERE
service_family=...` for a new referral line). Keep every rule monotonic and reproducible, and
prefer the documented cross-archetype invariants (severity precedence, accepted-chapter checks,
capacity sums, chart presence tests) which are stable across batches.

> The rule files describe the portal's business logic (the reusable engine), calibrated against
> training batches. Where a branch was never exercised by training data, the file says so — treat
> those as principled defaults and double-check them against the current task's data.
