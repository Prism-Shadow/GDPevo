# Skill Modes

This workspace uses only two modes:

```text
fewshot
reflect-3
```

It consumes existing skills. It does not generate, revise, or train skills.

Common rules:

- Use 3 existing independent skills for each source task group and mode.
- The `attempt_01` solver must use the `attempt_01` skill; `attempt_02` and
  `attempt_03` follow the same mapping.
- Testing uses the target task group's test tasks.
- No train task materials or train answers are staged in this workspace.

## fewshot

Required skill paths:

```text
skills/fewshot/<source_task_group_id>/fewshot_attempt_01/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_02/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_03/SKILL.md
```

Use the existing fewshot skills for the source task group. This transfer
workspace should not expose train answers or regenerate fewshot skills.

## reflect-3

Required skill paths:

```text
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_01/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_02/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_03/SKILL.md
```

Use the existing reflect-3 skills for the source task group. This transfer
workspace should not expose train answers or regenerate reflect-3 skills.

## Solver Exposure

For every mode, a test solver may see only:

- The current target test task `input/`.
- The target task group's remote environment entrypoint.
- The `SKILL.md` matching the current source/mode/attempt.

The solver must not see source or target train tasks, standard answers, notes,
evaluator files, `env/` source files, or another attempt's working directory.
