---
name: evaluating-survey-authenticity
description: Use only after a survey authenticity review ledger has been sealed. This skill evaluates sealed Autosurvey respondent-authenticity decisions against client labels, verifies seal hashes, computes post-seal metrics, checks stable-ID joins, and protects against label leakage or evaluator writes to decision columns.
---

# Evaluating Survey Authenticity

Use this skill only after the blind semantic decision ledger is complete and sealed.

## Boundary

The evaluator is not the decision maker. It must never inspect labels before the blind ledger is sealed, never write or edit decision columns, and never infer respondent authenticity from workbook content.

If the ledger is unsealed, stop with:

`BLOCKED_UNSEALED_LEDGER`

If a pre-seal path tries to use evaluator code on respondent content, stop with:

`FAILED_SCRIPTED_INFERENCE_FIREWALL`

## Required Checks

- Validate the seal manifest and hashes before reading labels.
- Join predictions to labels only by stable respondent ID, never row order.
- Keep all rows in denominators unless an explicit non-response or no-label rule is documented.
- Treat the client reject label as the positive class.
- Report confusion matrix, rejected recall, rejected precision, accepted specificity, balanced accuracy, macro F1, and residual error families.
- Verify evaluator outputs do not overwrite decision, rationale, signal, protective-evidence, citation, or confidence columns.
- Compare missed rejected rows to similar accepted controls and false positives to similar rejected controls.
- Feed only portable, counterexample-tested learnings back to the semantic skill.

## References

- [workflow.md](references/workflow.md) for post-seal evaluation sequence.
- [output-contract.md](references/output-contract.md) for public and internal output constraints.

Helper code in `scripts/evaluator_boundary.py` is allowed only for post-seal integrity checks and metrics. It must not be imported by the semantic review skill.
