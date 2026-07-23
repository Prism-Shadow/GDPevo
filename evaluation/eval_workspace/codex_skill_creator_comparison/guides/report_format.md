# Report Format

Write one report per model profile:

```text
report/<model_profile>/<task_group_id>.yaml
```

## Required Shape

```yaml
experiment_id: codex_skill_creator_comparison
task_group_id: <task_group_id>
scenario_id: <scenario_id>
model_profile: <profile id>
harness: codex
status: <complete|incomplete>

model:
  generator_model: <resolved model>
  solver_model: <resolved model>
  reasoning_effort: <resolved value>
  provider_id: <resolved provider>
  provider_wire_api: responses
  observed_identity: <identity|null>
  identity_consistent: <bool>

runtime:
  agent_image_id: <image id>
  task_image_id: <image id>
  codex_version: <version>
  agent_uid_gid: <uid:gid>
  startup_check: <passed|failed>

base:
  status: <complete|incomplete>
  incomplete_reason: <string|null>
  shared_across_creators: true
  overall_acc_at_3: <float|null>
  overall_std_at_3: <float|null>
  efficiency:
    input_tokens_avg_3: <float|null>
    cached_input_tokens_avg_3: <float|null>
    output_tokens_avg_3: <float|null>
    reasoning_output_tokens_avg_3: <float|null>
    cost_usd_avg_3: <float|null>
    rounds_avg_3: <float|null>
    tool_calls_avg_3: <float|null>
  tasks:
    test_001:
      status: <complete|incomplete>
      scores: [<float|null>, <float|null>, <float|null>]
      acc_at_3: <float|null>
      std_at_3: <float|null>
      input_tokens_avg_3: <float|null>
      cached_input_tokens_avg_3: <float|null>
      output_tokens_avg_3: <float|null>
      reasoning_output_tokens_avg_3: <float|null>
      cost_usd_avg_3: <float|null>
      rounds_avg_3: <float|null>
      tool_calls_avg_3: <float|null>
    test_002: <same independently populated shape>
    test_003: <same independently populated shape>
    test_004: <same independently populated shape>
    test_005: <same independently populated shape>

fewshot:
  creators:
    codex:
      status: <complete|incomplete>
      incomplete_reason: <string|null>
      source:
        revision: <immutable revision>
        skill_md_sha256: <sha256>
        bundle_sha256: <sha256>
        file_modes_sha256: <sha256>
      generation:
        attempts:
          attempt_01:
            status: <valid|invalid|missing|contaminated>
            skill_dir: <path|null>
            skill_bundle_sha256: <sha256|null>
            input_tokens: <int|null>
            cached_input_tokens: <int|null>
            output_tokens: <int|null>
            reasoning_output_tokens: <int|null>
            total_tokens: <int|null>
            cost_usd: <float|null>
            duration_seconds: <float|null>
            assistant_turns: <int|null>
            tool_calls: <int|null>
            file_count: <int|null>
            bytes: <int|null>
            portability_warnings: []
          attempt_02: <same independently populated shape>
          attempt_03: <same independently populated shape>
        valid_generation_rate: <float>
      overall_acc_at_3: <float|null>
      overall_std_at_3: <float|null>
      lift_over_shared_base: <float|null>
      efficiency: <same fields as base.efficiency>
      tasks: <same five-task shape as base.tasks>
    cc: <same independently populated shape>
    deepagents: <same independently populated shape>
    opencode: <same independently populated shape>

creator_pairwise_deltas:
  codex_minus_cc:
    status: <complete|unavailable>
    overall_delta: <float|null>
    tasks:
      test_001: <float|null>
      test_002: <float|null>
      test_003: <float|null>
      test_004: <float|null>
      test_005: <float|null>
  codex_minus_deepagents: <same independently populated shape>
  codex_minus_opencode: <same independently populated shape>
  cc_minus_deepagents: <same independently populated shape>
  cc_minus_opencode: <same independently populated shape>
  deepagents_minus_opencode: <same independently populated shape>

infrastructure_replacements: []
notes: []
```

Documentation shorthand such as `<same ... shape>` must be expanded in a formal
report. Do not use YAML anchors or aliases.

## Requirements

- Preserve all three raw scores for every test task and branch.
- Use population standard deviation.
- Always expand all four creators and five task mappings, including incomplete
  branches.
- Use `null` only for unavailable values; never fabricate zero.
- Every creator lift references the same shared base attempt set.
- Every few-shot solver attempt uses the same-numbered package from the same
  creator, and its package digest matches the generation record.
- Generation usage remains separate from solver efficiency.
- Trace paths and detailed attempt metadata stay in workspace audit files.
- An incomplete branch has a reason and null aggregate metrics.
- Pairwise deltas are available only when both creator branches are complete.
- Pricing and token semantics are profile-specific.
- `identity_consistent` must be true for a complete report.

## Cross-Model Summary

After both profile reports are finalized, optionally write:

```text
report/comparison/<task_group_id>.yaml
```

Use:

```yaml
experiment_id: codex_skill_creator_comparison
task_group_id: <task_group_id>
comparison_policy: side_by_side_no_pooling
profiles:
  gpt5_5_xhigh:
    report: ../gpt5_5_xhigh/<task_group_id>.yaml
    status: <complete|incomplete>
    base_acc_at_3: <float|null>
    creators:
      codex: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
      cc: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
      deepagents: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
      opencode: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
  deepseek_v4_max_preview:
    report: ../deepseek_v4_max_preview/<task_group_id>.yaml
    status: <complete|incomplete>
    base_acc_at_3: <float|null>
    creators:
      codex: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
      cc: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
      deepagents: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
      opencode: {status: <complete|incomplete>, acc_at_3: <float|null>, lift: <float|null>}
```

Do not pool profile attempts or pricing.
