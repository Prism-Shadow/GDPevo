# Evaluation

Languages: [English](README.md) | [中文](README.zh.md)

This directory runs released task groups under the benchmark conditions and writes structured reports. The evaluation compares four conditions: the cold baseline (`base`), `fewshot` from worked examples, `self` from train inputs and environment access without answers or judge feedback, and `reflect-3` from train-only judge feedback.

This directory contains [`eval_workspace/`](eval_workspace/), with reusable workspaces for the four primary runs: Codex / GPT-5.5, Claude Code / Opus 4.8, Claude Code / GLM-5.2, and Claude Code / DeepSeek V4 Pro Preview. Each workspace documents how to stage task groups, run attempts, collect `acc`, population `std`, round-count metrics where traces are available, token, cost, and timing metrics, and write final report YAML files.

The [`codex_skill_creator_comparison/`](eval_workspace/codex_skill_creator_comparison/) workspace is a focused Codex experiment with one shared `base` per model profile and four creator-specific `fewshot` branches: Codex, Claude Code, Deep Agents, and OpenCode skill creators.
