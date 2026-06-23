# Evolution Modes

This evaluation compares four conditions over the same task group, test tasks,
model, remote environment, and evaluators:

```text
base
fewshot
self
reflect-3
```

For each condition, train 3 independent agents (`attempt_01..03`). All
conditions share one test-time contract:

- `FUNC_INPUT` = `{ task_id, prompt, api_base_url, answer_template }`
- `FUNC_OUTPUT` = a single JSON object matching `answer_template` exactly.

The agent reads `prompt`, issues live requests against `api_base_url`, applies
the rules, and returns the answer JSON.

## base

No evolution. Train the agent on the contract only: `function_definition.md`
plus one schema-only example. No real train task is revealed.

## fewshot

Train 3 independent agents on the 5 solved train tasks as example pairs. The
training materials may include:

- Official train `FUNC_INPUT`.
- Gold train `FUNC_OUTPUT` from `output/answer.json`.
- The remote environment URL.

Training must not include test tasks, test answers, notes, or evaluator source.

## self

Train 3 independent agents with train inputs but without train outputs or judge
feedback. The instruction asks the agent to reason through the train tasks from
its own work and internalize transferable SOPs, field definitions, environment
usage, and pitfalls.

Training materials may include:

- Official train `FUNC_INPUT`.
- The remote environment URL.

Training must not include train gold answers, judge feedback, test tasks, test
answers, notes, or evaluator source.

## reflect-3

Train 3 independent agents for `reflect-3`. Each independent agent processes
`train_001` through `train_005` in order.

A judge-feedback round means: produce a candidate answer for the current train
task, submit it to the train-only judge, receive only `score` and `correct`
feedback, and use that feedback to adjust the next attempt on the same train
task.

Reflect training materials may include:

- Official train `FUNC_INPUT`.
- The remote environment URL.
- The train-only judge API instruction:

```text
POST {PANOFY_ENV_BASE_URL}{PANOFY_JUDGE_PATH}
Content-Type: application/json

{"task_id": "train_001", "answer": <candidate answer JSON>}
```

The judge response contains `correct`, normalized `score`, `scope: train_only`,
and a `notice` reminding the agent that this endpoint is only for train-task
feedback. It rejects test task ids. The judge API is valid only during reflect
training on train tasks; it is not a test-time tool, and final agent
instructions must not tell test agents to call it. Reflect training must not
include train gold answers, test tasks, test answers, notes, or evaluator
source.

The reflect instruction should require the agent to run this 3-round loop for
each train task before moving to the next one:

1. Read only the current train task input, the remote environment URL, and the
   judge API instruction.
2. Produce a candidate answer for the current train task.
3. Submit that candidate answer to the judge.
4. Record the returned `score` and `correct` values.
5. Use the judge feedback to adjust the next attempt on the same train task.
6. Repeat until exactly 3 judge submissions have been made for that train task.

After all 5 train tasks have completed this loop, the final procedure is applied
at test-time. It should not include candidate answers, train gold answers, or
test-time judge instructions.

## Evolution Quality

Good evolution yields executable, transferable experience:

- Transferable business rules and SOPs.
- How to use the exposed env API endpoints.
- Output field definitions and exact enum spellings.
- Common misjudgements and exclusion rules.

The training must not introduce anything derived from a test task, test answer,
note, or evaluator.
