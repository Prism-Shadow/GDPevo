---
name: ma-deal-workbench-review
description: Produce structured JSON deliverables (issue registers, deviation matrices, committee escalation memos, closing/transition packages) from an M&A "deal workbench" web app plus an answer_template.json. Use whenever a task gives a deal ID, points at a workbench that serves deal, playbook, and policy records, and demands JSON conforming to a supplied template with fixed enums, stable record IDs, and integer-dollar / percent-point units.
---

# M&A Deal Workbench → structured JSON review

You are counsel for one side of a deal. A workbench app holds the deal record and its
supporting tables; a playbook or policy holds your side's negotiating limits. Your job is to
compare the current draft against those limits, quantify the gaps, and emit **one JSON object
that conforms exactly to the supplied answer template — no prose outside the JSON**.

## The template is the specification

Read `input/payloads/answer_template.json` **before** touching the workbench. It fixes:

- the **top-level shape** — reproduce these keys exactly, at the same nesting depth;
- the **closed enums** — never invent a value for a field that lists allowed values;
- the **issue/redline ID vocabulary** — when the template enumerates stable IDs
  (`possible_issue_ids`, `stable_issue_ids`, an `issue_id` "one of:" list), that list *is* the
  row set to reason about. Do not add rows outside it;
- the **units** — integer dollars, percent points to the stated decimals, integer months;
- **which fields are nullable** — use `null` for genuinely inapplicable fields rather than 0.

Templates come in two styles: an *instance* (a filled-in example with placeholder values) and a
*schema description* (`required_output_shape` / `required_top_level_fields` blocks). For the
schema-description style, your answer is the **described object**, not the wrapper: emit the keys
listed inside `required_output_shape`, not the key `required_output_shape` itself.

Extra keys that the template does not mention are ignored by scoring; missing *required* values
are not. Prefer completeness over minimalism, but never pad a field with a wrong value where
`null` is truthful.

## Gather the data

1. Fetch the deal record for the **exact deal ID in the prompt**. Its `links` object enumerates
   every per-deal endpoint — use it as the checklist so no record type is missed.
2. Pull every linked record type, not just the ones the prompt names: terms, playbook or policy
   rules, benchmarks, risk estimates, cap table, consents, employees, material contracts,
   regulatory, diligence findings, notes, documents.
3. Fetch the rules for the deal's `playbook_id` **or** the thresholds for its `policy_id`
   (a deal has one or the other; that choice tells you whether the deliverable is a
   playbook-deviation review or a committee-policy escalation).
4. If the prompt offers a read-only SQL endpoint with a token, use it for cross-table checks and
   to confirm the API is not hiding rows (`SELECT ... FROM draft_terms WHERE deal_id = ...`).

`scripts/pull_deal.py` does steps 1–3 in one call and prints a normalized digest.

### Decoys are deliberate

- The workbench holds dozens of deals with **confusingly similar project names** (a "Project X"
  and a "Project X North", an "Orion" and an "Oriel"). Filter every table on the exact
  `deal_id`. Never let a record from a similar-sounding project into the answer.
- Draft terms carry a `staleness_flag`. **Only `current` rows are live.** A stale row is a
  distractor — exclude it, and when the template has an "excluded"/"in policy" list, name it there.
- Records exist that are simply in policy or below the escalation bar. When a task says
  "identify only the out-of-policy terms", in-policy rows belong in the exclusion list, not the
  main register.

## Build the analysis

For each row in the template's ID vocabulary:

- **Locate the source.** Put the real `term_id`s in `source_term_ids`, and the real
  `CNS_`/`MAT_`/`EMP_`/`FND_`/`RSK_` IDs in the record/source fields. Use `[]` (not `null`) when
  the issue is that the term is *absent*.
- **Compare to your side's limit.** Playbook rules give `preferred_position`, `fallback_position`
  and a numeric `limit_value`; policy thresholds give `threshold_value` and `restricted_flag`.
- **Classify** with `reference/analysis-conventions.md` — status, risk, action, and the
  direction of "better" for your client's side.
- **Quantify.** Percent → dollars against the correct base; compute the delta or shortfall to the
  fallback *and* to the preferred position when the template has slots for both.
- **Treat silence as an issue** when the prompt says to: a required protective term that appears
  in no current draft term is `missing_required_term` with an empty source list and an `add`
  action — but only where the surrounding records show the term is actually needed.

## Money rules

- **Base:** derive dollar amounts from the deal's `headline_value` unless a source explicitly
  states another basis (a term's `basis` field, or a rule's `basis`). "Enterprise value" and
  "equity value" resolve to the headline value unless a separate figure exists.
- **Verify by back-solving.** When a draft term's text quotes both a percent and a dollar figure,
  confirm `amount ÷ percent` reproduces your base. If it doesn't, you have the wrong base.
- Integer dollars only — round once, at the end, never mid-chain.
- Standard aggregates (each is a filter, not a total of everything):
  - closing-consent amount at risk = Σ `amount_at_risk` where `required_for_closing == "yes"`;
  - material-contract revenue conditioned = Σ `annual_revenue` where `consent_required == "yes"`;
  - PTO liability = Σ `pto_liability`, restricted to the employee group the field names;
  - modeled exposure = Σ risk-estimate `exposure_low`/`exposure_high`, **including only the
    categories your escalated issues actually implicate**; name the omitted category in the
    template's "excluded components" field.
- Counts in a summary block must be recomputed *from the rows you emitted*, never hand-tallied.

## Before returning

Run this check — arithmetic and ID fidelity are where these tasks are won:

1. Output parses as JSON and contains nothing but the JSON object.
2. Every enum value is copied character-for-character from the template.
3. Every ID referenced exists in the workbench (or, where the template explicitly permits a
   synthetic ID, is clearly marked as one).
4. Every summary count and total matches the rows above it.
5. Every percent and month is in the unit the template demands; every dollar is an integer.
6. No stale term, and no record from another deal, appears anywhere.
7. Rows are ordered as instructed (by ID ascending, or by stated priority).

`reference/analysis-conventions.md` holds the classification and priority conventions;
`reference/data-model.md` documents the record types and their fields.
