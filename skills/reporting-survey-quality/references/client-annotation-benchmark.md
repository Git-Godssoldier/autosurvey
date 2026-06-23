# Client Annotation Benchmark

Client-provided annotated workbooks are calibration examples. They show the minimum review surface a PM expects, not the target depth.

## Farnsworth benchmark

The Farnsworth final annotated workbook is a baseline validation set. In the reviewed file it contains 1,036 respondents and recommends no deletions. The client route is conservative: 988 rows are `Keep`, 45 rows are `Light review`, 3 rows are `Review closely`, and 0 rows are `Delete / Exclude`.

The client signal counts in the final review workbook are:

- qtime under 4 minutes: 4
- preferred brand inconsistent with consideration or recommendation: 47
- q32 straightline or near-straightline: 35
- outro off-topic or not gas and convenience-store relevant: 20
- high AI or open-end concern: 2
- moderate AI or open-end concern: 101
- duplicate IP records: 0
- no concerns: 841

The final review columns are:

- workbook-level cleaning summary with respondent counts, flag counts, action counts, and scoring notes
- row-level columns for qtime under four minutes, brand inconsistency, grid straightlining, open-end topic relevance, duplicate IP, respondent flags, respondent score, and recommended action
- visual fill colors for flagged cells
- no cell comments and limited prose explanation beyond scoring notes

The onboarding instructions also require review of:

- Datamap prompt text and response options before scoring
- qtime speeders and unusually long completes
- start-date or timestamp bursts, including odd starts between 22:00 and 04:00
- grid straightlining
- every open-ended response, especially `qc` or `outro`
- nonresponsive, AI-suspicious, duplicate, odd-theme, or off-theme open ends
- long, polished, punctuation-heavy, or em-dash-heavy open ends as possible support signals

## Baseline validation requirement

When a client annotated workbook is available, build `client_annotation_validation.md`, `client_annotation_validation.csv`, and `client_annotation_validation_summary.json` before final delivery.

The validation must compare autosurvey against the client baseline by respondent key. At minimum, it must report:

- client action counts
- client flag-family counts
- autosurvey review coverage for every client signal family
- every client `Review closely` row and whether autosurvey performed final semantic review
- every client `Light review` row and whether autosurvey routed it to review or explains why it did not
- autosurvey-reviewed rows that the client marked `No concerns`
- autosurvey discard rows that the client marked `Keep`
- artifact consistency between the discard set, findings essay, escalation packet, positive report, deep findings memo, and visual findings report

Low coverage against a client signal family is not automatically a failure if the client signal is only review context. It is a failure if autosurvey claims benchmark superiority without explaining the gap and recording the next-pass fix.

For the Farnsworth benchmark, autosurvey should be stricter than the client process in interpretation, not more reckless in deletion. The client baseline proves that q32 straightlining, moderate AI or open-end concern, preferred-brand inconsistency, and off-topic outro are review signals. They do not become row-level exclusion evidence until full-chain review finds converging support.

The June 2026 validation run surfaced these workflow lessons:

- Autosurvey must review every client `Review closely` row.
- Autosurvey must either review every client `Light review` row or explain why the signal family should remain report-only.
- Preferred-brand inconsistency and moderate AI or open-end concern need explicit coverage reporting because they can be easy to miss when the first pass focuses on text relevance.
- Rows that autosurvey discards but the client kept require a direct analyst note. The note must explain whether autosurvey found stronger full-chain evidence or whether the discard should be downgraded.
- Any disagreement between `agent_discard_set.csv` and Markdown reports blocks delivery until the reports are corrected.

## Autosurvey standard

Autosurvey should preserve the useful audit surface from the annotated workbook, then surpass it.

Each final package should include:

- equivalent practical fields or tables for qtime, timestamp/fielding pattern, straightline, brand mapping, open-end relevance, duplicate technical identifiers, respondent flags, score, and action
- Datamap-derived field roles before any scoring
- full question-chain and full response-chain context before final semantic review
- a focused semantic chain around `qcoe1`, `q9`, `q10`, `q32`, `q43`, and `outro` when those fields exist
- a final semantic decision that can override static checks when counterevidence exists
- clear discard rationale, keep rationale, full-chain counterevidence, and semantic discard basis
- readable prose analysis of best and worst response chains
- demographic and aggregate insights from fields such as `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, and `qPolitics`
- kept-review synthesis that turns survivor patterns into survey-question or fielding-parameter improvements
- next-pass signal inventory that says what should change before the next first-pass scoring run
- client-annotation validation that proves autosurvey preserved the client baseline and explains every material difference

A run that only recreates annotated columns, flags, charts, or scores is incomplete. The output must let a PM understand what the agent saw, why the recommendation is defensible, and how the next survey pass improves.
