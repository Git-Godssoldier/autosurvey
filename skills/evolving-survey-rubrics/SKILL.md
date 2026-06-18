---
name: evolving-survey-rubrics
description: Evolves survey quality rubrics from adjudicated respondent review examples. Use when improving scoring criteria, comparing Opulent candidate annotations to PM final review, tuning thresholds, creating self-improving loops, or justifying survey quality rubric changes with evidence.
---

# Evolving Survey Rubrics

Use this skill after at least one workbook has PM-adjudicated final review labels. Normal scoring should run on unannotated exports first; graded workbooks are calibration and evaluation surfaces. Never evolve the rubric from unreviewed model output alone.

This skill should evolve analysis methodology, generated criteria, discovery coverage, generated provisional weights, and evaluation quality. A flat scoring tweak is the last resort, not the default.

## Workflow

1. Load the candidate and adjudicated workbooks.
2. Join respondents by `uuid`, then `record`, then `RID`.
3. Compare candidate action, final action, score, and flag families.
4. Identify systematic misses:
   - false keep: candidate says `Keep`, PM says review
   - overflag: candidate says review, PM says `Keep`
   - severity mismatch: both review, but PM assigns a stricter action
   - escalation mismatch: Opulent escalated a survivor row, failed to escalate a true discard candidate, or lacked enough second-pass evidence for the discard decision
5. Propose the smallest methodology, generated-criteria, or generated-weight change that improves adjudicated precision or recall.
6. Write a proposed evolution record with:
   - old generated criterion or discovery behavior
   - proposed generated criterion, tag, or weighting rationale
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
- Treat the provided graded workbook as a sneak peek used to seed and test the loop, not as the expected future input shape.
- Prefer new generated candidate criteria, tags, dimension-level open-end evidence, and evaluation tests over static point changes.
- Prefer high-support criteria over one-off examples.
- If candidate and final labels already match, report rubric stability.
- Track provenance: source file, sheet, respondent key, columns used, old value, new decision.
- Track escalation impact: whether the change escalates only decisive discard candidates and keeps survivor rows with stronger rationale or survey-question recommendations.
- Separate open-end interpretation from numeric scoring.
- Evolve agent annotation guidance when reviewers had to redo the reasoning because the semantic analysis, fluency assessment, or trust rationale lacked depth.
- Promote survivor findings into question-design improvements when clearer answer frameworks would reduce fuzzy or gameable responses.
- Report chance-adjusted and ordinal disagreement metrics when labels exist.

## When To Read References

- Read `references/evolution-protocol.md` before proposing changes.
- Read `references/research-grounding.md` for AutoResearch-level validation requirements.
