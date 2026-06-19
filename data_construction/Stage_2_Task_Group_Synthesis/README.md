# Stage 2: Task Group Synthesis

Languages: [English](README.md) | [中文](README.zh.md)

Stage 2 turns scenario records into complete task groups. The task factory builds one shared business environment, 5 train tasks, 5 held-out test tasks, reference answers, task notes, and rule-based evaluators for each scenario.

This directory contains two workspace variants:

- [`task_factory/`](task_factory/) is the English task-group synthesis workspace.
- [`task_factory_zh/`](task_factory_zh/) is the Chinese mirror.

Read the workspace README and guides before running synthesis. Generated task groups should be written to the workspace `task_group/` directory and then passed to Stage 3 for quality filtering.
