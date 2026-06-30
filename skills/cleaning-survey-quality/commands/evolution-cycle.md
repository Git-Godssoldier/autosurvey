# Command: evolution-cycle

Improve the pipeline after receiving client feedback (annotated workbook with accept/reject decisions).

## When to use

After the PM reviews the blind-run output and the client provides accept/reject decisions, use the annotated workbook to:
1. Compare agent judgments against client decisions
2. Identify missed discards (false negatives) and wrong discards (false positives)
3. Update the evidence-family framework rules
4. Retrain the ML model with the new annotated data

This is a **separate activity** from the normal blind run. It does not run on unannotated data.

The current benchmark to beat is V7 on ECHO:
- Precision 0.664
- Recall 0.524
- F1 0.586
- Balanced accuracy 0.690
- False positives 147

Do not promote a change only because it increases recall. A successful change must preserve the V7 false-positive guardrails or explain why the added review burden is worth it.

## Steps

### 1. Normalize feedback data into SQLite

Read `references/production/dataset-normalization-sqlite.md` and create a run-local SQLite store for the annotated workbook, prior agent judgments, and any comparison outputs:
- `normalized/survey_quality.sqlite`
- `normalized/schema_summary.md`
- `normalized/field_roles.csv`
- `normalized/import_report.json`
- `normalized/analysis_queries.sql`

Verify status distribution, respondent matching rate, UUID uniqueness, marker distribution, and any unmapped fields before comparing metrics.

### 2. Compare agent judgments against client decisions

Run the comparison script to measure precision, recall, and F1:

```bash
python3 scripts/merge_and_compare_v4.py --agent-output /path/to/agent_judgments.json --client-annotated /path/to/annotated.xlsx
```

This produces:
- Confusion matrix (TP, FP, TN, FN)
- Precision, recall, F1
- Per-respondent comparison CSV
- False positive and false negative samples

### 3. Analyze misses

For each false negative (missed discard):
- Read the full response chain
- Identify which evidence family should have triggered
- Determine why the agent missed it (too strict? wrong threshold? missing signal?)
- Decide whether the miss is learnable from runtime fields or depends on hidden client process data

For each false positive (wrong discard):
- Read the full response chain
- Identify which evidence family triggered incorrectly
- Determine what protective factor should have prevented the discard
- Compare it to accepted rows with the same surface pattern and document the guardrail

Use SQLite queries for cohort counts before promoting any rule. Save final SQL in `normalized/analysis_queries.sql`.

### 4. Update the evidence-family framework

Based on the miss analysis:
- Update `build_agent_instructions()` in `run_holistic_agent_review.py`
- Adjust thresholds for evidence families
- Add new guardrails for false positive patterns
- Update `references/production/v7-calibration-and-guardrails.md` when the new benchmark beats V7
- Document the changes in the commit message

### 5. Retrain the ML model (optional)

If new annotated data is available:

```bash
python3 scripts/training/survey_quality_ml.py train
```

This runs leave-one-dataset-out CV on all annotated datasets and saves the updated model to `models/survey_quality_model.pkl`.

### 6. Re-run the blind flow to verify improvements

Run `commands/blind-run.md` on the unannotated workbook again and compare the new output against the client annotations to verify the improvements.

## References to read

- `references/evolution/authenticity-first-calibration.md` — Five-tier routing model and label-aware contrast
- `references/evolution/tfg-status-derived-detection-methodology.md` — Status-derived detection rules
- `references/evolution/dataset-cycle-loop.md` — Improvement cycle specification
- `references/evolution/ml-pipeline-report.md` — ML building process and per-dataset evaluation results
- `references/evolution/internal-signal-learning.md` — Internal comments and PM notes learning
- `references/production/v7-calibration-and-guardrails.md` — Current benchmark and guardrail rules
- `references/production/dataset-normalization-sqlite.md` — SQLite normalization and SQL analysis standards
