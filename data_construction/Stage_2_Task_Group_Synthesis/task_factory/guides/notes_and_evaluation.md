# Notes And Evaluation

## Notes

Every task must contain:

```text
notes/notes.md
```

This file is not solver input. It provides interpretability for data construction.

`notes/notes.md` should be bilingual in English and Chinese. The Chinese part is for human review only.

This is the only final task-group artifact that should contain Chinese. Keep solver-visible files and executable artifacts English-only, including `prompt.txt`, `input/payloads/`, `answer_template.json`, `output/answer.json`, `eval/`, `task_group.yaml`, `env/`, generated data, and calibration/run artifacts.

Follow the same style as Stage 1 example notes: a fixed heading template is not required, but the file must make the task explainable for later construction, review, and evaluation. It must cover:

- Data/source lineage: source scenario, source example IDs, task design brief, generated or public environment data, and task-local payloads.
- Task definition: business background, visible inputs, expected output, key constraints, important objects, and expected work process.
- Scenario fit: why this task belongs to the current scenario and task group, including the business workflow, object relationships, data flow, or system coordination it represents.
- Material map: what each important payload, public environment entry point, generated dataset, policy, table, API, or support file is used for.
- Solution and evaluation basis: key evidence, rules, calculations, output schema, answer construction, expected 6-10 scoring goals, scoring weights, distinct non-duplicate business outcomes, whole-point pass/fail checks, and likely model pitfalls.
- Transfer design:
  - For train tasks, explain what SOP, facts, field conventions, tool-use habits, or business judgment can be inferred from solving this real task and comparing against the answer.
  - For test tasks, explain which train task(s) anchor the transferable knowledge needed here, what knowledge must be inferred and transferred, and which high-value scoring goals depend on transfer rather than only task-local exploration.
  - For test tasks, explain how the transfer should help without restating the hidden SOP or answer path in the solver-visible prompt.
- Construction record: author, created date, updated date, and major changes.

## Notes Construction Prompt

Use this prompt when a task-builder subagent writes `notes/notes.md`:

```text
Write the hidden `notes/notes.md` file for <task_id>.

The notes are not solver input. They are for data construction, human review, debugging, and evaluation auditability. The final notes file must be bilingual in English and Chinese. Solver-visible files, answer files, evaluation files, task metadata, env files, generated data, and calibration artifacts must remain English-only.

Do not force a rigid section template. Use clear headings that fit the task, but cover all of the following content:

1. Data/source lineage: source scenario, source example IDs, task design brief, generated or public environment data, and task-local payloads used by this task.
2. Task definition: business background, visible inputs, expected output, key constraints, important objects, and expected work process.
3. Scenario fit: why this task belongs to the current scenario and task group, including the workflow, object relationships, data flow, or system coordination it represents.
4. Material map: what each important payload, public environment entry point, generated dataset, policy, table, API, or support file is used for.
5. Solution and evaluation basis: key evidence, rules, calculations, output schema, answer construction, 6-10 scoring goals, raw scoring weights, distinct non-duplicate business outcomes, whole-point pass/fail checks, and likely model pitfalls.
6. Transfer design:
   - If this is a train task, explain what transferable SOP, facts, field conventions, tool-use habits, or business judgment can be inferred from solving this real task and comparing the attempt against the answer. Do not describe the train task as a tutorial or worked example.
   - If this is a test task, name the train task(s) that anchor the transferable knowledge, describe what knowledge must be inferred and transferred, and identify which important scoring goals rely on transfer.
   - For test tasks, also separate transfer-dependent difficulty from task-specific exploration difficulty.
7. Construction record: author, created date, updated date, and major changes.

Keep the notes concrete. Refer to actual files, task IDs, field names, APIs, tables, business rules, scoring goals, and output fields whenever possible. Do not leak notes content into solver-visible input files.
```

## Standard Answer

`output/answer.json` stores the standard answer. Different tasks may use different JSON schemas, but field style should remain as consistent as possible within the same task group.

Each task must also provide a solver-visible `input/payloads/answer_template.json`. The template defines the required output shape, field types, numeric precision, units, stable identifiers, ordering rules, and allowed choices. `answer.json` should conform to that template.

The standard answer should be explainable from the evidence, rules, and data-generation process recorded in `notes/notes.md`.

## Evaluation

`eval/eval.sh` is the evaluation entry point. Each task should normally contain 6-10 scoring points. A scoring point is a weighted business-result dimension, not a tiny field or a sentence of explanation.

