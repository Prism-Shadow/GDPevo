# Evolution Modes

This evaluation compares three conditions over the same task group, the same test
tasks, the same model, and the same evaluators. They differ only in the **Panofy
training setup** — the materials uploaded and the training instruction. The
instruction tells the agent to **evolve from the train tasks**: learn from them
and get better at this family of tasks. Nothing is extracted — the evolution is
baked into the trained agent, and the test-time call is `predict()`.

For each condition, train 3 independent agents (`attempt_01..03`).

All three conditions share one input/output contract, stated in the
`function_definition.md` you stage as a training material:

- `FUNC_INPUT` = `{ task_id, prompt, api_base_url, answer_template }`
- `FUNC_OUTPUT` = a single JSON object matching `answer_template` exactly.

The agent reads `prompt`, issues live GETs against `api_base_url` for the
endpoints the prompt names, applies the rules, and returns the answer JSON.

## base (baseline)

No evolution. Train the agent on the **contract only**: `function_definition.md`
plus one schema-only example whose `FUNC_OUTPUT` is the `answer_template` shape
(empty strings, zeros, enum spellings) — no real train task is revealed. The
instruction says to solve directly from the input, with no prior worked examples.
This is the denominator for the lift.

The solver (this trained agent) may see:

- The current test task `FUNC_INPUT` (`prompt`, `api_base_url`, `answer_template`).
- The allowed remote env URL.

The solver must not see:

- Train tasks, test standard answers, test notes, evaluator details.

## fewshot

Train 3 independent agents on the **5 solved train tasks** as example pairs
(`FUNC_INPUT.json` / `FUNC_OUTPUT.json` plus
`train_example_02..05_{INPUT,OUTPUT}.json`), where each `OUTPUT` is that train
task's gold `answer.json`. The training instruction tells the agent to **evolve
from these train tasks**: study the solved examples, internalise the
**transferable** procedure — SOP, field definitions, inclusion/exclusion rules,
rounding, sort order, common pitfalls — and apply it to new inputs. The aim is a
reusable procedure that transfers.

The training (evolution) may see:

- Official `FUNC_INPUT` for the 5 train tasks.
- Standard `output/answer.json` for the 5 train tasks.
- The allowed remote env URL.

The training must not see:

- Test standard answers, test notes, evaluator details.

The solver sees the same as `base` (the test `FUNC_INPUT` + env URL); the
difference is which trained agent answers.

## reflect

Train 3 independent agents. Materials are the **same 5 solved train tasks**; only
the instruction differs. It tells the agent to **evolve from these train tasks by
reflection**:

1. For each train input, first work out the answer itself from the prompt and the
   API rules.
2. Compare against the provided correct answer.
3. Identify exactly where and why it diverged (misread rule, wrong filter,
   rounding, sort, enum).
4. Distil those corrections into a transferable procedure with explicit pitfalls.
5. Apply that corrected procedure to new inputs.

The blind-attempt / compare / reflect loop is requested in the **training
instruction** and carried out during training.

## Evolution quality

Good evolution yields executable, transferable experience. The training
instruction should drive the agent to internalise:

- Transferable business rules and SOPs that re-apply to the test tasks.
- How to use the exposed env API endpoints.
- Output field definitions and exact enum spellings.
- Common misjudgements and exclusion rules.

The training must not introduce:

- Anything derived from a test task, test answer, note, or evaluator.
- Rote memorisation of specific train values.
