# Common Creator Contract

This contract is staged unchanged for every creator branch. It defines the
experiment boundary, not the strategy for writing a good skill.

## Objective

Use the staged creator bundle to produce one reusable few-shot skill package for
a Codex test solver. The five staged train inputs and five staged standard
answers are the complete, authoritative examples for this run.

## Required Output

Write the complete generated package under:

```text
/work/skill/
```

The required entrypoint is:

```text
/work/skill/SKILL.md
```

Keep supporting scripts, references, and assets inside `/work/skill/`. Use
relative links from `SKILL.md`. Do not install the skill elsewhere.

## Target Runtime

The generated package will be read explicitly by a clean-context Codex solver.
Write portable instructions for that target. Do not require Claude Code,
Deep Agents, OpenCode, creator-only plugins, creator-side subagents, review
servers, or tools absent from the staged test-solving workspace.

## One-Pass Boundary

Complete one skill-generation pass in the current isolated process. Do not ask
for human feedback, wait for another conversation turn, spawn any subagent, make
any secondary model call, start a review UI, optimize activation queries, or
iterate through external eval loops. Bundled deterministic initialization or
validation scripts may be used when they operate only on staged files.

## Information Boundary

Use only the current `/work` contents and the allowed network task environment.
Do not access test tasks, test answers, notes, evaluator implementations, task
environment source, previous runs, other creators, or paths outside `/work`.

Train answers may inform reusable rules, but the generated skill must not copy
task-specific final values or contain reconstructed train answer records. It
must not speculate about evaluator internals.

## Completion

Finish only after `/work/skill/SKILL.md` exists and every local file it directly
references is present. Do not revise the generated package after this process
ends.