The rubric must cover at least 4 semantically distinct business outcomes. Do
not create separate points that merely restate or re-check the same criterion,
answer fact, or root decision. Points may use the same source evidence only when
they score genuinely different conclusions.

Each scoring point's raw `weight` can only be `1`, `2`, or `3`. Convert it into the score assigned to that point as:

```text
assigned_score = scoring_point.weight / sum(all scoring_point.weight)
```

If a task has raw weights `[2, 3, 1, 2, 1, 3, 2, 1]`, the total weight is `15`, so a scoring point with raw weight `3` contributes `3 / 15 = 0.20`.

Each scoring point must be deterministic and atomic. A point earns all of its
assigned score only when the complete business-result goal passes; otherwise it
earns zero. Within-point fractional credit is not allowed. If eligibility,
deadline, required action, inclusion, exclusion, or other results can fail
independently, represent them as separate meaningful rubric points instead of
combining them into one fractionally scored point. Do not create tiny points for
incidental fields merely to manufacture score granularity, and do not create
multiple points that reward the same result under different names.

For every point, evaluator output should report its assigned score, a boolean
pass result, earned score equal to either the assigned score or `0`, and
deterministic check details. The total score is:

```text
score = sum(assigned_score * point_pass)
point_pass in {0, 1}
```

This preserves the `1`/`2`/`3` raw weighting. The task-level score may still
fall anywhere between `0` and `1` because some rubric points can pass while
others fail, but no individual point may be partially earned.

Scoring points should focus as much as possible on numeric, enum, boolean, ranking, set, aggregate, or other normalized structured outputs. Avoid scoring free-form strings directly. If a result naturally looks like a string classification, status, reason code, action name, or label, expose it as a controlled-choice field in `answer_template.json` and evaluate the selected value exactly.

Most scoring points must be genuinely difficult business-result points. They should satisfy at least one of these conditions:

- They require transferring SOPs, facts, field conventions, tool-selection habits, or business judgment inferred from real train tasks.
- They require exploration and cross-checking across large data, multiple system entry points, complex APIs, Web pages, databases, or files.
- They require long-horizon work such as filtering, state tracking, effective-state reconstruction, conflict resolution across sources, aggregation, ranking, and final business decisions.

Do not allocate most score to low-difficulty items such as JSON parseability, field presence, copying entity names from the prompt, looking up values in a single small payload, correct output formatting, evidence-string similarity, or common-sense judgments that do not require train experience. These may be prerequisites or a small number of low-weight scoring points, but they must not be the main source of score.

Recommended rubric shape:

```yaml
rubric:
  - goal: Correct target entity set under the documented inclusion and exclusion rules.
    weight: 2
  - goal: Correct eligibility or policy classification for each selected entity.
    weight: 3
  - goal: Correct numeric exposure, amount, or aggregate calculation.
    weight: 2
  - goal: Correct priority ordering and required operational actions.
    weight: 2
```

Continue until the task has 6-10 scoring points spanning at least 4 genuinely
different business aspects. Keep `rubric` as a concise index of evaluation
goals. Put answer paths, whole-point pass/fail logic, normalization, tolerances,
and implementation details in the evaluation files.

Before calibration, create `scratch/rubric_validation.md` and confirm these
rules for every task: the rubric covers at least 4 distinct business outcomes;
no points score the same underlying criterion, answer fact, or root decision;
and every point always earns either all of its assigned score or zero. Merge or
redesign any points that violate these rules before calibration.

Evaluation should use reproducible rule checks, such as:

- Field presence and JSON parseability.
- Enums, statuses, tags, and classifications.
- Numeric results, sorting, coverage, and aggregates.
- Key business judgments.
- Correct use of SOPs, facts, or data conventions transferred from train tasks.

Numeric results should be compared deterministically at the precision declared by the task, such as currency to cents or ratios to a specified decimal place. Lists or sets should be normalized first, for example by sorting on a stable key, removing non-business whitespace, or applying a documented enum casing rule. Normalization rules must be written in the evaluator or notes.

Do not rely on subjective text-quality judgments. Do not evaluate only by whole-file equality unless the task answer is itself a single fully normalized machine field. Do not make evidence wording, formatting friction, irrelevant fields, or incidental strings independent scoring points. String-like scored outputs should be converted into enum or multiple-choice style fields whenever possible. A shared parser or prerequisite may invalidate an unreadable answer, but ordinary business mistakes should affect only their relevant whole rubric points so the weighted task score remains diagnostic rather than collapsing all points together.
