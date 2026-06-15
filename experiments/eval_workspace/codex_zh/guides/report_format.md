# Report Format

正式评估报告是一个 YAML 文件。每个 task group 对应一个 report。

在 workspace 内将报告写入：

```text
report/<task_group_id>.yaml
```

## YAML 格式

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
      attempt_01: ../skills/demonstration_skill/demonstration_skill_attempt_01
      attempt_02: ../skills/demonstration_skill/demonstration_skill_attempt_02
      attempt_03: ../skills/demonstration_skill/demonstration_skill_attempt_03
    overall_avg_at_3: <float>
    efficiency: <same shape as no_skill.efficiency>
    tasks: <same shape as no_skill.tasks>
  reflection_skill:
    skill_dirs:
      attempt_01: ../skills/reflection_skill/reflection_skill_attempt_01
      attempt_02: ../skills/reflection_skill/reflection_skill_attempt_02
      attempt_03: ../skills/reflection_skill/reflection_skill_attempt_03
    overall_avg_at_3: <float>
    efficiency: <same shape as no_skill.efficiency>
    tasks: <same shape as no_skill.tasks>
```

## 要求

- `overall_avg_at_3` 和每个 `avg_at_3` 保留合理小数精度；推荐 4 位小数。
- 遵循上面的 YAML 结构：顶层字符串在 YAML 不要求时不加引号，`scores` 写成 block list，每行一个分数。
- `scores` 必须保留 3 次原始运行分数，不能只保留平均值。
- `skill_dirs` 只用于 skill 条件。路径相对于 report YAML 所在目录，且 `attempt_01` / `attempt_02` / `attempt_03` 必须和使用该 skill 的 solver attempt 编号一致。
- `cached_input_tokens_avg_3`、`input_tokens_avg_3`、`output_tokens_avg_3` 来自 3 次 attempts 的 Codex session traces。如果 trace 不能被唯一匹配，应写 `null`，并在对应 workspace run record 中保留 trace 问题。
- `conditions.<mode>.efficiency.*_avg_3` 是该模式下所有 test tasks 的平均效率汇总。
- 效率指标和 `avg@3` 使用相同聚合方式：先对同一个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。
- 效率指标只统计 test solver subagents 写答案的过程。不要包含 skill 生成、环境启动、evaluator 执行或主 agent 汇总。
