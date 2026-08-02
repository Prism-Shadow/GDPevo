---
name: ma-deal-workbench-json
description: Produce structured JSON deal-review deliverables (issue registers, deviation matrices, closing packages, committee escalation memos, transition reviews) from the M&A deal workbench API. Use whenever a task names a deal_id like PRJ_*, points at a deal workbench base URL, and requires returning only JSON conforming to a supplied answer_template.json.
---

# M&A Deal Workbench → structured JSON

A family of tasks share one shape: you are counsel for one side of one deal, you
read that deal's records from a workbench API, you compare the current draft
against a playbook or policy, and you emit **one JSON object conforming to a
supplied `answer_template.json`** with no prose around it.

The deliverable name changes (issue register, deviation matrix, closing package,
committee escalation memo, transition review). The method below does not.

## The single most important rule

**The answer template is the specification. The prompt is context.**

Read `input/payloads/answer_template.json` completely before touching the
network. It dictates field names, nesting, enum vocabularies, id vocabularies,
units, and rounding. When the prompt and the template disagree about a field,
the template wins. When the template fixes a list of stable IDs, that list — not
the number of records you find — determines how many objects you emit.

Run this first to extract the machine-checkable contract:

```bash
python3 skill/scripts/extract_contract.py <path-to-answer_template.json>
```

It prints every enum vocabulary, every stable-ID list, every declared unit, and
the required field tree. Keep that output in front of you while you build.

## Workflow

### 1. Establish access

