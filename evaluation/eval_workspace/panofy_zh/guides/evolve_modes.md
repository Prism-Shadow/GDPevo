# Evolution Modes

本评估比较四种条件。四种条件使用同一个 task group、同一批 test tasks、同一个模型、同一个远程环境和同一套 evaluators：

```text
base
fewshot
self
reflect-3
```

每个条件训练 3 个独立 agent（`attempt_01..03`）。所有条件共用同一套 test-time 契约：

- `FUNC_INPUT` = `{ task_id, prompt, api_base_url, answer_template }`
- `FUNC_OUTPUT` = 一个严格匹配 `answer_template` 的 JSON 对象。

agent 读取 `prompt`，对 `api_base_url` 发起实时请求，应用规则，并返回 answer JSON。

## base

不进化。只用 `function_definition.md` 和一个 schema-only 示例训练 agent，不暴露真实 train task。

## fewshot（少样本进化）

用 5 个已解 train tasks 作为示例对训练 3 个独立 agent。训练材料可以包含：

- 官方 train `FUNC_INPUT`。
- 来自 `output/answer.json` 的 train gold `FUNC_OUTPUT`。
- 远程环境 URL。

训练不得包含 test tasks、test answers、notes 或 evaluator source。

## self

用 train inputs 训练 3 个独立 agent，但不提供 train outputs 或 judge feedback。训练 instruction 要求 agent 基于自己的推理完成/复盘 train tasks，并内化可迁移 SOP、字段定义、环境使用习惯和常见陷阱。

训练材料可以包含：

- 官方 train `FUNC_INPUT`。
- 远程环境 URL。

训练不得包含 train gold answers、judge feedback、test tasks、test answers、notes 或 evaluator source。

## reflect-3

为 `reflect-3` 训练 3 个独立 agent。每个独立 agent 都处理全部 5 个 train
tasks，但应逐题进行：每道 train task 先在同一道题上完成 3 轮
judge-feedback，再进入下一道 train task。这不是对全部 5 题做全局 3 个
epochs。

Reflect 训练材料可以包含：

- 官方 train `FUNC_INPUT`。
- 远程环境 URL。
- Train-only judge API 说明：

```text
POST {PANOFY_ENV_BASE_URL}{PANOFY_JUDGE_PATH}
Content-Type: application/json

{"task_id": "train_001", "answer": <candidate answer JSON>}
```

judge 响应包含 `correct`、归一化 `score`、`scope: train_only`，以及提醒
agent 该接口只用于 train-task feedback 的 `notice`，并拒绝 test task id。
Judge API 只在 reflect 训练的 train tasks 上有效；它不是 test-time 工具，
最终 agent instruction 不能要求 test agent 调用它。Reflect 训练不得包含 train gold answers、test tasks、test answers、notes 或 evaluator source。

Reflect instruction 应要求 agent 按顺序处理 train tasks。对每一道 train
task，agent 应提交 candidate answer 给 judge，用返回的 score 做反馈，修订内部
流程，并在同一道 train task 上重试，直到该 task 正好完成 3 次 judge 提交。
全部 5 个 train tasks 都完成这 3 轮流程后，再将最终流程用于 test-time。

## 进化质量

好的进化应产生可执行、可迁移的经验：

- 可迁移业务规则和 SOP。
- 如何使用暴露的 env API endpoints。
- 输出字段定义和确切枚举拼写。
- 常见误判和排除规则。

训练不得引入任何来自 test task、test answer、note 或 evaluator 的东西。
