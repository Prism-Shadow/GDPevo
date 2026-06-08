# Task Groups

Languages: [English](README.md) | [Chinese](README.zh.md)

This directory contains the released benchmark task groups. Each task group is a
self-contained benchmark unit with a shared environment, five train tasks, and
five test tasks.

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
| `task_group.yaml` | Task group index with metadata, task paths, environment files, and scoring goals. |
| `env/` | Shared business environment used by all train and test tasks in the task group. |
| `env/README.md` | Environment setup and access instructions, when provided. |
| `train_tasks/*/input/prompt.txt` | The task prompt shown to the agent for a train task. |
| `test_tasks/*/input/prompt.txt` | The task prompt shown to the agent for a test task. |
| `*/input/payloads/` | Task-local input files, including answer templates and any task-specific request materials. |
| `*/input/payloads/answer_template.json` | Expected answer schema for the task, when provided. |
| `*/output/answer.json` | Reference answer used for evaluation. |
| `*/eval/` | Task-specific evaluator files. |
| `*/notes/notes.md` | Maintainer and evaluator notes explaining the task definition, expected reasoning path, likely failure modes, and evaluation criteria. |

## Usage Notes

Train tasks are used to derive skills. Test tasks are used to
measure whether those skills transfer to related tasks in the same business
environment.

When running an evaluation, the solver agent should receive only the task input,
the allowed environment access exposed by the evaluation harness or task group
metadata, and any skill file required by the evaluation condition. Reference
answers, evaluator files, and task notes are for evaluation, inspection, and
benchmark documentation.
