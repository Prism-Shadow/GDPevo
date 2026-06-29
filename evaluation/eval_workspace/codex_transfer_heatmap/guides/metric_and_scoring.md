# Metrics And Scoring

## Single Attempt Score

Each solver attempt solves one target test task and writes:

```text
answer.json
```

The main agent scores that answer with the target test task evaluator. The
resulting score must be between 0 and 1.

## Task-Level acc@3

For one off-diagonal matrix cell `<source> -> <target>`, each target test task
has 3 scores:

```text
attempt_01 score
attempt_02 score
attempt_03 score
```

These 3 attempts correspond to 3 existing independent source skills.

The test task `acc@3` is:

```text
mean(score_01, score_02, score_03)
```

## Task-Level std@3

Use population standard deviation:

```text
sqrt(((score_01 - mean)^2 + (score_02 - mean)^2 + (score_03 - mean)^2) / 3)
```

## Cell-Level acc@3

One matrix cell contains the target task group's 5 test tasks.

The cell `acc@3` is:

```text
mean(test_001_acc@3, test_002_acc@3, test_003_acc@3, test_004_acc@3, test_005_acc@3)
```

## Cell-Level std@3

The cell `std@3` is:

```text
mean(test_001_std@3, test_002_std@3, test_003_std@3, test_004_std@3, test_005_std@3)
```

## Heatmap Value

Heatmap colors and labels use cell-level `acc@3` by default.

`std@3` is preserved in `report/matrix.yaml`, `report/matrix.json`, and
`heatmaps/data/matrices.json` for later stability analysis.

Diagonal cells where source and target are the same task group are marked
`not_required` and are excluded from scoring and aggregation.
