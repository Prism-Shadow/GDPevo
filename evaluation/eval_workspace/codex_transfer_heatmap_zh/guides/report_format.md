# Report Format

每个非对角线矩阵单元格写一个 YAML：

```text
report/cells/<mode>/<source_task_group_id>__to__<target_task_group_id>.yaml
```

示例：

```yaml
mode: fewshot
harness: codex
model: GPT-5.5
reasoning_effort: xhigh
source_task_group_id: task_group_002
source_label: CRM
target_task_group_id: task_group_006
target_label: ERP
skill_dirs:
  attempt_01: ../../../skills/fewshot/task_group_002/fewshot_attempt_01
  attempt_02: ../../../skills/fewshot/task_group_002/fewshot_attempt_02
  attempt_03: ../../../skills/fewshot/task_group_002/fewshot_attempt_03
tasks:
  test_001:
    scores:
      - 0.0
      - 0.0
      - 0.0
    acc_at_3: 0.0
    std_at_3: 0.0
    attempt_dirs:
      attempt_01: ../../../runs/fewshot/task_group_002__to__task_group_006/test_001/attempt_01
      attempt_02: ../../../runs/fewshot/task_group_002__to__task_group_006/test_001/attempt_02
      attempt_03: ../../../runs/fewshot/task_group_002__to__task_group_006/test_001/attempt_03
    trace_dirs:
      attempt_01: ../../../original_traces/fewshot/task_group_002__to__task_group_006/test_001/attempt_01
      attempt_02: ../../../original_traces/fewshot/task_group_002__to__task_group_006/test_001/attempt_02
      attempt_03: ../../../original_traces/fewshot/task_group_002__to__task_group_006/test_001/attempt_03
  test_002:
    scores: [0.0, 0.0, 0.0]
    acc_at_3: 0.0
    std_at_3: 0.0
  test_003:
    scores: [0.0, 0.0, 0.0]
    acc_at_3: 0.0
    std_at_3: 0.0
  test_004:
    scores: [0.0, 0.0, 0.0]
    acc_at_3: 0.0
    std_at_3: 0.0
  test_005:
    scores: [0.0, 0.0, 0.0]
    acc_at_3: 0.0
    std_at_3: 0.0
cell_acc_at_3: 0.0
cell_std_at_3: 0.0
excluded_attempts: []
notes: []
```

要求：

- `scores` 必须保留 3 个原始 attempt score。
- `scores` 的 3 个值必须分别来自 3 个独立 skill。
- `trace_dirs` 如存在，应指向同一批 attempts 复制进工作区的 Codex 原始 trace。
- `cell_acc_at_3` 和 `cell_std_at_3` 可以由脚本重新计算；如果手写，仍应与
  `tasks` 中的 raw scores 一致。
- 污染 attempt 不进入 `scores`；需要在新的 clean attempt 中补齐 3 个有效 score。

聚合脚本会读取这些 cell reports，并生成：

```text
report/matrix.yaml
report/matrix.json
heatmaps/data/matrices.json
heatmaps/data/<mode>_matrix.csv
heatmaps/index.html
```
