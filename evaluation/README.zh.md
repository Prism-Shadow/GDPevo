# Evaluation

语言：[English](README.md) | [中文](README.zh.md)

本目录用于在发布任务组上运行评测并生成结构化报告。评测对比冷启动基线（`base`）和两种自进化模式：少样本进化让智能体从带答案样例中进化，反思进化让智能体从自己尝试后的反馈中进化。

本目录包含 [`eval_workspace/`](eval_workspace/)，其中提供 Codex、Claude Code 和 Panofy 的可复用评测工作区。每个工作区都会说明如何放置任务组、运行多次尝试、收集 `acc@3`、token、费用和耗时指标，并写出最终 report YAML。
