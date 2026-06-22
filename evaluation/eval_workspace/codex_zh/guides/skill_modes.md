# Skill Modes

本评估比较四种条件。四种条件必须使用同一个 task group、同一批 test tasks、同一个模型配置、同一个远程环境和同一套 evaluators：

```text
base
fewshot
self
reflect-3
```

少样本条件在 report 和目录中继续使用 `fewshot` 作为 key。

主 agent 应将每个 skill-generation 或 solver subagent 允许读取的材料 staging 到该 subagent 专属 workspace/cwd 中。不要把完整 task group 目录给 subagent。

所有非 reflect staging 都只应暴露 `.env` 中的远程环境 URL：

```text
GDPEVO_ENV_BASE_URL=<remote task environment>
```

主 agent 也可以从 `.env` 读取 train-only judge path，但这个值只能 staging 给
reflect skill-generation subagents：

```text
GDPEVO_JUDGE_PATH=/api/judge
```

Reflect skill-generation prompt 应显式加入这个接口说明：

```text
POST {GDPEVO_ENV_BASE_URL}{GDPEVO_JUDGE_PATH}
Content-Type: application/json

{"task_id": "train_001", "answer": <candidate answer JSON>}
```

响应包含 `correct`、归一化 `score`、`scope: train_only`，以及提醒 agent
该接口只用于 train-task feedback 的 `notice`。接口会拒绝 test task id。
Judge API 只在基于 train tasks 生成 reflect skills 的阶段有效；它不是
test-time 工具，生成的 `SKILL.md` 不能要求 solver 调用它。

## base

不生成 skill。

Solver 只能看到：

- 当前 test task 的 `input/`。
- 远程环境入口。

Solver 不能看到 train tasks、test 标准答案、test notes、evaluator files、generated skills 或 judge 说明。

## fewshot（少样本进化）

使用 3 个干净上下文的 skill-generation subagents 生成 3 个独立 skills。每个 generator 可以看到：

- 5 个 train tasks 的正式 `input/`。
- 5 个 train tasks 的标准 `output/answer.json`。
- 远程环境入口。

Generator 不能看到 test 标准答案、test notes 或 evaluator files。

保存为：

```text
skills/fewshot/fewshot_attempt_01/SKILL.md
skills/fewshot/fewshot_attempt_02/SKILL.md
skills/fewshot/fewshot_attempt_03/SKILL.md
```

Solver 接收当前 test input、远程环境入口，以及匹配 attempt 编号的 fewshot skill。

## self

使用 3 个干净上下文的 skill-generation subagents 生成 3 个独立 skills。这个模式表示没有 train outputs、也没有 judge feedback 的自我进化。

Generator 可以看到：

- 5 个 train tasks 的正式 `input/`。
- 远程环境入口。

Generator 不能看到：

- Train `output/answer.json`。
- Judge endpoint 或 judge feedback。
- Test 标准答案、test notes 或 evaluator files。

Generator 应基于自己的推理完成或复盘 train tasks，并将可迁移 SOP、字段口径、环境使用习惯和常见陷阱沉淀为：

```text
skills/self/self_attempt_01/SKILL.md
skills/self/self_attempt_02/SKILL.md
skills/self/self_attempt_03/SKILL.md
```

Solver 接收当前 test input、远程环境入口，以及匹配的 self skill。

## reflect-3

生成 3 个独立 reflect skills。`reflect-3` 对 5 个 train tasks 跑 3 个 epochs。

Generator 可以看到：

- 5 个 train tasks 的正式 `input/`。
- 远程环境入口。
- 上面 train-only judge API 的说明。

Generator 不能看到：

- Train `output/answer.json`。
- Test 标准答案、test notes 或 evaluator files。

每个 epoch 中，generator 应：

1. 基于可见输入和远程环境尝试完成全部 5 个 train tasks。
2. 将每个 candidate answer 提交给 `POST /api/judge`。
3. 记录返回的 `score` 和 `correct`。
4. 反思错误、修订工作规则，并把经验带入下一个 epoch。

第三个 epoch 后，将可迁移流程沉淀为对应 skill：

```text
skills/reflect-3/reflect-3_attempt_01/SKILL.md
skills/reflect-3/reflect-3_attempt_02/SKILL.md
skills/reflect-3/reflect-3_attempt_03/SKILL.md
```

Solver 接收当前 test input、远程环境入口，以及匹配的 `reflect-3` skill。

## Skill 质量要求

Skill 应该是可执行经验，而不是 train answers 的复述。

好的 skill 应包含：

- 可迁移业务规则。
- 如何使用远程 Web/API 或数据库环境。
- 输出字段定义。
- 常见误判和排除规则。
- 从 train tasks 学到、应迁移到 test tasks 的 SOP。

Skill 不能包含：

- Test task 答案或推导。
- 从 train `output/answer.json` 复制出的标准答案；fewshot 模式中 solved train examples 可以用于归纳 skill。
- Judge endpoint 调用说明、judge feedback 记录，或任何要求 test solving 时调用 judge API 的指令。
- 暴露或猜测 evaluator internals 的推测性内容。
