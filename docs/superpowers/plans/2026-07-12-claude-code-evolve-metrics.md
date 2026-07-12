# Claude Code Evolve Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record skill-generation token usage, USD cost, and complete session traces in every Claude Code evaluation workspace.

**Architecture:** Extend each workspace's existing Claude session-trace accounting from solver attempts to skill-generation attempts. Keep evolve usage in a top-level `evolve` report block so it never changes solver efficiency semantics.

**Tech Stack:** Markdown workspace contracts, YAML report schemas, Claude Code session JSONL.

## Global Constraints

- Update `claude_code`, `claude_code_zh`, `claude_code_glm_5_2`, `claude_code_kimi2_6`, and `claude_code_deepseek_v4_pro` only.
- Do not change Panofy or cross-task transfer heatmap workspaces.
- Preserve complete skill-generation Claude session traces.
- Use the model-specific price formulas already published in `experiments/EXPERIMENT_BOARD.md`.
- Leave missing trace-derived values as `null`; do not infer absent token buckets.
- Do not mix evolve usage into solver efficiency metrics.

---

### Task 1: Generic Claude Code Workspace Contracts

**Files:**
- Modify: `evaluation/eval_workspace/claude_code/CODEX_ORCHESTRATOR.md`
- Modify: `evaluation/eval_workspace/claude_code/README.md`
- Modify: `evaluation/eval_workspace/claude_code/guides/workflow.md`
- Modify: `evaluation/eval_workspace/claude_code/guides/metric_and_scoring.md`
- Modify: `evaluation/eval_workspace/claude_code/guides/report_format.md`
- Modify: `evaluation/eval_workspace/claude_code_zh/CODEX_ORCHESTRATOR.md`
- Modify: `evaluation/eval_workspace/claude_code_zh/README.md`
- Modify: `evaluation/eval_workspace/claude_code_zh/guides/workflow.md`
- Modify: `evaluation/eval_workspace/claude_code_zh/guides/metric_and_scoring.md`
- Modify: `evaluation/eval_workspace/claude_code_zh/guides/report_format.md`

**Produces:** Equivalent English and Chinese requirements for skill-generation trace capture, `evolve_metadata.yaml`, Opus token accounting, and evolve report aggregation.

- [ ] Add dedicated `CLAUDE_CONFIG_DIR` and session trace paths for each skill-generation attempt.
- [ ] Define `evolve_metadata.yaml` with input, cache creation, cache read, output, total token, and cost fields.
- [ ] Add the Opus 4.8 rate card: input 5.00, cache creation 6.25, cache read 0.50, output 25.00 USD per million tokens.
- [ ] Add the top-level report `evolve` schema with three attempts and per-bucket `avg_3` fields for each non-base mode.
- [ ] Verify English and Chinese structures with:

```bash
rg -n "evolve_metadata|original_traces/skill_generation|cost_usd_avg_3" \
  evaluation/eval_workspace/claude_code \
  evaluation/eval_workspace/claude_code_zh
```

Expected: all three concepts occur in both workspace variants.

### Task 2: Model-Specific Claude Code Workspaces

**Files:**
- Modify the same five contract files under `evaluation/eval_workspace/claude_code_glm_5_2/`
- Modify the same five contract files under `evaluation/eval_workspace/claude_code_kimi2_6/`
- Modify the same five contract files under `evaluation/eval_workspace/claude_code_deepseek_v4_pro/`

**Produces:** The same evolve artifact/report contract with model-specific pricing.

- [ ] Add GLM pricing: input 1.40, cache creation 0.00, cache read 0.26, output 4.40 USD per million tokens.
- [ ] Add Kimi pricing: input 0.95, cache read 0.16, output 4.00 USD per million tokens; retain a nullable/zero-compatible cache-creation bucket without charging it.
- [ ] Add DeepSeek pricing: input 0.435, cache read 0.003625, output 0.87 USD per million tokens; retain a nullable/zero-compatible cache-creation bucket without charging it.
- [ ] Remove model-specific statements that forbid formal cost fields now that an agreed rate card exists.
- [ ] Validate all scoped workspaces and untouched exclusions with:

```bash
git diff --check
for d in claude_code claude_code_zh claude_code_glm_5_2 claude_code_kimi2_6 claude_code_deepseek_v4_pro; do
  rg -l "evolve:" "evaluation/eval_workspace/$d/guides/report_format.md"
  rg -l "evolve_metadata.yaml" "evaluation/eval_workspace/$d"
done
git diff --name-only | rg "evaluation/eval_workspace/(panofy|codex_transfer_heatmap)" && exit 1 || true
```

Expected: five report formats and all five workspace contracts mention evolve metadata; no excluded workspace appears in the diff.

### Task 3: Final Consistency Review

**Files:**
- Review all files modified by Tasks 1 and 2.

**Produces:** A clean, internally consistent documentation change.

- [ ] Scan for old statements that make all skill-generation cost reporting out of scope:

```bash
rg -n "Do not add cost|cost conversion is intentionally out of scope" \
  evaluation/eval_workspace/claude_code* --glob '*.md'
```

Expected: no matches in the five scoped workspaces.

- [ ] Confirm the only changed evaluation workspaces are the five scoped Claude Code variants.
- [ ] Run `git diff --check` and inspect `git diff --stat` before committing.
- [ ] Commit with `git commit -m "Track Claude Code evolve token cost and traces"`.
