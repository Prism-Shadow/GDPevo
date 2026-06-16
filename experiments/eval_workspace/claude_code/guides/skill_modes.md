# Skill Modes

This evaluation compares three conditions. All three conditions must use the same task group, the same test tasks, the same model and reasoning/effort configuration, and the same evaluators.

The main agent should stage the allowed materials for each subagent into that subagent's dedicated directory and restrict the subagent to it. Do not give skill-generation or solver subagents the full task group directory.

## base

No skill is generated.

The solver may see:

- The current test task `input/`.
- Allowed environment entrypoints, such as exposed ports, Web/API URLs, or database connections.

The solver must not see:

- Train tasks.
- Test standard answers.
- Test notes.
- Evaluator implementation details.

## demo

For this condition, generate 3 independent skills with 3 clean-context skill-generation subagents. Each generator should use the `skill-creator` skill.

The skill generator may see:

- Official `input/` for the 5 train tasks.
- Standard `output/answer.json` for the 5 train tasks.
- Allowed exposed ports, Web/API URLs, or database connections.

The skill generator must not see:

- Test standard answers.
- Test notes.
- Evaluator implementation details.

Save the generated skills as:

```text
skills/demo/demo_attempt_01/SKILL.md
skills/demo/demo_attempt_02/SKILL.md
skills/demo/demo_attempt_03/SKILL.md
```

The solver may see:

- The current test task `input/`.
- Allowed exposed ports, Web/API URLs, or database connections.
- The demonstration skill whose attempt number matches the solver attempt number.

## reflect

For this condition, generate 3 independent skills with 3 clean-context skill-generation subagents. Each generator should use the `skill-creator` skill, and each skill is generated through independent attempts, answer comparison, and error reflection.

Generation process:

1. Read only the official `input/` for the 5 train tasks and allowed exposed ports, Web/API URLs, or database connections.
2. Independently complete the 5 train tasks and save blind attempts.
3. Read the standard `output/answer.json` for the 5 train tasks.
4. Compare its own answers against the standard answers and reflect on error sources.
5. Summarize transferable SOPs, field definitions, environment usage, business judgment rules, and common pitfalls.

Save the generated skills as:

```text
skills/reflect/reflect_attempt_01/SKILL.md
skills/reflect/reflect_attempt_02/SKILL.md
skills/reflect/reflect_attempt_03/SKILL.md
```

The solver may see:

- The current test task `input/`.
- Allowed exposed ports, Web/API URLs, or database connections.
- The reflection skill whose attempt number matches the solver attempt number.

## Skill Quality Requirements

A skill should be executable experience, not a restatement of train answers.

A good skill should include:

- Transferable business rules.
- How to use the exposed Web/API or database environment.
- Output field definitions.
- Common misjudgments and exclusion rules.
- SOPs learned from train tasks that must be re-applied to test tasks.

A skill must not include:

- Test task answers or derivations.
- Non-transferable restatements of individual train examples.
- Speculative statements that reveal or guess evaluator checkpoints.
