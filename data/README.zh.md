# 数据

语言：[English](README.md) | [中文](README.zh.md)

本目录包含已发布的 GDPevo benchmark 数据：**240 个 GDP-worthy tasks**，组织为
**24 个 task group**。每个 task group 包含一个共享业务环境、**5 个 train
tasks**、**5 个 held-out test tasks**、参考答案、确定性评测器和任务说明。

## 内容

| 路径 | 用途 |
| --- | --- |
| [DATA_BOARD.zh.md](DATA_BOARD.zh.md) | 已发布 task groups 的汇总看板。 |
| [task_groups/](task_groups/) | 可执行的 benchmark task groups 和任务级数据。 |

## Task Groups

每个 task group 都是一个用于 stateful agent evaluation 的自包含 benchmark 单元。
Train tasks 在同一业务环境中驱动 evolve；held-out test tasks 用来衡量生成的
更新与规则能否迁移到 agent 没见过的后续任务。

当前公开 task groups 覆盖 CRM、ERP、Finance、医疗、法律、数据分析和工程运营等真实业务场景。它们由
GDPval 和 SOP-Bench 等真实工作来源 seed，再扩展成共享业务环境；环境中包含
lookalike records、反复出现的业务规则和确定性的 rule-based graders。

## 目录结构

```text
task_groups/
└── task_group_001/
    ├── task_group.yaml
    ├── env/
    │   └── ...
    ├── train_tasks/
    │   ├── 001/
    │   │   ├── input/
    │   │   │   ├── prompt.txt
    │   │   │   └── payloads/
    │   │   │       ├── answer_template.json
    │   │   │       └── ...
    │   │   ├── output/
    │   │   │   └── answer.json
    │   │   ├── eval/
    │   │   └── notes/
    │   │       └── notes.md
    │   └── ...
    └── test_tasks/
        ├── 001/
        │   ├── input/
        │   │   ├── prompt.txt
        │   │   └── payloads/
        │   │       ├── answer_template.json
        │   │       └── ...
        │   ├── output/
        │   │   └── answer.json
        │   ├── eval/
        │   └── notes/
        │       └── notes.md
        └── ...
```

## 文件说明

| 路径 | 用途 |
| --- | --- |
| `task_groups/*/task_group.yaml` | task group 索引文件，记录元信息、任务路径、环境文件和评分目标。 |
| `task_groups/*/env/` | 该 task group 内所有 train 和 held-out test tasks 共用的业务环境。 |
| `task_groups/*/env/README.md` | 环境启动和访问说明；如果该环境提供了此文件。 |
| `task_groups/*/train_tasks/*/input/prompt.txt` | train task 展示给 agent 的任务 prompt。 |
| `task_groups/*/test_tasks/*/input/prompt.txt` | held-out test task 展示给 agent 的任务 prompt。 |
| `task_groups/*/*/input/payloads/` | 该任务的本地输入文件，包括答案模板以及该任务专用的请求材料。 |
| `task_groups/*/*/input/payloads/answer_template.json` | 该任务期望的答案格式；如果该任务提供了此文件。 |
| `task_groups/*/*/output/answer.json` | 用于评测的参考答案。 |
| `task_groups/*/*/eval/` | 该任务对应的评测器文件。 |
| `task_groups/*/*/notes/notes.md` | 面向维护者和评测者的数据说明文件，用于解释任务定义、预期解法、常见错误点和评测标准。 |

## 使用说明

运行评估时，solver agent 应该只接收任务输入、evaluation harness 或 task group
元信息暴露出来的可用环境入口，以及当前 evaluation mode 所要求的特定 artifact。参考答案、
评测器文件和任务 notes 主要用于评测、检查和 benchmark 文档说明。
