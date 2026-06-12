# GDPevo

语言：[English](README.md) | [中文](README.zh.md)

GDPevo 是一个面向真实业务场景的公开 agent benchmark，用于评估自进化 agent 在具有经济价值的任务中学习和迁移规则的能力。据我们所知，它是首个面向 GDP-valued tasks 的 stateful benchmark：agent 先完成一组相关 train tasks，将经验沉淀为可复用 skill，再在同一业务环境下的 held-out test tasks 上接受评估。

多数现有 agent benchmark 仍然评估“无状态”的单次任务完成。GDPevo 关注的是另一类能力：agent 能否从早期任务中学习业务规则、信息来源优先级、操作流程和输出规范，并让后续任务在准确率和执行成本上获得提升。

这个 benchmark 可以用于：

- 评估带有自进化或持续学习能力的 agent。
- 评估 Skill Creator / SkillOpt 的能力。
- 评估 Agent Memory 的端到端效果。

首个公开版本包含 120 个由先进 agent 合成的任务，并组织为 12 个 task groups。每个 task group 包含一个共享业务环境、5 个 train tasks 和 5 个 test tasks。任务组都对应具有经济价值的产业场景，例如金融、企业 CRM 和 ERP 自动化。

在已发布的 Codex GPT-5.5 xhigh 运行中，自进化后的 agent 在归纳学习后平均获得 18.21 个百分点的准确率提升，同时 token 成本平均节省 25.75%。当前公开内容包括可执行 task groups、评估报告、生成的 skill packages，以及可复用的 evaluation workspace，用于自动执行完整评估流程并生成最终分数。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `data/` | 已发布的 task group 数据、数据看板、共享环境、train/test tasks、答案、评测器和数据说明。 |
| `experiments/` | 已发布的评估协议、evaluation workspaces、结果报告、生成 skills 和实验看板。 |
| `site/` | 用于 GitHub Pages 的静态网站和 blog 内容。 |
| `assets/` | 已发布材料使用的图片、logo 和视觉资源。 |

## 数据

每个 task group 包含一个共享业务环境、5 个 train tasks 和 5 个 test tasks。Train tasks 提供经验来源，test tasks 用于衡量生成的 skills 是否能让同一业务环境下的后续任务获得提升。

已发布 task groups 汇总在 [data/DATA_BOARD.zh.md](data/DATA_BOARD.zh.md)。

数据目录说明和 task group 格式见 [data/README.zh.md](data/README.zh.md)。

## 实验

当前公开的评估运行比较三种条件：

- `no_skill`
- `demonstration_skill`
- `reflection_skill`

结果汇总在 [experiments/EXPERIMENT_BOARD.zh.md](experiments/EXPERIMENT_BOARD.zh.md)。

详细说明见 [experiments/README.zh.md](experiments/README.zh.md)。

## Evaluation Workspace

中文 evaluation workspace 位于 [experiments/eval_workspace_zh/](experiments/eval_workspace_zh/)，英文版本位于 [experiments/eval_workspace/](experiments/eval_workspace/)。它说明了如何使用 Codex 组织完整评估流程：生成 skill、运行 solver、聚合 `avg@3`、记录 token 和 cost 指标，并写出最终报告。
