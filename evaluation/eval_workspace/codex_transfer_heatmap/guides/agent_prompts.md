# Fixed Transfer Solver Prompt

Pass this exact template as the final prompt to `codex exec`. Replace only the
angle-bracket placeholders. Do not append task hints, answer summaries,
evaluator details, or paths outside `/work`.

```text
eval_attempt_id: <unique_eval_attempt_id>
run_type: cross_task_test_solver
mode: <fewshot|reflect-3>
source_task_group: <source_task_group_id>
target_task_group: <target_task_group_id>

Solve exactly one transfer-evaluation test task using only files staged in the current /work directory. Read skill/SKILL.md and any files it references inside skill/, then read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running target environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write answer.json following input/payloads/answer_template.json exactly.
```
