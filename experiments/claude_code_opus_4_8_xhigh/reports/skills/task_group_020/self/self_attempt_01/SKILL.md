---
name: ma-deal-workbench-json
description: Produce schema-conformant JSON deliverables (issue registers, deviation matrices, closing-readiness packages, committee escalation memos, transition reviews) from the M&A deal workbench HTTP/SQL API. Use whenever a prompt names a deal ID like PRJ_XXXX, points at a deal workbench base URL, references a playbook (PB_*) or policy (POL_*), and requires output conforming to an answer_template.json with no prose.
---

# M&A Deal Workbench → Schema-Conformant JSON

Tasks in this family all share one shape: read a deal's records from a workbench API,
compare the **current draft terms** against the **governing standard** (a playbook or a
policy), classify and quantify each deviation, and emit **one JSON object** that conforms
exactly to a supplied `answer_template.json`.

Two things fail these tasks far more often than legal judgment does:
pulling data from the **wrong deal or a stale row**, and emitting JSON that **doesn't match
the template's shape, enums, or units**. Spend your effort there.

## Operating procedure

### 1. Extract the task contract before touching the network

From `prompt.txt` record: the exact `deal_id`; the client side (buyer/seller counsel);
the named playbook/policy IDs; the deliverable sections you must cover; and every explicit
unit/format directive (percent decimal places, integer dollars, integer months, date format).
Unit directives differ between tasks in this family — one task may want percent points to two
decimals while another wants one decimal, four decimals for holder percentages, or whole
percent points. Never carry a convention over from a previous task.

Then read `payloads/answer_template.json` **completely** and decide which genre it is:

- **Skeleton** — the template *is* the answer shape, with `null`s, `0`s, `"a | b | c"` enum
  strings and one example array element. Emit the same keys; replace every placeholder.
- **Descriptor** — the template *describes* the answer under meta-keys such as
  `required_output_shape`, `required_top_level_fields`, `issue_object_fields`,
  `summary_metrics_fields`, `allowed_enums`, `instructions`. Emit the **described** object.
  Never emit the meta-keys themselves.

Write down the full key list and every allowed enum value now; you will validate against it.

### 2. Resolve the deal by ID, never by name

