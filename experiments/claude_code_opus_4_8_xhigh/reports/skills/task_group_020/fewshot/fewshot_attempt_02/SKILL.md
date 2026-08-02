---
name: ma-deal-workbench-analysis
description: Produce structured JSON transaction-counsel deliverables from the M&A deal workbench environment — issue registers, closing/economics packages, committee escalation memos, transition reviews, and deviation matrices. Use when a prompt names a deal ID (PRJ_*), points at a deal workbench base URL, and requires JSON conforming to an answer_template.json.
---

# M&A Deal Workbench Analysis

Read deal records from a running M&A workbench API, compare the current draft
against the client's playbook or the internal policy, and return **only** JSON
conforming to the task's `answer_template.json`.

These tasks are graded on exact field-by-field agreement. Most lost points come
from mechanics, not legal judgment: analyzing a stale term, computing off the
wrong value base, leaving a template placeholder in place, emitting a float
where integer dollars are required, or dropping fields the template declares.

## Supporting files

| File | Use |
|---|---|
| `reference/workbench-api.md` | Endpoints, SQL tables, every record field |
| `reference/answer-conventions.md` | Value bases, comparison rules, computations, normalization |
| `scripts/fetch_deal.py` | Pull the whole evidence bundle for one deal |
| `scripts/validate_answer.py` | Shape-check the answer against the template |

Read `reference/answer-conventions.md` before writing any values — it holds the
rules that decide most graded fields.

## Workflow

### 1. Read the prompt and the template together

From the prompt, note: the `deal_id`, which side you act for, the named
playbook or policy ID, the coverage list ("your package must cover…"), and the
stated units and precision.

Then read `input/payloads/answer_template.json` in full. Templates come in two
dialects and the difference decides your top-level keys:

- **Skeleton** — the template mirrors the output. Keep its structure and keys;
  replace `null`, `0`, and `"A | B | C"` placeholders with real values. Arrays
  hold one exemplar object; expand to as many as the data supports.
- **Descriptor** — the template *describes* the output through wrapper keys
  (`required_output_shape`, `required_top_level_fields`, `issue_object_fields`,
  `allowed_enums`, `instructions`, `possible_issue_ids`). Your answer's
  top-level keys are the **described** field names. Never emit the wrapper keys
  themselves (`schema_name`, `allowed_enums`, `instructions`, …).

Either way: emit **every** declared field on every object, using `null` / `[]`
where a field does not apply. Do not add fields the template does not declare.
Stable ID lists in the template are a closed vocabulary — use those exact
strings.

### 2. Pull the evidence

Set the base URL from the prompt or `environment_access.md`:

```bash
export TASK_ENV_BASE_URL="http://<host>:<port>"
python3 scripts/fetch_deal.py PRJ_EXAMPLE --summary
python3 scripts/fetch_deal.py PRJ_EXAMPLE --out /tmp/bundle.json >/dev/null
```

The summary separates current from stale terms, prints the playbook and policy
side by side, and pre-totals the consent, contract-revenue, employee, PTO, and
exposure figures that templates ask for. Verify those totals rather than
trusting them blind.

For cross-table checks and column sums, the read-only SQL endpoint is faster
and less error-prone than re-reading JSON:

```bash
curl -s -X POST "$TASK_ENV_BASE_URL/api/query" -H 'Content-Type: application/json' \
  -d '{"token":"deal-workbench-readonly","sql":"SELECT ... WHERE deal_id = ..."}'
```

Read every record type the prompt names, plus `notes` and `documents` — they
supply source IDs for issues where the draft is silent. Read each term's
`draft_value` prose, not just its `numeric_value`; the prose carries second
amounts, exclusions, and carve-out lists that the numeric field omits.

### 3. Filter to what counts

- Keep draft terms with `staleness_flag == "current"`. **Stale rows are
  decoys** — near-threshold numbers in plausible categories. If the template
  asks for excluded terms, list stale/out-of-scope IDs there and only there.
- Filter every table on the prompt's `deal_id`. The workbench holds many deals,
  some with near-identical project names. Never borrow a neighbor's value.
- Use the playbook or policy the prompt names; otherwise the deal header's.

### 4. Build the issue set

For each category in the prompt's coverage list:

1. Find the current draft term (if any).
2. Find the matching playbook rule or policy threshold.
3. Classify the status with the template's enums — compliant, deviating in the
   direction adverse to your client, or absent when required.
4. Compute the amounts: percent × the correct value base, deltas to preferred
   and fallback, months gaps.
5. Assign a risk rating and a recommended action from the template's enums.
6. Record the source IDs — the term IDs, and the consent / contract / employee /
   finding / risk / document IDs that support the position. Missing terms carry
   an empty `source_term_ids` and cite the record proving the need.

Include an issue for a term the draft omits when the client's position requires
it and the data shows it is needed. Do not manufacture issues the data does not
support, and do not escalate a policy category that has no current draft term.

### 5. Aggregate

Compute summary metrics from the arrays you actually emitted, then re-derive
them independently and compare. Watch the distinctions in
`reference/answer-conventions.md` §8 — distinct-value counters versus row
counters, and umbrella counters that span several status enums.

### 6. Validate before returning

```bash
python3 scripts/validate_answer.py /tmp/answer.json input/payloads/answer_template.json
```

Fix every ERROR. Warnings are advisory: "keys omitted here but present on
sibling rows" is expected for category-dependent objects, and a problem
otherwise. The check covers shape only — it cannot tell you the analysis is
right, so re-verify the arithmetic and the source IDs yourself.

Then confirm by hand:

- Currency values are integers; percents use the prompt's precision and are in
  percent points; months and counts are integers; dates are `YYYY-MM-DD`.
- No placeholder text (`"A | B | C"`, `"stable consent ID"`, `"string"`) remains.
- Every ID cited exists in the records for **this** deal.
- Priority/order arrays contain each ID exactly once.
- Descriptor-template answers carry the described keys, not the wrapper keys.

### 7. Return

Output **only** the JSON object. No prose, no markdown fences, no commentary
before or after — several prompts state this explicitly and it is graded.

## Judgment calls

The data is built so a careful reading resolves most questions. When something
is genuinely underdetermined, prefer the reading that the records support with
a citable ID, state the assumption in no more than a short note *inside* an
allowed free-text field if the template has one, and never outside the JSON. If
an amount simply is not in the workbench and the template offers a status enum
for that, use the enum instead of inventing a number.
