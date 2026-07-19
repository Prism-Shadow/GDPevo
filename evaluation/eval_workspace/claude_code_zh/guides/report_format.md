# Report Format

正式评估报告是一个 YAML 文件：

```text
report/<task_group_id>.yaml
```

## YAML 格式

四种条件使用同一 task 结构：

```yaml
task_group_id: <task_group_id>
scenario_id: <scenario_id>
model: <model_name_or_config>
harness: claude_code

evolve:
  pricing:
    basis: claude_opus_4_8_api
    input_usd_per_million: 5.00
    cache_creation_usd_per_million: 6.25
    cache_read_usd_per_million: 0.50
    output_usd_per_million: 25.00
  conditions:
    fewshot:
      attempts:
        attempt_01:
          input_tokens: <int or null>
          cache_creation_tokens: <int or null>
          cache_read_tokens: <int or null>
          output_tokens: <int or null>
          total_tokens: <int or null>
          cost_usd: <float or null>
        attempt_02: <same shape as attempt_01>
        attempt_03: <same shape as attempt_01>
      summary:
        input_tokens_avg_3: <float or null>
        cache_creation_tokens_avg_3: <float or null>
        cache_read_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        cost_usd_avg_3: <float or null>
    self: <same shape as fewshot>
    reflect-3: <same shape as fewshot>

conditions:
  base:
    overall_acc_at_3: <float>
    overall_std_at_3: <float>
    efficiency:
      input_tokens_avg_3: <float or null>
      cache_creation_tokens_avg_3: <float or null>
      cache_read_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      cost_usd_avg_3: <float or null>
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
        input_tokens_avg_3: <float or null>
        cache_creation_tokens_avg_3: <float or null>
        cache_read_tokens_avg_3: <float or null>
        output_tokens_avg_3: <float or null>
        cost_usd_avg_3: <float or null>
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

## 要求

- `overall_acc_at_3`、`overall_std_at_3`、每个 `acc_at_3` 和
  `std_at_3` 保留合理小数精度；推荐 4 位。
- `scores` 必须保留 3 次原始运行分数，不能只保留平均值。
- `std_at_3` 是同一 test task 三次原始分数的 population std；
  `overall_std_at_3` 是 5 个 test-task `std_at_3` 的平均值。
- `rounds_avg_3` 统计 solver 的 assistant/model-response turns；`tool_calls_avg_3` 统计 solver 发起的工具调用次数。两者在 task 层面先对同一 test task 的 3 次 attempts 取平均，condition 层面再对 5 个 test tasks 取平均。若某个正式 attempt 的 trace 不能匹配，对应字段写 `null`，并在对应 run record 中保留原因。
- `skill_dirs` 只用于非 base 条件。路径相对于 report YAML 所在目录，attempt
  编号必须和使用该 skill 的 solver attempt 编号一致。
- Token 字段来自直接复制到对应
  `original_traces/.../attempt_<nn>/` 目录、并按 `message.id` 去重后的 Claude Code
  主 session JSONL。如果 session trace 缺失，应写 `null`，并在对应 run record
  中保留问题。
- `evolve` 只记录三个非 base 模式的 skill-generation 用量。保留 3 次 attempt
  的 token 和费用记录。metadata 和原始 trace 路径仅保留在工作区审计文件中，
  不写入正式 report；summary 保留每个 token bucket 和美元费用的三次
  算术平均值。
- Evolve 费用使用 report 中记录的 pricing 区块计算。Claude 的四个 token 桶互不
  重叠，各计费一次。
- 效率指标和 `acc@3` 使用相同聚合方式：先对同一个 test task 的 3 次
  attempts 取平均，再对 5 个 test tasks 取平均。
- `cost_usd_avg_3` 使用 `evolve.pricing` 中记录的同一模型费率，并采用相同的
  task 后 condition 两级聚合方式。
- 效率指标只统计 test solver runs 写答案的过程。不要包含 skill
  generation、环境检查、evaluator 执行或主 agent 汇总。
- 如果任何 test attempt 因访问或泄漏禁止材料而污染，应将其排除出 report
  分数和聚合。污染原因与替代 attempt 记录在对应 run record 中，不写入正式
  report YAML。
