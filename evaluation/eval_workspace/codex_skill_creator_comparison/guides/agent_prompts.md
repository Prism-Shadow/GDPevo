# Fixed Isolated-Agent Prompts

Pass exactly one template as the final prompt to `codex exec`. Replace only
angle-bracket placeholders. Model and provider settings belong to the resolved
runtime configuration, not the prompt.

## Fewshot Skill Generation

```text
agent_run_id: <opaque_uuid>
run_type: skill_generation
condition: fewshot
model_profile: <model_profile_id>

Generate exactly one reusable skill package using only files staged in the current /work directory. First read creator_contract.md, then read creator/SKILL.md and every local creator resource it directs you to use. For each of train_001 through train_005, read its input/prompt.txt and every file under its input/payloads/, plus the matching answer.json under the same train ID in train_answers/. These five complete inputs and five matching answers are the complete few-shot evidence. Use environment_access.md only to reach the running task environment over the network. Follow the portable one-pass boundary in creator_contract.md. If unexpected material is present, stop and write contamination_report.txt. Otherwise create skill/ with skill/SKILL.md as its entrypoint and keep every supporting output inside skill/. Do not copy task-specific final answer values into the reusable skill.
```

## Base Test Solver

```text
agent_run_id: <opaque_uuid>
run_type: test_solver
condition: base
model_profile: <model_profile_id>

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running task environment over the network. No skill should be present. Do not call a judge API. If unexpected material is present, stop and write contamination_report.txt instead of an answer. Otherwise write answer.json following input/payloads/answer_template.json exactly.
```

## Fewshot Test Solver

```text
agent_run_id: <opaque_uuid>
run_type: test_solver
condition: fewshot
model_profile: <model_profile_id>

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running task environment over the network. Read skill/SKILL.md and any supporting files it references inside skill/. Do not call a judge API. If unexpected material is present, stop and write contamination_report.txt instead of an answer. Otherwise write answer.json following input/payloads/answer_template.json exactly.
```

Generate each `<opaque_uuid>` independently. It must contain no creator, model,
task, condition, or attempt label. The descriptive logical attempt ID and creator
identity remain outside `/work` in orchestrator metadata. Within one model
profile, use byte-identical few-shot prompt text for all four creators except for
the fresh opaque UUID.

A run with a modified prompt, extra hints, forbidden staged files, an unpinned
creator, post-edited generated skill, or evidence of forbidden access is
invalid. Preserve it for audit and follow the failure rules in the workflow.
