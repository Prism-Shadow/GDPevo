# Metrics And Scoring

## Single Attempt Score

每个 solver attempt 只求解一个 target test task，并输出：

```text
answer.json
```

主 agent 使用 target test task 的 evaluator 对该 answer 评分，得到 0 到 1 之间的
score。

## Task-Level acc@3

对一个非对角线矩阵单元格 `<source> -> <target>`，每道 target test task 有 3 个 score：

```text
attempt_01 score
attempt_02 score
attempt_03 score
```

这 3 个 attempt 分别对应 3 个既有独立 source skill。

该 test task 的 `acc@3`：

```text
mean(score_01, score_02, score_03)
```

## Task-Level std@3

使用 population standard deviation：

```text
sqrt(((score_01 - mean)^2 + (score_02 - mean)^2 + (score_03 - mean)^2) / 3)
```

## Cell-Level acc@3

一个矩阵单元格包含 target task group 的 5 道 test tasks。

单元格 `acc@3`：

```text
mean(test_001_acc@3, test_002_acc@3, test_003_acc@3, test_004_acc@3, test_005_acc@3)
```

## Cell-Level std@3

单元格 `std@3`：

```text
mean(test_001_std@3, test_002_std@3, test_003_std@3, test_004_std@3, test_005_std@3)
```

## Heatmap Value

热力图颜色和值默认使用 cell-level `acc@3`。

`std@3` 保存在 `report/matrix.yaml`、`report/matrix.json` 和
`heatmaps/data/matrices.json` 中，便于后续做稳定性分析。

source 和 target 相同的主对角线单元格标记为 `not_required`，不参与评分和聚合。
