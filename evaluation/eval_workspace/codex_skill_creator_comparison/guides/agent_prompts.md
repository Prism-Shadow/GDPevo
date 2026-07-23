# Fixed Isolated-Agent Prompts

Pass exactly one template as the final prompt to `codex exec`. Replace only
angle-bracket placeholders. Model and provider settings belong to the resolved
runtime configuration, not the prompt.

## Rendering Contract

Use these stable template IDs:

| Template ID | Run |
| --- | --- |
| `fewshot_skill_generation` | All four creator generation branches |
| `base_test_solver` | Shared base solver |
| `fewshot_test_solver` | All four creator solver branches |

Every template has exactly two allowed placeholders:

| Placeholder | Allowed value |
| --- | --- |
| `<opaque_uuid>` | A fresh random UUIDv4 in canonical lowercase form, equal to this attempt's metadata `agent_run_id` |
| `<model_profile_id>` | The one selected ID from `configs/models/` |

Replace each placeholder exactly once by literal string substitution. Reject the
render if either placeholder is missing, duplicated, unresolved, or replaced
with a value outside the rules above. Do not prepend or append text.

Creator, task, condition, attempt, model string, provider, reasoning effort,
proxy, endpoint, host path, and container name are not prompt variables.
`run_type` and `condition` are fixed text in the selected template. Creator,
task, and attempt identity belong only in orchestrator metadata and staged
files. Model, provider, reasoning, and proxy values belong only in the resolved
runtime configuration.

For hashing, define the canonical template as the UTF-8 text inside the first
`text` fence immediately following the selected template heading, excluding the
fence lines, with LF line endings and no trailing LF. Define the rendered
prompt as that canonical template after the two literal substitutions, also
with no trailing LF. Record:

```text
prompt_template_id
prompt_template_sha256
rendered_prompt_sha256
```

`prompt_template_sha256` verifies fairness across attempts and creators that use
the same `prompt_template_id`. `rendered_prompt_sha256` authenticates the exact
per-process payload and can be recomputed from the canonical template plus the
two recorded substitution values. It will normally differ because the UUID
differs. Never require rendered hashes from different attempts to match.

## Fewshot Skill Generation

```text
agent_run_id: <opaque_uuid>
run_type: skill_generation
condition: fewshot
model_profile: <model_profile_id>

Generate exactly one reusable skill package using only files staged in the current /work directory. First read creator_contract.md, then read creator/SKILL.md and every local creator resource it directs you to use. For each of train_tasks/train_001 through train_tasks/train_005, read its input/prompt.txt and every file under its input/payloads/, plus the matching answer.json under the corresponding train_answers/train_001 through train_answers/train_005 directory. These five complete inputs and five matching answers are the complete few-shot evidence. Use environment_access.md only to reach the running task environment over the network. Follow the portable one-pass boundary in creator_contract.md. If unexpected material is present, stop and write contamination_report.txt. Otherwise create skill/ with skill/SKILL.md as its entrypoint and keep every supporting output inside skill/. Do not copy task-specific final answer values into the reusable skill.
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

## Rendered Example

For `prompt_template_id=fewshot_skill_generation`, an allowed substitution is:

```text
<opaque_uuid>      -> 7ff34352-6537-40af-99f6-fde9d540fb66
<model_profile_id> -> gpt5_5_xhigh
```

The rendered prompt begins:

```text
agent_run_id: 7ff34352-6537-40af-99f6-fde9d540fb66
run_type: skill_generation
condition: fewshot
model_profile: gpt5_5_xhigh
```

The remainder is byte-identical to the fixed template body. The creator ID is
not added; `/work/creator/` is the only creator-specific generation input.

## Launch Example

After rendering, validating, and hashing the prompt, pass it as one quoted final
argument. Do not use `eval` or concatenate runtime metadata into it.

```bash
HOME=/tmp/gdpevo-agent-home \
CODEX_HOME=/tmp/gdpevo-codex-home \
codex exec \
  -C /work \
  -m "$RESOLVED_MODEL_ID" \
  -c "model_provider=\"$RESOLVED_MODEL_PROVIDER_ID\"" \
  -c "model_reasoning_effort=\"$RESOLVED_REASONING_EFFORT\"" \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$RENDERED_PROMPT"
```

The model, provider, and reasoning variables in this command are resolved
runtime values; they are not prompt substitutions. For a custom provider, its
base URL and provider definition live in the minimum container-local Codex
configuration. Credentials use the profile's declared environment variable,
and proxy values remain container environment settings. None of these values
may be included in `RENDERED_PROMPT`.

Generate each `<opaque_uuid>` independently. It must contain no creator, model,
task, condition, or attempt label. The descriptive logical attempt ID and creator
identity remain outside `/work` in orchestrator metadata. Within one model
profile, use byte-identical few-shot prompt text for all four creators except for
the fresh opaque UUID.

Reject an unknown template ID, unexpected placeholder, modified template, extra
hint, forbidden staged file, unpinned creator, or post-edited generated skill
before launching the affected generation or solver process. If such an
orchestrator defect is discovered only after launch, preserve it as an
infrastructure failure and replace the logical slot from clean inputs.
Agent-originated forbidden access or contamination is a logical result. Follow
the failure rules in the workflow.
