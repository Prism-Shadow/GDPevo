# 评估流程

本文说明主评估 agent 如何在 Panofy 平台上完整跑一次评估。

这里的 solver 是**通过 SDK 访问的、训练好的 Panofy agent**。你通过直接调用 SDK（`train`、`predict`）并运行每个 task 自带的官方 `eval/eval.sh` 来驱动评估。每次 `predict()` 本身就是一次隔离的 function-mode 运行，只能看到自己的 `FUNC_INPUT`，所以没有 subagent 需要 staging 或限制。需要时把临时的 SDK / 聚合脚本写在 `scratch/` 下，并在 `uv` 管理的环境里运行（见 `README.md` 的「环境准备」）。`panofy` 包自带的 README 有确切的调用签名。

agent 在**训练时根据 train task 进行 evolve**:训练 instruction 让它从这些任务上学习、在这一类任务上变得更强。**不导出任何东西**,进化烤进训练好的 agent。所以一个条件就是一组特定的训练材料 + instruction。

## 1. 准备 Task Group

本工作区一次评估一个 task group，位于：

```text
task_group/<task_group_id>/
```

该 task group 必须已通过质量审核。

## 2. 检查工作区

确认工作区只包含一个 task group，且包含：

- 5 个 train tasks。
- 5 个 test tasks。
- task-group 级别的共享环境（`env/`）。
- 每个 task 的官方 input、标准答案和 evaluator（`eval/eval.sh`）。

同时用运行时的 base URL + API key 列一下 agent（`panofy.agents.list()`；不消耗 points）确认 Panofy 连通性。

## 3. 指向远程环境

训练好的 agent 运行在远端、**可以发起外网 HTTP 请求**，但够不到本地服务。因此任务环境部署在**启动 prompt 给出的远程 URL** 上。你把这个 URL 注入每次 `FUNC_INPUT` 的 `api_base_url`；agent 据此对 task prompt 里点名的端点发起 GET。

运行前确认：

- env 的 health / index 端点能正常返回 HTTP 200。这个路径**各 task group 不统一**——可能是 `/health`、`/api/health`、或就是 `/`（HTML 首页）；以 `task_group/env` 为准看本组用的是哪个。
- 暴露的端点返回的是与本地 `task_group/env` server 相同的**公开投影**——隐藏 / 构造字段不得暴露。

把 env URL 和重启记录写进 `scratch/`。不要进入或向 agent 暴露隐藏的 `env/` 字段；它只看到远程 URL。

## 4. 训练 Agent

**为每个条件训练 3 个独立 agent**——`attempt_<nn>` → 一个 agent——这样 acc@3 能捕捉训练方差。每个条件之间唯一不同的只是训练材料和训练 instruction（见 `evolve_modes.md`）。

把每个条件的材料 staging 到专属目录，例如：

```text
scratch/materials/base/attempt_01/
scratch/materials/demo/attempt_01/
scratch/materials/reflect/attempt_01/
```

对 `reflect`，材料同样包含 train 标准答案（agent 需要它来反思）；差别在 instruction，它要求「盲做 / 对答案 / 反思」这个循环。然后用 SDK 的**异步**一站式 `train()`（用 `asyncio.run` 包一下）训练每个 (condition, attempt)；它会建 agent、上传材料、训练到完成，并返回新的 `agent_id`。把每个 `agent_id` 记录到 `agents/registry.json`。训练成本**不**计入 solver 效率指标。

不要把任何 test task、test 答案、test note 或 evaluator 放进训练材料。只允许 train 输入和 train 标准答案。

## 5. 运行 Base 实验

每个 test task 独立运行 3 次。`attempt_<nn>` 的 solver 是训练为 `attempt_<nn>` 的 `base` agent。每次 `predict()` 只收到该 test task 的官方 `FUNC_INPUT`——`task_id`、`prompt`、`api_base_url`、`answer_template`——以及允许的远程 env URL。

