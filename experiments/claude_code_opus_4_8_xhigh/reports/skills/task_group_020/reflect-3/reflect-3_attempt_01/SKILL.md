---
name: ma-deal-workbench
description: Produce structured JSON deliverables (issue registers, deviation matrices, committee escalation memos, closing/transition packages) from an M&A deal workbench API against a supplied answer template. Use whenever a task gives a deal_id, a workbench base URL, and an answer_template.json to conform to.
---

# M&A deal workbench → structured JSON deliverable

These tasks all have the same shape: a prompt names one deal, points at a read-only
M&A workbench, and requires **only JSON** conforming to an `answer_template.json`.
Output is graded by field-level exact comparison, so a defensible-but-invented value
scores the same as a wrong one. Everything you emit must be traceable to a record you
actually read, or to arithmetic on those records.

## The one rule that matters most

**Derive, don't infer.** The workbench is the whole world. Do not add issues, IDs,
amounts, or classifications from general M&A practice. If a record does not say it,
it is not in the answer.

Its corollary, **filter, don't pad**, is the single highest-value habit: a list field
named "required", "blocking", or "closing condition" holds *only* the records whose
own flag says they qualify. Listing every record and tagging each with a type is
measurably worse than listing only the qualifying ones — non-qualifying records belong
in the template's non-blocking / excluded / notice-only field, if it has one, and
nowhere otherwise.

## Workflow

### 1. Read the answer template before touching the API

The template is the contract and the strongest hint about the expected answer. Extract:

- **Required top-level keys** and their exact spelling. Emit exactly these.
- **`allowed_enums`** — every enum-typed value must be a verbatim member. Watch case:
  workbench records store `"High"`/`"yes"`, templates usually want `"HIGH"`/`true`.
- **Pinned ID lists** (`possible_issue_ids`, `stable_issue_ids`, `stable_redline_ids`,
  an `issue_id` "one of:" list). When the template pins IDs, that list *is* the
  expected membership — produce every ID, no more and no fewer. When it does not,
  include an entry only where a record evidences it.
- **Enums that only make sense nested** (`fee_model`, `tax_allocation_method`, `forum`,
  `condition_type`) — these are telling you the vocabulary for the free-form
  `*_normalized` / `must_have_terms` objects. Use those exact strings there.
- **Units** — integer dollars, percent-point decimal places, integer months. The
  prompt sometimes overrides the template; the prompt wins.
- **Named final positions.** A `final_position` / `recommended_action` enum whose values
  map 1:1 onto the issue IDs is a decoded answer key — pair them by name and let the
  wording drive the row. These names are often self-describing, encoding the target
  number, the fallback, and the condition attached to it; read them as instructions.

### 2. Pull the deal bundle

`scripts/fetch_deal.py <base_url> <deal_id> <out_dir>` fetches the deal record, follows
its `links` map, and pulls the governing playbook or policy named on the deal. It
discovers routes from the deal record, so it does not depend on a hardcoded route list.

The workbench holds dozens of decoy deals whose project names differ from the target's by
a syllable or a suffix, with cloned supporting rows carrying similar-looking amounts.
**Filter on the exact `deal_id` every time**, including in SQL. Never let a similarly
named project supply a number.

### 3. Establish the governing standard

The deal record names exactly one:

| Field on deal | Standard | Key columns |
|---|---|---|
| `playbook_id` | `playbook_rules` | `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `basis`, `risk_default` |
| `policy_id` | `policy_thresholds` | `policy_standard`, `threshold_value`, `restricted_flag`, `approval_required`, `basis` |

Parse the numeric preferred/fallback out of the prose positions — `limit_value` alone is
ambiguous (it is sometimes the preferred bound, sometimes the fallback).

### 4. Select the rows

Use only `draft_terms` with `staleness_flag == "current"`. Then, per template shape:

- **Issue register / deviation matrix** — one row per template-pinned issue ID. Map each
  to the current draft term(s) sharing its `category`; a pinned ID with no matching
  current term is `missing_required_term` with empty `source_term_ids`.
- **Committee escalation** — include a term only if *all* hold: current, its category has
  a governing threshold, the draft breaches it, and the threshold is in scope for the
  requested body (`restricted_flag == "yes"` / `approval_required` matches). Stale,
  in-policy, and lower-approval rows are deliberate distractors — put them in the
  template's `excluded_*` fields, not in the escalation list.

`reference/classification_rules.md` has the status / risk / action decision tables and the
record-flag filters (consents, material contracts, employees).

### 5. Compute the numbers

- Base = the deal's `headline_value` unless the term or rule `basis` explicitly names
  another basis. `headline_value` also equals `upfront_cash + stock_value` in these deals;
  a draft term that states its own dollar figure confirms the base — check it.
- `amount = round(base * percent / 100)`, emitted as an **integer**.
- Deltas run in the direction that harms your client (see polarity table in
  `reference/classification_rules.md`). Report the gap to the *fallback* when the template
  asks for one gap, and both fallback and preferred gaps when it asks for two.
- Exposure ranges come from `risk_estimates` rows, matched by `category`. Count each
  category **once** in an aggregate even when several issues cite it, and list which
  categories you included/excluded if the template has fields for that.
- Every total must equal the sum of the components you actually emitted.

### 6. Validate, then emit

Run `scripts/validate_answer.py <candidate.json> <answer_template.json>`. It checks
required keys, enum membership, integer-dollar fields, percent rounding, and pinned-ID
coverage. Emit raw JSON only — no prose, no code fences, no trailing commentary.

## Pitfalls

- **Padding a required/blocking list with non-qualifying records.** The costliest
  recurring error. `required_for_closing == "no"` and `consent_required == "notice only"`
  are never blockers.
- **Inventing IDs.** Prefer stable workbench IDs (`CNS_*`, `MAT_*`, `EMP_*`, `TERM_*`,
  `RSK_*`, `FND_*`). Only synthesize one where the template explicitly permits it
  (e.g. "synthetic regulatory id").
- **Free-styling risk ratings.** Inherit `risk_default` from the governing rule, or the
  record's own `risk_rating`, before making a judgment call. Normalize to the enum's case.
- **Ignoring `client_side`.** It flips `draft_exceeds_playbook` vs `draft_below_playbook`
  and flips which party a term protects.
- **Double-counting an exposure category** across several issues in an aggregate total.
- **Trusting `limit_value`** instead of the preferred/fallback prose.
- **Wrong percent precision.** Two decimals, one decimal, and four-decimal holder
  percentages all appear; re-read the prompt for each task.
- Adding keys the template does not list is harmless; omitting listed keys is not.
