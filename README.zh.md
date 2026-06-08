# Agent Learn Bench

语言：[English](README.md) | [中文](README.zh.md)

Agent Learn Bench 是一个公开 benchmark，用于评估 agent 在真实业务环境中学习并迁移 skill 的能力。

这个 benchmark 主要关注两类能力：

- 在大规模真实业务环境中完成长流程任务。
- 从 train tasks 中学习可复用 skills，并迁移到相关 test tasks。

当前公开内容包括可执行的 task groups、评估报告、生成的 skill packages，以及可复用的 evaluation workspace。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `data/task_groups/` | 已发布的 task groups，包含共享环境、train tasks、test tasks、答案、评测器和数据说明。 |
| `experiments/` | 已发布的评估协议、evaluation workspaces、结果报告、生成 skills 和实验看板。 |
| `site/` | 预留给后续网站或 blog 内容。 |
| `assets/` | 预留给后续图片、logo 和视觉资源。 |

## 数据

每个 task group 包含一个共享业务环境、5 个 train tasks 和 5 个 test tasks。Train tasks 用于生成或沉淀 skills，test tasks 用于衡量这些 skills 是否能够迁移到同一环境下的相关任务。

Task group 格式见 [data/task_groups/README.zh.md](data/task_groups/README.zh.md)。

## 实验

当前公开的评估运行比较三种条件：

- `no_skill`
- `demonstration_skill`
- `reflection_skill`

结果汇总在 [experiments/EXPERIMENT_BOARD.zh.md](experiments/EXPERIMENT_BOARD.zh.md)。

详细说明见 [experiments/README.zh.md](experiments/README.zh.md)。

## Evaluation Workspace

中文 evaluation workspace 位于 [experiments/eval_workspace_zh/](experiments/eval_workspace_zh/)，英文版本位于 [experiments/eval_workspace/](experiments/eval_workspace/)。它说明了如何使用干净上下文的 skill-generation agent 和 solver agent 运行 `avg@3` 评估，如何记录 token/time 指标，以及如何写最终报告。