Set the base URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL`) and substitute it for
`<TASK_ENV_BASE_URL>`. Fetch the deal record and confirm `deal_id`, `client_side`, and
`playbook_id`/`policy_id` agree with the prompt.

The workbench holds many decoy deals whose `project_name` and `target_name` are near-misses
of the target's (differing by a syllable), with different client sides and different
playbooks. **Every record you use must carry `deal_id == <target>`.** `/api/search` searches
across all deals and will return other deals' rows — filter its output.

`scripts/fetch_deal.py <DEAL_ID>` pulls the deal plus all sub-records and the bound
playbook/policy into a single bundle and flags stale rows. See `references/workbench-api.md`
for the endpoint map, the `POST /api/query` SQL contract, and the table schemas.

### 3. Take only the current draft terms

`draft_terms.staleness_flag` is `current` or `stale`. Use `current` rows only. Stale rows are
planted distractors and often sit in a category adjacent to a live one (a `termination_fee`
row beside a live `reverse_termination_fee` row), so filter on the flag, not on plausibility.

If the template asks for an exclusions list (`excluded_in_policy_terms`,
`excluded_from_draft`, `excluded_contract_ids`, `non_blocking_notices`), populate it with the
IDs you deliberately left out — that list is graded too.

### 4. Compare each term against the governing standard

Seller-side → seller playbook; buyer-side → buyer playbook; committee escalation → the deal's
policy thresholds. For each in-scope category build one row:

| draft | standard | direction | status | risk | action | quantification |

- The standard's numeric limit is in `limit_value`/`threshold_value`; the **preferred** number
  usually appears only inside the `preferred_position` / `fallback_position` / `policy_standard`
  prose. Parse both.
- **Fallbacks are conditional.** Prose like "may reach X% only for verified <condition>" or
  "X months if escrow is Y% or higher" unlocks only when another record in *this* deal
  evidences the condition. Check it, and carry the condition into the recommendation and any
  `required_conditions` field.
- **Direction depends on the client side.** A seller wants a lower cap, lower escrow, shorter
  survival, shorter TSA; a buyer wants the opposite, plus a full materiality scrape and more
  consent conditions. Pick `draft_exceeds_playbook` vs `draft_below_playbook` from which side
  of the limit the draft sits on *for your client*, and sign deltas so a shortfall is the
  amount needed to reach the target.
- **Silence is an issue.** When the playbook requires a protection and no current term covers
  it, emit the issue with `missing_required_term`, `source_term_ids: []`, draft-side fields
  `null`, and any `*_status` field set to its not-found enum. Derive the required position
  from the standard's preferred/fallback text.
- Committee-style tasks add a third filter beyond current-and-out-of-policy: the threshold's
  `approval_required` routing and `restricted_flag`. Rows routed elsewhere are non-committee
  distractors even when they breach their own threshold.

### 5. Quantify

Percent → dollars is `pct / 100 × base`. Take the base from the `basis` field on the term or
rule ("purchase price", "equity value", "enterprise value" → the deal's headline value;
"upfront cash" → the upfront cash field), defaulting to headline value unless a source
explicitly names another basis. Dollar amounts are integers — round half-up explicitly
(`scripts/units.py`), not with bare `round()`.

Exposure ranges come from the deal's `risk_estimates` rows (`exposure_low`/`exposure_high`) by
category; include exactly the components the template names and list the rest in the excluded
field. Consent exposure comes from `consents.amount_at_risk`, contract exposure from
`material_contracts.annual_revenue`, PTO from `employees.pto_liability`.

Template field names are selectors into source rows: a field naming an employee group or a
finding topic means "use the row whose `employee_group`/`topic` matches that phrase", not the
total.

### 6. Reconcile aggregates from your own output

Compute every summary metric from the rows you actually emitted — counts equal array lengths,
risk tallies equal the ratings you assigned, totals equal the sum of the component fields in
your own JSON. Never estimate a total independently of the rows.

### 7. Normalize, validate, emit

Apply `references/output-contract.md` in full, then run
`scripts/validate_answer.py <answer.json> <template.json>`. It catches unreplaced placeholders,
leaked meta-keys, enum violations, non-integer dollars, and count/array mismatches.

Emit **only** the JSON object — no prose, no markdown fences, no trailing commentary.

## Non-negotiables

1. One JSON object, conforming to the template, nothing outside it.
2. Every source row filtered to the target `deal_id`; every draft term `current`.
3. Every enum value copied exactly from the template's allowed list — never a `"a | b | c"`
   placeholder, never source casing (`High` → `HIGH` when the enum is uppercase).
4. Stable IDs from the workbench (`TERM_*`, `CNS_*`, `MAT_*`, `EMP_*`, `FND_*`, `RSK_*`,
   `BM_*`, `NOTE_*`, `DOC_*`) — never invented, unless the template supplies its own fixed ID
   vocabulary, in which case use that.
5. Integer dollars; percent decimals exactly as the prompt directs; integer months; dates
   `YYYY-MM-DD`.
6. Aggregates arithmetically consistent with the emitted rows.
7. Cover every section the prompt lists and every key the template defines — a missing key is
   a failure, so use an explicit `null` or the not-found enum instead of dropping it.

## Files

- `references/workbench-api.md` — endpoints, SQL contract, table schemas, field vocabularies.
- `references/output-contract.md` — template genres, enum/unit normalization, emission rules.
- `references/analysis-playbook.md` — status/risk/action decision rules and quantification recipes.
- `scripts/fetch_deal.py` — pull one deal's complete record bundle.
- `scripts/units.py` — half-up dollar/percent/month rounding helpers.
- `scripts/validate_answer.py` — conformance checks before you emit.
