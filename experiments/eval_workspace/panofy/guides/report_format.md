# Report Format

The formal evaluation report is a YAML file. Each task group has one report:

```text
report/<task_group_id>.yaml
```

## YAML Format

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id or null>
model: <model_id, e.g. PANOFY_PRO>
harness: panofy

conditions:
  base:
    overall_avg_at_3: <float>
    efficiency:
      cache_read_tokens_avg_3: <float or null>
      cache_write_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      points_consumed_avg_3: <float or null>
    tasks:
      test_001:
        scores:
          - <float>
          - <float>
          - <float>
        avg_at_3: <float>
        cache_read_tokens_avg_3: <float or null>
        cache_write_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        points_consumed_avg_3: <float or null>
      test_002:
        <same shape as test_001>
      test_003:
        <same shape as test_001>
      test_004:
        <same shape as test_001>
      test_005:
        <same shape as test_001>
  demo:
    agents:
      attempt_01: <agent_id>
      attempt_02: <agent_id>
      attempt_03: <agent_id>
    overall_avg_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  reflect:
    agents:
      attempt_01: <agent_id>
      attempt_02: <agent_id>
      attempt_03: <agent_id>
    overall_avg_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>

accuracy_lift_vs_base:
  demo: <float>
  reflect: <float>
```

## Requirements

- Keep reasonable decimal precision for `overall_avg_at_3` and each `avg_at_3`;
  4 decimal places is recommended.
- `scores` must contain all 3 raw run scores (one per attempt). Write it as a
  block list with one score per line.
- `agents` is only used for evolve conditions. It maps `attempt_<nn>` to the
  trained agent that answered that attempt — the same agent index used at train
  and predict time.
- The three token buckets (`cache_read_tokens`, `cache_write_tokens`,
  `output_tokens`) and `points_consumed_avg_3` come from each attempt's
  `run_metadata.yaml` (SDK `run.usage` + `run.points_consumed`). If any attempt
  is missing a value, write the average as `null`.
- `conditions.<mode>.efficiency.*_avg_3` is the average across the 5 test tasks
  for that mode. Efficiency follows the same aggregation shape as `avg@3`:
  average the 3 attempts for one test task, then average the 5 test tasks.
- Efficiency metrics only count test-task `predict()` work. Do not include
  training, environment startup, or evaluator execution.
- `accuracy_lift_vs_base` is each evolve condition's overall `avg@3` minus the
  `base` overall `avg@3`.
