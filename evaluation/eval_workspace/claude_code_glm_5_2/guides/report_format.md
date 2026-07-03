# Report Format

The formal evaluation report is a YAML file:

```text
report/<task_group_id>.yaml
```

## YAML Format

Use the same task shape for all four conditions:

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id>
model: glm-5.2, max
harness: claude_code

conditions:
  base:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency:
      input_tokens_avg_3: <float or null>
      cache_creation_tokens_avg_3: <float or null>
      cache_read_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      rounds_avg_3: <float or null>
    tasks:
      test_001:
        scores:
          - <float>
          - <float>
          - <float>
        acc_at_3: <float>
        std_at_3: <float>
        input_tokens_avg_3: <float or null>
        cache_creation_tokens_avg_3: <float or null>
        cache_read_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        rounds_avg_3: <float or null>
      test_002: <same shape as test_001>
      test_003: <same shape as test_001>
      test_004: <same shape as test_001>
      test_005: <same shape as test_001>
  fewshot:
    skill_dirs:
      attempt_01: ../skills/fewshot/fewshot_attempt_01
      attempt_02: ../skills/fewshot/fewshot_attempt_02
      attempt_03: ../skills/fewshot/fewshot_attempt_03
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  self:
    skill_dirs:
      attempt_01: ../skills/self/self_attempt_01
      attempt_02: ../skills/self/self_attempt_02
      attempt_03: ../skills/self/self_attempt_03
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  reflect-3:
    skill_dirs:
      attempt_01: ../skills/reflect-3/reflect-3_attempt_01
      attempt_02: ../skills/reflect-3/reflect-3_attempt_02
      attempt_03: ../skills/reflect-3/reflect-3_attempt_03
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
```

## Requirements

- Keep reasonable decimal precision for `overall_acc_at_3`,
  `overall_std_at_3`, each `acc_at_3`, and each `std_at_3`; 4 decimal
  places is recommended.
- `scores` must preserve the 3 raw run scores, not only the average.
- `std_at_3` is the population standard deviation of the 3 raw scores for
  one test task. `overall_std_at_3` is the average of the 5 test-task
  `std_at_3` values.
- `rounds_avg_3` counts solver assistant/model-response turns. At the task level, average the 3 attempts for the same test task; at the condition `efficiency.rounds_avg_3` level, average the 5 test tasks. If a formal attempt trace cannot be matched, write the turn field as `null` and preserve the reason in the corresponding run record.
- `skill_dirs` is only used for non-base conditions. Paths are relative to the
  directory containing the report YAML, and attempt numbers must match the solver
  attempt number that used that skill.
- Token fields come from the deduped Claude Code subagent transcripts copied
  under `original_traces/`. If a transcript cannot be matched uniquely, write
  `null` and preserve the issue in the corresponding run record.
- If the GLM trace does not expose a token bucket directly, keep that field
  `null` instead of inferring it from another provider-specific field.
- Efficiency metrics follow the same aggregation shape as `acc@3`: average the
  3 attempts for the same test task, then average the 5 test tasks.
- Efficiency metrics only count answer-writing by test solver subagents. Do not
  include skill generation, remote environment checks, evaluator execution, or
  main-agent summarization.
- If any test attempt was contaminated by forbidden material access or leakage,
  exclude it from report scores and aggregation. Preserve the contamination
  reason and replacement attempt in the corresponding run record instead of the
  formal report YAML.
