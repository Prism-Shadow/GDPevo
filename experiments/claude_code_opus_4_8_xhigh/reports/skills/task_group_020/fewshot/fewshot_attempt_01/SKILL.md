---
name: ma-deal-workbench-analysis
description: >
  Produce structured JSON transaction-analysis deliverables from the M&A deal
  workbench API — seller/buyer issue registers, SPA deviation matrices, closing
  and economics packages, carveout transition reviews, and M&A Committee
  escalation memos. Use whenever a task supplies a deal_id, a workbench base URL,
  and an answer_template.json to conform to.
---

# M&A Deal Workbench Analysis

Tasks give you a deal id, a running workbench, and `input/payloads/answer_template.json`.
You return **one JSON object conforming to that template and nothing else**.

The deliverable's name changes between tasks (issue register, deviation matrix,
closing package, transition review, committee memo) but the work is always the
same: pull the deal's records, compare the current draft against the governing
playbook or policy, quantify the gaps in dollars, and classify each one.

Scoring is field-by-field against a reference answer, so a right analysis in the
wrong units, casing, or shape loses the point. Precision matters more than prose.

## Procedure

### 1. Read the prompt for the contract it sets

Extract and write down: `deal_id`, which side you act for, the playbook or policy
id, the required units (currency, percent precision, month format, date format),
and the list of topics the answer must cover. Prompts state per-task overrides —
percent precision differs between tasks, and one task can set a different
precision for a single field. The prompt's own wording wins over any default.

### 2. Read the template before gathering data

`answer_template.json` is the specification: it fixes the key names, the array
sort order, the enum vocabularies, the stable issue/redline id lists, and the
null convention. Templates come in two styles:

- **mirror** — the JSON shape itself, with placeholder values
- **descriptive** — blocks like `required_output_shape`, `allowed_enums`,
  `issue_object_fields` that describe the shape in prose

Both are binding. Where a template enumerates `possible_issue_ids` or
`stable_issue_ids`, those ids are the complete candidate set: work through every
one and decide whether the deal data supports it.

### 3. Pull the deal bundle

```bash
python3 skill/scripts/fetch_deal.py <DEAL_ID> -o bundle.json --triage
```

This fetches every per-deal record plus the governing playbook rules and policy
thresholds into one JSON file, and prints a triage report to stderr: stale terms
flagged for exclusion, playbook preferred-vs-fallback prose, consent and contract
splits, employee totals, exact risk-estimate sums, and a percent-of-headline
ready reckoner.

The workbench holds ~85 deals, many of them **deliberate near-name clones** of the
real one. Key every lookup on the exact `deal_id`; never resolve a deal by project
or target name. For cross-table checks use `POST /api/query` with
`{"token": "deal-workbench-readonly", "sql": "..."}`.

### 4. Analyse

Work through `reference/analysis_rules.md`. The four rules that decide most of
the score:

1. **Drop stale terms.** Only `staleness_flag = "current"` rows are live. Stale
   rows exist to be excluded — and templates often want their ids listed as
   exclusions.
2. **Read the prose, not just the numbers.** A term's `numeric_value` carries its
   headline figure, but `draft_value` text routinely holds a second figure the
   template asks for separately. Playbook `limit_value` is the **fallback**; the
   preferred position exists only in `preferred_position` prose, and a fallback's
   conditional clause can set another issue's required position.
3. **Missing terms are findings.** When the client's position requires an
   affirmative provision and the draft is silent, emit the issue with
   `missing_required_term` and an empty `source_term_ids`.
4. **Quantify against the stated basis.** Dollar figures come from
   `headline_value` unless a source names another basis; deltas are positive
   integers measured in the client's favour.

Direction of every comparison follows `client_side`: a buyer wants a higher cap
and longer survival, a seller the opposite.

### 5. Validate before returning

```bash
python3 skill/scripts/validate_answer.py answer.json input/payloads/answer_template.json \
    --bundle bundle.json --percent-decimals 2
```

Checks enum conformance, integer-dollar formatting, percent precision, count
fields against the arrays they summarise, required top-level keys, and every
record id against the bundle so nothing is hallucinated. Pass per-field precision
overrides as `--percent-decimals '1,fully_diluted_pct=4'`. Exit code is non-zero
when something is wrong; fix and re-run until clean.

Then re-read the prompt's coverage list and confirm each requested topic appears.

## Output discipline

- Emit only the JSON object — no prose, no markdown fence.
- Currency as bare integers. Percent points at the stated precision. Months as integers.
- Enum strings and record ids copied exactly; normalise source `High`/`Medium`/`Low`
  to the template's `HIGH`/`MEDIUM`/`LOW`.
- Never round a sourced figure to make it look tidy — some stored values end in
  irregular digits on purpose.
- Follow the template's null convention: emit every field with explicit `null`
  when the template lists each field as "... or null"; include only applicable
  keys when the template's sample object is a union of variant-specific fields.

## Files

- `reference/workbench_data_model.md` — endpoints, response wrappers, table and
  field reference, and what each decision-carrying field means
- `reference/analysis_rules.md` — classification, arithmetic, aggregation,
  risk-rating, prioritisation and output rules
- `scripts/fetch_deal.py` — deal bundle fetcher + triage report
- `scripts/validate_answer.py` — template conformance and hallucination checker
