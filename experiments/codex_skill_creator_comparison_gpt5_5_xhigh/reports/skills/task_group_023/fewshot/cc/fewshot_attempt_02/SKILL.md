---
name: public-health-observatory-audits
description: Use this skill for Public Health Observatory tasks that require solving registered state, county, or country audit analyses from a read-only PHO Web portal and returning a strict JSON answer_template result. Trigger on prompts mentioning PHO, Public Health Observatory, protocol_id values such as PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, or country burden revision audits, especially when the task asks for publication/cohort resolution, jackknife, nested ridge or elastic-net, wild bootstrap, grouped conformal calibration, PCA clustering, source perturbation, or controlled decisions.
---

# Public Health Observatory Audits

Use this skill to solve PHO audit prompts from the supplied portal and payload files. The task is usually graded as exact structured data, so prioritize deterministic evidence resolution, declared ordering, unrounded internal calculations, and exact JSON shape over narrative explanation.

## First Pass

1. Read the user's prompt, `analysis_request.json`, and `answer_template.json`.
2. Extract the portal base URL from the prompt. Do not hardcode a training URL.
3. Identify the workflow:
   - If `analysis_request.json` has a recognized `protocol_id`, read `references/protocol-workflows.md` and use only that exact protocol profile.
   - If there is no recognized `protocol_id` but the template is a country burden revision audit, read the country workflow in `references/protocol-workflows.md`.
   - For formulas, tie-breaking, PRNGs, PCA, clustering, and validation, read `references/statistical-methods.md`.
4. Resolve one effective request before fetching or computing data. Apply any direct keys and `_overrides` sections to the exact canonical target; deep-merge objects, replace arrays whole, replace scalars exactly, and reject unknown targets or type coercions.
5. Fetch portal evidence, preferably with CSV downloads:
   ```bash
   python skill/scripts/pho_snapshot.py "$TASK_ENV_BASE_URL" ./pho_snapshot
   ```
   The script saves only authorized public portal datasets. If the skill is installed elsewhere, use the installed skill path for the script.
6. Compute every requested module, even if an early gate fails. Evaluate decisions only after all module evidence is complete.
7. Build exactly the JSON object described by `answer_template.json`. Do not add `protocol_registry_record` or provenance keys unless the template explicitly requires them.
8. Validate the top-level shape before final submission:
   ```bash
   python skill/scripts/check_answer_shape.py answer_template.json answer.json
   ```

## Evidence Rules

- Use only the portal and local payloads authorized by the task.
- Resolve releases independently for each declared entity, year, measure, value type, source, and release status.
- Suppressed, invalid, withdrawn, blank, null, or scale-break values are unavailable analytic values. Never zero-fill them.
- Count publication records before analytic completeness exclusions only when the request asks for publication counts.
- Preserve every declared order: years, variables, features, states, counties, countries, divisions, folds, grids, checkpoints, source groups, scenarios, and output keys.
- Keep aligned arrays aligned. Never sort one aligned value array independently from its identifier array.
- Use unrounded values for fitting, inference, tie-breaking, gates, and decisions. Round only at final JSON serialization to the precision declared by the request or template.
- Use JSON `null` only for a mathematically unavailable requested statistic. Do not output `NaN`, `Infinity`, strings for numbers, or strings for booleans.

## Output Discipline

Return only the final JSON object. If you need intermediate files, keep them local and do not mention them in the final answer. Match the template's enum strings and boolean types exactly. When a template says "exactly" the required top-level keys, omit any optional notes, registry records, debug summaries, or extra provenance.

## Portable Helpers

- `scripts/pho_snapshot.py`: downloads the portal CSV datasets into a local directory and writes a manifest.
- `scripts/check_answer_shape.py`: checks JSON parseability and basic top-level/template key presence.

These helpers are deterministic and contain no task-specific solved values. They do not replace the statistical workflow; use them to avoid transcription and shape mistakes.
