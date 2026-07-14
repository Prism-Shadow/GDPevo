# Task Design

## Train-Predict Goal

The task group should implement a train-predict workflow: an isolated fewshot generator reads the solver-visible inputs and standard answers of the real train tasks, distills transferable experience into a skill, and test solvers apply that skill to unseen tasks.

The design should satisfy all of the following:

- Train and test tasks come from the same scenario and the same real-task distribution, sharing transferable business context, SOPs, data conventions, tool-use patterns, or key fact types.
- Train tasks must not be teaching problems, tutorials, worked examples, easier versions of test tasks, or explicit SOP demonstrations. They are formal business tasks that happen to be exposed first in the calibration workflow.
- Train and test tasks must not be simple template variants. They need diversity across sub-scenarios, data forms, environment entry points, output schemas, or decision goals.
- Every formal task should align with the complexity and difficulty of the stage 1 examples and preserve long-horizon task characteristics.
- Test tasks must not be solvable only from local input materials. Some SOPs, key facts, field conventions, tool-selection experience, or business-judgment habits must be inferred from the train inputs and standard answers available to fewshot skill generation.

## Example Difficulty Alignment

Before designing tasks, read the source examples and identify their difficulty drivers: data volume, number of systems or tools, ambiguity in source selection, cross-record reconciliation, business-rule depth, long-horizon workflow length, and required verification.

Each train and test task should match that difficulty band. It may use new entities, generated data, and different business surfaces, but it should not collapse the example into a small lookup, a single-file transformation, or a short prompt-following exercise. It should also not become much harder than the examples by adding unrelated systems, hidden rules, or excessive missing information.

The design draft should include an example difficulty audit:

| Source example | Difficulty drivers | Task-group design response |
| --- | --- | --- |
| `E001` | Multi-source CRM/event reconciliation, sponsor-vs-attendee distinction, validation workflow | Reused as event-to-CRM train/test tasks with comparable source conflicts and workflow length |

## Transfer Distance Control

Train/test transfer should be close enough that a real train-derived skill can help, but not so close that test tasks become template copies.

## Diversity Band

Diversity should stay inside a transfer band. A task group should not use its 5 train tasks to cover five unrelated workflow families, then test each family once. That creates a broad but shallow train-derived skill: the skill records many isolated facts, but fewshot attempts still need to rediscover each test task's main business logic.

Prefer 2-3 recurring operation families within the same scenario. Vary the entities, accounts, events, campaigns, products, data volume, noise patterns, source conflicts, environment surfaces, and output schemas while preserving enough repeated decision frames for train-derived experience to transfer.

Reusable conventions should normally appear more than once across the train set, or appear once as a formal train task and be reinforced by another train task through the same source-precedence rule, field convention, calculation style, routing logic, or validation habit. A test task may still contain unanchored high-weight points for real data exploration, but its transfer-dependent core should not rely on a single isolated train/test pair.

Good diversity changes:

- new customer, event, campaign, batch, region, product line, or account set;
- larger or messier records, stale exports, overlapping sources, missing values, and realistic distractors;
- different environment entry points over the same business objects;
- different structured outputs over the same decision frame.

Bad diversity changes:

- a new business objective that no train task exercises;
- a new SOP family that appears only in test;
- a new hidden policy, scoring logic, or source-precedence rule that cannot be inferred from train;
- an integrated board or rollup task when train has no comparable aggregation or repeated component workflows.

Each test task should have a meaningful transfer core: some high-weight scoring points whose correct solution depends on SOPs, source-precedence rules, field conventions, calculations, output conventions, or business judgments that can be inferred from the train inputs and standard answers. These transfer-dependent scoring points should have explicit train anchors, but those anchors should be real tasks rather than simplified teaching examples. Other high-weight points may come from task-specific exploration, data scale, noisy evidence, or long-horizon work.

For every test task, the design draft must include a transfer coverage matrix for the scoring points that are intended to depend on train transfer:

| Test task | Test scoring point | Train anchor | What transfers | What changes |
| --- | --- | --- | --- | --- |
| `test_001` | `SP003` | `train_001` | Sponsor/attendee separation and lead qualification convention | New event, new source conflicts, larger CRM state |

There is no requirement that every high-weight scoring point map to train. The requirement is that a nontrivial subset of high-weight points can only be solved well by transferring methods inferred from real train tasks. Unanchored high-weight points are allowed when they measure genuine task-specific data exploration or long-horizon work rather than an unstated new SOP.

