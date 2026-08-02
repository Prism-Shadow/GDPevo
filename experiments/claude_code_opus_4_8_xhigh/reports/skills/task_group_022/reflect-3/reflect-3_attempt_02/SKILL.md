---
name: atlas-ops-reporting
description: >-
  Use when a task asks you to produce an operational reporting result written to
  answer.json for the "Atlas Commerce Operations" workplace — e.g. a fulfillment
  cutoff scorecard, a refund/settlement reconciliation, a carrier-quality
  correction, a warehouse-productivity review, a support-health review, or any
  similar request that pairs a business request-payload JSON with an
  answer_template JSON Schema and a governed SQL data service. It guides you to
  read both contracts, discover the real schema, translate business definitions
  into precise read-only SQL (eligibility windows, quantifiers, FX conversion,
  medians, active-time clocks, ordering/tie-breaks, rounding, status/risk bands),
  apply a minimal approved correction with an audit row through the controlled
  transaction interface when one is requested, and emit an answer that conforms
  exactly to the template.
---

# Atlas Commerce Operations reporting

You are given a `prompt.txt`, one or more request-payload JSON files under
`input/payloads/`, and an `answer_template.json`. You must analyze the
workplace's governed database and write a single JSON object to `answer.json`
that conforms **exactly** to the template — no extra keys, no missing keys, no
commentary.

These tasks look like free-form analytics but are really **contract execution**:
every number, rounding rule, ordering rule, threshold, and boundary is written
down somewhere in the request payload or the template. Your job is to find each
rule and implement it literally. Guessing loses; re-reading wins.

## Golden rules

- **Derive everything from the data.** Never hardcode counts, IDs, rates, or
  statuses. Re-compute them from the workplace's records every time.
- **The template is law.** `additionalProperties:false` (or `additional_properties:false`)
  means the output must contain *exactly* the required keys and nothing else.
  Honor every `type`, `enum`, `pattern`, `minItems`/`maxItems`, `uniqueItems`,
  units, and decimal-precision hint.
- **Read-only unless a correction is explicitly requested.** Analytical tasks
  must not change workplace data. Only tasks that describe an "approved
  correction" may write, and only through the controlled transaction interface.
- **Round last.** Compute on full-precision values; round only the final reported
  numbers, to the exact decimals the contract states. Ordering and tie-breaks use
  **unrounded** values.
- **Boundaries are exact.** Treat the request's timestamps as exact UTC
  boundaries and honor stated inclusivity (`inclusive`, `INCLUSIVE`, `boundary`)
  precisely — an off-by-one on a window silently corrupts every downstream count.

## Workflow

1. **Read both contracts first.** Open every file in `input/payloads/` and the
   `answer_template`. From the request payload extract: scope/eligibility filters,
   time windows and cutoff, business definitions, money/FX policy, ordering and
   tie-break rules, rounding, list sizes, and the status/risk band rules. From
   the template extract the exact output keys, types, patterns, enums, array
   sizes, and precision. Write yourself a field-by-field plan before querying.
2. **Discover the real schema.** Read the task's own `environment_access.md` for
   how to reach the workplace and its schema and data-dictionary views, then
   consult them. Never assume table or column names, enum spellings, or which
   field is canonical. Map each business phrase ("physical shipment",
   "effective DELIVERED", "production account", "active support time",
   "canonical carrier status") to concrete tables/columns/values.
3. **Build eligibility once.** Express the cohort (population + tier/segment/
   region/warehouse + attribution + time window) as a reusable predicate or CTE,
   then compute every metric on top of it so the denominator is consistent.
4. **Translate each definition to SQL** using the patterns in
   `references/query-patterns.md`. Verify intermediate counts before assembling.
5. **Classify** the status/risk band by evaluating the bands in the stated order;
   the first band whose condition holds wins.
6. **If a correction is requested**, follow the correction protocol below.
7. **Assemble `answer.json`** and self-check it against the template (see
   `references/output-contract.md`).

