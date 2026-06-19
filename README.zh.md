# GDPevo

语言：[English](README.md) | [中文](README.zh.md)

[![Blog](https://img.shields.io/badge/Blog-Read%20the%20blog-0f7b5f?style=flat&logo=readthedocs&logoColor=white)](https://prism-shadow.github.io/GDPevo/blog.html)

**GDPevo** 是一个公开基准，用来评估智能体在真实企业任务上的自进化能力。当前版本包含 120 个任务，覆盖客户关系管理（CRM）、企业资源计划（ERP）和金融三类业务，共 12 个任务组；每个任务组都有一个共享业务环境、5 个训练任务和 5 个保留测试任务。完整动机、构建流程和结果分析见[项目博客](https://prism-shadow.github.io/GDPevo/blog.html)。

## 评测结果

准确率使用 `acc@3`，并在 12 个任务组上取均值。费用以美元计。

| 评测框架 | 模型 | 思考强度 | 基线准确率 | 少样本进化准确率 | 反思进化准确率 | 准确率提升 | 费用变化 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 48.35% | 65.99% | 67.13% | +18.21 个百分点 | -25.75% |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 70.90% | 67.94% | +20.31 个百分点 | -8.69% |
| Panofy | Opus 4.6 | high | 50.17% | 68.24% | 67.98% | +17.94 个百分点 | +11.82% |

完整汇总见 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md)。

逐任务报告见：

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)

## 目录结构

| 路径 | 内容 |
| --- | --- |
| [`data/`](data/) | 已发布的基准数据，包括任务组、共享环境、训练与测试任务、参考答案和基于规则的评测器。 |
| [`data_construction/`](data_construction/) | 四阶段构建与评测工作区，覆盖场景发现、任务组生成、质量过滤和分数评测。 |
| [`experiments/`](experiments/) | 已发布的评测结果、报告文件和实验汇总表。 |
| [`site/`](site/) | 基准发布用的公开网站与博客。 |

## 如何使用这个仓库

- 基准数据：阅读 [`data/DATA_BOARD.zh.md`](data/DATA_BOARD.zh.md) 了解任务组概览，再查看 [`data/task_groups/`](data/task_groups/) 中的具体任务。
- 评测结果：在 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md) 查看汇总结果，再进入三个实验目录阅读逐任务报告。
- 构建与评测工作区：四阶段流程都在 [`data_construction/`](data_construction/) 下。每个工作区都有自己的 README 和 guides。
- 前三阶段默认通过 Codex 工作流实现。其他智能体框架可以复用整体结构，但需要适度改写。
- 本地预览公开网站：

```bash
cd site
npm ci
npm run build
npm run preview
```

## 工作区使用指南

| 阶段 | 工作区 | 功能 | 提示语 |
| --- | --- | --- | --- |
| 场景发现 | [`data_construction/Stage_1_Scenario_Discovery/`](data_construction/Stage_1_Scenario_Discovery/) | 根据给定业务场景搜寻可归并的来源数据集原始数据。 | `阅读 README.md，根据 <target_scenario> 搜寻来源数据集原始数据，并在 scenario/<scenario_id>/ 下写出场景数据。` |
| 任务组生成 | [`data_construction/Stage_2_Task_Group_Synthesis/`](data_construction/Stage_2_Task_Group_Synthesis/) | 从一个场景生成完整任务组。 | `阅读 README.md 和 guides/，生成 task_group/<task_group_id>/。` |
| 质量过滤 | [`data_construction/Stage_3_Quality_Filtering/`](data_construction/Stage_3_Quality_Filtering/) | 对一个完成构建的任务组做结构检查，并组织独立审核智能体投票。 | `阅读 README.md 和 guides/，审核一个 task_group/，收集 6 票，并写出 ../reports/<task_group_id>.yaml。` |
| 分数评测 | [`data_construction/Stage_4_Score_Evaluation/eval_workspace/`](data_construction/Stage_4_Score_Evaluation/eval_workspace/) | 对一个发布任务组运行正式评测，统计 `acc@3`、token 和费用。目录下包含 Codex、Claude Code、Panofy 以及中文镜像工作区。 | `使用 Codex GPT-5.5 xhigh、Claude Code Opus 4.8 xhigh 或 Panofy，运行分数评测，并写出 report/<task_group_id>.yaml。` Panofy 先加载 `.env`。 |

## 引用

```bibtex
@misc{gdpevo2026,
  title  = {GDPevo: Measuring agent self-evolution on real business work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}
```
