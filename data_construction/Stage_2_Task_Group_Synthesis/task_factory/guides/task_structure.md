# Task Structure

## Input

Each construction run reads one scenario. The scenario should contain several examples, and each example should contain:

- `example_id`
- `source`
- `prompt`
- `notes`
- `attachments`

These examples define task complexity, business context, data types, and long-horizon work intensity. The task group must not simply copy the examples; it should abstract transferable scenario experience and SOPs from them.

## Output Directory

`task_factory/task_group/<task_group_id>/` should contain:

A completed task group should contain exactly 5 train tasks and 5 test tasks.

```text
task_group_001/
├── task_group.yaml
├── env/
│   ├── setup.sh
│   ├── judge_api.py
│   └── <shared business services, data, setup files, and support files>
├── train_tasks/
│   ├── 001/
│       ├── input/
│       │   ├── prompt.txt
│       │   └── payloads/
│       │       └── answer_template.json
│       ├── notes/
│       │   └── notes.md
│       ├── output/
│       │   └── answer.json
│       └── eval/
│           └── eval.sh
│   └── 005/
│       └── ...
└── test_tasks/
    ├── 001/
        ├── input/
        │   ├── prompt.txt
        │   └── payloads/
        │       └── answer_template.json
        ├── notes/
        │   └── notes.md
        ├── output/
        │   └── answer.json
        └── eval/
            └── eval.sh
    └── 005/
        └── ...
```

## task_group.yaml

```yaml
task_group:
  task_group_id: task_group_001
  scenario_id: SCN_001_example_scenario
  source_examples:
    - E001
    - E002
  domain: Example Domain
  description: |
    Describe the train-predict benchmark and the shared business environment.

env:
  setup: env/setup.sh
  files:
    - env/setup.sh
    - env/judge_api.py
    - env/<shared_business_service_or_support_file>

train_tasks:
  - task_id: train_001
    input: train_tasks/001/input/
    prompt_txt: train_tasks/001/input/prompt.txt
    payloads:
      - train_tasks/001/input/payloads/answer_template.json
      - train_tasks/001/input/payloads/<task_material>
    notes: train_tasks/001/notes/notes.md
    output: train_tasks/001/output/
    answer_json: train_tasks/001/output/answer.json
    eval:
      script: train_tasks/001/eval/eval.sh
      files:
        - train_tasks/001/eval/eval.sh
      rubric:
        - goal: <rule-based business-result check>
          weight: 2
        # Repeat until the task has 6-10 scoring points.
  # Repeat through train_005.

test_tasks:
  - task_id: test_001
    input: test_tasks/001/input/
    prompt_txt: test_tasks/001/input/prompt.txt
    payloads:
      - test_tasks/001/input/payloads/answer_template.json
      - test_tasks/001/input/payloads/<task_material>
    notes: test_tasks/001/notes/notes.md
    output: test_tasks/001/output/
    answer_json: test_tasks/001/output/answer.json
    eval:
      script: test_tasks/001/eval/eval.sh
      files:
        - test_tasks/001/eval/eval.sh
      rubric:
        - goal: <rule-based business-result check>
          weight: 2
        # Repeat until the task has 6-10 scoring points.
  # Repeat through test_005.
```

## Field Requirements

| Field | Required | Description |
| --- | --- | --- |
| `task_group.task_group_id` | Yes | Globally unique task group identifier; the directory name must match this field |
| `task_group.scenario_id` | Yes | Source scenario ID |
| `task_group.source_examples` | Yes | Stage 1 example IDs used to construct the task group; all must come from the same scenario |
| `task_group.domain` | Yes | Domain label |
| `task_group.description` | Yes | Shared task-group background; not default solver input |
| `env.setup` | Yes | Environment setup entry point |
| `env.files` | Yes | Shared environment files that should be declared in the final task group index |
| `train_tasks` | Yes | Exactly 5 train task entries: `train_001` through `train_005` |
| `test_tasks` | Yes | Exactly 5 test task entries: `test_001` through `test_005` |

Each item under `train_tasks` and `test_tasks` is a formal task:

| Field | Required | Description |
| --- | --- | --- |
| `task_id` | Yes | Task identifier unique within the task group; use `train_001` or `test_001` |
| `input` | Yes | Solver input directory |
| `prompt_txt` | Yes | Solver-visible task request |
| `payloads` | Yes | List of solver-visible payload files; must include `input/payloads/answer_template.json` |
| `notes` | Yes | Hidden bilingual notes file in English and Chinese; use `<task>/notes/notes.md` |
| `output` | Yes | Standard-answer directory |
| `answer_json` | Yes | Standard-answer file |
| `eval.script` | Yes | Evaluation entry script |
| `eval.files` | Yes | Evaluation-related files |
| `eval.rubric` | Yes | 6-10 scoring points; each item uses `goal` and `weight`; each `weight` can only be `1`, `2`, or `3`, and its final score contribution is `weight / sum(weight)` |

## answer_template.json

Every train and test task must provide:

```text
input/payloads/answer_template.json
```

This file is solver-visible and specifies the exact expected output format. It should include:

- Required top-level keys and nested keys.
- Field types, such as number, integer, boolean, enum, list, object, or string.
- Numeric precision and units for scored numeric values.
- Allowed enum values for classifications, statuses, actions, tags, or other choice fields.
- List ordering rules, stable identifiers, and required object keys.

`answer_template.json` should remove output-schema uncertainty without revealing answers, scoring weights, hidden notes, SOPs, or evidence shortcuts.
