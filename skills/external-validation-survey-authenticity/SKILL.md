---
name: external-validation-survey-authenticity
description: Runs sealed one-shot external validation for Autosurvey respondent-authenticity predictions. Use when scoring a previously blinded survey against newly supplied client decisions, requiring pre-registration, prediction sealing, respondent reconciliation, accuracy profiling, leakage audits, and benchmark consumption tracking.
---

# External validation survey authenticity

Use this skill when a client supplies decisions for a previously blinded survey sample.

External validation is not a calibration run. The benchmark is scored once, sealed, unblinded once, and then marked consumed.

Do not use this skill name for the 11 existing TFG original/graded workbook pairs. Those pairs are development data because they have already been used for methodology development. Use `build_continuous_evolution_loop.py` from the reporting skill for retrospective nested validation on those pairs.

## Required order

1. Inventory the repository, latest methodology, original blinded workbook, and candidate label files by metadata and headers only.
2. Pre-register metrics, thresholds, cohorts, baselines, join keys, and failure rules.
3. Commit the predictor, evaluator, seal, reconciliation, metric, report, and audit code before prediction.
4. Run the predictor against the unlabeled response workbook only.
5. Seal prediction hashes, input hashes, row universe hashes, thresholds, prompts, skills, and evaluator code.
6. Validate the seal before opening labels.
7. Reconcile labels by stable respondent ID, not row order.
8. Compute every pre-registered metric and every five-tier cutoff.
9. Write technical, client-facing, machine-readable, audit, scorecard, and benchmark-consumption artifacts.
10. Write a post-unblind row-level semantic error analysis when labels are available. This analysis must review every joined respondent as a learning case, separating false negatives, false positives, true positives, true accepts, and accepted guardrails.
11. Put post-unblind learning only into a test-derived hypothesis backlog. Do not change the sealed predictions.

## Role separation

- Predictor may read the original blank workbook and frozen development artifacts. It may not read client decisions.
- Registrar seals predictions and code. It may not read client decision values.
- Evaluator validates the seal, then opens labels and calculates metrics. It may not rerun or change the predictor.
- Integrity auditor checks hashes, row coverage, metric completeness, leakage, and benchmark consumption.

## Required scripts

Use the reporting skill scripts:

```bash
python3 scripts/discover_external_validation_inputs.py --output-dir /path/to/run
python3 scripts/run_blind_autosurvey_prediction.py --output-dir /path/to/run
python3 scripts/seal_external_predictions.py --output-dir /path/to/run
python3 scripts/reconcile_client_labels.py --output-dir /path/to/run
python3 scripts/evaluate_external_accuracy.py --output-dir /path/to/run
python3 scripts/build_external_validation_reports.py --output-dir /path/to/run
python3 scripts/audit_external_validation_integrity.py --output-dir /path/to/run
```

The evaluator must refuse to run if `prediction_seal_manifest.json` is missing or any sealed file hash has changed.

Post-unblind row analysis must not alter the sealed prediction file. Its purpose is to learn why the frozen method missed or overflagged rows, so the next methodology-development cycle can improve safely.

## Reporting standard

Report client-decision agreement, not fraud proof. Client rejection is an operational outcome unless the client provides a separate fraud taxonomy.

Always separate:

- `client_reject_probability`
- `authenticity_risk_probability`
- `attention_or_validity_risk`
- `protective_human_evidence`
- `model_uncertainty`
- `operational_tier`

Only Tier 5 is the exclusion-candidate set. Tiers 2 to 4 are review and annotation surfaces.

## Completion gate

The run is complete only when:

- predictions were sealed before label access;
- every eligible row has a prediction or pre-registered abstention;
- labels reconcile by stable ID;
- all required metrics and tier cutoffs are populated or explicitly failed;
- integrity verdict is written;
- benchmark registry marks the benchmark as consumed when labels were opened;
- tests pass;
- post-unblind row analysis exists when labels were opened;
- code and safe documentation are committed without committing client data or output artifacts.
