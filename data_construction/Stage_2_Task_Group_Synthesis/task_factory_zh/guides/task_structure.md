# 任务结构

## 输入

每次构造读取一个 scenario。该 scenario 应包含若干 examples，且每个 example 都应包含：

- `example_id`
- `source`
- `prompt`
- `notes`
- `attachments`

这些 examples 用于定义 task group 的任务复杂度、业务背景、数据类型和长程工作强度。task group 不能只复刻 examples，而应从 examples 中抽象出可迁移的场景经验和 SOP。

## 输出目录

`task_factory/task_group/<task_group_id>/` 应包含：

完整 task group 应包含 5 个 train tasks 和 5 个 test tasks。

```text
task_group_001/
├── task_group.yaml
├── env/
│   ├── setup.sh
│   ├── judge_api.py
│   ├── endpoints.txt
│   └── <共享业务服务、数据、setup 文件和支持文件>
├── train_tasks/
│   ├── 001/
│       ├── input/
│       │   ├── prompt.txt
│       │   └── payloads/
│       │       └── answer_template.json
│       ├── notes/
│       │   └── notes.md
│       ├── output/
│       │   └── answer.json
│       └── eval/
│           └── eval.sh
│   └── 005/
│       └── ...
└── test_tasks/
    ├── 001/
        ├── input/
        │   ├── prompt.txt
        │   └── payloads/
        │       └── answer_template.json
        ├── notes/
        │   └── notes.md
        ├── output/
        │   └── answer.json
        └── eval/
            └── eval.sh
    └── 005/
        └── ...
```

## task_group.yaml

```yaml
task_group:
  task_group_id: task_group_001
  scenario_id: SCN_001_example_scenario
  source_examples:
    - E001
    - E002
  domain: Example Domain
  description: |
    Describe the train-predict benchmark and the shared business environment.

env:
  setup: env/setup.sh
  files:
    - env/setup.sh
    - env/judge_api.py
    - env/endpoints.txt
    - env/<shared_business_service_or_support_file>

train_tasks:
  - task_id: train_001
    input: train_tasks/001/input/
    prompt_txt: train_tasks/001/input/prompt.txt
    payloads:
      - train_tasks/001/input/payloads/answer_template.json
      - train_tasks/001/input/payloads/<task_material>
    notes: train_tasks/001/notes/notes.md
    output: train_tasks/001/output/
    answer_json: train_tasks/001/output/answer.json
    eval:
      script: train_tasks/001/eval/eval.sh
      files:
        - train_tasks/001/eval/eval.sh
      rubric:
        - goal: <rule-based business-result check>
          weight: 2
        # Repeat until the task has 6-10 scoring points.
  # Repeat through train_005.

test_tasks:
  - task_id: test_001
    input: test_tasks/001/input/
    prompt_txt: test_tasks/001/input/prompt.txt
    payloads:
      - test_tasks/001/input/payloads/answer_template.json
      - test_tasks/001/input/payloads/<task_material>
    notes: test_tasks/001/notes/notes.md
    output: test_tasks/001/output/
    answer_json: test_tasks/001/output/answer.json
    eval:
      script: test_tasks/001/eval/eval.sh
      files:
        - test_tasks/001/eval/eval.sh
      rubric:
        - goal: <rule-based business-result check>
          weight: 2
        # Repeat until the task has 6-10 scoring points.
  # Repeat through test_005.
```

## 字段要求

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `task_group.task_group_id` | 是 | task group 全局唯一标识，目录名必须与该字段一致 |
| `task_group.scenario_id` | 是 | 来源场景 ID |
| `task_group.source_examples` | 是 | 用于构造该 task group 的第一阶段 example ID 列表，必须来自同一个 scenario |
| `task_group.domain` | 是 | 领域标签 |
| `task_group.description` | 是 | task group 的共享背景说明，不作为 solver 默认输入 |
| `env.setup` | 是 | 环境准备入口 |
| `env.files` | 是 | 最终 task group 索引中声明的公共环境文件；必须包含 `env/endpoints.txt` |
| `train_tasks` | 是 | 5 个 train task 条目：`train_001` 到 `train_005` |
| `test_tasks` | 是 | 5 个 test task 条目：`test_001` 到 `test_005` |

`env/endpoints.txt` 是纯 endpoint 清单。每个可访问 endpoint 只写一行
`METHOD /path`，需要包含业务 endpoint、`/health` 和 `/api/judge`。不能写接口
介绍、样例、host、凭据或调用说明。

`train_tasks` 和 `test_tasks` 中的每一项表示一个正式任务：

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `task_id` | 是 | task group 内唯一任务标识，建议使用 `train_001` 或 `test_001` |
| `input` | 是 | solver 输入目录 |
| `prompt_txt` | 是 | solver 可见的任务请求 |
| `payloads` | 是 | solver 可见的 payload 文件列表；必须包含 `input/payloads/answer_template.json` |
| `notes` | 是 | 隐藏说明文件，应为中英双语；使用 `<task>/notes/notes.md` |
| `output` | 是 | 标准答案目录 |
| `answer_json` | 是 | 标准答案文件 |
| `eval.script` | 是 | 评测入口脚本 |
| `eval.files` | 是 | 评测相关文件列表 |
| `eval.rubric` | 是 | 6-10 个 scoring points，覆盖至少 4 个可以独立失败的业务方面；每项只写 `goal` 和 `weight`；`weight` 只能为 `1`、`2` 或 `3`，该点最大贡献为 `weight / sum(weight)`；evaluator 可以在 point 内给出确定性的部分得分比例 |

## answer_template.json

每个 train/test task 都必须提供：

```text
input/payloads/answer_template.json
```

该文件对 solver 可见，用于明确规定答案输出格式。它应包含：

- 必需的顶层字段和嵌套字段。
- 字段类型，例如 number、integer、boolean、enum、list、object 或 string。
- 被评分数值的精度和单位。
- 分类、状态、动作、标签等选择型字段的可选枚举值。
- 列表排序规则、稳定标识符和对象必需字段。

`answer_template.json` 应消除输出 schema 的不确定性，但不能泄露答案、评分权重、隐藏 notes、SOP 或证据捷径。
