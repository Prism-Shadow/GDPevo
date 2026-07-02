# Evaluation

语言：[English](README.md) | [中文](README.zh.md)

本目录用于在发布任务组上运行评测并生成结构化报告。评测对比四种条件：冷启动基线（`base`）、从带答案样例中归纳的 `fewshot`、只看训练输入和环境的 `self`，以及使用训练阶段 judge 反馈的 `reflect-3`。

本目录包含 [`eval_workspace/`](eval_workspace/)，其中提供 Codex、Claude Code（包括 GLM-5.2 变体）和 Panofy 的可复用评测工作区。每个工作区都会说明如何放置任务组、运行多次尝试、收集 `acc@3`、population `std@3`、token、费用和耗时指标，并写出最终 report YAML。
