---
name: ma-deal-workbench-json
description: Produce template-conformant JSON deliverables (issue registers, deviation matrices, closing packages, committee escalation memos, transition reviews) from an M&A "deal workbench" HTTP service. Use whenever a prompt casts you as buyer-side or seller-side counsel on a deal ID like PRJ_*, points at a workbench base URL with /api/deals routes, and requires output conforming to an answer_template.json with no prose outside the JSON.
---

# M&A Deal Workbench → Structured JSON

You are counsel on one deal. A read-only workbench holds the facts; a JSON template
defines the deliverable. Your job is to reconcile the **current draft terms** against the
**standard that binds this deal** (playbook or policy), quantify the gaps against the
**correct dollar base**, and emit JSON that conforms to the template exactly.

Grading is mechanical. Prose quality earns nothing; a wrong enum case, a stale term, or an
aggregate that disagrees with your own rows costs everything.

## Five non-negotiables

1. **The template is the contract.** Key names, enum spellings, nesting, and units come
   from the template — never from your judgment about what would be cleaner.
2. **`deal_id` is the only join key.** Project names are deliberately duplicated across
   unrelated deals. Never match on `project_name`, `target_name`, or client name.
3. **Filter `staleness_flag == "current"`** on draft terms before any comparison. Stale
   rows are planted distractors and often carry near-miss categories.
4. **Every number traces to a record**, and every dollar figure names its base. No
   estimates, no round numbers you invented, no averaging across deals.
5. **Aggregates are recomputed from the rows you actually emitted** — not tallied by hand
   and not copied from a source record.

## Workflow

### 0. Read every input, then plan against the template
Read `prompt.txt` **and every file** under `input/payloads/` — the template is the spec
sheet, and it may carry `instructions`, `units`, `allowed_enums`, `ordering`, and stable
ID lists that the prompt never repeats. Enumerate the exact output keys before fetching
anything; that list tells you which records you need.

### 1. Harvest the deal
```bash
export TASK_ENV_BASE_URL=http://task-env:9020   # or the value the prompt/env file gives
scripts/fetch_deal.sh PRJ_XXXX > /tmp/PRJ_XXXX.json
```
This bundles the deal record, all sub-resources, and the playbook/policy the deal record
actually points to. It pre-filters `current_terms`, and surfaces both distractor traps up
front: `_stale_term_ids` and `_decoys` (other deals whose project name resembles this one).
Read the bundle in full before reasoning — templates ask for fields that only appear in
records the prompt never mentions; notes, documents, and diligence findings frequently
carry the fact that decides an issue.

`_rollups` are **unscoped raw totals** over every row — a starting point, not an answer.
Most templates scope their aggregates (continuing employees only, closing consents only),
so re-derive each total over the rows you actually emitted.

### 2. Resolve the binding standard — from the deal record
The deal row carries `playbook_id` **and** `policy_id`; typically one is populated and
the other is `null`. Use the populated one. Other playbooks and policies exist purely as
decoys (one is even labelled a legacy policy in its own notes). If the prompt names an ID,
confirm it matches the deal record; on conflict the deal record binds and the discrepancy
is worth a line in your reasoning, not a silent override.

**Playbook numbers hide in prose.** `limit_value` is the *fallback* bound. The *preferred*
figure lives in the `preferred_position` sentence, and `fallback_position` may state a
**conditional** fallback ("fallback N months if escrow is M% or higher"). Parse both
sentences; templates routinely ask for preferred, fallback, and the condition separately.

### 3. Build one row per issue the template asks for
Join draft terms to standard rules by **category, semantically** — not by string equality.
The vocabularies overlap but do not match (`reverse_break_fee` vs `reverse_termination_fee`
vs `termination_fee`; `customer_consent_condition` vs `consent_closing_condition`).

A standard has only a handful of rules, while templates ask for many issues. The remainder
are **missing-term issues**: the draft is silent and the surrounding deal data shows the
term is needed. For those set `issue_status` to the missing-term enum, `source_term_ids`
to `[]`, and the action to `add`. Assert "missing" only after checking terms, documents,
and notes — and only when a record shows the protection is warranted.

