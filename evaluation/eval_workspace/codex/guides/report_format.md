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
model: <model_name_or_config>
harness: codex

evolve:
  pricing:
    basis: standard_api_text_token_equivalent
    uncached_input_usd_per_million: 5.00
    cached_input_usd_per_million: 0.50
    output_usd_per_million: 30.00
  conditions:
    fewshot:
      attempts:
        attempt_01:
          metadata_file: ../scratch/skill_generation/fewshot_attempt_01/evolve_metadata.yaml
          trace_file: <path under ../original_traces/skill_generation/fewshot/attempt_01/ or null>
          input_tokens: <int or null>
          cached_input_tokens: <int or null>
          output_tokens: <int or null>
          reasoning_output_tokens: <int or null>
          total_tokens: <int or null>
          cost_usd: <float or null>
        attempt_02: <same shape as attempt_01>
        attempt_03: <same shape as attempt_01>
      summary:
        input_tokens_avg_3: <float or null>
        cached_input_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        reasoning_output_tokens_avg_3: <float or null>
        cost_usd_avg_3: <float or null>
    self: <same shape as fewshot>
    reflect-3: <same shape as fewshot>

conditions:
  base:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency:
      cached_input_tokens_avg_3: <float or null>
      input_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      rounds_avg_3: <float or null>
      tool_calls_avg_3: <float or null>
    tasks:
      test_001:
        scores:
          - <float>
          - <float>
          - <float>
        acc_at_3: <float>
        std_at_3: <float>
        cached_input_tokens_avg_3: <float or null>
        input_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        rounds_avg_3: <float or null>
        tool_calls_avg_3: <float or null>
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
- `rounds_avg_3` counts solver assistant/model-response turns; `tool_calls_avg_3` counts solver tool-call requests. At the task level, average the 3 attempts for the same test task; at the condition efficiency level, average the 5 test tasks. If a formal attempt trace cannot be matched, write the corresponding field as `null` and preserve the reason in the corresponding run record.
- `skill_dirs` is only used for non-base conditions. Paths are relative to the
  directory containing the report YAML, and attempt numbers must match the solver
  attempt number that used that skill.
- Token fields come from the Codex session traces copied under
  `original_traces/`. If a trace cannot be matched uniquely, write `null` and
  preserve the trace issue in the corresponding run record.
- `evolve` contains only skill-generation usage for the three non-base modes.
  Preserve all 3 attempt records and their complete raw trace paths. The summary
  retains the arithmetic `avg_3` for every token bucket and for USD cost.
- Calculate evolve cost with the pricing block recorded in the report. Cached
  input is a subset of input, and reasoning output is a subset of output; do not
  double-count either field.
- Efficiency metrics follow the same aggregation shape as `acc@3`: average the
  3 attempts for the same test task, then average the 5 test tasks.
- Efficiency metrics only count answer-writing by test solver subagents. Do not
  include skill generation, remote environment checks, evaluator execution, or
  main-agent summarization.
- If any test attempt was contaminated by forbidden material access or leakage,
  exclude it from report scores and aggregation. Preserve the contamination
  reason and replacement attempt in the corresponding run record instead of the
  formal report YAML.
