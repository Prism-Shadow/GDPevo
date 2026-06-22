# Evaluation

Languages: [English](README.md) | [中文](README.zh.md)

This directory runs released task groups under the benchmark conditions and writes structured reports. The evaluation compares a cold baseline (`base`) with two self-evolution modes: `fewshot`, where the agent evolves from worked examples, and `reflect`, where the agent evolves from feedback on its own attempts.

This directory contains [`eval_workspace/`](eval_workspace/), with reusable workspaces for Codex, Claude Code, and Panofy. Each workspace documents how to stage task groups, run attempts, collect `acc@3`, token, cost, and timing metrics, and write final report YAML files.
