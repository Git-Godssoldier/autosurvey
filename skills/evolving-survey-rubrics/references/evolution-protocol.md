# Evolution Protocol

## Required Inputs

- Candidate workbook from the Opulent-generated process.
- PM final-review workbook.
- Stable respondent key: prefer `uuid`.
- Current rubric JSON or the seed rubric from `cleaning-survey-quality/references/rubric-seed.md`.

## Candidate Change Types

1. Threshold tuning:
   - Change action cutoffs only when many rows cluster near a boundary and PM labels consistently differ.
2. Weight tuning:
   - Adjust criterion points only when a criterion is consistently too weak or too strong.
3. New deterministic criterion:
   - Add only when a column-level signal explains repeated PM corrections.
4. New open-end rubric instruction:
   - Add only when examples show repeatable language patterns that PMs reject.
5. New evaluation dimension:
   - Add when adjudicated evidence shows that effort, relevance, completeness, or gibberish/noise explains failures better than a broad open-end flag.

## Acceptance Criteria

A proposed change must include:

- At least 5 adjudicated examples, unless the criterion is severe fraud or safety related.
- No material loss in review precision.
- Improved recall for PM-reviewed poor-quality respondents, or a clear PM-time reduction.
- Agreement metrics beyond raw match rate when labels exist.
- Evidence that the change generalizes across at least one meaningful slice, such as supplier/source, wave, audience, or open-end question.
- Row-level examples with source columns and observed values.
- A rollback condition if the next wave does not reproduce the gain.

## Reject Conditions

Reject changes when:

- Evidence comes only from model-generated labels.
- The rule cannot be explained to a PM.
- The rule depends on hidden prompt behavior rather than workbook data.
- The rule disproportionately flags one supplier/source without evidence of actual quality issues.
- The added complexity does not reduce PM review time.
- The rule compresses distinct open-end failure modes into one opaque score.
- Validation relies only on percentage agreement.
- The rule was tuned on one graded file and not tested on a held-out or future wave.
