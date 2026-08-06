---
name: ops-request-scorecard
description: >-
  Use when a task provides an operations "request" JSON (business scope, metric
  and classification definitions) plus a strict answer_template JSON Schema and
  asks you to compute exact figures from an authenticated operations database and
  write them to answer.json. Covers cutoff/window-based scorecards, refund and
  money reconciliations, warehouse/support productivity and SLA reviews, and
  minimal canonical data-correction tasks. Turns a prose business spec into
  precise, schema-exact numeric answers derived from the live records.
---

# Operations request → schema-exact answer

This skill solves a recurring task family: an operations stakeholder supplies a
**request specification** (a JSON payload of scope, business definitions, rollups,
rounding, ordering, and status rules) and a **strict output contract**
(`answer_template.json`, a JSON Schema). You must compute the exact figures from
the workplace's operations records and emit a single JSON object — conforming to
the template exactly — to `answer.json`, with no commentary.

The numbers live in the database. Almost every mistake on these tasks is a
**definition misread**, not an arithmetic error. Read the spec as a contract and
translate each clause literally.

## Workflow

1. **Read everything before querying.** Read the prompt, the `*_request.json`
   payload, and `answer_template.json` in full. The request payload is the source
   of truth for *what* to compute; the template is the contract for *shape*.
2. **Learn the real data model.** The workplace exposes an authenticated schema
   description and a data dictionary. Consult both first — never guess table or
   column names, and never assume a field's meaning; the dictionary distinguishes
   raw vs. canonical/effective columns, status vocabularies, flags, and units.
3. **Draft the cohort filter, then the metrics.** Build the eligible population
   first (production filter + scope + window). Get its count right before layering
   on rates and lists — most downstream fields share that denominator.
4. **Query the records read-only.** Use the read-only SQL facility for analysis.
   Push filtering/aggregation into SQL, but pull the raw rows for any field whose
   definition has edge cases you need to verify by hand.
5. **For correction tasks**, follow the mutation protocol below.
6. **Assemble, verify, and write** the answer object to `answer.json`. Validate it
   against every constraint in the template before finishing.

## Reading the business spec — the recurring rules

These clauses appear again and again. Treat each as a checklist item.

- **Production only.** Scope almost always says "production" accounts/orders/
  shipments/cases. Find the production flag and filter to it; exclude test/
  non-production rows from *every* count, rate, and list.
- **Scope filters are conjunctive.** Segment, tier, region, warehouse, campaign
  attribution — apply all of them. "Eligible" typically means attributed to the
  named entity **and** created/opened within the official active window.
- **Time boundaries are exact UTC.** Treat every timestamp as an exact UTC
  boundary. Honor the stated inclusivity (`inclusive`/`INCLUSIVE` → `>=`/`<=` on
  both ends). A "cutoff" evaluates state **as of** that instant: only events at or
  before the cutoff count; later events do not exist yet for this report.
- **Use effective/canonical values, never raw.** Records carry raw source values
  alongside canonical/corrected ones, and refunds carry linked reversals. Always
  compute on the **effective** value: canonical (post-correction) status, refund
  amounts **net of** linked reversals, the latest/settled row. If a definition says
  "effective settled," exclude unsettled and reversed components.
- **Denominators keep the bad cases.** Rate denominators are the full eligible
  population unless stated otherwise — incomplete/unresolved/breached items stay
  in the denominator. Don't quietly drop them.
- **Compute unrounded; round only at the end.** Carry full precision through all
  intermediate math. Round **only** the final reported rate/amount to the stated
  decimals (e.g. 4 dp for rates, 2 dp for money/hours). Rank and break ties on the
  **unrounded** value, not the rounded display value.
- **Ordering + tie-breaks + exact size.** "Worst/top N" lists: sort by the named
  metric in the named direction, then by the stated tie-break (usually id/region/
  code ascending), then return **exactly** N items. Emit ID lists sorted ascending
  and matching the template's regex pattern exactly.
- **Multi-condition definitions have deliberate edge cases.** "Severe/exception"
  and similar composite definitions include explicit carve-outs (e.g. an item with
  no promise timestamp does *not* satisfy the "past promise" branch; an item with
  no shipment is incomplete). Encode each branch and each carve-out separately.
- **Status/risk classification is ordered, first-match-wins.** Evaluate the status
  rules top to bottom against the **unrounded** rates; the first satisfied rule
  wins; the final "otherwise" clause is the fallback. Check every sub-condition of
  a tier (a status usually requires *all* of its listed thresholds).
- **Median rule.** Median across the resolved set; for an **even** count, average
  the two central values; then round to the stated decimals.
- **SLA / active-clock metrics.** Use the specified clock basis (e.g. support
  active time, productive minutes), compare against the **per-priority** threshold,
  and for still-open/unresponded items use elapsed active time **at the cutoff**.
- **Money & FX.** Convert to the reporting currency using the daily rate for each
  row's own service_date and currency; value cross-currency comparisons at the rate
  the definition names (e.g. the settled-refund service_date rate).

## Data-correction (mutation) tasks

Some tasks ask you to fix exactly one raw/canonical contradiction and report before/
after figures. The workplace provides a controlled transaction facility and a
correction-audit view for these.

- **Find the single contradiction** the spec promises (one scan/shipment/row where
  the canonical field disagrees with the reconciled truth). Correct **only** the
  minimal canonical field named by the scope. Leave raw source values, source/
  identity fields, and all unrelated rows untouched.
- **Commit atomically:** exactly one business row updated **and** one audit row
  inserted, in a single transaction. Populate the audit row with the approved
  reason_code, actor, audit_id, correction_key, and corrected_at from the request.
- **Report `APPLIED` only if** exactly those row counts committed **and** a fresh
  post-change read confirms the corrected canonical value. Otherwise report
  `NOT_APPLIED` with the counts and backlog figures you actually observed.
- Compute the pre- and post-correction figures (e.g. backlog counts and their
  delta) as separate reads so they reconcile with the mutation you made.

## Output discipline

- The template is authoritative. If it sets `additionalProperties: false`, emit
  **no** extra keys. Include every `required` key. Match every type, `enum`,
  `pattern`, array `minItems`/`maxItems`, and `multipleOf`/decimal-places constraint.
- `multipleOf: 0.0001` / `precision: 2` means the value must be pre-rounded to that
  granularity — round before serializing.
- `answer.json` contains **only** the JSON object. No prose, no markdown, no
  trailing commentary.

## Verify before finishing

- Cross-foot the counts: complete + incomplete = eligible; open-at-cutoff ⊇
  reopened subset; per-region/per-team parts reconcile with the overall.
- Re-derive each rate from its numerator and denominator; confirm rounding was
  applied only once, at the end.
- Re-check every list's sort order, tie-break, size, and id pattern.
- Re-read each classification rule and confirm the chosen status/risk label is the
  first fully-satisfied tier.
- Validate the final object against the template constraint-by-constraint.

See `references/spec-checklist.md` for a compact per-field checklist to run against
any new request of this family.
