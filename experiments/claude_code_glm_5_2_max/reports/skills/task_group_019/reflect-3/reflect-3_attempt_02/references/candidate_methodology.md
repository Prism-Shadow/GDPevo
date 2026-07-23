# Candidate assembly and verification methodology

How to turn environment data into a conformed answer, and how to refine it when a score
channel is available. This describes process, not any specific answer values.

## Build pipeline

1. **Cache the raw endpoints.** Fetch the listed GET endpoints once and store the JSON
   locally (one file per endpoint). `policies` first — its values gate every decision.
2. **Index by join key.** Build local indexes: applications by `application_id`, license
   history by `license_id`, bonds/insurance/violations/correspondence/inspections by their
   `*_application_id`; for liquor, settlements/incidents/evidence by `location_id`;
   for renewal, licensees by `license_no` and violations by `license_no` and `address`.
3. **Filter to targets.** Keep only records for the prompt's target ids, excluding
   distractors (`distractors.md`).
4. **Decide per the family rules** (`contractor_rules.md` / `liquor_rules.md` /
   `renewal_rules.md`). Record the *reason* each code is set so you can revise quickly.
5. **Emit JSON strictly to the template** — only the shown keys, allowed enum values,
   required orderings, empty arrays for nothing-applies.

## Self-checks (do these every time, for every family)

- **Schema conformance**: every value is in the template's allowed list; every list is in
  the required order; required lengths/counts are exact (e.g. queue length, batch size,
  ranks 1..N with no gaps).
- **No extra keys / no prose / no markdown.**
- **Summary ↔ items consistency**: counts in the summary equal tallies over the
  per-item decisions; id-lists in the summary are subsets of the target ids.
- **Block discipline** (contractor): a block (open serious violation or active suspension)
  ⇒ `DENY` and (usually) `high` risk; never mark a blocked app `HOLD`.
- **Gaps ↔ posture** (liquor): non-empty `verification_gap_codes` ⇒ posture
  `request_follow_up` (or `deny`), not `issue_restricted`.
- **Matching discipline** (renewal): only exact-license + successor matches; post-boundary
  `*-LATE` rows excluded from counts but listed in the exclusion summary.

## Refining with a score channel (train tasks only)

When you can submit a candidate and read back a `score` in [0,1] and a `correct` boolean
(and only that — no per-field detail), iterate deliberately:

- **One variable per round.** Change exactly one field or one set-membership decision
  between submissions so a score change is attributable. Changing several fields at once
  makes regressions uninterpretable.
- **Hypothesize by confidence.** Spend rounds on the fields most likely wrong and most
  decisive: determinations/postures, booleans (`same_premises_basis_applies`,
  `policy_impacted`), match-confidence tiers, and the summary id-lists. Fine-grained code
  lists are usually lower-leverage and easier to get right from the rules.
- **Regressions are information.** If a change lowers the score, the prior value was more
  likely correct for that field. Do not keep regressing — revert that field and try a
  different dimension.
- **Revert to the best candidate when stuck.** Your best-scoring submission is a valid
  final answer. If the last round regressed, resubmit the best-scoring content as the final
  round rather than shipping a worse "improvement."
- **Recognize a plateau.** If two genuinely different content variants return the same
  score, the mismatches live in fields you are not editing. Stop churning the same
  dimension; either pick a different field class or accept the defensible candidate.
- **Score is roughly exact-match-weighted.** Small structural flips (DENY↔HOLD,
  high↔medium tier, adding/removing a code, flipping a boolean) can move the score more
  than adding correct-but-uncertain detail. More codes is not always better; precision
  matters more than recall for these set-valued fields.

## What never to do at test time

- Do not call any judge / scoring / feedback endpoint. Those exist only for train tasks.
- Do not hard-code any id, code, count, or date from a train task into a template that
  might be reused — re-derive everything from the environment for the task at hand.
- Do not pad lists with distractor records to "be thorough"; distractors are scored as
  errors.
