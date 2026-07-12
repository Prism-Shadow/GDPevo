# Claude Code Evolve Metrics Design

## Scope

Update the following evaluation workspaces:

- `claude_code`
- `claude_code_zh`
- `claude_code_glm_5_2`
- `claude_code_kimi2_6`
- `claude_code_deepseek_v4_pro`

Do not change the Panofy or cross-task transfer heatmap workspaces.

## Behavior

For every `fewshot`, `self`, and `reflect-3` skill-generation attempt:

1. Run Claude Code with a dedicated mounted `CLAUDE_CONFIG_DIR` and unique session ID.
2. Preserve the complete Claude Code session JSONL under
   `original_traces/skill_generation/<condition>/attempt_<nn>/`.
3. Write `evolve_metadata.yaml` under the matching directory in
   `scratch/skill_generation/`.
4. Read token buckets from the session trace using the workspace's existing
   provider-specific deduplication rules.
5. Calculate USD cost using the model pricing already defined for that
   workspace. Missing trace fields remain `null` and are not inferred.

## Report Contract

Add an `evolve` block to each report schema. It records all three attempts for
each non-base mode, including metadata and trace paths, token buckets, total
tokens, and cost. Its summary keeps the per-bucket token averages and average
cost across the three skill-generation attempts, matching solver report
granularity without duplicating per-bucket totals.

Solver token, cost, turn, and tool-call metrics retain their current meaning and
aggregation rules. Skill-generation usage must not be mixed into solver
efficiency fields.

## Files

Within each scoped workspace, align these files where present:

- `CODEX_ORCHESTRATOR.md`
- `README.md`
- `guides/workflow.md`
- `guides/metric_and_scoring.md`
- `guides/report_format.md`

The English and Chinese generic Claude Code workspaces must remain equivalent
translations. Model-specific workspaces retain their existing execution and
pricing details.

## Validation

- Verify all five workspaces require complete skill-generation session traces.
- Verify all five report schemas contain the same evolve-attempt and aggregate
  structure, with provider-specific token names where required.
- Verify no files under Panofy or transfer heatmap workspaces change.
- Scan for contradictory instructions that exclude skill generation from all
  token/cost reporting.
