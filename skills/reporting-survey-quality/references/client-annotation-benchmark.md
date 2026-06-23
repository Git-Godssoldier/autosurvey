# Client Annotation Benchmark

Client-provided annotated workbooks are calibration examples. They show the minimum review surface a PM expects, not the target depth.

## Farnsworth benchmark

The Farnsworth example contains:

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

A run that only recreates annotated columns, flags, charts, or scores is incomplete. The output must let a PM understand what the agent saw, why the recommendation is defensible, and how the next survey pass improves.
