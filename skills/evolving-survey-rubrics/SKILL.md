---
name: evolving-survey-rubrics
description: Evolves survey quality rubrics from adjudicated respondent review examples. Use when improving scoring criteria, comparing Opulent candidate annotations to PM final review, tuning thresholds, creating self-improving loops, or justifying survey quality rubric changes with evidence.
---

# Evolving Survey Rubrics

Use this skill after at least one workbook has PM-adjudicated final review labels, internal comments, client annotations, findings essays, escalation packets, signal banks, or next-pass signal inventories. Normal scoring should run on unannotated exports first; graded workbooks are calibration and evaluation surfaces. Never promote a stable discard rule from unreviewed model output alone.

This skill should evolve analysis methodology, generated criteria, discovery coverage, generated provisional weights, and evaluation quality. A flat scoring tweak is the last resort, not the default.

## Workflow

1. Load the candidate and adjudicated workbooks.
2. Load available learning artifacts from prior runs:
   - `agent_findings_essay.md`
   - `agent_escalation_packet.md`
   - `internal_quality_signal_bank.md`
   - `next_pass_signal_inventory.csv`
   - `agent_review_judgment_table.csv`
   - `agent_discard_set.csv`
   - client or PM annotation workbooks
3. Join respondents by `uuid`, then `record`, then `RID` when adjudicated row labels exist.
4. Compare candidate action, final action, score, and flag families.
5. Identify systematic misses:
   - false keep: candidate says `Keep`, PM says review
   - overflag: candidate says review, PM says `Keep`
   - severity mismatch: both review, but PM assigns a stricter action
   - escalation mismatch: Opulent escalated a survivor row, failed to escalate a true discard candidate, or lacked enough second-pass evidence for the discard decision
   - signal-bank mismatch: a prior internal signal would have helped, but was not used
   - false-positive regression: a prior false-positive guardrail was ignored
   - analysis-quality miss: the final essay or escalation packet was too shallow for a PM to act on
6. Propose the smallest methodology, generated-criteria, generated-weight, field-role mapping, or agent-review instruction change that improves the next run.
7. Write a proposed evolution record with:
   - old generated criterion or discovery behavior
   - proposed generated criterion, tag, or weighting rationale
   - whether the change affects first-pass scoring, review routing, final escalation, reporting, or the internal signal bank
   - evidence rows
   - metric delta
   - annotation-quality delta when PM feedback shows the explanation was too shallow, too rigid, or linguistically unconvincing
   - risk notes
   - rollback condition

Run:

```bash
python3 ../cleaning-survey-quality/scripts/run_quality_loop.py \
  --candidate-file /path/to/candidate_review_export.xlsx \
  --adjudicated-file /path/to/final_pm_review.xlsx \
  --output-dir /path/to/outputs/rubric-evolution
```

## Evolution Rules

- Require adjudicated examples before promoting a generated criterion or generated weight into a stable project policy.
- Require PM approval or repeated cross-run evidence before promoting an internal signal into a discard criterion.
- Treat the provided graded workbook as a sneak peek used to seed and test the loop, not as the expected future input shape.
- Prefer new generated candidate criteria, tags, dimension-level open-end evidence, and evaluation tests over static point changes.
- Prefer high-support criteria over one-off examples.
- If candidate and final labels already match, report rubric stability.
- Track provenance: source file, sheet, respondent key, columns used, old value, new decision.
- Track escalation impact: whether the change escalates only decisive discard candidates and keeps survivor rows with stronger rationale or survey-question recommendations.
- Separate open-end interpretation from numeric scoring.
- Evolve agent annotation guidance when reviewers had to redo the reasoning because the semantic analysis, fluency assessment, or trust rationale lacked depth.
- Evolve the findings essay and escalation packet guidance when a PM could not act from the prose alone.
- Keep false-positive guardrails as important as discard signals. A signal that prevents over-discarding is a successful evolution.
- Update `internal_quality_signal_bank.md` when a run confirms, weakens, retires, or reframes an internal criterion.
- Promote survivor findings into question-design improvements when clearer answer frameworks would reduce fuzzy or gameable responses.
- Report chance-adjusted and ordinal disagreement metrics when labels exist.

## When To Read References

- Read `references/evolution-protocol.md` before proposing changes.
- Read `references/research-grounding.md` for AutoResearch-level validation requirements.
