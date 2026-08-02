---
name: pho-registered-audit
description: >-
  Complete a Public Health Observatory (PHO) "registered algorithmic audit"
  task: given a prompt.txt plus payloads/analysis_request.json and
  payloads/answer_template.json, use ONLY the read-only PHO web portal
  (<TASK_ENV_BASE_URL> from environment_access.md) to resolve final data
  releases, build the declared cohorts, run the declared multi-module
  statistical audit, apply the controlled decision rule, and return exactly one
  JSON object conforming to answer_template.json with no narrative outside it.
  Use whenever a task references the Public Health Observatory portal, a
  registered/algorithmic audit, transportability/robustness/mediation of a
  health signal, or supplies an analysis_request.json + answer_template.json pair.
---

# PHO registered algorithmic audit

## What this family is
The Public Health Observatory publishes a briefing decision (transportability /
robustness / mediation of a health signal at state, county, or country level).
You are handed three files per task:

- `input/prompt.txt` — the business framing and the hard output rules.
- `input/payloads/analysis_request.json` — **authoritative for method**: scope,
  release/cohort rules, the registered audit modules with their seeds/grids/orders,
  and the decision gates.
- `input/payloads/answer_template.json` — **authoritative for the response
  contract**: required top-level keys, per-field types, array lengths, cardinality
  rules, identifier rules, numeric precision, and the allowed enum values.

Your deliverable is **exactly one JSON object** that conforms to
`answer_template.json`, with **no prose outside the JSON**. Every reported number,
order, identifier, and enum must satisfy both payloads simultaneously.

When these payloads (or the PHO portal) are present, follow this skill. The two
supporting references are load-bearing — read them before you start:
- `references/portal.md` — datasets, endpoints, and the methodology rules that
  break every release/revision/quality tie.
- `references/audit_modules.md` — the recurring module family and the exact
  reproducibility contract each module must satisfy.
- `scripts/portal_client.py` — a GET-only portal CSV client (`Portal().fetch(...)`).

## Non-negotiable invariants (they decide pass/fail)
1. **Evidence source = the portal only.** Base URL from `environment_access.md`
   (`GDPEVO_ENV_BASE_URL`). GET-only. Pull complete tables with
   `/download?dataset=<name>&format=csv` — the HTML `/data/*` pages paginate.
2. **Read every knob from the current payload.** Seeds, streams, replicate counts,
   checkpoint lists, lambda/alpha/l1 grids, feature/coefficient orders, cohort
   definitions, thresholds — all come from *this* task's `analysis_request.json`.
   Never reuse a value from another task.
3. **Preserve declared order; align positionally.** Any array that "aligns with"
   another (delete-one coefficients ↔ state_order, scores ↔ units, checkpoints ↔
   replicates) must be emitted in that exact order. Do not independently sort an
   aligned array.
4. **Missing is missing, never zero.** Suppressed / blank / invalid-flagged cells
   are UNAVAILABLE. Never zero-fill. `null` only when a statistic is mathematically
   undefined — never `NaN`/`Infinity`.
5. **Precision & types exactly as declared.** Round reported non-integers to the
   declared decimal places (commonly 4; some tasks say computed=6, literals=4 —
   read the `reporting` block). Counts/ranks/seeds/PRNG-states = integers; flags =
   JSON booleans; identifiers exactly as required (uppercase state codes, uppercase
   ISO3, FIPS as text with leading zeros, portal division/region names verbatim).
6. **Output is one JSON object, nothing else.** No markdown, no commentary.

## Operating procedure

### Phase 0 — Triage the payloads
- Confirm the three inputs exist and read all of them in full. The
  `required_top_level_keys` in the template is your output skeleton and your
  checklist. List every module and every required field/length/cardinality rule.
- Note the geography level (state / county / country) → it selects the datasets and
  the geography reference (division for states, rucc/region for counties, iso3/alias
  for countries).

### Phase 1 — Discover the environment
- `GET /catalog` for live schema and filterable columns; skim `GET /methodology`.
- Read the specific methodology docs your task depends on (release-lifecycle,
  publication-values, state-estimates, suppression, quality, aliases,
  country-revisions, rucc, geographic-ids — see `references/portal.md`). Prefer
  CURRENT docs; a DRAFT or SUPERSEDED doc does not change policy.

### Phase 2 — Resolve final releases & revisions (per record, independently)
- Filter to the declared `value_type` / `source_type` / `release_status`.
- Keep `FINAL` over `PROVISIONAL`; among FINAL, the **highest APPLIED final
  revision governs** (apply the request's revision-priority tuple when it gives one,
  e.g. `[revision, released_at, observation_id]`).
- Apply `revisions` events whose `status = APPLIED`; ignore `PENDING`/`WITHDRAWN`.
  Exclude cells carrying the request's `invalid_quality_flags`.
- Reconcile identifiers: country labels → ISO3 via `alternate_labels`; keep FIPS as
  text. Resolve the exact universe the request scopes (e.g. 50 states + DC = 51).

### Phase 3 — Build the declared cohorts
- Implement each cohort definition literally on the resolved evidence: complete-case
  over the named variables; primary/reference-year; balanced (complete in every
  study year); ML/broad (extra features); strict dual-source. A value is complete
  only if nonsuppressed, non-null, and not invalid-flagged; never zero-fill.
- Emit exactly the cohort audit fields the template names (counts, excluded codes,
  yearly complete counts, state census) in the required order.

### Phase 4 — Run each registered module exactly
- Match each declared method to its family in `references/audit_modules.md` and
  implement it on the module's named cohort with the module's declared orders,
  grids, seeds, and PRNG. Reproduce deterministic generators (PCG32 / xorshift32)
  bit-for-bit and **verify against any requested checkpoint** before trusting the run.
- Produce every `required_evidence` / template key at the declared length and
  alignment. Fix row order deterministically before any order-dependent algorithm.

### Phase 5 — Apply the controlled decision rule
- Evaluate each gate/flag against its exact threshold from the request (`>=`, `<=`,
  `<`, sign conditions, counts). Set each boolean, count the passing gates, and map
  through the declared **precedence** to one allowed classification enum. Emit the
  `first_failed_module` / passed-count fields the template requires.

### Phase 6 — Assemble & self-validate
- Build the single JSON object with exactly the `required_top_level_keys`.
- Validate before submitting: every required key present; every array the declared
  length; every cardinality rule met (e.g. "length equals state_n", "must match
  X.state_order", "one item per balanced state code"); numbers at the right
  precision as JSON numbers; enums from the allowed set; `required_value` fields
  matched; no `NaN`/`Infinity`; no extra keys or narrative.

## Common pitfalls
- Using paginated `/data/*` HTML and silently truncating at 50 rows → use `/download`.
- Zero-filling suppressed/missing cells, or dropping the leading zero on a FIPS.
- Carrying a seed/grid/threshold from a prior task instead of reading this payload.
- Re-sorting an array that must align positionally with another.
- Treating a PENDING/WITHDRAWN revision, or a SUPERSEDED/DRAFT methodology doc, as
  authoritative.
- Emitting rounded strings instead of JSON numbers, or `null` where the statistic is
  actually defined (or a number where it is genuinely unavailable).
- Adding explanation around the JSON. The output is the JSON object alone.
