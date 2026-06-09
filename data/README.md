# Data

Languages: [English](README.md) | [Chinese](README.zh.md)

This directory contains the released GDPevo benchmark data. The current release
is organized as task groups: each task group packages one shared business
environment, five train tasks, five test tasks, reference answers, evaluators,
and task notes.

## Contents

| Path | Purpose |
| --- | --- |
| [DATA_BOARD.md](DATA_BOARD.md) | Summary table for released task groups. |
| [task_groups/](task_groups/) | Executable benchmark task groups and task-level data. |

## Task Groups

Each task group is a self-contained benchmark unit with one shared environment,
five train tasks, and five test tasks. Train tasks are used to derive skills,
and test tasks measure whether those skills transfer to related work in the same
business environment.

## Directory Layout

```text
task_groups/
└── task_group_001/
    ├── task_group.yaml
    ├── env/
    │   └── ...
    ├── train_tasks/
    │   ├── 001/
    │   │   ├── input/
    │   │   │   ├── prompt.txt
    │   │   │   └── payloads/
    │   │   │       ├── answer_template.json
    │   │   │       └── ...
    │   │   ├── output/
    │   │   │   └── answer.json
    │   │   ├── eval/
    │   │   └── notes/
    │   │       └── notes.md
    │   └── ...
    └── test_tasks/
        ├── 001/
        │   ├── input/
        │   │   ├── prompt.txt
        │   │   └── payloads/
        │   │       ├── answer_template.json
        │   │       └── ...
        │   ├── output/
        │   │   └── answer.json
        │   ├── eval/
        │   └── notes/
        │       └── notes.md
        └── ...
```

## Files

| Path | Purpose |
| --- | --- |
| `task_groups/*/task_group.yaml` | Task group index with metadata, task paths, environment files, and scoring goals. |
| `task_groups/*/env/` | Shared business environment used by all train and test tasks in the task group. |
| `task_groups/*/env/README.md` | Environment setup and access instructions, when provided. |
| `task_groups/*/train_tasks/*/input/prompt.txt` | The task prompt shown to the agent for a train task. |
| `task_groups/*/test_tasks/*/input/prompt.txt` | The task prompt shown to the agent for a test task. |
| `task_groups/*/*/input/payloads/` | Task-local input files, including answer templates and any task-specific request materials. |
| `task_groups/*/*/input/payloads/answer_template.json` | Expected answer schema for the task, when provided. |
| `task_groups/*/*/output/answer.json` | Reference answer used for evaluation. |
| `task_groups/*/*/eval/` | Task-specific evaluator files. |
| `task_groups/*/*/notes/notes.md` | Maintainer and evaluator notes explaining the task definition, expected solution approach, likely failure modes, and evaluation criteria. |

## Usage Notes

When running an evaluation, the solver agent should receive only the task input,
the allowed environment access exposed by the evaluation harness or task group
metadata, and any skill file required by the evaluation condition. Reference
answers, evaluator files, and task notes are for evaluation, inspection, and
benchmark documentation.
