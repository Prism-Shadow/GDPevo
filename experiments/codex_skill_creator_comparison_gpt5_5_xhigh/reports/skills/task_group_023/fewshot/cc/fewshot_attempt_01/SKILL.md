---
name: pho-observatory-audits
description: Use this skill for Public Health Observatory audit tasks that provide an analysis_request.json and answer_template.json, require evidence only from the PHO Web portal, or mention exact PHO protocols such as PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, or country burden/revision PCA audits. It helps produce the final JSON answer with strict release resolution, ordered statistical diagnostics, reproducibility checkpoints, and controlled decisions.
---

# PHO Observatory Audits

Use this skill when a task asks for a Public Health Observatory audit from a
portal URL plus `analysis_request.json` and `answer_template.json`.

The task is usually graded on exact reproducibility, not prose quality. Treat
the request and template as the contract, compute from portal evidence, and
return one JSON object with no narrative outside it.

## Required Workflow

1. Read the prompt, `analysis_request.json`, and `answer_template.json`.
2. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment. Use only that
   portal and local task inputs.
3. Download the needed portal CSVs with:
   `/download?dataset=<dataset_name>&format=csv`.
4. Build one effective request before computation. Apply exact-protocol defaults
   and request overrides first; arrays replace in full, objects merge by exact
   key, and unknown override targets are errors.
5. Resolve publication records independently for each dataset, measure, source,
   value type, year, and geography key. Preserve selected publication counts
   before analytic completeness exclusions when the template asks for them.
6. Construct cohorts only from selected records. Suppressed, invalid, withdrawn,
   blank, null, or mathematically unavailable values are unavailable and are
   never zero-filled.
7. Run every declared audit module in the request order. Use unrounded values for
   subsequent modules, gates, ties, and decisions.
8. Round only at final serialization, using the precision and literal-value rules
   in the template or `analysis_request.reporting`.
9. Emit exactly the JSON shape requested by `answer_template.json`. Preserve every
   declared order: states, counties, countries, years, folds, grids, checkpoints,
   feature lists, source groups, and coefficient arrays.

## Portal Loading

The portal normally exposes these datasets:

`states`, `counties`, `countries`, `state_health`, `state_socioeconomic`,
`county_health`, `county_socioeconomic`, `country_indicators`, and `revisions`.

Prefer CSV downloads over scraping HTML tables. If a task supplies filters in the
request, it is still safer to download the complete relevant dataset and filter
locally so release resolution, ordering, and counts are auditable.

Use `scripts/pho_math.py` for repeatable helpers:

```bash
python - <<'PY'
from scripts.pho_math import download_portal_csvs
base_url = "http://task-env:9023"
tables = download_portal_csvs(base_url, ["states", "state_health"])
print(len(tables["states"]), len(tables["state_health"]))
PY
```

Copy or import the helper script into the active solving workspace when needed;
do not edit the skill package during a solve.

## Protocol Routing

Read [references/protocols.md](references/protocols.md) before implementing a
module. It summarizes the reusable method semantics inferred from the staged
examples without carrying any solved answer values.

Use exact routing:

- `PHO_STATE_TRANSPORT_AUDIT_V1`: state-level longevity transport audit.
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`: county poverty/inactivity/obesity
  mediation transport audit.
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`: reliability-weighted state robustness
  audit.
- `PHO_COUNTY_PANEL_TRANSPORT_V1`: county dynamic panel transport audit.
- Country burden/revision audit: use this route when the request is a country
  cross-section/panel burden PCA audit with country label reconciliation,
  revision notices, burden clusters, and a region-adjusted panel model.

If a future request has a similar subject but a different exact `protocol_id`,
do not silently reuse a registered protocol profile. Follow only the explicit
future request and template, borrowing general helper routines as ordinary math.

## Common Statistical Conventions

- Record selection: filter to the effective publication status/source/value type
  first. Then apply the request's revision priority. Most PHO final-release
  tasks use greatest revision and latest release timestamp, with the identifier
  tie direction specified by the exact protocol or request.
- Inference: compute p-values and critical values with the requested Student-t
  degrees of freedom. If SciPy is available, use it; otherwise implement the
  needed distribution carefully or verify by an independent numerical method.
- Cluster CR1: form cluster scores from the model's transformed design and
  residuals, apply the finite-sample factor requested by the profile, and use
  `G - 1` degrees of freedom unless the request states otherwise.
- HC3: compute leverage on the weighted design for WLS models and use residual
  degrees of freedom `n - k`.
- Ridge and elastic-net fits: compute scaling from training data only; refit from
  scratch for every fold, deletion, penalty, source perturbation, or bootstrap
  sample unless the protocol explicitly says to reuse selected hyperparameters.
- PCA/clustering: rebuild standardization, orientation, initialization, and
  clustering inside every stability refit. Orient loadings so the earliest
  maximum-absolute loading is positive.
- Bootstrap streams: maintain one continuous PRNG stream, draw clusters in the
  registered order, and record checkpoints only after completing the replicate.
- Decisions: finish all modules first, evaluate gates on unrounded values, then
  apply the controlled decision precedence from the request/template.

## Output Discipline

Before finalizing, validate that:

- all top-level keys and required nested keys from the template are present;
- arrays have the requested lengths and order;
- JSON numbers are finite, with `null` only when the requested statistic is
  mathematically unavailable;
- booleans and integers are JSON native types, not strings;
- no explanatory text surrounds the JSON.
