# GDPevo

语言：[English](README.md) | [中文](README.zh.md)

GDPevo 是一个公开 benchmark，用于评估 agent 在真实业务生产环境中学习并迁移 skill 的能力。参考 GDPVal 这类 real-world work evaluation 的思路，这里的任务对应具备生产力属性的真实业务工作，而不是孤立题目。

这个 benchmark 主要关注三个问题：

- agent 能否在真实业务生产环境中完成长流程任务。
- agent 能否从 train tasks 中学习可复用 skills，并迁移到相关 test tasks。
- 这些 skills 是否让下游求解更准确、成本更低；token 和 cost 指标用于观察下游求解效率。

当前公开内容包括可执行的 task groups、评估报告、生成的 skill packages，以及可复用的 evaluation workspace。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `data/task_groups/` | 已发布的 task groups，包含共享环境、train tasks、test tasks、答案、评测器和数据说明。 |
| `experiments/` | 已发布的评估协议、evaluation workspaces、结果报告、生成 skills 和实验看板。 |
| `site/` | 用于 GitHub Pages 的静态网站和 blog 内容。 |
| `assets/` | 已发布材料使用的图片、logo 和视觉资源。 |

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
