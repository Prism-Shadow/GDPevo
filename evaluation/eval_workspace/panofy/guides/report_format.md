# Report Format

The formal evaluation report is a YAML file:

```text
report/<task_group_id>.yaml
```

## YAML Format

Use the same task shape for all four conditions:

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id or null>
model: <model_id, e.g. claude-opus-4-6>
harness: panofy

conditions:
  base:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency:
      cache_read_tokens_avg_3: <float or null>
      cache_write_tokens_avg_3: <float or null>
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
        cache_read_tokens_avg_3: <float or null>
        cache_write_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        rounds_avg_3: <float or null>
      test_002: <same shape as test_001>
      test_003: <same shape as test_001>
      test_004: <same shape as test_001>
      test_005: <same shape as test_001>
  fewshot:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  self:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  reflect-3:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
```

## Requirements

- Keep reasonable decimal precision for `overall_acc_at_3`,
  `overall_std_at_3`, each `acc_at_3`, and each `std_at_3`; 4 decimal
  places is recommended.
- `scores` must contain all 3 raw run scores.
- `std_at_3` is the population standard deviation of the 3 raw scores for
  one test task. `overall_std_at_3` is the average of the 5 test-task
  `std_at_3` values.
- `rounds_avg_3` counts solver assistant/model-response turns. At the task level, average the 3 attempts for the same test task; at the condition `efficiency.rounds_avg_3` level, average the 5 test tasks. If a formal attempt trace cannot be matched, write the turn field as `null` and preserve the reason in the corresponding run record.
- The three token buckets come from each attempt's `run_metadata.yaml` SDK
  usage. If any attempt is missing a value, write the average as `null`.
- Efficiency follows the same aggregation shape as `acc@3`: average the 3
  attempts for one test task, then average the 5 test tasks.
- Efficiency metrics only count test-task `predict()` work. Do not include
  training, remote environment checks, or evaluator execution.
- If any test attempt was contaminated by forbidden material access or leakage,
  exclude it from report scores and aggregation. Preserve the contamination
  reason and replacement attempt in the corresponding run record instead of the
  formal report YAML.
