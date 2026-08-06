# GDPevo: 在真实企业任务上评估 Agent 的自进化能力

语言：[English](README.md) | [中文](README.zh.md)

[![Blog](https://img.shields.io/badge/Blog-Read%20the%20blog-0f7b5f?style=flat&logo=readthedocs&logoColor=white)](https://prism-shadow.github.io/GDPevo/blog.html)
[![Paper](https://img.shields.io/badge/arXiv-2608.03764-b31b1b?style=flat&logo=arxiv&logoColor=white)](https://arxiv.org/abs/2608.03764)

**GDPevo** 是一个公开基准，用来评估智能体在真实企业任务上的自进化能力。当前数据版本包含 240 个任务，共 24 个任务组，覆盖 CRM、ERP、金融、医疗、法律、数据分析和工程运营等业务场景；每个任务组都有一个共享业务环境、5 个训练任务和 5 个保留测试任务。完整动机、构建流程和结果分析见[项目博客](https://prism-shadow.github.io/GDPevo/blog.html)。

## 评测结果

每个实验都运行了三次，括号里面的数字代表标准差，其余默认代表均值。准确率用 `acc` 表示。`rounds` 表示 solver 每次 attempt 的平均模型响应轮次，`tool calls` 表示 solver 每次 attempt 的平均工具调用次数。费用以美元计；准确率提升和费用变化均相对 `base` 计算。

主要发布评测对比四种 mode。另有两组独立的 skill creator 对比实验，固定
Codex harness 与 solver model，只改变 few-shot skill 所使用的 creator：
[GPT-5.5 xhigh](experiments/codex_skill_creator_comparison_gpt5_5_xhigh/) 和
[DeepSeek V4 Pro Preview max](experiments/codex_skill_creator_comparison_deepseek_v4_pro_max/)。

- **base**：直接运行测试任务，不经过任何进化步骤。
- **self**：只基于训练输入和环境，自行进化工作策略，不使用训练答案。
- **fewshot**：从训练输入和标准答案组成的示例中学习。
- **reflect-3**：通过仅限训练阶段的 judge 反馈迭代，再沉淀进化后的工作流程。

主榜单使用 task groups 001–024。为与论文保持一致，当前榜单和任务组雷达图仅纳入下列四组具有完整 24 个任务组数据的 v2 实验。仅包含 V1 的 12 组旧实验仍归档在 `experiments/` 下，但不进入当前对比。

| 评测框架 | 模型 | 思考强度 | `base` acc | `fewshot` acc | `self` acc | `reflect-3` acc | `base` 轮次 | `base` 工具调用 | `fewshot` 轮次 | `fewshot` 工具调用 | `self` 轮次 | `self` 工具调用 | `reflect-3` 轮次 | `reflect-3` 工具调用 | `fewshot` 费用变化 | `self` 费用变化 | `reflect-3` 费用变化 | `fewshot` 提升 | `self` 提升 | `reflect-3` 提升 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 49.37% (±5.51%) | 64.51% (±6.31%) | 55.80% (±7.63%) | 57.82% (±7.38%) | 14.96 | 36.19 | 12.04 | 28.02 | 11.45 | 26.77 | 11.85 | 27.88 | -20.88% | -22.87% | -17.23% | +15.14 个百分点 | +6.42 个百分点 | +8.45 个百分点 |
| Claude Code | Opus 4.8 | xhigh | 50.63% (±5.37%) | 67.07% (±6.22%) | 55.05% (±6.96%) | 59.27% (±7.01%) | 17.06 | 19.30 | 14.46 | 18.16 | 15.57 | 19.33 | 15.58 | 19.43 | -0.57% | +9.06% | +4.77% | +16.44 个百分点 | +4.42 个百分点 | +8.64 个百分点 |
| Claude Code | GLM-5.2 | max | 46.12% (±5.82%) | 60.09% (±7.90%) | 50.96% (±8.32%) | 55.49% (±8.28%) | 22.94 | 30.60 | 22.63 | 31.26 | 21.93 | 30.84 | 20.65 | 28.67 | +5.74% | -0.92% | -7.07% | +13.97 个百分点 | +4.84 个百分点 | +9.37 个百分点 |
| Claude Code | DeepSeek V4 Pro Preview | max | 43.58% (±7.77%) | 48.79% (±9.05%) | 46.17% (±7.89%) | 47.15% (±8.18%) | 15.65 | 27.31 | 14.73 | 25.35 | 14.29 | 24.45 | 12.68 | 21.90 | +2.58% | +2.52% | -4.77% | +5.21 个百分点 | +2.59 个百分点 | +3.57 个百分点 |

完整汇总见 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md)。

逐任务报告见：

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/codex_skill_creator_comparison_gpt5_5_xhigh/`](experiments/codex_skill_creator_comparison_gpt5_5_xhigh/) —— 固定 Codex harness 与 GPT-5.5 xhigh，对比五种 few-shot skill creator（含最小 naive 对照）
- [`experiments/codex_skill_creator_comparison_deepseek_v4_pro_max/`](experiments/codex_skill_creator_comparison_deepseek_v4_pro_max/) —— 固定 Codex harness 与 DeepSeek V4 Pro Preview max，进行相同的五种 creator 对比
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/claude_code_glm_5_2_max/`](experiments/claude_code_glm_5_2_max/)
- [`experiments/claude_code_deepseek_v4_pro_max/`](experiments/claude_code_deepseek_v4_pro_max/)

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

  - **用途**：对一个发布任务组运行正式评测，统计 `acc`、population `std`、turn-count、token 和费用。目录下包含 Codex、Claude Code 以及中文镜像工作区。
  - **输入数据**：放入所选评测工作区的一个已发布任务组，以及该工作区需要的密钥或配置。
  - **提示词**：`阅读 README.md 和 guides/，对已放入的任务组运行分数评测，并写出 report/<task_group_id>.yaml。`

## 引用

```bibtex
@misc{gdpevo2026,
  title         = {{GDPevo}: Evaluating Agent Self-Evolution on Real Business Tasks},
  author        = {Zhou, Leijun and Liu, Zhihao and Qu, Xiang and Liu, Chenxu and Liu, Yifei and Yu, Yanke and Xu, Jingzhe and Wu, Xuejun and Qian, Buyue and Chen, Xi and Zheng, Yaowei and Hu, Junhao},
  year          = {2026},
  eprint        = {2608.03764},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url           = {https://arxiv.org/abs/2608.03764}
}
```
