# Quality Review Workspace

`review_workspace_zh/` 是第三阶段质量审核的中文工作入口。你是本阶段的主审核 agent，目标是判断一个已经完成构造、校准和内部检查的 `task_group` 是否可以进入最终评估池。

本工作区只审核一个 task group。你需要运行脚本化结构检查，组织 6 个上下文干净的 reviewer subagents 独立投票，并把脚本结果、6 票结论和最终判断汇总到审核报告中。

审核不是继续生产数据，也不是自动过滤。不要修改待审核 task group 的内容；如果发现问题，应在报告中说明并要求回到第二阶段返工。

`task_group/` 只放正式数据本体；`scratch/` 放第二阶段对应的 `task_factory/scratch`。这些 scratch 记录不是 solver 可见输入，也不是正式 task group 的一部分；其中可以包含标准答案、构造草稿、校准记录和反思材料，这本身不算答案泄露。

## Directories

| Path | Purpose |
| --- | --- |
| `guides/` | 审核流程、审核标准和报告格式 |
| `scripts/` | 确定性的结构检查脚本 |
| `task_group/` | 当前待审核的一个 task group |
| `scratch/` | 当前 task group 对应的第二阶段 `task_factory/scratch`，以及审核过程中的临时材料 |

最终审核报告应写入：

```text
../reports/<task_group_id>.yaml
```

## Guides

开始审核前按顺序阅读：

1. `guides/workflow.md` - 第三阶段审核流程和 6 票机制
2. `guides/review_criteria.md` - 脚本检查范围和 reviewer 审核标准
3. `guides/report_format.md` - 最终审核报告格式

## Workflow

1. 确认 `task_group/` 下只放置一个待审核目录：

```text
task_group/<task_group_id>/
```

2. 确认 `scratch/` 下放置同一个 task group 对应的第二阶段 scratch：

```text
scratch/
```

这里的 scratch 指第二阶段生产数据时留下的 `task_factory/scratch`，reviewer 可按需要参考其中的设计、校准、尝试和返工记录。不要因为 `scratch/` 中出现答案或构造 truth 就判定泄露；泄露检查只针对正式 task group 中 solver 可见的输入、payload、answer template 和公开环境入口。

3. 运行脚本化结构检查：

```bash
python3 scripts/check_task_group.py task_group/<task_group_id>
```

4. 如果脚本检查失败，停止审核投票，在报告中记录失败原因，并要求该 task group 回到第二阶段返工。

5. 如果脚本检查通过，启动 6 个上下文干净的 reviewer subagents。每个 reviewer 必须独立阅读同一个 task group 和对应 scratch，并根据 `guides/review_criteria.md` 给出 `pass` 或 `fail`。

6. 将 reviewer 的原始结论保存在 `scratch/`，再汇总生成 `../reports/<task_group_id>.yaml`。

7. 只有同时满足脚本检查通过、6 票中至少 5 票通过，task group 才算通过第三阶段审核。

## Review Principles

- 脚本只检查确定性的结构和自洽性，不判断数据质量。
- 6 个 reviewer 必须上下文干净，不能互相参考结论，也不能由主 agent 在同一上下文里模拟投票。
- Reviewer 应判断 task group 是否适合作为 benchmark 数据，而不是只看文件是否齐全。
- 基于 `task_group/` 和 `scratch/` 重点检查来源场景一致性、train/test 迁移设计、可迁移的 diversity、环境与容器边界、答案泄漏风险、notes 可解释性、评测可信度、rubric 独立性和 partial-credit 行为、Dockerized 难度校准及构造过程。答案泄漏风险只看正式 task group 的 solver-visible surface，不把 `scratch/` 中的构造证据视为泄露。
- 小问题可以作为 `concerns` 记录；答案泄漏、eval 不可信、迁移无效、校准失效或结构缺失应判为 `fail`。
- 返工后的 task group 必须重新运行脚本检查，并重新组织 6 票审核；不能沿用返工前的投票。

## Reviewer Prompt

给每个 reviewer subagent 使用下面的简短任务说明：

```text
Please independently review <task_group_path> and scratch/ using guides/review_criteria.md as the standard. Inspect the actual evaluators and scratch/rubric_validation.md; verify that each task measures multiple independently fail-able business aspects, that selective mistakes do not make all rubric points move together, and that deterministic partial credit works where specified. Also verify the fixed-prompt Dockerized Codex calibration evidence. Do not use other reviewers' conclusions. Return one vote: pass or fail, with concise support for each required check.
```
