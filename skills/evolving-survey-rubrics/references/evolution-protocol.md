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
   - Adjust criterion points only when a criterion is consistently too weak or too strong after semantic expansion has been reviewed.
   - Include the agent-authored weight basis, not only the old and new number.
3. New deterministic criterion:
   - Add only when a column-level signal explains repeated PM corrections.
4. New open-end rubric instruction:
   - Add only when examples show repeatable language patterns that PMs reject.
   - State whether the rejected pattern is wrong-universe, adjacent-but-acceptable, survey-meta, generic filler, semantic drift, copied text, or low-detail but valid.
5. New evaluation dimension:
   - Add when adjudicated evidence shows that effort, relevance, completeness, or gibberish/noise explains failures better than a broad open-end flag.
6. New semantic expansion requirement:
   - Add when a raw check failed because it ignored question similarity, answer timing, prompt fit, respondent-universe fit, full-chain coherence, accepted-row guardrails, or survey-design ambiguity.

## Acceptance Criteria

A proposed change must include:

- At least 5 adjudicated examples, unless the criterion is severe fraud or safety related.
- A frozen blind record created before labels were revealed when annotated status data is used.
- Similar accepted controls for rejected examples, or an explanation of why no suitable controls exist.
- Similar rejected controls for suspicious accepted examples, or an explanation of why no suitable controls exist.
- A three-perspective readout: forensic concern, human-protective explanation, and final evidence judgment.
- No material loss in review precision.
- Improved recall for PM-reviewed poor-quality respondents, or a clear PM-time reduction.
- Agreement metrics beyond raw match rate when labels exist.
- Evidence that the change generalizes across at least one meaningful slice, such as supplier/source, wave, audience, or open-end question.
- Validation on a held-out entire dataset or future wave before the signal is called stable.
- Row-level examples with source columns and observed values.
- Agent-authored weight basis for each promoted signal, including prompt fit, question similarity, time plausibility, semantic authenticity, chain coherence, signal independence, recurrence, and accepted-row guardrails.
- A rollback condition if the next wave does not reproduce the gain.

## Reject Conditions

Reject changes when:

- Evidence comes only from model-generated labels.
- The rule cannot be explained to a PM.
- The rule depends on hidden prompt behavior rather than workbook data.
- The rule disproportionately flags one supplier/source without evidence of actual quality issues.
- The added complexity does not reduce PM review time.
- The rule compresses distinct open-end failure modes into one opaque score.
- The rule promotes straightlining without checking question similarity and answer-time plausibility.
- The rule promotes open-end topic mismatch without checking prompt fit, respondent-universe fit, adjacent-topic validity, and full-chain coherence.
- The rule changes weights without a plain-language explanation of why the evidence became stronger or weaker.
- Validation relies only on percentage agreement.
- The rule was tuned on one graded file and not tested on a held-out or future wave.
- The rule cannot distinguish client-rejection probability, authenticity risk, and model-error or audit risk.
- The rule was promoted before every Tier 5 example was audited.
