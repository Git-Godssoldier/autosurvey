# Post-Seal Evaluation Workflow

## 1. Verify Seal

Before labels are read, confirm the sealed ledger manifest exists, the terminal state is sealed, and file hashes match the current decision artifacts.

## 2. Load Labels

Open only the label source specified for the benchmark. Confirm which value means accepted and which value means rejected. The rejected status is the positive class for confusion metrics.

## 3. Stable-ID Join

Join the sealed ledger to labels on stable respondent identity only. Refuse duplicate IDs, missing IDs, or row-order joins.

## 4. Evaluate

Compute metrics over all eligible rows:

- Confusion matrix.
- Rejected recall.
- Rejected precision.
- Accepted specificity.
- Balanced accuracy.
- Macro F1.
- Dataset-level and overall performance.

## 5. Explain Errors

Do not stop at numbers. Read the sealed rationales and write natural-language error analysis:

- Why missed rejected rows were missed.
- Why false positives looked suspicious.
- Which accepted guardrails worked.
- Which client rejection patterns remain unexplained.
- Which signal hypotheses should be promoted, revised, or killed.

## 6. Update Safely

Only post-seal learnings may update the semantic signal bank. Promoted signals must include human protective guardrails and counterexamples.