Avoid far-transfer-only design. If fewshot attempts fail to improve over base attempts, first check whether diversity is too wide: too many unrelated workflow families, too many one-off train anchors, or test-only SOPs that never recur in train. Rework by narrowing the operation-family spread, adding real train coverage for recurring conventions, tightening train/test distribution alignment, or clarifying which high-weight points depend on transfer versus task-specific exploration before making the task easier in superficial ways.

## Sources Of Complexity

Test difficulty should come from two sources:

- Transferring SOPs and key facts from train tasks.
- Intrinsic task complexity, such as long workflows, many tools, many APIs, many Web pages, complex SQLite-backed query surfaces, large data, messy data, dirty data, conflicting similar sources, or stale local materials.

Do not create difficulty through arbitrary ambiguity, bad formatting, or unrecoverable missing information. Difficulty should come from real business complexity, long-horizon operations, information discovery, source selection, and transfer failure.

## Prompt And Input Materials

`prompt.txt` and `input/payloads/` are solver-visible.

Do not plainly write these in the prompt or input files:

- Complete steps for transferable SOPs.
- Answer-like summaries of key facts.
- Tool-call order.
- Solution-flow checklists, especially step lists such as `(1)(2)(3)(4)`.
- Standard answers, evaluation rules, or notes content.

The prompt should read like a real user request: state the goal, necessary context, available materials or environment entry points, and output requirements, without teaching the solver how to complete the task step by step.

When a task uses a shared API, web app, or other running environment, solver-visible
prompts and payloads must use the placeholder `<TASK_ENV_BASE_URL>` for the base
URL. Do not write hard-coded localhost URLs, private IPs, public deployment URLs,
ports, or setup commands into `prompt.txt` or `input/payloads/`. The concrete
endpoint is configured by the evaluation workspace through `.env`.

`input/payloads/` should contain realistic, diverse, sufficiently large, and potentially noisy materials. Payloads may include solver-visible small exports, emails, spreadsheets, logs, templates, or local materials, but they must not become solution manuals.

Every train and test task must include `input/payloads/answer_template.json`. The template should define the output JSON schema, field types, numeric precision, units, stable identifiers, list ordering rules, and allowed enum choices. It should prevent format friction while avoiding answer leakage.

Scored outputs should prefer numeric, enum, boolean, ranking, set, or normalized structured fields. If a business result would otherwise be evaluated through free-form string matching, redesign it as a controlled-choice field, such as an enum or choice list in `answer_template.json`.

## Task Group Design Draft

Before creating formal task files, the main agent should first write:

```text
task_factory/scratch/task_group_design.md
```

The draft should include at least:

- Source scenario and examples.
- Example difficulty audit, showing how train/test task difficulty is aligned with the source examples.
- Train/test task list, with exactly 5 train tasks and 5 test tasks.
- A task-builder assignment plan with one assigned subagent brief for each of the 10 tasks.
- Each task's role, complexity, long-horizon workflow, and output shape.
- Which SOPs, facts, field conventions, or environment experience should be inferable from the train tasks and transfer to test tasks.
- A diversity-band explanation: which 2-3 operation families recur across the group, what changes across tasks, and which changes are intentionally left for task-specific exploration.
- A transfer coverage matrix that maps transfer-dependent test scoring points to one or more train anchors and states exactly what transfers.
- Shared environment blueprint, or a pointer to `scratch/env_blueprint.md`.
- Programmatic data-generation plan for the env-builder coding subagent to implement.
- Evaluation and calibration plan, including each task's expected 6-10 scoring points, `1`/`2`/`3` raw weights, at least 3 independently fail-able business aspects, and deterministic exact-match or partial-credit logic.
- A rubric independence map showing which business question and answer fields each point measures, which points share upstream dependencies, and why the rubric will not behave as one duplicated all-or-nothing check.
- Output-shape plan for `answer_template.json`, including numeric precision and controlled-choice fields for string-like outputs.
- Labels for which scoring points depend on train-derived experience and which depend on substantial data exploration or long-horizon work, ensuring most score cannot be obtained by base attempts through simple reading.
- A skill-saturation check: the train-derived skill should improve test performance but should not make most or all test tasks near-perfect.

The design draft should assign task ownership and provide enough task-specific brief material for each task-builder subagent. It should not directly generate every task's `input/`, `notes/`, `output/`, and `eval/`. Those files are produced later by 10 task-builder subagents, one per task.
