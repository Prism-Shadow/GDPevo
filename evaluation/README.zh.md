# Evaluation

语言：[English](README.md) | [中文](README.zh.md)

本目录用于在发布任务组上运行评测并生成结构化报告。评测对比四种条件：冷启动基线（`base`）、从带答案样例中归纳的 `fewshot`、只看训练输入和环境的 `self`，以及使用训练阶段 judge 反馈的 `reflect-3`。

本目录包含 [`eval_workspace/`](eval_workspace/)，其中提供四个主运行的可复用评测工作区：Codex / GPT-5.5、Claude Code / Opus 4.8、Claude Code / GLM-5.2，以及 Claude Code / DeepSeek V4 Pro Preview。每个工作区都会说明如何放置任务组、运行多次尝试、收集 `acc`、population `std`、trace 可用时的轮次、token、费用和耗时指标，并写出最终 report YAML。
