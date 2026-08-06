---
name: ma-deal-workbench-json
description: Produce structured JSON deliverables (issue registers, deviation matrices, closing/economics packages, committee escalation memos, transition reviews) from the M&A deal workbench HTTP API by comparing a deal's current draft terms against its playbook rules or policy thresholds. Use when a task names a deal ID like PRJ_XXXX, points at a workbench base URL, and supplies an answer_template.json to conform to.
---

# M&A deal workbench → structured JSON

Every task in this family is the same job wearing different clothes: pull one
deal's records from a live workbench, diff the counterparty's **current** draft
terms against the client's **playbook rules** (negotiation tasks) or **policy
thresholds** (committee tasks), quantify the gaps in dollars, and emit a single
JSON object matching a supplied template exactly.

Grading compares your JSON field by field. Correct legal reasoning expressed in
the wrong shape scores nothing, and so does a right-shaped answer built on a
number you assumed instead of fetched.

## Steps

**1. Read the template first.** `input/payloads/answer_template.json` is the spec.
Before touching the API, list its required fields, enum vocabularies, stable ID
lists, and unit declarations. The template tells you which questions to answer;
the prompt tells you which lens to answer them through. Where the two disagree on
units or precision, the prompt wins.

**2. Pull the deal bundle.**

```bash
python3 scripts/fetch_deal.py PRJ_XXXX --out bundle.json
```

Base URL resolves from `--base-url`, then `$GDPEVO_ENV_BASE_URL`, then
`environment_access.md`. The script fetches every sub-resource plus the deal's
playbook or policy, and prints a digest: economics, current vs stale terms,
playbook preferred/fallback prose, policy limits with committee flags, consent and
contract roll-ups, employee totals, and risk-estimate sums. It writes the same
figures to `bundle.json` under `derived`, so you can re-read without refetching.

Read the digest before writing anything. Most template fields are answered
directly by it.

**3. Confirm scope.** Filter on the exact `deal_id`. The workbench holds decoy
deals with confusingly similar project names, and some advertise stale and
duplicate rows. Drop every `staleness_flag = stale` term unless the template
explicitly asks you to enumerate excluded ones. Check that each `*_id` you emit
contains your deal ID in its middle segment.

**4. Build the issue set.** For each category the prompt scopes:

- find the current draft term, or establish there is none;
- read the matching playbook rule or policy threshold — parse both the
  `preferred_position` and `fallback_position` prose, since `limit_value` matches
  only one of them and which one varies by rule;
- classify the deviation *from your client's side* — one and the same indemnity
  cap is `draft_exceeds_playbook` for a seller and generous for a buyer;
- convert percents to dollars off `headline_value` and compute the delta;
- attach the supporting records: consents, material contracts, employees,
  findings, benchmarks, risk estimates.

Treat an absent seller-protective or buyer-protective provision as a
`missing_required_term` with empty `source_term_ids` whenever the surrounding
records show the term is needed — a required HSR clearance with no clearance
condition, employee groups with no transfer process, a carveout with no Section
1060 allocation. Draft silence is a finding, not an absence of findings.

`reference/derivation_rules.md` has the arithmetic, the direction-of-deviation
table, the aggregation rules, the committee escalation filter, and the rating
calibration. Consult it for anything you would otherwise guess.
`reference/data_model.md` documents the endpoints, tables, and field semantics.

**5. Compute totals from your own issue set**, not by re-reading the API. Counts,
risk-rating tallies, summed exposures, and consent totals must agree with the rows
you actually emitted — a summary that contradicts the register is two errors.

**6. Validate before submitting.**

```bash
python3 scripts/validate_answer.py answer.json input/payloads/answer_template.json
```

Add `--percent-decimals N` for a prompt that names a different precision, and
`--percent-decimals some_key=N` for a field with its own convention (holder
fractions often differ from percent points). The script catches placeholder text,
enum violations, IDs outside a declared stable list, non-integer dollars, and
over-precise percents. It checks form only — it cannot tell you whether you picked
the right issues. Exit status 1 means errors.

## Output contract

Return **one** JSON object and nothing else. No prose, no explanation, no fenced
code block, no trailing commentary. Populate every field the template declares,
including nulls. Use the template's exact key names, exact enum spellings, and
exact stable IDs — never invent an issue ID when the template enumerates them.

## Pitfalls

- **Prose carries numbers `numeric_value` does not.** Special-indemnity amounts,
  escrow release periods, excluded contract categories, and match-right windows
  live in `draft_value` text. Read it for every term you cite.
- **`limit_value` is not always the fallback.** Parse both position strings.
- **Stale rows are traps**, and so are records from similarly named deals.
- **`notice only` is not a blocker.** Neither is a consent with
  `required_for_closing = no`. Both belong in the non-blocking or tradeable list.
- **Don't model your own exposure.** Use `risk_estimates` values verbatim,
  including the ones that are not round numbers.
- **`null` ≠ `0`.** A term that provides no fee is `0`; a field that does not
  apply is `null`.
- **Employee rows are groups**, not individuals; `count` is already a group total.
- **Percentages are fractions in the cap table** and percent points everywhere
  else.
