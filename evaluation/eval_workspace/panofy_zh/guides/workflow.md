# 评估流程

本文说明主评估 agent 如何在 Panofy 平台上完整跑一次评估。

这里的 solver 是**通过 SDK 访问的、训练好的 Panofy agent**。你通过
SDK（`train`、`predict`）和每个 task 自带的官方 `eval/eval.sh` 来驱动
评估。每次 `predict()` 本身就是一次隔离的 function-mode 运行，只能看到
自己的 `FUNC_INPUT`，所以没有 subagent 需要 staging 或限制。需要时把临时
SDK / 聚合脚本写在 `scratch/` 下，并在 `README.md` 所述的 `uv` 环境中运行。

agent 在**训练时根据 train task 进行 evolve**：训练 instruction 让它从这些
任务上学习、在这一类任务上变强。一个条件就是一组特定训练材料加一条训练
instruction。

## 1. 准备 Task Group

本工作区一次评估一个 task group：

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

同时用运行时 base URL 和 API key 列一下 agents
（`panofy.agents.list()`；这不是 test-task `predict()` run）确认 Panofy 连通性。

## 3. 指向远程环境

Panofy agent 运行在远端、**可以发起外网 HTTP 请求**，但够不到本地服务。
因此任务环境必须部署在 `.env` 提供的远程 URL 上：

```text
PANOFY_ENV_BASE_URL=<remote task-group environment URL>
PANOFY_JUDGE_PATH=/api/judge
```

把 env base URL 注入每次 `FUNC_INPUT` 的 `api_base_url`；agent 据此访问
task prompt 中点名的公开 GET 端点。运行前确认 env 的 health / index 端点
能返回 HTTP 200，且暴露端点与本地 `task_group/env` server 的**公开投影**
一致。隐藏 / 构造字段不得暴露。

只有 reflect 训练会收到 judge 端点。它只在 reflect 训练期间对 train tasks
有效，绝不能放入 test `FUNC_INPUT`，也不能写入最终 test-time agent
instructions。

## 4. 训练 Agent

**为每个条件训练 3 个独立 agent**：

```text
base
fewshot
self
reflect-3
```

`attempt_<nn>` 对应一个训练好的 agent，让 acc@3 能捕捉训练方差。各条件的
差异只在训练材料和训练 instruction；详见 `evolve_modes.md`。

将每个条件的材料 staging 到专属目录，例如：

```text
scratch/materials/base/attempt_01/
scratch/materials/fewshot/attempt_01/
scratch/materials/self/attempt_01/
scratch/materials/reflect-3/attempt_03/
```

训练材料边界：

- `base`：不使用 task-specific train 材料，只给通用 instruction 和远程环境 URL。
- `fewshot`：train inputs 加 train 标准答案。
- `self`：train inputs 加远程环境 URL；不含 train answers，也不含 judge feedback。
- `reflect-3`：train inputs、远程环境 URL 和 judge API 调用说明；不含 train
  answers。

train 和 test 都先构造同一种官方 task input packet：`task_id`、`prompt`、
`api_base_url`、`answer_template`，以及该 task 声明的所有 input payload 文件，排除
`answer_template.json`。如果 task prompt 引用了
`input/payloads/month_end_exception_scope.json` 这类较长相对路径，在任何使用该 packet
的地方都追加同一条简短 runner note：`Runner note: 官方 input payload
input/payloads/month_end_exception_scope.json 已上传，agent 可按文件名
month_end_exception_scope.json 访问。` 该 packet 不包括 notes、evaluator 文件，也不包括
标准答案，除非当前模式明确允许使用标准答案。

Reflect 训练中，agent 先根据可见 input 作答某个 train task，然后调用：

```text
POST {PANOFY_ENV_BASE_URL}{PANOFY_JUDGE_PATH}
```

请求体：

```json
{"task_id": "train_001", "answer": <candidate answer JSON>}
```

返回值只包含分数 / 正确性反馈，不暴露标准答案或 evaluator 细节。

不要把任何 test task、test 答案、test note 或 evaluator 放进训练材料。
对每个 `(condition, attempt)` 使用 SDK 的异步一站式 `train()`，将返回的
`agent_id` 记录到 `agents/registry.json`。训练用量不计入 solver 效率指标。
如果一次训练调用失败，或返回的 agent 无法确认已完成训练，就为同一个
`(condition, attempt)` 重新发起一次全新的独立 `train()`，并单独保留失败记录。
不要使用 SDK 的 `retrain` 接口来恢复失败训练。

