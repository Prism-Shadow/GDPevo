# Skill Modes

本工作区只使用两个 mode：

```text
fewshot
reflect-3
```

本工作区消费既有 skills，不生成、不修订、不训练 skills。

下文每个 attempt 目录都是一个完整 skill 目录包，`SKILL.md` 是必需入口文件。
运行时应把整个匹配 attempt 目录 staging 为 `/work/skill/`，不能只抽出一个
`SKILL.md`。

共同规则：

- 每个 source task group、每个 mode 使用 3 个既有独立 skill。
- `attempt_01` solver 必须使用 `attempt_01` skill；`attempt_02` 和
  `attempt_03` 同理。
- 测试时使用 target task group 的 test tasks。
- 这个 workspace 不 staging train task 材料或 train answer。

## fewshot

必需 skill 路径：

```text
skills/fewshot/<source_task_group_id>/fewshot_attempt_01/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_02/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_03/SKILL.md
```

使用 source task group 的既有 fewshot skills。这个 transfer workspace 不暴露 train
answers，也不重新生成 fewshot skills。

## reflect-3

必需 skill 路径：

```text
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_01/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_02/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_03/SKILL.md
```

使用 source task group 的既有 reflect-3 skills。这个 transfer workspace 不暴露 train
answers，也不重新生成 reflect-3 skills。

## Solver Exposure

无论 mode 是什么，test solver 只能看到：

- 当前 target test task 的 `input/`。
- target task group 的容器可访问环境入口。
- 当前 source/mode/attempt 对应的完整 skill 目录包，以 `skill/` staging。

solver 不能看到 source 或 target 的 train tasks、standard answers、notes、evaluator
files、`env/` 源文件或其他 attempt 的工作目录。