Classification and risk decision tables: `references/classification_rules.md`.

### 4. Quantify against the named base
Resolve the base from the rule's own `basis` field, never by habit:
"purchase price" / "equity value" / "enterprise value" → the deal's `headline_value`;
"upfront cash" → `upfront_cash`; findings-based escrow → the finding amounts.
`headline_value` is authoritative and is **not** the sum of the cash/stock/milestone
fields — read it, never reconstruct it.

Where no base exists, emit `null` (or the template's `not_quantified` /
`amount_not_in_workbench` enum) rather than a guess.

### 5. Aggregate, order, and cross-check
Recompute counts as lengths of your emitted arrays and sums from your emitted values.
Employee rows are **groups with a `count` field** — head-count sums `count`, not rows.
Priority order runs closing-certainty blockers first, then magnitude of quantified
exposure, and must contain exactly the issue IDs you emitted.

### 6. Validate before answering
```bash
python3 scripts/validate_answer.py answer.json path/to/answer_template.json --percent-dp 2
```
Catches the failures that actually happen: enum-union placeholders left verbatim
(`"LOW | MEDIUM | HIGH"`), source casing copied through (`"High"` where the template
demands `"HIGH"`), non-integer currency, template skeleton rows never replaced, counts
disagreeing with array lengths. Fix everything it reports, then re-run.

Output **only** the JSON object — no fences, no preamble, no trailing commentary.

## Field map

| Need | Record | Fields that matter |
|---|---|---|
| Headline economics | `deals` | `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `client_side`, `playbook_id`, `policy_id`, `signing_date`, `meeting_date` |
| Draft position | `draft_terms` | `staleness_flag`, `category`, `numeric_value`, `unit`, `clause_ref`, `draft_value`, `basis` |
| Standard | `playbook_rules` / `policy_thresholds` | `limit_value` (fallback), `preferred_position`/`fallback_position` prose, `basis`, `risk_default`, `restricted_flag`, `approval_required` |
| Closing blockers | `consents`, `material_contracts` | `required_for_closing`, `amount_at_risk`, `consent_required`, `annual_revenue` |
| People | `employees` | `count` (group size), `pto_liability`, `service_credit_required`, `warn_risk` |
| Exposure / market | `risk_estimates`, `benchmarks` | `exposure_low`/`exposure_high`, `median_value`, `upper_quartile`, `sample_size` |
| Regulatory | `regulatory` (single object) | `hsr_required`, `hell_or_high_water_required`, `regulatory_approval`, `threshold_basis` |

Full endpoint list, SQL recipes, and source vocabularies: `references/workbench_api.md`.
Template-conformance rules (placeholders, enums, units, null policy):
`references/output_contract.md`.

## Traps that have actually bitten

- **Name collisions.** Several unrelated deals share a project name with the target deal
  and differ in client side and binding standard. Filter by `deal_id`.
- **Stale terms.** Present in the same response as current ones, no filtering by default.
- **Decoy standards.** Playbooks and policies not bound to the deal, including a legacy one.
- **Preferred vs fallback.** `limit_value` alone will give you the fallback twice.
- **Casing.** Sources say `High`/`Medium`/`Low`; templates usually demand upper case.
  Sources say `yes`/`no`; templates often want booleans. `hell_or_high_water_required` has
  a third source value, `limited covenant`, which is neither `yes` nor `no` — map it to the
  template's own vocabulary and treat the gap as an issue when the client's position
  requires a full covenant.
- **Employee counts.** Three rows can mean a hundred-plus people.
- **Percent conventions.** Percent-point fields are `12.50`, not `0.125`; cap-table
  `fully_diluted_pct` is already a fraction that sums to 1.0 across holders. Decimal places
  differ per template and sometimes per field within one template.
- **Union strings.** `"a | b"` in a template is a menu, not a value. Pick one member.