## 5. 运行 Test 实验

对每个条件，每个 test task 独立运行 3 次。`attempt_<nn>` 的 solver 使用同一
条件、同一 attempt 编号训练出的 agent。每次 `predict()` 只收到官方 test
`FUNC_INPUT`，且 top-level keys 固定为：

```text
task_id
prompt
api_base_url
answer_template
```

test `FUNC_INPUT` 在所有条件下相同；唯一变化是训练好的 agent。不要把 test
标准答案、notes、evaluator 细节、train 材料或 judge 端点说明放进 test
`FUNC_INPUT`。

每次 test `predict()` 前，runner 必须从该 task input packet 收集官方 input payload
文件，并在同一次 SDK 调用里通过 `files=` 参数上传，或使用等价的 SDK 文件输入机制并确保
记录/上传的是同一批文件。只上传官方 input payload。官方 input payload 文件属于允许的
test 输入，不算污染。

模式允许的训练阶段暴露不算污染：例如 fewshot 训练可以使用 train 标准答案。下面的污染检查
只针对 test-time inputs、instructions、responses 和 run artifacts。

如果 test agent 的回复或 run artifact 显示 `FUNC_INPUT` 泄漏了禁止材料，或
test-time agent 看到了 test 答案、notes、evaluator 细节、env 源码、judge 调用说明、
当前模式/阶段不允许的 train 材料或其它 run files，停止使用该结果。将该 attempt
标记为污染，及时报告给用户，排除出聚合，并用修正后的 input 在新的干净 run 目录中
重跑受影响任务。

一次只答一个、逐个顺序跑：每次 `predict()` 只回答一个 test task，5 个 test
task 一个一个来。不要把多个任务塞进同一次输入，也不要并发发起 predicts。

推荐记录布局。每次 attempt 和重跑都使用全新目录，不要覆盖旧 attempt 目录：

```text
runs/<condition>/test_001/attempt_01/func_input.json
runs/<condition>/test_001/attempt_01/answer.json
runs/<condition>/test_001/attempt_01/score.yaml
runs/<condition>/test_001/attempt_01/run_metadata.yaml
```

使用 `predict_with_metadata()` 捕获 `run.usage`，并设置 `output_dir=None`。如果 task
有额外官方 input payload 文件，调用形式应为 `predict_with_metadata(func_input,
files=<official_payload_paths>, output_dir=None)` 或 SDK 等价形式，并保持文件解析开启；
没有额外 payload 文件时才可以使用 `resolve_files=False`。`answer.json` 是解析后的
`FUNC_OUTPUT`。

## 6. 打分与聚合

每次 `predict()` 写出 `answer.json` 后，用该 task 的 **`eval/eval.sh`**，把
prediction 路径作为 `$1` 传入来打分。读取已归一到 `[0,1]` 的
`total_score`；必要时从 earned / max 字段推导归一分数。写入 `score.yaml`。

将 SDK 返回的 token 用量写入 `run_metadata.yaml`，并带唯一 `eval_attempt_id`：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

所有 `score.yaml` 就绪后，聚合每个 task 的 `acc@3` 和 `std@3`、整体 `acc@3` 和 `std@3`，以及每个
条件的平均 token buckets。效率指标只统计 **test-task 的 `predict()`** 工作；
不包含训练、远程环境检查或 evaluator 执行。聚合方式同 `acc@3`：先对同一
test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。最终报告按
`report_format.md` 写入 `report/<task_group_id>.yaml`。

## 7. 解读结果

在报告或附带说明中解释：

- 四种条件各自的整体 `acc@3` 和 population `std@3`。
- `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。
- 哪些 test tasks 明显提升、哪些没有。
- 每个条件的 token 用量。
- 任何环境不稳、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。

## 失败处理

以下情况记为失败并在报告中说明：`predict()` 抛错、agent 返回无法解析的
`answer.json`、evaluator 失败，或无法确定 `[0,1]` 分数。失败后重试，直到
拿到一次有效可打分的 attempt，并把失败记录保留在 attempt 目录里。不要把
失败 attempt 记为 `0`，也不要丢掉它继续算 `acc@3`。如果重试仍拿不到有效
分数，停下并报告问题。
