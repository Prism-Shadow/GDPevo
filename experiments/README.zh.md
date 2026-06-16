# Experiments

语言：[English](README.md) | [中文](README.zh.md)

本目录包含已发布的 GDPevo 评估方法和结果产物。评估将无状态 baseline 与两种 evolve 方法进行对比：`demo` 和 `reflect`。它可以用于观察自进化 agent、Skill Creator / SkillOpt，以及 Agent Memory 的端到端效果。

## 内容

| 路径 | 用途 |
| --- | --- |
| `EXPERIMENT_BOARD.md` | 已发布评估结果的汇总表 |
| `eval_workspace/` | 可复用的英文 evaluation workspace 和 guides |
| `eval_workspace_zh/` | 可复用的中文 evaluation workspace 和 guides |
| `codex_gpt5_5_xhigh/` | 已发布的 Codex GPT-5.5 xhigh 评估运行 |

每个已发布实验目录都包含 `config.yaml`、结构化 report YAML 文件，以及这些 reports 引用的生成 skill packages。
