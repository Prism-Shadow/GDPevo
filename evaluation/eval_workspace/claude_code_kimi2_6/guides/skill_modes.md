# Skill Modes

This evaluation compares four conditions over the same task group, test tasks,
Kimi 2.6 model configuration, `xhigh` effort setting, remote environment, and
evaluators:

```text
base
fewshot
self
reflect-3
```

Use `fewshot` as the report/directory key for the few-shot condition.

The main agent stages the allowed materials for each skill-generation or solver
subagent into that subagent's dedicated directory. Do not give subagents the full
task group directory.

Never stage an entire train task or test task directory. Stage only the
allowlisted files for the current mode. `notes/`, `eval/`, `env/`, unrelated
tasks, and previous run outputs are never allowlisted for subagents.

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

The generator must not see train `notes/`, train `eval/`, test answers, test
notes, evaluator files, `env/`, or any full task directory copy.

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
- Train `notes/` or `eval/`.
- The judge endpoint or judge feedback.
- Test answers, test notes, or evaluator files.
- `env/` or any full task directory copy.

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

Generate 3 independent reflect skills. In each reflect skill generation run,
process `train_001` through `train_005` in order.

A judge-feedback round means: produce a candidate answer for the current train
task, submit it to `POST /api/judge`, receive only `score` and `correct`
feedback, and use that feedback to adjust the next attempt on the same train
task.

The generator may see:

- Official `input/` for the 5 train tasks.
- The remote environment entrypoint.
- The train-only judge API description above.

The generator must not see:

- Train `output/answer.json`.
- Train `notes/` or `eval/`.
- Test answers, test notes, or evaluator files.
- `env/` or any full task directory copy.

For each train task in a reflect skill generation run, the generator should run
this 3-round loop before moving to the next train task:

1. Read only the current train task input, the remote environment entrypoint,
   and the judge API instructions.
2. Produce a candidate answer for the current train task.
3. Submit that candidate answer to `POST /api/judge`.
4. Record the returned `score` and `correct` values.
5. Use the judge feedback to adjust the next attempt on the same train task.
6. Repeat until exactly 3 judge submissions have been made for that train task.

After all 5 train tasks have each completed their 3 judge-feedback rounds,
distill the accumulated transferable lessons into the matching skill. The skill
should contain reusable workflow rules, not candidate answers, train gold
answers, or test-time judge instructions:

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
