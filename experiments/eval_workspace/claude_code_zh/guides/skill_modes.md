# Skill Modes

本评估比较三种条件。三种条件必须使用同一个 task group、同一批 test tasks、同一套模型和 reasoning/effort 配置，以及同一套 evaluators。

主 agent 应将每个 subagent 允许读取的材料 staging 到该 subagent 专属目录中，并将该 subagent 限定在该目录内。不要把完整 task group 目录交给 skill-generation 或 solver subagents。

## base

不生成 skill。

Solver 可以看到：

- 当前 test task 的 `input/`。
- 允许的环境入口，例如暴露的端口、Web/API URL 或数据库连接。

Solver 不能看到：

- Train tasks。
- Test 标准答案。
- Test notes。
- Evaluator 实现细节。

## demo

这个条件下，使用 3 个干净上下文的 skill-generation subagents 生成 3 个独立 skills。每个 generator 应使用 `skill-creator` skill。

Skill generator 可以看到：

- 5 个 train tasks 的正式 `input/`。
- 5 个 train tasks 的标准 `output/answer.json`。
- 允许的暴露端口、Web/API URL 或数据库连接。

Skill generator 不能看到：

- Test 标准答案。
- Test notes。
- Evaluator 实现细节。

将生成的 skills 保存为：

```text
skills/demo/demo_attempt_01/SKILL.md
skills/demo/demo_attempt_02/SKILL.md
skills/demo/demo_attempt_03/SKILL.md
```

Solver 可以看到：

- 当前 test task 的 `input/`。
- 允许的暴露端口、Web/API URL 或数据库连接。
- 与 solver attempt 编号匹配的 demonstration skill。

## reflect

这个条件下，使用 3 个干净上下文的 skill-generation subagents 生成 3 个独立 skills。每个 generator 应使用 `skill-creator` skill，并通过独立尝试、答案对比和错误反思生成 skill。

生成流程：

1. 只读取 5 个 train tasks 的正式 `input/`，以及允许的暴露端口、Web/API URL 或数据库连接。
2. 独立完成 5 个 train tasks，并保存 blind attempts。
3. 读取 5 个 train tasks 的标准 `output/answer.json`。
4. 将自己的答案与标准答案对比，并反思错误来源。
5. 总结可迁移 SOP、字段定义、环境使用方法、业务判断规则和常见错误点。

将生成的 skills 保存为：

```text
skills/reflect/reflect_attempt_01/SKILL.md
skills/reflect/reflect_attempt_02/SKILL.md
skills/reflect/reflect_attempt_03/SKILL.md
```

Solver 可以看到：

- 当前 test task 的 `input/`。
- 允许的暴露端口、Web/API URL 或数据库连接。
- 与 solver attempt 编号匹配的 reflection skill。

## Skill 质量要求

Skill 应该是可执行的经验，而不是 train answers 的复述。

好的 skill 应包含：

- 可迁移的业务规则。
- 如何使用暴露的 Web/API 或数据库环境。
- 输出字段定义。
- 常见误判和排除规则。
- 从 train tasks 学到、并需要重新应用到 test tasks 的 SOP。

Skill 不能包含：

- Test task 答案或推导。
- 不可迁移的单个 train example 复述。
- 暴露或猜测 evaluator checkpoints 的推测性内容。
