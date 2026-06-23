# Skill Modes

This evaluation compares four conditions over the same task group, test tasks,
model configuration, remote environment, and evaluators:

```text
base
fewshot
self
reflect-3
```

Use `fewshot` as the report/directory key for the few-shot condition.

The main agent stages the allowed materials for each skill-generation or solver
subagent into that subagent's dedicated workspace/cwd. Do not give subagents the
full task group directory.

All non-reflect staging should expose only the remote environment URL from
`.env`:

```text
GDPEVO_ENV_BASE_URL=<remote task environment>
```

The main agent may also read the train-only judge path from `.env`, but it must
stage that value only for reflect skill-generation subagents:

```text
GDPEVO_JUDGE_PATH=/api/judge
```

Reflect skill-generation prompts should include this interface:

```text
POST {GDPEVO_ENV_BASE_URL}{GDPEVO_JUDGE_PATH}
Content-Type: application/json

{"task_id": "train_001", "answer": <candidate answer JSON>}
```

The response contains `correct`, normalized `score`, `scope: train_only`, and a
`notice` reminding the agent that this endpoint is only for train-task feedback.
It rejects test task ids. The judge API is valid only while generating reflect
skills on train tasks; it is not a test-time tool, and generated `SKILL.md`
files must not tell solvers to call it.

## base

No skill is generated.

The solver may see only:

- The current test task `input/`.
- The remote environment entrypoint.

The solver must not see train tasks, test answers, test notes, evaluator files,
generated skills, or judge instructions.

## fewshot

Generate 3 independent skills with 3 clean-context skill-generation subagents.
Each generator may see:

- Official `input/` for the 5 train tasks.
- Standard `output/answer.json` for the 5 train tasks.
- The remote environment entrypoint.

The generator must not see test answers, test notes, or evaluator files.

Save the generated skills as:

```text
skills/fewshot/fewshot_attempt_01/SKILL.md
skills/fewshot/fewshot_attempt_02/SKILL.md
skills/fewshot/fewshot_attempt_03/SKILL.md
```

The solver receives the current test input, remote environment entrypoint, and
the matching fewshot skill.

## self

Generate 3 independent skills with 3 clean-context skill-generation subagents.
This mode is self-evolution without train outputs or judge feedback.

The generator may see:

- Official `input/` for the 5 train tasks.
- The remote environment entrypoint.

The generator must not see:

- Train `output/answer.json`.
- The judge endpoint or judge feedback.
- Test answers, test notes, or evaluator files.

The generator should solve or reason through the train tasks from its own work,
then distill transferable SOPs, field conventions, environment usage habits,
and pitfalls into:

```text
skills/self/self_attempt_01/SKILL.md
skills/self/self_attempt_02/SKILL.md
skills/self/self_attempt_03/SKILL.md
```

The solver receives the current test input, remote environment entrypoint, and
the matching self skill.

## reflect-3

Generate 3 independent reflect skills. Each reflect skill generation run should
process all 5 train tasks one task at a time. For each train task, complete
exactly 3 judge-feedback rounds on that task before moving to the next train
task. This is not a global 3-epoch loop over all 5 tasks.

The generator may see:

- Official `input/` for the 5 train tasks.
- The remote environment entrypoint.
- The train-only judge API description above.

The generator must not see:

- Train `output/answer.json`.
- Test answers, test notes, or evaluator files.

For each train task in a reflect skill generation run, the generator should:

1. Attempt the current train task from the visible input and remote environment.
2. Submit the candidate answer to `POST /api/judge`.
3. Record the returned `score` and `correct` values.
4. Reflect on errors, revise the working rules, and retry the same train task.
5. Repeat until exactly 3 judge submissions have been made for that train task.
6. Move to the next train task and repeat the same 3-round loop.

After all 5 train tasks have each completed their 3 judge-feedback rounds,
distill the learned transferable procedure into the matching skill:

```text
skills/reflect-3/reflect-3_attempt_01/SKILL.md
skills/reflect-3/reflect-3_attempt_02/SKILL.md
skills/reflect-3/reflect-3_attempt_03/SKILL.md
```

The solver receives the current test input, remote environment entrypoint, and
the matching `reflect-3` skill.

## Skill Quality Requirements

A skill should be executable experience, not a restatement of train answers.

A good skill should include:

- Transferable business rules.
- How to use the remote Web/API or database environment.
- Output field definitions.
- Common misjudgments and exclusion rules.
- SOPs learned from train tasks that should transfer to test tasks.

A skill must not include:

- Test task answers or derivations.
- Train standard answers copied from `output/answer.json`, except in fewshot
  mode where solved train examples may inform the skill.
- Judge endpoint instructions, judge feedback transcripts, or any instruction
  to call the judge API during test solving.
- Speculative statements that reveal or guess evaluator internals.
