# Fixed Isolated-Agent Prompts

The orchestrator must pass exactly one template below as the final prompt to
`codex exec` or `claude -p`. Replace only angle-bracket placeholders. Do not
append task hints, answer summaries, notes, evaluator or rubric details,
construction truth, or paths outside `/work`.

Stage files with the names used below. The process may inspect only its mounted
`/work`; model and effort settings belong to command/configuration, not the
prompt.

## Fewshot Skill Generation

```text
generation_run_id: <unique_generation_run_id>
run_type: skill_generation
condition: fewshot

Generate one reusable skill package using only files staged in the current /work directory. Read all five train inputs from train_tasks/train_001/input/ through train_tasks/train_005/input/, including every payload, and the five matching standard answers from train_answers/train_001/answer.json through train_answers/train_005/answer.json. Use environment_access.md only to reach the running environment over the network. If any unexpected material is present in /work, stop and write contamination_report.txt. Otherwise create skill/ and write the reusable entry instructions to skill/SKILL.md without copying task-specific answer values. Keep any supporting files inside skill/.
```

## Self Skill Generation

```text
generation_run_id: <unique_generation_run_id>
run_type: skill_generation
condition: self

Generate one reusable skill package using only files staged in the current /work directory. Read all five train inputs from train_tasks/train_001/input/ through train_tasks/train_005/input/, including every payload, and use environment_access.md only for network access. Work through train_001 to train_005 from the visible evidence and distill reusable operating rules. If any unexpected material is present in /work, stop and write contamination_report.txt. Otherwise create skill/ and write the reusable entry instructions to skill/SKILL.md without task-specific final values. Keep any supporting files inside skill/.
```

## Reflect-3 Skill Generation

```text
generation_run_id: <unique_generation_run_id>
run_type: skill_generation
condition: reflect-3

Generate one reusable skill package using only files staged in the current /work directory. Read the five inputs from train_tasks/train_001/input/ through train_tasks/train_005/input/ and environment_access.md, then follow judge_access.md. Process train_001 through train_005 in order. For each task, produce a candidate, submit exactly three judge-feedback rounds, and use only the returned score and correct values to improve the next candidate before moving on. If any unexpected material is present in /work, stop and write contamination_report.txt. Otherwise create skill/ and distill the transferable entry instructions into skill/SKILL.md, keeping any supporting files inside skill/. Do not include candidate answers, task-specific final values, judge transcripts, endpoint instructions, or any instruction to call the judge during test solving.
```

## Test Solver

```text
eval_attempt_id: <unique_eval_attempt_id>
run_type: test_solver
condition: <base|fewshot|self|reflect-3>

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running environment over the network. When skill/ is staged for this condition, read skill/SKILL.md and any supporting files it references inside skill/. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write answer.json following input/payloads/answer_template.json exactly.
```

A run with a modified prompt, extra hints, forbidden staged files, or evidence of
forbidden access is invalid. Preserve it for audit and rerun in a fresh
directory with a new run id.