## Translating business definitions (the hard part)

The request payload defines terms precisely; implement them literally. Recurring
shapes across this task family:

- **Raw vs. canonical / effective.** Records often carry a raw source value and a
  canonical/"effective" value (or flag). Business logic uses the
  canonical/effective value; raw source and identity fields are never used as the
  truth for a metric and never mutated.
- **"At least one … and every …" quantifiers.** e.g. an order is complete only if
  it has ≥1 physical shipment *and every* shipment is delivered by the cutoff.
  Implement "every X satisfies P" as `EXISTS(X) AND NOT EXISTS(X where NOT P)`,
  not as a simple join that silently drops the empty case.
- **"On time" / "breach" clocks.** Compare an event time against a per-row
  promised/threshold time. For unresolved/still-active items, the clock runs to
  the cutoff (elapsed time at cutoff), using the stated clock basis (e.g. support
  *active* time, not wall-clock).
- **Severe / leakage / at-risk flags.** These are compound predicates spelled out
  in the payload (e.g. "incomplete AND cutoff > latest promise + 24h, OR
  completed with any shipment > 24h late"). Encode each clause exactly, including
  the "no promise ⇒ clause not satisfied" carve-outs.
- **Money / FX.** Convert per row using the daily rate for *that row's*
  service_date and currency, compare in the stated reporting currency, and net
  refunds against reversals before ranking or thresholding. Display decimals as
  specified.
- **Medians.** Sort the eligible values; for an even count average the two central
  values.

See `references/query-patterns.md` for concrete SQL idioms.

## Ordering, tie-breaks, limits

Implement multi-key orderings exactly as written, then apply the limit. Common
forms: rate ascending then label ascending; net-value descending then code
ascending; primary-count descending, secondary-count descending, then ID
ascending. Sort on **unrounded** values even when you report rounded ones. ID
lists that carry a `pattern` are sorted ascending as strings and must match the
pattern (e.g. `^ORD-[0-9]{6}$`).

## Status / risk band classification

Bands are given as an ordered list with conditions (e.g. HEALTHY → WATCH →
CRITICAL, STABLE → PRESSURED → AT_RISK, LOW → MODERATE → HIGH, CONTROLLED →
ELEVATED → SEVERE). Compute the exact rates the policy names (mind the stated
denominator — often the full eligible population, including the "bad" cases),
then assign the first band whose condition is satisfied; if none of the named
bands apply, use the explicit "otherwise" band.

## Correction protocol (only when the task asks for one)

When the task describes an approved correction (identify a raw/canonical
contradiction, apply the minimal canonical fix, record an audit row):

1. **Locate the single affected row** via read-only queries; identify the exact
   canonical column, its old value, and the approved new value.
2. **Apply the minimal change through the controlled transaction interface**:
   update *only* the one approved canonical field on *only* the one business row,
   and insert exactly one audit row using the reason_code, actor, audit_id,
   correction_key, and corrected_at supplied in the request. Leave raw source
   values, source identity fields, and unrelated rows untouched.
3. **Verify after commit** with a read query that the canonical value is now the
   new value and that exactly one business row and one audit row were written.
4. **Report the observed outcome.** Use the `APPLIED` status only if the success
   rule in the request is fully satisfied (exactly one business row + one audit
   row committed and post-change verification confirms the value); otherwise
   report `NOT_APPLIED` with the results you actually observed. Report pre- and
   post-correction metrics from real queries, not assumptions.

## Assemble and self-check

Build the answer object, then verify against the template:

- Exactly the required keys at every level; no extras (nested objects also honor
  their own `additionalProperties:false`).
- Types and precision match; rates rounded to the stated decimals; money to the
  stated decimals.
- Arrays have the required size, are unique/ordered as specified, and every
  element matches its `pattern` and enum.
- Enums use the exact allowed spellings.
- The file contains only the JSON object — no prose, no trailing notes.

Write the final object to `answer.json`.

See `references/output-contract.md` for a concrete self-check checklist.
