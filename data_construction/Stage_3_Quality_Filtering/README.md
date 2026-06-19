# Stage 3: Quality Filtering

Languages: [English](README.md) | [中文](README.zh.md)

Stage 3 audits candidate task groups before release. Reviewer agents check structure, completeness, hidden-rule placement, evaluator reproducibility, and whether the train/test split can actually measure self-evolution.

This directory contains [`review_workspace/`](review_workspace/), the English review workspace used to run the quality filter. A Chinese mirror is available at [`review_workspace_zh/`](review_workspace_zh/). Candidate task groups should be copied into the workspace `task_group/` directory. Review outputs and scratch checks stay inside the workspace until a task group passes the release threshold.
