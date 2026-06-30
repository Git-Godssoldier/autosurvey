# AutoQuality work and research ledger

Date: 2026-06-30

## Current status

The 90% target is still open for production-safe AutoQuality.

Best production-safe held-out result from the Echo end-to-end self-improvement flow:

| Metric | Value |
|---|---:|
| Accuracy | 80.3% |
| Precision | 80.1% |
| Recall | 59.0% |
| F1 | 67.9% |
| AUC | 0.820 |
| Errors | 308 |

Best global-threshold probe:

| Metric | Value |
|---|---:|
| Accuracy | 80.9% |
| Errors | 299 |

The 90% gate allows at most 156 errors across 1,566 respondents. The best probe is still 143 errors short.

## Work completed

- Added run-control requirements to the survey quality skill.
- Added a required `run_todolist.md` and `workledger.md` at the start of full AutoQuality runs.
- Added SQLite normalization guidance for production, benchmark, and evolution runs.
- Changed chunk review instructions from parallel by default to an explicit concurrency policy. For traceable improvement runs, concurrency is 1.
- Ran the full Echo end-to-end dataset flow.
- Ran sequential self-improvement loops through packet features and error-source analysis.
- Logged false negatives, false positives, likely client-boundary cases, and guarded repair tests.

## Research findings

The remaining errors are not mostly simple fraud misses. Many missed client discards look human, low-risk, and on-topic from the available runtime features.

The best score-only and packet-feature loops improved the result, but only modestly. Loop 08 fixed 31 loop 07 errors and broke 27 rows that loop 07 had correct.

The most important finding is leakage separation. The client label markers directly encode the client decision:

- 553 of 553 client discards contain `badopen` and `bad:` markers.
- 1,013 of 1,013 client keeps start with `qualified,` and do not contain those bad markers.

Using those marker strings can clear 90%, but that is a diagnostic ceiling test. It is not blind AutoQuality performance.

## SQLite assessment

SQLite was helpful.

It gave one place to join respondents, field roles, long-form answers, client labels, agent judgments, strict and soft evaluation rows, loop metrics, and error ledgers.

It made the false-positive and false-negative work faster because the analysis could use SQL instead of repeatedly reparsing Excel files and JSON files.

It also made the leakage finding clear because the marker distribution could be tested directly against client labels.

SQLite did not improve the model by itself. Its value was auditability, repeatability, and cleaner error analysis.

## Next steps

Do not treat the 90% target as met unless a production-safe run reaches it without status, markers, or post-review client fields.

The next useful inputs are:

- client reject reasons,
- human adjudication of the 95 client rejects that AutoQuality marked KEEP,
- a second labeled Echo wave for train-on-one and test-on-one validation,
- panelist history across surveys.

The next useful engineering work is to keep the SQLite-backed run ledger and build a validation harness that clearly separates production-safe metrics, exploratory probes, and leakage ceiling tests.
