---
name: pho-algorithmic-audit
description: >
  Solve Public Health Observatory (PHO) "registered algorithmic audit" tasks: a
  prompt plus an analysis_request.json and answer_template.json that ask you to
  build cohorts from a read-only health/socioeconomic data portal and run a
  registered multi-module statistical audit (fixed-effects/GMM jackknife, nested
  ridge/elastic-net CV, wild cluster bootstrap-t, split conformal, trajectory
  PCA+k-means stability, source/feature perturbation) into one strict JSON object.
  Use when a task references the PHO portal, a six-module robustness/transport
  audit, registered final-release resolution, cohorts, and a controlled decision.
---

# Public Health Observatory registered algorithmic audit

These tasks look intimidating but share one shape: **resolve published records
from a data portal → build declared cohorts → run N declared statistical modules
→ evaluate decision gates → emit one JSON object** that conforms exactly to
`answer_template.json`. The portal is the only evidence source; everything is
computed deterministically from it (the sole randomness is inside a bootstrap
whose PRNG is fully specified).

## Inputs you are given (per task)
- `prompt.txt` — the framing and the portal base URL (a placeholder like
  `<TASK_ENV_BASE_URL>`).
- `payloads/analysis_request.json` — the registered protocol: scope, years,
  outcome/exposure, evidence filters, cohort definitions, the audit modules (each
  with its `standard_method`, feature/coefficient order, grids, seeds and
  `required_evidence`), and the decision rule / gates.
- `payloads/answer_template.json` — the response contract: required keys, array
  lengths, orderings, identifier and precision rules, enum values.

Read all three fully before computing. The request and template are exhaustive —
they tell you every field, order and threshold. Treat them as the spec.

## Workflow
1. **Map the portal.** From the given base URL, read `GET /catalog` (datasets,
   columns, filters, CSV export) and `GET /methodology` (the publication rules).
   Download whole datasets as CSV and process locally — they are small.
2. **Resolve releases.** Apply registered-final-release resolution to every
   requested series: keep FINAL, take the highest revision, drop PROVISIONAL,
   treat suppressed/invalid-flagged values as unavailable (never zero-fill), honor
   direct-vs-rollup and crude-vs-age-adjusted. For country tasks, apply the
   revision-notice / scale-break logic. See `references/data_model.md`.
3. **Build the declared cohorts** (complete-case per year, reference/primary,
   balanced panel, ML/augmented, strict dual-source) and report the audit counts
   exactly as the template asks — including that resolved-record *counts include
   suppressed rows*, while *completeness* excludes them.
4. **Implement each audit module** from its declared spec, matching the
   reproducibility conventions in `references/audit_modules.md` (SE variants,
   training-only standardization, the exact named PRNG + seed/stream, covariance
   PCA + deterministic k-means init, tie-breaks). Preserve every declared order.
5. **Evaluate the decision block**: turn each gate's threshold expression into a
   boolean on your computed statistics, count passes, apply the classification /
   precedence ladder literally.
6. **Emit one JSON object** matching the template: correct keys and array lengths,
   declared decimal places as JSON numbers, integers/booleans as natural types,
   identifiers exactly, `null` only for mathematically-unavailable statistics.
   No text outside the JSON.

## Reference files
- `references/data_model.md` — portal datasets, the exact release/revision
  resolution rules, country scale-break handling, cohort patterns, and the output
  contract (rounding, ordering, identifiers, null rule).
- `references/audit_modules.md` — the six recurring module families with the
  conventions that make each field reproducible, and how to build the decision block.
- `references/portal_toolkit.py` — a dependency-light Python helper (takes the
  portal base URL as an argument): CSV dataset loading, `resolve_final`,
  suppression handling, geography lookups, and country-label reconciliation.
  Import and extend it; it hardcodes no task values.

## What makes or breaks the score
The graded output is the *numbers*, so precision and convention-matching dominate:
- **Resolution is the foundation.** A wrong revision/suppression/direct-vs-rollup
  choice silently corrupts every downstream cohort and statistic. Verify counts.
- **Match declared conventions exactly**: SE type (CR1 vs classical vs HC3),
  standardization scope (training-only), penalty/units (`_per_10000`, `log_*`),
  PCA covariance-vs-correlation and sign rule, k-means initialization, and CV
  tie-breaks. A plausible-but-different convention scores as wrong.
- **Reproduce the specified PRNG bit-for-bit** (XORSHIFT32 / PCG32 with the given
  seed/stream, draw order, and weight family); emit the requested PRNG-state and
  statistic checkpoints and the terminal state.
- **Ordering and identifiers**: never re-sort an aligned array; use exact codes,
  division names, ISO3 and enum strings; round to the declared places; `null`
  only when truly undefined.
- **Decision logic is deterministic** once the module statistics exist — evaluate
  each gate literally and apply the precedence ladder.

Work in a scratch dir (not the task input); build a small reusable toolkit for
resolution + the module families and reuse it across tasks, since the portal
schema, resolution rules and module families are stable across the family.
