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

Train 3 independent agents for `reflect-3`. This condition runs 3 epochs over
the five train tasks.

Reflect training materials may include:

- Official train `FUNC_INPUT`.
- The remote environment URL.
- The train-only judge API instruction:

```text
POST {PANOFY_ENV_BASE_URL}{PANOFY_JUDGE_PATH}
Content-Type: application/json

{"task_id": "train_001", "answer": <candidate answer JSON>}
```

The judge response contains `correct` and normalized `score`; it rejects test
task ids. Reflect training must not include train gold answers, test tasks, test
answers, notes, or evaluator source.

The reflect instruction should require the agent to attempt all 5 train tasks in
each of 3 epochs, submit candidate answers to the judge, use the returned score
as feedback, revise its internal procedure, and apply the final procedure at
test-time.

## Evolution Quality

Good evolution yields executable, transferable experience:

- Transferable business rules and SOPs.
- How to use the exposed env API endpoints.
- Output field definitions and exact enum spellings.
- Common misjudgements and exclusion rules.

The training must not introduce anything derived from a test task, test answer,
note, or evaluator.
