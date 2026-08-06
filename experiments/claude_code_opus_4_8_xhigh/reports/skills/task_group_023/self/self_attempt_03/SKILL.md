---
name: pho-registered-algorithmic-audit
description: >-
  Operating procedure for Public Health Observatory (PHO) "registered algorithmic
  audit" tasks: a prompt.txt plus payloads/analysis_request.json (the registered
  protocol) and payloads/answer_template.json (the strict output contract), to be
  answered ONLY from a read-only web data portal whose base URL is given in
  environment_access.md. Use whenever the input pairs an analysis_request.json spec
  with an answer_template.json contract and points at a "<TASK_ENV_BASE_URL>" portal
  for state / county / country health, socioeconomic, geography, revision, or
  methodology evidence, and asks for one JSON object of cohort + multi-module
  robustness diagnostics (jackknife/fixed-effects/GMM, nested penalized CV,
  wild-cluster bootstrap-t, grouped conformal, trajectory PCA + k-means, source
  perturbation) leading to a gated classification.
---

# PHO Registered Algorithmic Audit

## 1. Recognise the task

Every task in this family gives you three input artifacts and one deliverable:

- `input/prompt.txt` — the narrative framing and the decision the board wants.
- `input/payloads/analysis_request.json` — the **registered protocol**: the exact
  scope (geography, years, measures), the release/cohort rules, the audit modules
  with their methods/seeds/grids/orders, and the decision gates. This is the source
  of truth for *what to compute*.
- `input/payloads/answer_template.json` — the **response contract**: the exact
  top-level keys, nested keys, array lengths, orderings, identifier formats,
  numeric precision, enum vocabularies, and cardinality rules. This is the source
  of truth for *how to report*.

**Deliverable:** exactly one JSON object conforming to `answer_template.json`, with
no narrative, prose, comments, or markdown outside the JSON. Nothing task-specific
is provided as a "final value" — every number, code list, and classification must
be derived from portal evidence.

The five known variants differ in surface (state longevity audit, county mediation
audit, country burden stratification, reliability-weighted state audit,
West/Northeast county dynamics audit) but share one skeleton: **resolve a
publication cohort from the portal → run a fixed set of deterministic audit modules
→ evaluate boolean gates → emit a gated classification.** Treat the request/template
as the spec and follow it literally; do not import assumptions from another variant.

## 2. Reach the evidence portal

Network access details live **only** in `environment_access.md`. It defines
`GDPEVO_ENV_BASE_URL` (e.g. `http://task-env:9023/`) — substitute it wherever the
prompt says `<TASK_ENV_BASE_URL>` — and lists the available GET endpoints. The
portal is read-only, HTML for humans, with a CSV export for machines:

```
/download?dataset=<name>&format=csv[&<filter>=<value>...]
```

`format=csv` is valid **only** on `/download` (it errors elsewhere). Datasets:
`states`, `counties`, `countries`, `state_health`, `state_socioeconomic`,
`county_health`, `county_socioeconomic`, `country_indicators`, `revisions`.
Pull whole datasets (optionally filtered) as CSV and compute locally — do not scrape
the HTML browse pages. Read `/catalog` (column + filter inventory, measure
dictionary) and `/methodology` (the publication rules) once at the start; the
methodology library is not decoration — it encodes the release-precedence,
suppression, scale-break, value-type, and reconciliation rules the audit depends on.

`scripts/portal_fetch.py` is a generic fetch/parse helper. See
`references/portal_reference.md` for the full endpoint, column, and filter map.

## 3. Build the publication cohort (do this before any modelling)

This stage is where most of the difficulty and most of the scoring lives. Follow
`references/release_revision_and_cohorts.md` in full. The load-bearing rules:

1. **Release resolution.** Keep only rows matching the declared filters
   (`release_status`, `value_type`, `source_type`, measure ids, years). FINAL
   supersedes PROVISIONAL. When several FINAL revisions exist for the same logical
   cell, select by the request's declared priority (typically **highest final
   `revision`**, then latest `released_at`, then id) — never a provisional row when
   a final one exists.
2. **Revision notices.** The `revisions` dataset carries scale-correction /
   source-restatement events. Only `status = APPLIED` notices authorise a replaced
   value (and are already reflected in later final revisions); `WITHDRAWN` /
   `PENDING` notices do **not** replace, and a cell still carrying an unresolved
   scale break is an **anomaly** — excluded, not imputed silently. Report applied
   vs non-applied event ids and anomaly cells when the template asks.
