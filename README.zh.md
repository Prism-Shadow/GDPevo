# GDPevo: 在真实企业任务上评估 Agent 的自进化能力

语言：[English](README.md) | [中文](README.zh.md)

[![Blog](https://img.shields.io/badge/Blog-Read%20the%20blog-0f7b5f?style=flat&logo=readthedocs&logoColor=white)](https://prism-shadow.github.io/GDPevo/blog.html)

**GDPevo** 是一个公开基准，用来评估智能体在真实企业任务上的自进化能力。当前版本包含 120 个任务，覆盖客户关系管理（CRM）、企业资源计划（ERP）和金融三类业务，共 12 个任务组；每个任务组都有一个共享业务环境、5 个训练任务和 5 个保留测试任务。完整动机、构建流程和结果分析见[项目博客](https://prism-shadow.github.io/GDPevo/blog.html)。

## 评测结果

准确率使用 `acc@3`，并在 12 个任务组上取均值。稳定性使用 population `std@3`。`rounds@3` 表示 solver 每次 attempt 的平均模型响应轮次；仅在 solver trace 完整的运行中展示。费用以美元计；准确率提升和费用变化均相对 `base` 计算。

| 评测框架 | 模型 | 思考强度 | `base` acc@3 | `base` std@3 | `fewshot` acc@3 | `fewshot` std@3 | `self` acc@3 | `self` std@3 | `reflect-3` acc@3 | `reflect-3` std@3 | `base` 轮次@3 | `fewshot` 轮次@3 | `self` 轮次@3 | `reflect-3` 轮次@3 | `fewshot` 费用变化 | `self` 费用变化 | `reflect-3` 费用变化 | `fewshot` 提升 | `self` 提升 | `reflect-3` 提升 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 46.72% | 5.13% | 64.91% | 6.36% | 54.99% | 8.73% | 57.45% | 7.62% | n/a | n/a | n/a | n/a | -29.24% | -32.18% | -25.74% | +18.19 个百分点 | +8.27 个百分点 | +10.73 个百分点 |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 5.25% | 70.90% | 6.38% | 57.37% | 6.79% | 62.72% | 6.68% | 14.62 | 11.10 | 11.78 | 12.15 | -9.61% | +0.53% | -0.34% | +21.79 个百分点 | +8.26 个百分点 | +13.62 个百分点 |
| Panofy | Opus 4.6 | high | 50.40% | 6.99% | 71.47% | 4.93% | 58.39% | 5.74% | 59.82% | 7.31% | 15.16 | 13.48 | 12.51 | 14.37 | +8.27% | -6.00% | +1.99% | +21.07 个百分点 | +7.99 个百分点 | +9.41 个百分点 |
| Claude Code | GLM-5.2 | max | 47.73% | 5.21% | 69.55% | 8.85% | 55.91% | 7.84% | 63.35% | 7.51% | 17.57 | 15.49 | 15.98 | 15.36 | -12.28% | -10.23% | -16.50% | +21.83 个百分点 | +8.18 个百分点 | +15.62 个百分点 |

完整汇总见 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md)。

逐任务报告见：

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)
- [`experiments/claude_code_glm_5_2_max/`](experiments/claude_code_glm_5_2_max/)

## 目录结构

| 路径 | 内容 |
| --- | --- |
| [`data/`](data/) | 已发布的基准数据，包括任务组、共享环境、训练与测试任务、参考答案和基于规则的评测器。 |
| [`data_construction/`](data_construction/) | 构建工作区，包括场景发现、任务组生成和质量过滤。 |
| [`evaluation/`](evaluation/) | 面向已发布任务组的可复用分数评测工作区。 |
| [`experiments/`](experiments/) | 已发布的评测结果、报告文件和实验汇总表。 |
| [`site/`](site/) | 基准发布用的公开网站与博客。 |

## 如何使用这个仓库

- 基准数据：阅读 [`data/DATA_BOARD.zh.md`](data/DATA_BOARD.zh.md) 了解任务组概览，再查看 [`data/task_groups/`](data/task_groups/) 中的具体任务。
- 评测结果：在 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md) 查看汇总结果，再进入已发布实验目录阅读逐任务报告。
- 构建工作区：前三阶段流程在 [`data_construction/`](data_construction/) 下。
- 分数评测工作区：使用 [`evaluation/eval_workspace/`](evaluation/eval_workspace/)。
- 前三阶段默认通过 Codex 工作流实现。其他智能体框架可以复用整体结构，但需要适度改写。

## 工作区使用指南

这些工作区是可直接用 agent 运行的文件夹，用来构建、审核和评测 GDPevo。使用时，用 agent 打开对应文件夹，放入该阶段需要的输入数据，然后输入提示词触发流程。

- **场景发现**：[`data_construction/Stage_1_Scenario_Discovery/`](data_construction/Stage_1_Scenario_Discovery/)

  - **用途**：根据给定业务场景搜寻可归并的来源数据集原始数据。
  - **输入数据**：给定业务场景（`<target_scenario>`）和可检索的来源 benchmark 原始数据。
  - **提示词**：`阅读 README.md，根据 <target_scenario> 搜寻来源数据集原始数据，并在 scenario/<scenario_id>/ 下写出场景数据。`

- **任务组生成**：[`data_construction/Stage_2_Task_Group_Synthesis/`](data_construction/Stage_2_Task_Group_Synthesis/)

  - **用途**：从一个场景生成完整任务组。
  - **输入数据**：放入 `seed_scenario/` 的一条 Stage 1 场景数据，包括 `scenario.yaml`、notes 和 attachments。
  - **提示词**：`阅读 README.md 和 guides/，生成 task_group/<task_group_id>/。`

- **质量过滤**：[`data_construction/Stage_3_Quality_Filtering/`](data_construction/Stage_3_Quality_Filtering/)

  - **用途**：对一个完成构建的任务组做结构检查，并组织独立审核智能体投票。
  - **输入数据**：放入 `task_group/` 的一个完整任务组；对应的 Stage 2 构建记录放入 `scratch/`。
  - **提示词**：`阅读 README.md 和 guides/，审核一个 task_group/，收集 6 票，并写出 ../reports/<task_group_id>.yaml。`

- **分数评测**：[`evaluation/eval_workspace/`](evaluation/eval_workspace/)

  - **用途**：对一个发布任务组运行正式评测，统计 `acc@3`、token 和费用。目录下包含 Codex、Claude Code、Panofy 以及中文镜像工作区。
  - **输入数据**：放入所选评测工作区的一个已发布任务组，以及该工作区需要的密钥或配置。
  - **提示词**：`阅读 README.md 和 guides/，对已放入的任务组运行分数评测，并写出 report/<task_group_id>.yaml。`

## 引用

```bibtex
@misc{gdpevo2026,
  title  = {GDPevo: Measuring agent self-evolution on real business work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}
```
