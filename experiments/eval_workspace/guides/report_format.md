# Report Format

The formal evaluation report is a YAML file. Each task group has one report.

Write the report inside the workspace:

```text
eval_workspace/report/<task_group_id>.yaml
```

## YAML Format

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id>
model: <model_name_or_config>
harness: <evaluation_harness, e.g. codex>

conditions:
  no_skill:
    overall_avg_at_3: <float>
    efficiency:
      cached_input_tokens_avg_3: <float or null>
      input_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      seconds_avg_3: <float or null>
    tasks:
      test_001:
        scores:
          - <float>
          - <float>
          - <float>
        avg_at_3: <float>
        cached_input_tokens_avg_3: <float or null>
        input_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        seconds_avg_3: <float or null>
      test_002:
        <same shape as test_001>
      test_003:
        <same shape as test_001>
      test_004:
        <same shape as test_001>
      test_005:
        <same shape as test_001>
  demonstration_skill:
    skill_dirs:
      attempt_01: skills/<task_group_id>/demonstration_skill/demonstration_skill_attempt_01
      attempt_02: skills/<task_group_id>/demonstration_skill/demonstration_skill_attempt_02
      attempt_03: skills/<task_group_id>/demonstration_skill/demonstration_skill_attempt_03
    overall_avg_at_3: <float>
    efficiency: <same shape as no_skill.efficiency>
    tasks: <same shape as no_skill.tasks>
  reflection_skill:
    skill_dirs:
      attempt_01: skills/<task_group_id>/reflection_skill/reflection_skill_attempt_01
      attempt_02: skills/<task_group_id>/reflection_skill/reflection_skill_attempt_02
      attempt_03: skills/<task_group_id>/reflection_skill/reflection_skill_attempt_03
    overall_avg_at_3: <float>
    efficiency: <same shape as no_skill.efficiency>
    tasks: <same shape as no_skill.tasks>
```

## Requirements

- Keep reasonable decimal precision for `overall_avg_at_3` and each `avg_at_3`; 4 decimal places is recommended.
- Follow the YAML shape above: keep top-level strings unquoted unless YAML requires quotes, and write `scores` as a block list with one score per line.
- `scores` must preserve the 3 raw run scores, not only the average.
- `skill_dirs` is only used for skill conditions. Paths are relative to the directory containing the report YAML, and `attempt_01` / `attempt_02` / `attempt_03` must match the solver attempt number that used that skill.
- `cached_input_tokens_avg_3`, `input_tokens_avg_3`, `output_tokens_avg_3`, and `seconds_avg_3` come from the Codex session traces for the 3 attempts. If the trace cannot be matched uniquely, write `null` and preserve the trace issue in the corresponding workspace run record.
- `conditions.<mode>.efficiency.*_avg_3` is the average efficiency summary across all test tasks for that mode.
- Efficiency metrics follow the same aggregation shape as `avg@3`: average the 3 attempts for the same test task, then average the 5 test tasks.
- Efficiency metrics only count answer-writing by test solver subagents. Do not include skill generation, environment startup, evaluator execution, or main-agent summarization.
