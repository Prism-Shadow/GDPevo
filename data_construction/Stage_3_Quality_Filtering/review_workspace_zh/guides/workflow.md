# 审核流程

## 目标

第三阶段审核的目标是判断一个完成构造和校准的 `task_group` 是否可以进入最终评估池。审核不是自动过滤流水线，而是由多个上下文干净的 reviewer 独立判断数据质量。

## 输入约定

审核开始时，`review_workspace_zh/` 中应已经放好一个待审核 task group：

```text
task_group/<task_group_id>/
```

以及它对应的第二阶段 scratch：

```text
scratch/
```

`task_group/` 只放正式数据本体；`scratch/` 放第二阶段 `task_factory/scratch`。这些 scratch 记录不是 solver 可见输入，也不是正式 task group 的一部分，reviewer 可按需要参考。`scratch/` 可以包含标准答案、构造草稿、校准记录和反思材料，这本身不构成答案泄露。

`review_workspace_zh/` 是临时审核工作区，一次只审核一个 task group。

## Agent Workflow

1. 主 agent 读取 `task_group/<task_group_id>/` 和 `scratch/`，确认二者对应同一个 task group。不要修改待审核 task group 的正式数据。

2. 主 agent 运行脚本化结构检查：

```bash
python3 scripts/check_task_group.py task_group/<task_group_id>
```

3. 如果脚本检查失败，停止 reviewer 投票，并在 `../reports/<task_group_id>.yaml` 中记录 `script_check.pass: false` 和失败原因。

4. 如果脚本检查通过，主 agent 启动 6 个上下文干净的 reviewer subagents。每个 reviewer 独立阅读同一个 task group 和对应 `scratch/`，包括 evaluator 实现、`rubric_validation.md`、固定 prompt 校准记录和保留的运行证据，不能参考其他 reviewer 的结论。

5. 每个 reviewer 按 `review_criteria.md` 给出一票：

```text
decision: pass
```

或：

```text
decision: fail
```

6. 主 agent 汇总 6 票，生成 `review_votes`：

- `pass_votes >= 5` 时，`review_votes.pass: true`
- `pass_votes < 5` 时，`review_votes.pass: false`

7. 主 agent 根据 6 个 reviewer 的结论汇总 `manual_review`，并写入：

```text
../reports/<task_group_id>.yaml
```

8. 如果审核不通过，报告中说明需要返工的问题。返工后的 task group 必须重新运行脚本检查，并重新进行 6 票审核；不能沿用返工前的投票。

审核中的脚本输出、reviewer 原始结论和中间汇总可以放在 `scratch/review/`。

## 通过规则

审核通过必须同时满足：

- `script_check.pass: true`
- `review_votes.pass: true`
- `manual_review.overall.pass: true`

## Reviewer Prompt

主 agent 可以给每个 reviewer subagent 使用下面的简短任务说明：

```text
Please independently review <task_group_path> and scratch/ using guides/review_criteria.md as the standard. Inspect the actual evaluators and scratch/rubric_validation.md; verify that each task measures at least 4 semantically distinct business outcomes, does not reward the same underlying criterion or answer fact more than once, and gives each point either all of its assigned score or zero. Also verify the fixed-prompt Dockerized Codex calibration evidence. Do not use other reviewers' conclusions. Return one vote: pass or fail, with concise support for each required check.
```

Reviewer 应重点判断 task group 是否能作为 benchmark 数据，而不是只检查文件是否存在。

泄露检查只针对正式 task group 的 solver 可见部分，例如 prompt、payload、answer template 和公开环境入口。不要因为 `scratch/` 中保存了答案、构造 truth 或生产过程记录而判定泄露；只有这些内容被复制到 solver-visible surface 时才算泄露。
