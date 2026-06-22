# 报告格式

正式评估报告是一个 YAML 文件：

```text
report/<task_group_id>.yaml
```

## YAML 格式

四种条件使用同一 task 结构：

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
      test_002: <same shape as test_001>
      test_003: <same shape as test_001>
      test_004: <same shape as test_001>
      test_005: <same shape as test_001>
  fewshot:
    overall_acc_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  self:
    overall_acc_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
  reflect-3:
    overall_acc_at_3: <float>
    efficiency: <same shape as base.efficiency>
    tasks: <same shape as base.tasks>
```

## 要求

- `overall_acc_at_3` 和每个 `acc_at_3` 保留合理小数位；建议 4 位。
- `scores` 必须保留 3 个原始 run 分数。
- 三桶 token 来自每次 attempt 的 `run_metadata.yaml` SDK usage。若任一
  attempt 缺值，该平均写 `null`。
- `cost_usd_avg_3` 根据平均 token buckets 和模型价格推导。
- 效率指标遵循与 `acc@3` 相同的聚合方式：先对同一 test task 的 3 次
  attempts 取平均，再对 5 个 test tasks 取平均。
- 效率指标只统计 test-task 的 `predict()` 工作。不包含训练、远程环境检查或
  evaluator 执行。
