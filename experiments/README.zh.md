# Experiments

语言：[English](README.md) | [中文](README.zh.md)

本目录包含已发布的 GDPevo 评测结果和报告产物。已发布评测将无状态基线（`base`）与三种进化模式进行对比：`fewshot`、`self` 和 `reflect-3`。它可以用于观察智能体自进化、更新机制和端到端记忆系统的效果。

## 内容

| 路径 | 用途 |
| --- | --- |
| `EXPERIMENT_BOARD.md` | 已发布评估结果的汇总表 |
| `codex_gpt5_5_xhigh/` | 已发布的 Codex GPT-5.5 xhigh 评估运行 |
| `claude_code_opus_4_8_xhigh/` | 已发布的 Claude Code Opus 4.8 xhigh 评估运行 |
| `panofy_claude_opus_4_6_high/` | 已发布的 Panofy Claude Opus 4.6 high 评估运行 |
| `claude_code_glm_5_2_max/` | 已发布的 Claude Code GLM-5.2 max 评估运行 |

每个已发布实验目录都包含 `config.yaml`、结构化 report YAML 文件，以及这些 reports 引用的生成 artifacts（如果有）。
可复用评测工作区位于 [`../evaluation/eval_workspace/`](../evaluation/eval_workspace/)。
