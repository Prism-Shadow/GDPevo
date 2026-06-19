# 报告格式

正式评估报告是一个 YAML 文件。每个 task group 一份报告：

```text
report/<task_group_id>.yaml
```

## YAML 格式

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id or null>
model: <model_id, e.g. claude-opus-4-6>
harness: panofy

conditions:
  base:
    overall_acc_at_3: <float>
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
        acc_at_3: <float>
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
    overall_acc_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  reflect:
    overall_acc_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>

```

## 要求

- `overall_acc_at_3` 和每个 `acc_at_3` 保留合理小数位；建议 4 位。
- `scores` 必须保留 3 个原始 run 分数，而不只是平均值。写成块状列表，每行一个分数。
- 三桶 token（`cache_read_tokens`、`cache_write_tokens`、`output_tokens`）来自每次 attempt 的 `run_metadata.yaml`（SDK 的 `run.usage`）。若任一 attempt 缺值，该平均写 `null`。
- `cost_usd_avg_3` 根据三个平均 token 桶以及模型的 5-minute cache write、cache hit、output token 价格计算：

```text
cost_USD_avg_3 =
  (cache_write_tokens_avg_3 * cache_write_5m_price
   + cache_read_tokens_avg_3 * cache_hit_price
   + output_tokens_avg_3 * output_price) / 1_000_000
```
- `conditions.<mode>.efficiency.*_avg_3` 是该 mode 下 5 个 test tasks 的平均。效率遵循与 `acc@3` 相同的聚合形状：先对同一 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。
- 效率指标只统计 test-task 的 `predict()` 工作。不含训练、环境启动或 evaluator 执行。
