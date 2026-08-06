---
name: ma-workbench-json-deliverables
description: Produce structured JSON legal work product (issue registers, deviation matrices, committee escalation memos, closing/transition packages) from a read-only M&A deal workbench containing deal records, draft terms, playbook rules, policy thresholds, benchmarks, risk estimates, cap tables, consents, employees, material contracts, regulatory records, diligence findings, notes, and documents. Use whenever a prompt names a deal ID, points at a deal workbench, and requires an answer conforming to a supplied answer template.
---

# M&A workbench → structured JSON deliverables

These tasks look like legal drafting but are graded like data extraction. The grader
compares your JSON field-by-field against a reference answer and awards partial credit
per field. Prose quality earns nothing; a wrong number, a missing row, or an invented
record ID loses a point each. Optimize for **every scalar traceable to a record**.

## Non-negotiables

1. **Return only the JSON object.** No prose, no markdown fences, no commentary.
2. **The answer template is the contract.** Reproduce its exact key names, nesting, and
   spelling. Never rename, never add top-level keys, never drop a field.
3. **Never invent a record ID.** Every ID you emit must appear verbatim in the workbench
   (or be an explicitly synthetic ID that the template itself authorizes).
4. **One deal only.** The workbench holds dozens of deals whose records follow identical
   naming patterns and near-identical field values. Filter every query and every reasoning
   step by the single deal ID in the prompt.

## Procedure

### 1. Read the answer template before touching the data

The template tells you what to look for and, often, exactly how many rows to emit.

- Closed ID lists — `possible_*_ids`, `stable_issue_ids`, `stable_redline_ids`, or an
  `issue_id` field spelled `"one of: a, b, c"` — are the row set. Emit one row per ID
  unless the prompt says to include only qualifying items.
- A closed list of outcome strings (e.g. a `final_position` enum) with the same
  cardinality as the ID list is a **1:1 mapping**. Pair them up in listed order.
- Note the declared units (integer dollars, percent points at N decimals, integer months,
  fraction vs percent for holder percentages, `YYYY-MM-DD` dates) and honor them exactly.
- Note ordering instructions (`sort by issue_id ascending`, `highest priority first`) and
  apply them per array.

### 2. Pull the whole record set for the deal, once

The prompt lists the entry points and any read-only query credentials available to you.
Prefer whichever facility returns whole tables — one pass per record family for the deal
beats clicking through pages, and you need every family anyway because templates cross-
reference them. Start by listing the available record families and their columns, then
pull all of them for the one deal.

See `references/record-model.md` for what each record family carries and which fields
drive answers.

### 3. Build a fact table before writing any JSON

For each draft term record: category, numeric value, unit, basis, clause reference,
staleness flag. For each governing rule (playbook or policy): preferred position,
fallback position, limit value, unit, basis, required action, default risk, restricted
flag, approval owner. Line them up category by category. Everything downstream is a
comparison between these two columns.

**Distractors are deliberate.** Drop draft terms flagged stale. Use only the playbook or
policy ID named on the deal record — legacy variants with almost the same ID exist and
carry different thresholds. Ignore rule categories that the deal has no facts for.

### 4. Classify each item

Compare draft value against preferred, then fallback, in the direction that favors your
client's side (a seller resists high caps and long survival; a buyer wants the opposite).
Then pick the template's status enum. See `references/derivation-rules.md` for the
classification decision table, the missing-term test, and the consent/contract selection
rules.

### 5. Quantify from the right base

- A term's own `basis` field names its base. Absent that, use the deal's headline value.
- **Back-solve to confirm.** When draft text quotes a dollar figure alongside a percent,
  divide to recover the base and check it matches the value you were about to use. This
  catches a wrong base before it poisons a dozen fields.
- Compute deltas as `draft − applicable limit`, in the template's own field (dollars,
  percent points, or months). Where the template asks for both a shortfall to preferred
  and to fallback, compute both against the same draft figure.
- Emit `null` for a quantity the records genuinely do not support. Do not substitute `0`
  for "unknown" — the template distinguishes them, and status enums such as
  `not_found_in_current_records` exist precisely to carry that meaning.

### 6. Recompute every aggregate from the rows you emitted

Counts, risk tallies, and sums must be arithmetically consistent with your own arrays —
an internally inconsistent summary block fails several checks at once. Sum exposure only
over the risk-estimate categories the template names in its inclusion/exclusion lists;
when the template lists an excluded component, leave it out of the totals but still name
it in the exclusion field.

### 7. Self-check before returning

Run `scripts/check_answer.py <answer_template.json> <candidate.json>`. It flags leftover
template placeholders, unknown or missing keys, enum violations, non-integer currency
values, and count fields that disagree with the arrays they summarize. Fix everything it
reports, then re-read the prompt's bullet list of required coverage and confirm each
bullet is represented.

## Where points are actually won

Ranked by observed yield:

1. Derived dollar amounts and deltas computed off the correct base.
2. Record ID sets — which consents block closing, which contracts need consent versus
   notice, which employee groups carry the liability.
3. Counts and sums that agree with your own rows.
4. Status and action enums driven by the draft-versus-rule comparison.
5. Free-text codes, condition labels, and narrative fields. These are the least
   predictable; keep them short, snake_case where the template hints at it, and phrased
   in the source records' own vocabulary rather than invented wording.