**一次只答一个、逐个顺序跑（三个条件都适用）：** 每次 `predict()` 只回答一个 test task，5 个 test 一个一个来——不要把多个任务塞进同一次输入，也不要并发发起 predict。平台对并发任务有上限，重叠运行会失败。

建议记录布局：

```text
runs/base/test_001/attempt_01/func_input.json
runs/base/test_001/attempt_01/answer.json
runs/base/test_001/attempt_01/score.yaml
runs/base/test_001/attempt_01/run_metadata.yaml
```

不要把标准答案、notes 或 evaluator 细节放进任何 test `FUNC_INPUT`。用 `Panofy(base_url, api_key, agent_id)` 客户端作答：调 `predict(func_input)`（FUNC_INPUT 作单个位置参数），传 `resolve_files=False` 和 `output_dir=None`，因为这些输入都是纯 JSON 值（没有本地文件路径）；用 `predict_with_metadata()` 同时拿到 `run.usage` 和 `run.points_consumed`。`answer.json` 就是它返回的、解析后的 `FUNC_OUTPUT`。

## 6. 运行 Demo 实验

每个 test task 独立运行 3 次。`attempt_<nn>` 由训练为 `attempt_<nn>` 的 `demo` agent 作答：

```text
attempt_01 -> demo agent attempt_01
attempt_02 -> demo agent attempt_02
attempt_03 -> demo agent attempt_03
```

test `FUNC_INPUT` 与 base 条件完全一致；只是 agent 不同（它在 5 个已解 train task 上训过）。记录在 `runs/demo/test_00N/attempt_0M/`。

## 7. 运行 Reflect 实验

与 §6 相同，换成 `reflect` agent（用反思 instruction 训练）。记录在 `runs/reflect/test_00N/attempt_0M/`。

## 8. 打分与聚合

每次 `predict()` 写出 `answer.json` 后，用该 task 的 **`eval/eval.sh`**、把 prediction 路径作为 `$1` 传入来打分——这个入口每个 task 都有，会自动路由到它所用的 evaluator（`evaluate.py` / `eval.py` / `evaluator.py` / rubric）。读取 `total_score`（已归一到 `[0,1]`）写入 `score.yaml`。

token 用量和 points 直接来自 SDK——不用解析 transcript。`predict_with_metadata()` 返回 `run.points_consumed` 和 `run.usage`（`cache_read`、`cache_write`、`output_token`）。把它们记进 `run_metadata.yaml`，并带一个唯一的 `eval_attempt_id`：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

所有 `score.yaml` 就绪后，聚合每个 task 的 `acc@3`、整体 `acc@3`，以及每个条件的平均 points / 各桶 token。这些效率指标只统计 **test-task 的 `predict()`** ——不含训练（进化步骤）、环境启动或 evaluator 执行。聚合方式同 `acc@3`：先对同一 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。临时聚合代码放 `scratch/`。最终报告按 `report_format.md` 写入 `report/<task_group_id>.yaml`。

## 9. 解读结果

在报告（或附带说明）中解释：

- 三种条件各自的整体 `acc@3`。
- 每个 evolve 条件相对 base 的提升。
- reflect 是否优于 demo。
- 哪些 test tasks 明显提升、哪些没有。
- 每个条件的 point / token 成本——训练是在「花更少 points」的同时买到准确率，还是更多？
- 任何环境不稳、输出 schema 摩擦（agent 必须返回严格匹配 `answer_template` 的 JSON）、evaluator 问题或可疑的泄漏风险。

## 失败处理

以下情况记为失败并在报告中说明：`predict()` 抛错、agent 返回无法解析的 `answer.json`、evaluator 失败 / 返回不了 `[0,1]` 分。失败后重试，直到拿到一次有效可打分的 attempt，并把失败记录保留在 attempt 目录里。不要把失败的 attempt 记 `0` 分，也不要丢掉它继续算 `acc@3`。如果重试仍拿不到有效分，停下并报告问题。
