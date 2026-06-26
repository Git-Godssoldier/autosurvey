# Command: evolution-cycle

Improve the pipeline after receiving client feedback (annotated workbook with accept/reject decisions).

## When to use

After the PM reviews the blind-run output and the client provides accept/reject decisions, use the annotated workbook to:
1. Compare agent judgments against client decisions
2. Identify missed discards (false negatives) and wrong discards (false positives)
3. Update the evidence-family framework rules
4. Retrain the ML model with the new annotated data

This is a **separate activity** from the normal blind run. It does not run on unannotated data.

## Steps

### 1. Compare agent judgments against client decisions

Run the comparison script to measure precision, recall, and F1:

```bash
python3 scripts/merge_and_compare_v4.py --agent-output /path/to/agent_judgments.json --client-annotated /path/to/annotated.xlsx
```

This produces:
- Confusion matrix (TP, FP, TN, FN)
- Precision, recall, F1
- Per-respondent comparison CSV
- False positive and false negative samples

### 2. Analyze misses

For each false negative (missed discard):
- Read the full response chain
- Identify which evidence family should have triggered
- Determine why the agent missed it (too strict? wrong threshold? missing signal?)

For each false positive (wrong discard):
- Read the full response chain
- Identify which evidence family triggered incorrectly
- Determine what protective factor should have prevented the discard

### 3. Update the evidence-family framework

Based on the miss analysis:
- Update `build_agent_instructions()` in `run_holistic_agent_review.py`
- Adjust thresholds for evidence families
- Add new guardrails for false positive patterns
- Document the changes in the commit message

### 4. Retrain the ML model (optional)

If new annotated data is available:

```bash
python3 scripts/training/survey_quality_ml.py train
```

This runs leave-one-dataset-out CV on all annotated datasets and saves the updated model to `models/survey_quality_model.pkl`.

### 5. Re-run the blind flow to verify improvements

Run `commands/blind-run.md` on the unannotated workbook again and compare the new output against the client annotations to verify the improvements.

## References to read

- `references/evolution/authenticity-first-calibration.md` — Five-tier routing model and label-aware contrast
- `references/evolution/tfg-status-derived-detection-methodology.md` — Status-derived detection rules
- `references/evolution/dataset-cycle-loop.md` — Improvement cycle specification
- `references/evolution/ml-pipeline-report.md` — ML building process and per-dataset evaluation results
- `references/evolution/internal-signal-learning.md` — Internal comments and PM notes learning
