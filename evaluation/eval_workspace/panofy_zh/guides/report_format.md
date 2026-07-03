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

## 要求

- `overall_acc_at_3`、`overall_std_at_3`、每个 `acc_at_3` 和
  `std_at_3` 保留合理小数位；建议 4 位。
- `scores` 必须保留 3 个原始 run 分数。
- `std_at_3` 是同一 test task 三次原始分数的 population std；
  `overall_std_at_3` 是 5 个 test-task `std_at_3` 的平均值。
- `rounds_avg_3` 在实验后已有打包 Panofy 服务日志时，统计 solver 的
  assistant/model-response turns。如果生成报告时没有可用日志包，turn 字段写
  `null`。
- 三桶 token 来自每次 attempt 的 `run_metadata.yaml` SDK usage。若任一
  attempt 缺值，该平均写 `null`。
- 效率指标遵循与 `acc@3` 相同的聚合方式：先对同一 test task 的 3 次
  attempts 取平均，再对 5 个 test tasks 取平均。
- 效率指标只统计 test-task 的 `predict()` 工作。不包含训练、远程环境检查或
  evaluator 执行。
- 如果任何 test attempt 因访问或泄漏禁止材料而污染，应将其排除出 report
  分数和聚合。污染原因与替代 attempt 记录在对应 run record 中，不写入正式
  report YAML。
