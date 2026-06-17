# Report Format

The formal evaluation report is a YAML file. Each task group has one report:

```text
report/<task_group_id>.yaml
```

## YAML Format

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id or null>
model: <model_id, e.g. claude-opus-4-6>
harness: panofy

conditions:
  base:
    overall_avg_at_3: <float>
    efficiency:
      cache_read_tokens_avg_3: <float or null>
      cache_write_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      cost_usd_avg_3: <float or null>
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
        cost_usd_avg_3: <float or null>
      test_002:
        <same shape as test_001>
      test_003:
        <same shape as test_001>
      test_004:
        <same shape as test_001>
      test_005:
        <same shape as test_001>
  demo:
    overall_avg_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  reflect:
    overall_avg_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>

```

## Requirements

- Keep reasonable decimal precision for `overall_avg_at_3` and each `avg_at_3`;
  4 decimal places is recommended.
- `scores` must contain all 3 raw run scores (one per attempt). Write it as a
  block list with one score per line.
- The three token buckets (`cache_read_tokens`, `cache_write_tokens`,
  `output_tokens`) come from each attempt's `run_metadata.yaml` SDK `run.usage`.
  If any attempt is missing a value, write the average as `null`.
- `cost_usd_avg_3` is derived from the three averaged token buckets using the
  model prices for 5-minute cache writes, cache hits, and output tokens:

```text
cost_USD_avg_3 =
  (cache_write_tokens_avg_3 * cache_write_5m_price
   + cache_read_tokens_avg_3 * cache_hit_price
   + output_tokens_avg_3 * output_price) / 1_000_000
```
- `conditions.<mode>.efficiency.*_avg_3` is the average across the 5 test tasks
  for that mode. Efficiency follows the same aggregation shape as `avg@3`:
  average the 3 attempts for one test task, then average the 5 test tasks.
- Efficiency metrics only count test-task `predict()` work. Do not include
  training, environment startup, or evaluator execution.
