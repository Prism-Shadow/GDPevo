---
name: pho-algorithmic-audits
description: "Solve Public Health Observatory Web-only portal tasks that provide analysis_request.json and answer_template.json and require publication/release resolution, cohort construction, registered statistical audit modules, transportability or robustness gates, and exact JSON-only answers. Use especially for exact protocol_id values PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, or country burden revision/PCA clustering audits."
---

# PHO Algorithmic Audits

Use this skill for Public Health Observatory tasks where the prompt names a read-only Web portal, an `analysis_request.json`, and an `answer_template.json`. Produce the final response as exactly one JSON object.

## Mandatory Workflow

1. Read the prompt, `analysis_request.json`, and `answer_template.json` completely.
2. Extract the effective portal base URL from the prompt. Fetch portal evidence only from that base URL. Start with `/catalog`, `/methodology`, and `/download` if available, then use the specific data endpoints needed for the request.
3. Resolve one effective request before any data access, fit, random draw, fold split, aggregation, or decision. If the request has a known `protocol_id`, read [protocols.md](references/protocols.md) and apply the exact matching profile only.
4. Use [computation.md](references/computation.md) for release resolution, missingness, modeling, resampling, conformal, PCA/clustering, perturbation, and controlled-decision rules.
5. Build a local calculation script or notebook in the task workspace when computations are nontrivial. Keep all intermediate values unrounded and round only when constructing the final JSON.
6. Validate the final object against `answer_template.json`: required keys, field names, list lengths, enum values, identifier spelling, ordering, numeric precision, integer/Boolean/null types, and cross-field cardinalities.
7. Return JSON only. Do not include explanatory text outside the object.

## Evidence Rules

- Treat the portal as the sole evidence source. Do not use web search or remembered values.
- Resolve health, socioeconomic, country indicator, geography, and revision records independently according to the effective request's filters and priority rules.
- Selected but suppressed, invalid, withdrawn, blank, or null analytical values are unavailable. Never zero-fill unavailable values.
- Preserve declared order exactly. Do not independently sort aligned coefficient, prediction, fold, loading, label, checkpoint, or perturbation arrays unless the template explicitly requests a set-like sorted list.
- Compute gates and classifications from unrounded values. Round only the reported JSON fields.
- Use JSON `null` only for mathematically unavailable requested statistics. Do not emit `NaN`, `Infinity`, or strings for numbers.

## Protocol Registry Output

For the exact registered protocol IDs documented in [protocols.md](references/protocols.md), it is acceptable to include a leading `protocol_registry_record.portable_protocol_profile` when the task format tolerates optional provenance. Keep it method-only:

- Include protocol identity, activation, override, instance-boundary, module order, and reusable method semantics.
- Do not include solved counts, coefficients, p-values, selected states, selected clusters, final decisions, or any other invocation-specific analytical values.
- If the future template or prompt explicitly rejects extra keys, omit the registry record and still apply the matching method profile internally.

## Portal Endpoints

Expected PHO portal paths include:

- `/catalog`
- `/methodology`
- `/download`
- `/geographies/states`
- `/geographies/counties`
- `/geographies/countries`
- `/data/state-health`
- `/data/state-socioeconomic`
- `/data/county-health`
- `/data/county-socioeconomic`
- `/data/country-indicators`
- `/data/revisions`

Inspect `/catalog` and `/methodology` before assuming schemas. Prefer `/download` for a complete local snapshot when it exists, then load the downloaded JSON/CSV files with stable parsers.

## Output Discipline

Use the answer template as the response contract, not as pseudocode. Replace descriptors with values, omit template instruction fields, and keep natural JSON types. For "exactly" or "only" wording, do not add unrequested analytical keys except the optional method-only registry record for known protocols as described above.