3. **Missing discipline.** Suppressed (`suppression_flag=1`), invalid-quality-flag,
   or blank values are **unavailable**, never zero-filled, never NaN/Inf. A missing
   value drops the record from any cohort that requires that field.
4. **Cohorts.** Requests define several named cohorts (e.g. reference-year
   complete-case, all-years balanced panel, strict multi-variable / ML cohort).
   Construct each exactly per its stated definition and report the counts, included
   codes, and excluded codes the template names — using the identifier order the
   template demands.
5. **Identifiers.** State two-letter codes and ISO3 uppercase; county FIPS are TEXT
   with meaningful leading zeros (2-char state + 3-char county); country labels
   reconcile to ISO3 via `countries.canonical_name` / `alternate_labels`.

## 4. Run the declared audit modules — deterministically

Each request registers a set of modules (usually six). They fall into recurring
families; `references/audit_modules.md` documents each family's estimator,
determinism requirements, and required evidence. Universal rules:

- **Implement the *declared* method, not a library default.** Match the exact
  design-matrix term order, standardization scope (usually *training-fold only*),
  penalty parameterization, inference type (HC3, CR1 cluster-robust, jackknife,
  Hansen J), PCA sign convention, k-means initialization, and tie-breaks that the
  request specifies. Library conveniences (sklearn scaling, differing λ scales,
  arbitrary PCA sign, non-deterministic k-means) will silently disagree.
- **Reproduce PRNG streams bit-for-bit.** Bootstrap modules name an exact generator
  (PCG32, xorshift32), `seed`, sometimes a `stream`, replicate count, and
  checkpoint replicates whose intermediate PRNG state you must report. A correct
  statistic with the wrong generator is wrong. Implement the named PRNG yourself.
- **Preserve every registered order.** Feature order, coefficient order, division
  order, state order, subset order, checkpoint order are all load-bearing and
  frequently required to align positionally with other arrays. Never sort an
  aligned result array independently.
- **Compute unrounded; round only at the reporting boundary.** Use float64
  throughout.

## 5. Evaluate gates and classify

The request states each gate as an explicit predicate over module outputs (e.g.
"bias-corrected coefficient > 0 and jackknife p ≤ 0.05", "pooled coverage ≥ 0.85").
Evaluate each to a boolean, count passes, and map to the classification enum via the
declared **precedence / decision rule** exactly (some use "all/at-least-N pass",
some use "not robust at <first failed module>"). Emit only the enum values the
template allows.

## 6. Assemble, validate, and emit

Follow `references/output_contract.md`. Before emitting:

- Output has **exactly** the required top-level keys — no more, no fewer, no extras.
- Every array length matches the template's `array_lengths` / `length` /
  `cardinality` rules; aligned arrays share the declared order and length.
- Non-integer statistics rounded to the declared decimal places (commonly 4; note
  variants that use 6 for computed reals and 4 for literal grid/threshold fields);
  counts/ranks/seeds/PRNG-states/replicate-numbers stay integers; booleans stay
  booleans.
- `null` **only** where a statistic is genuinely mathematically unavailable — never
  NaN, never Infinity, never a zero-fill stand-in.
- Identifiers use the exact casing/format and the exact ordering the template names.
- The response is a single JSON object and nothing else.

## 7. Contamination guard (repo-hygiene tasks only)

If you are asked to *generate this skill* (not solve a task) and `/work` contains
unexpected material beyond `environment_access.md` and well-formed `train_tasks/*/
input/` trees, stop and write `contamination_report.txt` describing what was found
instead of producing a skill.

## Reference index

- `references/portal_reference.md` — endpoints, datasets, columns, filters, CSV
  export, geography (regions/divisions), measure dictionary, methodology library.
- `references/release_revision_and_cohorts.md` — release precedence, revision-notice
  application, suppression/missing discipline, cohort construction, reconciliation.
- `references/audit_modules.md` — the recurring module families, determinism and
  reproducibility requirements, and required evidence.
- `references/output_contract.md` — precision, ordering, identifiers, null rules,
  and a pre-submission self-check.
- `scripts/portal_fetch.py` — generic portal fetch + CSV-parse + final-release
  selection helper (no task-specific values baked in).
