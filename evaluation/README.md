# Evaluation

Languages: [English](README.md) | [中文](README.zh.md)

This directory runs released task groups under the benchmark conditions and writes structured reports. The evaluation compares four conditions: the cold baseline (`base`), `fewshot` from worked examples, `self` from train inputs and environment access without answers or judge feedback, and `reflect-3` from train-only judge feedback.

This directory contains [`eval_workspace/`](eval_workspace/), with reusable workspaces for Codex, Claude Code including the GLM-5.2 variant, and Panofy. Each workspace documents how to stage task groups, run attempts, collect `acc@3`, population `std@3`, round-count metrics where traces are available, token, cost, and timing metrics, and write final report YAML files.
