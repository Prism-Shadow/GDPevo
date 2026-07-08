# Report Format

Write one YAML file per off-diagonal matrix cell:

```text
report/cells/<mode>/<source_task_group_id>__to__<target_task_group_id>.yaml
```

Example:

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

Requirements:

- `scores` must preserve the 3 raw attempt scores.
- The 3 values in `scores` must come from 3 independent skills.
- `trace_dirs`, when present, point to the copied raw Codex traces for the same
  attempts.
- `cell_acc_at_3` and `cell_std_at_3` may be recomputed by the build script. If
  they are written manually, they must remain consistent with the raw scores in
  `tasks`.
- Contaminated attempts must not enter `scores`; rerun in a clean attempt
  directory until there are 3 valid scores.

The build script reads these cell reports and creates:

```text
report/matrix.yaml
report/matrix.json
heatmaps/data/matrices.json
heatmaps/data/<mode>_matrix.csv
heatmaps/index.html
```
