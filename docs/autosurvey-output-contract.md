# Autosurvey output contract

Autosurvey has two output zones.

## Public output folder

The public folder must contain exactly two files:

- `AUTOSURVEY_RESULTS.xlsx`
- `AUTOSURVEY_EVOLUTION.md`

`AUTOSURVEY_RESULTS.xlsx` must have exactly two visible worksheets:

- `Labeled Rows`
- `Dashboard`

The `Labeled Rows` sheet must contain one row per respondent. It must include stable source fields and then the standardized Autosurvey columns for dataset id, respondent id, client label when available, five-tier decision, binary prediction, authenticity risk, client rejection probability, confidence, semantic rationale, signal evidence, protective evidence, agreement, error type, and model version.

The `Dashboard` sheet must keep the confusion matrix and rejected-class recall near the headline metrics. A single headline accuracy is not enough.

## Internal audit folder

Detailed artifacts belong under `.autosurvey-internal/`.

Internal artifacts include pair registries, input hashes, leakage audits, fold assignments, sealed or frozen predictions, metric tables, error ledgers, model registries, signal performance tables, and run manifests.

Do not delete internal audit evidence to make the public folder clean. Keep the public folder clean by placing audit evidence in the internal folder from the start.

## Benchmark language

The 11 current TFG original/graded pairs are development data. They support retrospective nested validation and signal evolution. They do not support an untouched external-release claim.

Use `TARGET_MET` only when the development gate and future untouched external-release gate both pass. Otherwise report the honest terminal state.