Read `environment_access.md` for the base URL, the allowed endpoint list, and
the `POST /api/query` token. Use **only** what that file authorizes. Confirm the
service is up before planning around it:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/api/deals"
```

If `POST /api/query` is authorized, prefer it — one SQL round trip beats a dozen
REST calls, and it is the only practical way to do cross-table checks.

### 2. Pull the whole deal bundle at once

```bash
python3 skill/scripts/wb.py bundle PRJ_XXXX          # every table for one deal
python3 skill/scripts/wb.py sql "SELECT ..."         # read-only SQL
python3 skill/scripts/wb.py get /api/deals/PRJ_XXXX  # raw endpoint
```

Pull everything up front — terms, playbook/policy, consents, employees,
material contracts, regulatory, cap table, diligence findings, benchmarks, risk
estimates, notes, documents. Fields you think are irrelevant routinely turn out
to be the evidence that a required term is missing.

See `reference/workbench_api.md` for the endpoint map, JSON wrapper keys, and
the full table schema.

### 3. Scope to exactly one deal

The corpus holds many decoy deals, and **project names are deliberately reused
across unrelated deal_ids** (near-twin names differing by one word or suffix are
the norm, and several distinct deals share an identical `project_name`).

- Filter every table on `deal_id = '<the id in the prompt>'`. Never match on
  `project_name`, target name, or counterparty.
- `GET /api/search` searches **across all deals**. Treat its output as leads
  only; re-fetch anything you intend to use, scoped by `deal_id`.
- Take `client_side`, `playbook_id`, and `policy_id` from the target deal's own
  `deals` row. Do not infer the playbook from the prompt's framing — a deal can
  carry a counterparty-flavored playbook id, and decoy deals carry the *other*
  policy version with different thresholds.
- A deal has a playbook or a policy, rarely both. Compare against whichever the
  `deals` row names; if it names neither, the comparison basis must come from
  the prompt or template.

### 4. Keep only current draft terms

`draft_terms.staleness_flag` is `current` or `stale`.

- **Filter to `current` for every substantive comparison.** Stale rows are
  planted distractors.
- A category whose only row is `stale` means **the current draft is silent on
  that category** — it is a *missing term*, not a draft position. Never read a
  numeric off a stale row.
- Expect at most one current row per `(deal_id, category)`. Two current rows in
  one category means you mis-scoped the query.

### 5. Compare against the playbook or policy

Read `reference/field_semantics.md` before doing this — the numeric columns do
not mean what their names suggest. In particular:

- `playbook_rules.limit_value` is the **fallback** threshold, not the preferred
  one. The preferred position exists only as prose in `preferred_position` and
  must be parsed out of that sentence.
- Fallbacks are frequently **conditional** ("fallback N months *if* escrow is at
  least X%", "cap may reach N% *only for* verified …"). The condition is part of
  the position; check it against the deal's own data and let it drive the
  `final_position` / `recommended_action` enum you pick.
- **Polarity flips with `client_side`.** Sellers want caps, escrows, and
  survival *low*; buyers want them *high*. The same draft number is
  `draft_below_playbook` for one side and `draft_exceeds_playbook` for the
  other. Derive direction from `client_side`, never from intuition about which
  number is "worse".
- For policy-driven committee tasks, escalate only categories where
  `policy_thresholds.restricted_flag = 'yes'` (equivalently, the row's
  `approval_required` names the committee). Categories routed to a lower
  approver are distractors even when the draft sits near their threshold.

### 6. Treat absent terms as issues

Most templates enumerate more issues than the deal has draft terms. The gap is
intentional: where the template names an issue the current draft does not
address, and the surrounding records show the protection is needed, emit it as a
missing term.

- `source_term_ids` (or equivalent) → `[]`
- `issue_status` → `missing_required_term`
- `recommended_action` → `add`

Conversely, several draft terms may collapse into **one** template issue — the
source-id field is an array precisely so a scope term and its fee term can share
an issue. Emit one object per template ID, not one per record.

### 7. Compute amounts

- Default base is the deal's `headline_value`. Override it whenever a source row
  states a different `basis` — `enterprise value`, `equity value`,
  `upfront_cash`, `fully diluted shares`, `material contracts`. The `basis`
  column is authoritative over the prompt's default.
- `amount = round(base * percent_points / 100)`, emitted as an **integer**.
- Deltas point to the position you are demanding: `delta_to_fallback =
  draft_amount - fallback_amount` (keep the sign convention consistent across
  the document and consistent with the field's name).
- Composite terms hide their second number in prose. `numeric_value` carries one
  quantity only; a row reading "escrow equals X% for N months" exposes X in
  `numeric_value` and leaves N to be parsed from `draft_value`.
- Rounding is per-task — 2dp, 1dp, whole points, and 4-decimal holder fractions
  all appear. Take it from the prompt and template, never from habit.
- `cap_table.fully_diluted_pct` is a **fraction summing to 1.0**, not percent
  points. Multiply consideration by it directly; convert only if the template
  asks for percent points. Use `as_converted_shares`, not `shares`, wherever the
  template says as-converted.
- Sanity check: `upfront_cash + stock_value + milestone_value` should reconcile
  to `headline_value`. If it does not, re-check that you are on the right deal.

### 8. Map supporting tables to fields

| Need | Source | Rule |
|---|---|---|
| Closing consents, amount at risk | `consents` | Count/sum only `required_for_closing = 'yes'` |
| Material-contract blockers | `material_contracts` | `consent_required` is **three-valued**: `yes` / `no` / `notice only`. `notice only` is a notice, not a closing condition |
| Employee counts, PTO | `employees` | Sum `count` and `pto_liability` across groups; groups are rows, not individuals |
| WARN / selection risk | `employees` | `warn_risk`, plus `draft_treatment` prose for buyer selection ("may select"/"cherry-pick") rights |
| HSR, hell-or-high-water | `regulatory` | One row per deal; copy its verbatim values into the matching enums |
| Benchmark position | `benchmarks` | Classify the draft against `median_value` / `upper_quartile` using the template's position enum |
| Quantified exposure | `risk_estimates` | Three categories per deal: closing certainty, indemnity leakage, transition disruption |
| Special indemnity sizing | `diligence_findings` | `amount` by `topic` / `severity` |

Aggregate exposure totals include **only** the components your escalated issues
actually rely on. When a template has `included_` / `excluded_exposure_components`
fields, it expects you to drop the categories no live issue maps to — and to say
so explicitly rather than silently summing all three.

### 9. Emit and validate

Output **one JSON object, nothing else** — no markdown fence, no commentary.

```bash
python3 skill/scripts/validate_answer.py answer.json <path-to-answer_template.json>
```

It flags unknown enum values, IDs outside a fixed vocabulary, non-integer
currency, template placeholders left unreplaced, and structural drift. Fix
everything it reports, then re-read the checklist below.

## Pre-submission checklist

- [ ] Every record used came from a query filtered on the target `deal_id`.
- [ ] Only `staleness_flag = 'current'` rows drove numbers; stale-only
      categories were treated as missing, not as positions.
- [ ] Playbook/policy came from the target deal's own `deals` row.
- [ ] Comparison direction matches `client_side`.
- [ ] Preferred values were parsed from prose; `limit_value` was used as the
      fallback only.
- [ ] Every template stable ID appears exactly once; no invented IDs.
- [ ] Every enum value is copied verbatim from the template's vocabulary.
- [ ] Currency fields are integers; percents and months match the required
      precision; dates are `YYYY-MM-DD`.
- [ ] Counts in the summary block agree with the arrays they describe.
- [ ] Nulls are used where the template allows them, rather than `0` standing in
      for "not applicable".
- [ ] Output parses as JSON and contains no prose.

## Files

- `reference/workbench_api.md` — endpoints, wrapper keys, table schema
- `reference/field_semantics.md` — column meanings and the traps in each
- `scripts/wb.py` — fetch a deal bundle, run read-only SQL, hit raw endpoints
- `scripts/extract_contract.py` — pull enums, stable IDs, and units from a template
- `scripts/validate_answer.py` — check an answer against the template contract
