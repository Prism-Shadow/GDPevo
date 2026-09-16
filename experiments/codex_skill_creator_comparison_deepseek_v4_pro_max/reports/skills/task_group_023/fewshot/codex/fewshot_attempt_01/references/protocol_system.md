# Protocol System

The PHO protocol system maps analysis requests to reusable method profiles
through case-sensitive protocol IDs and a deterministic override-resolution
mechanism.

## Protocol Registry Record

When a task's answer template expects a `protocol_registry_record` at the
top level, the output must include a `portable_protocol_profile` section.
This profile is optional solved-answer provenance only: it is not part of
the solver-visible input, is not expanded or required by the answer
template, and is ignored by the evaluator.

The protocol profile **applies method semantics** only. All instance-specific
content (entities, measures, years, geographic scope, random seeds,
hyperparameter grids, business cutoffs, output labels) binds exclusively
from the effective future analysis request.

## Protocol ID Matching

The analysis request carries a `protocol_id` string (e.g.,
`PHO_STATE_TRANSPORT_AUDIT_V1`, `PHO_COUNTY_MEDIATION_TRANSPORT_V1`,
`PHO_STATE_ROBUSTNESS_TRANSPORT_V1`, `PHO_COUNTY_PANEL_TRANSPORT_V1`).

The protocol registry record matches by **exact case-sensitive** comparison:

- `protocol_id` in request == `protocol_id` in profile: activate the profile.
- Family membership, similar names, or similar subject matter: **no match**.
- No `protocol_id` in request: no profile activation (use request as-is).

## Override Resolution

The protocol system merges a base method profile with overrides from the
analysis request to produce one effective contract. This contract is frozen
before any data access, random draw, fit, aggregation, or decision.

### Resolution Order

1. Verify the exact `protocol_id` match.
2. Start from the base method profile and any inherited canonical defaults
   for this exact protocol version.
3. Bind direct keys from the request: a direct root key `k` targets the
   canonical root key of the identical name. Inside a named canonical section
   or module, a direct child key targets only the identical child path.
4. Resolve override aliases:
   - `section_overrides` -> canonical `section` (strip `_overrides` suffix)
   - `module_overrides.<module_name>` -> canonical top-level module of that
     exact name
   - `reporting_overrides` -> reporting
5. Merge in request document order:
   - **Objects**: Recursively merge by exact key name. A key present in the
     request overrides that same key in the base.
   - **Arrays**: A request array replaces the base array in full. Never
     concatenate, union, or merge by position.
   - **Scalars/strings/booleans/null**: An explicit scalar replaces only its
     exact path.
   - **Absent keys**: Inherit unchanged from the base.
6. Freeze the resolved contract. Use it consistently across every module.

### Validation

Before any computation, validate the merged contract:

- **Reject** unknown override targets (keys that don't match any canonical path).
- **Reject** implicit aliases, renamed keys, or positional array patching.
- **Reject** type coercion between different types at the same path.
- **Task-local direct bindings and resolved overrides** take precedence over
  inherited values at the same path.

## Instance Boundary

The protocol profile classification is `REUSABLE_METHOD_ONLY`. This means:

**Method semantics** carried by the profile:
- Statistical algorithm specifications (formulas, steps, convergence criteria)
- PRNG algorithms (PCG32, xorshift32) and their mapping rules
- Inference formulas (HC3, CR1, jackknife, bootstrap-t, conformal)
- Jacobi eigendecomposition, k-means initialization, ARI computation
- Coordinate descent and soft-thresholding formulas
- GMM moment conditions and weighting logic
- Sensitivity surface formulas
- Override resolution rules

**Task-local content** binds from the future request only:
- Entity codes (state abbreviations, county FIPS, ISO3)
- Measure identifiers (life_expectancy, adult_obesity, poverty, etc.)
- Calendar years and geographic scope
- Release filters (FINAL, AGE_ADJUSTED, DIRECT_SURVEY, etc.)
- Random seeds and PRNG initialization values
- Replicate counts and checkpoint schedules
- Hyperparameter grids (lambda values, alpha, l1_ratio)
- Business cutoffs and decision rule strings
- Output vocabulary (classification labels)

## Module Execution Order

The protocol profile declares a `module_execution_order` array. Modules
execute in that exact order. Within each module, follow the reusable method
specification linked by the module name. The module name in the profile
matches the audit module name in the analysis request when both are present.

## Protocol Families

Three protocol families span the PHO audit space:

| Family | ID Prefix | Geography | Typical Outcome |
|--------|-----------|-----------|----------------|
| `PHO_STATE_ALGORITHMIC_TRANSPORT_FAMILY_V1` | `PHO_STATE_` | 50 states + DC | Life expectancy, diagnosed diabetes |
| `PHO_COUNTY_ALGORITHMIC_TRANSPORT_FAMILY_V1` | `PHO_COUNTY_` | Midwest/South or West/Northeast counties | Adult obesity, diabetes change |
| Country burden-stratification | `PHO_CBR_` | 48 fictional countries | Life expectancy |

Protocol family membership is **not** a match criterion. The family_id is
informational only; activation requires exact `protocol_id` match.

## Working Without a Protocol ID

When no `protocol_id` is present in the analysis request, or the ID does not
exactly match any known profile, use the analysis request directly as the
sole effective contract. Apply its declared modules, methods, cohorts, grids,
and business rules without any override resolution. The statistical modules
in `statistical_modules.md` still provide the reusable method semantics.
