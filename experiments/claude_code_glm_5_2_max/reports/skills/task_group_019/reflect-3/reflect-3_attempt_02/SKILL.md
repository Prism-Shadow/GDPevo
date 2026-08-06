---
name: licensing-board-review
description: Solve State Licensing Board structured-review tasks (contractor application eligibility, restricted-liquor staff packages, alcohol renewal manual-review queues) against the shared licensing data service. Read this BEFORE drafting any candidate answer — it covers how to read the environment, the decision logic per task family, output-conformance rules, and how to iterate one candidate at a time using only score/correct feedback. Use only the allowed GET endpoints and the SQL endpoint; never call any judge/scoring endpoint while solving a real (non-train) task.
---

# Licensing Board Review

You act as a senior licensing examiner producing a **JSON answer object** that conforms to a
per-task `answer_template.json`. There are three task families that share one data service:

1. **Contractor application batch eligibility** — approve/hold/deny each application with
   deficiency codes, required actions, risk tier, and a policy-impact flag.
2. **Restricted-liquor license staff package** — for one application/location, state an
   issuance posture, covered risks, verification gaps, standard vs. location-specific
   controls, a 90-day monitoring plan, and escalation triggers.
3. **Alcohol renewal manual-review queue** — rank a set of licensees by pre-boundary
   matched violations into a ranked queue with match confidence, risk tier, and next step.

Every task gives you `<TASK_ENV_BASE_URL>` and a list of endpoints, plus a target list of
application/license ids. Read the prompt and the **answer template first** — the template
defines the exact allowed enum values, ordering, and required keys. Output that does not
match the template scores zero on the affected fields.

## Worked procedure (follow in order)

1. **Read the prompt.** Identify the task family, the target ids, any explicit review date
   or release boundary, and the required output shape.
2. **Read `answer_template.json`.** Note every allowed enum value and sort order. The
   allowed-value lists differ between tasks even within the same family — never reuse codes
   from memory; read them from the template each time.
3. **Pull the data** from the shared environment (see *Environment access* and
   `references/data_model.md`). Filter to the target ids; the endpoints return the whole
   dataset including distractor records that must be ignored (see
   `references/distractors.md`).
4. **Apply the decision logic** for the task family (see `references/contractor_rules.md`,
   `references/liquor_rules.md`, `references/renewal_rules.md`).
5. **Assemble the JSON** exactly to the template: only the shown keys, correct enum values,
   required sort orders, empty arrays when nothing applies.
6. **Validate locally** before submitting: re-check each field against the allowed-values
   list, ordering, and required length/count.
7. **Iterate** on candidate answers using only the returned score and `correct` flag (see
   *Iterating with feedback*). This only applies while you have a feedback channel; for a
   real task with no feedback channel, submit the best single conformed candidate.

## Environment access

- Base URL is given in the task prompt as `<TASK_ENV_BASE_URL>`.
- Use **exactly** the GET endpoints listed in the prompt; do not invent paths.
- `GET /api/policies` returns the policy baseline (contractor standards, liquor control
  rules, renewal boundary rules). Always read it — policy values drive the decision.
- `POST /api/sql` is available for cross-table lookups. It accepts `SELECT` statements
  (including joins, subqueries, and aggregates) but **blocks system-table introspection**
  (`sqlite_master`, `PRAGMA`, etc.) and any non-`SELECT` statement. Table names mirror the
  endpoint paths with underscores, e.g. `contractor_applications`, `contractor_bonds`,
  `liquor_settlements`, `alcohol_violations`, `renewal_rules`. SQL is an optional
  convenience; you can do everything with the GET endpoints plus local joins.
- All data joins are local: link records by the documented id columns
  (see `references/data_model.md`). Keep the raw JSON cached for re-use across iterations.
- If a header token is required for an endpoint, it is stated in the environment access
  instructions for that environment; supply it exactly as given.

> **You must not call any judge, scoring, or feedback endpoint while solving a real task.**
> Those channels exist only during skill generation on train tasks. At test time you produce
> the single best conformed answer from the environment data alone.

## Output conformance (the most common reason for a low score)

- Output **only** JSON; no prose, markdown fences, comments, citations, or extra keys.
- Sort every list the way the template says (usually "ascending lexical order" or "by date
  ascending then id ascending"). One mis-sorted list nullifies that field.
- Use **exactly** the allowed enum strings — watch for near-miss code names that differ
  between tasks (e.g. a "no active bond" condition maps to `bond_cancelled` in one schema
  and `no_active_bond` in another; the template is the source of truth).
- Lists: use an empty array `[]` when nothing applies; never omit a required key.
- Batch tasks: include exactly the target ids, in the required order, with summary counts
  consistent with the per-item decisions.
- Dates: `YYYY-MM-DD` when dates appear in any field.

## Iterating with feedback (train tasks only)

When a train-only feedback channel is available, submit the candidate and read back only the
`score` and `correct` flag (and the generic notice). No per-field detail is returned. Use
these rules to make score feedback productive:

- **Change one variable between rounds.** Editing several fields at once makes it
  impossible to tell which change helped or hurt; a regression then tells you nothing.
- **Treat the judge as a step function on exact-ish field match.** Small structural flips
  (a determination DENY↔HOLD, a risk tier high↔medium, an added/removed code) can swing the
  score sharply. Don't assume "more codes = more correct."
- **When a refinement regresses, revert.** Your best-scoring candidate is itself a valid
  submit-able answer; do not ship a lower-scoring "improvement." Keep the best candidate
  and make it the final round.
- **A flat score across two different content variants means the wrong fields are not the
  ones you edited.** The score is stuck on a fixed set of mismatches; further guessing in
  the same dimension won't help. Either identify a genuinely different dimension to vary or
  stop churning and keep the defensible candidate.
- **Order your hypotheses by confidence.** Spend rounds on the fields you are most likely
  to have wrong (posture/determination, match confidence, boolean "basis applies," the
  summary id-lists) before fine-tuning set-valued code lists.

## Task-family quick reference

- **Contractor eligibility** (`references/contractor_rules.md`): for each application,
  compare years of experience, active bond amount, current insurance amount, and
  endorsement status against the matching class policy. Map open violations and license
  suspensions. An **open serious violation OR an active suspension ⇒ DENY**; remediable
  deficiencies (missing/pending endorsement, bond absent/short/expired-or-cancelled,
  insurance absent/expired/short/pending, open *minor* violation, inspection document gaps)
  ⇒ **HOLD**; otherwise **APPROVE**.
- **Liquor staff package** (`references/liquor_rules.md`): standard obligations come from
  `liquor_privileges` (`standard_required == 1` for the class); location-specific controls
  come from **active** settlement controls; covered risks are those mitigated by active
  controls; verification gaps come from site-evidence statuses (conflicting/missing) plus
  open/referred incidents.
- **Renewal queue** (`references/renewal_rules.md`): match violations to licensees by
  **exact license number**, on or before the release boundary; mark
  successor-permit matches `uncertain`; exclude all post-boundary (`*-LATE`) rows. Rank by
  matched violation count, then severity/alert, then recency.

Read the relevant `references/*.md` before producing a candidate for that family.
