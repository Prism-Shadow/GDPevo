# Planted decoys & common mistakes

These environments plant distractor records. Excluding them correctly is usually the point
of the task, and the excluded record almost always belongs in `basis_audit.exception_record_ids`.

## Decoys to exclude

- **Stale documents.** `documents.is_current = 0` (types like `stale_export`, source systems
  like `LegacyUM`) look like evidence but must be excluded from `evidence_documents` and
  from controlling records. Rely only on `is_current = 1`.
- **Stale / legacy rate schedules.** A `payment_benchmarks` row whose `effective_end`
  precedes the claim's `service_date` (e.g. a "Legacy Imaging Export") is the source the
  claim was *mispaid* against — it is the `stale_source_rejected`, never the benchmark.
- **Distractor schedules.** A benchmark for a *different* CPT or plan_type (e.g. a
  "Distractor Schedule" priced for a CPT the claim doesn't contain) matches nothing —
  don't let its amount leak into a line.
- **Undocumented drug trials.** `drug_trials.documented = 0` / "mentioned but fill missing"
  is an insufficient failure, not a documented one; it drives a `partial` failures criterion
  and a packet gap.
- **Informational criteria.** `policy_criteria.approval_required = 0` (e.g. a
  new-P2P-information criterion) is usually **not** one of the answer template's required
  criterion keys — don't add keys the template doesn't ask for.
- **Charge-sensitive vs below-threshold.** A charge-sensitive row is not automatically a
  problem; below-threshold (ratio < threshold) is the actionable issue and outranks
  charge-sensitivity in precedence.

## Output mistakes to avoid

- Emitting an enum value that isn't an exact allowed choice.
- Using `""` for an absent modifier instead of `null`.
- Wrong ordering (forgetting ascending document_id / ascending CPT / alphabetical /
  claim-line order / queue_row_ids order / choices order for factor lists).
- Forgetting `allowed_amount` is **per unit** (must multiply by line units).
- Wrong precision (currency not 2 dp; ratio not at the template's precision).
- Adding keys the template doesn't list when `additional_fields` are disallowed, or
  wrapping the JSON in prose/markdown.
- Inventing IDs, auth numbers, amounts, or deadlines instead of tracing them to records.
- Relying on truncated SQL output (`row_count` near 500 / `limited=true`) — filter tighter.
- Miscounting a calendar-day deadline window (count days from the correct determination/
  denial date; return `null` when no deadline applies).
