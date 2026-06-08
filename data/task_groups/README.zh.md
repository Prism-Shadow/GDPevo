# Task Groups

语言：[English](README.md) | [中文](README.zh.md)

本目录包含已发布的 benchmark task groups。每个 task group 都是一个自包含的 benchmark 单元，包含一个共享环境、5 个 train tasks 和 5 个 test tasks。

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
| `task_group.yaml` | task group 索引文件，记录元信息、任务路径、环境文件和评分目标。 |
| `env/` | 该 task group 内所有 train 和 test tasks 共用的业务环境。 |
| `env/README.md` | 环境启动和访问说明；如果该环境提供了此文件。 |
| `train_tasks/*/input/prompt.txt` | train task 展示给 agent 的任务 prompt。 |
| `test_tasks/*/input/prompt.txt` | test task 展示给 agent 的任务 prompt。 |
| `*/input/payloads/` | 该任务的本地输入文件，包括答案模板以及该任务专用的请求材料。 |
| `*/input/payloads/answer_template.json` | 该任务期望的答案格式；如果该任务提供了此文件。 |
| `*/output/answer.json` | 用于评测的参考答案。 |
| `*/eval/` | 该任务对应的评测器文件。 |
| `*/notes/notes.md` | 面向维护者和评测者的数据说明文件，用于解释任务定义、预期推理路径、常见错误点和评测标准。 |

## 使用说明

Train tasks 用于生成或沉淀 skills。Test tasks 用于衡量这些 skills 是否能够迁移到同一业务环境下的相关任务。

运行评估时，solver agent 应该只接收任务输入、evaluation harness 或 task group 元信息暴露出来的可用环境入口，以及当前评估条件所要求的 skill 文件。参考答案、评测器文件和任务 notes 主要用于评测、检查和 benchmark 文档说明。
