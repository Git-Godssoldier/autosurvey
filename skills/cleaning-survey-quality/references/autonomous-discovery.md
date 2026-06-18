# Autonomous Discovery

The discovery pass should find meaningful candidate analyses before applying or evolving a rubric.

## Required Discovery Output

For each analysis, output:

- `analysis_id`
- status: `scorable`, `needs_mapping`, or `not_available`
- candidate columns or column groups
- business meaning
- scoring readiness

## Analysis Families

1. Completion-time quality
   - Find qtime, duration, elapsed, or completion-time fields.
   - Score raw times under four minutes.
   - Flag missing or ambiguous timing fields in the report.
2. Duplicate technical signal
   - Find IP or comparable respondent technical identifiers.
   - Score repeated values as review signals, not automatic fraud proof.
3. Matrix straightlining
   - Group repeated grid column prefixes such as `q32_Lr1r1...q32_Lr1r20`.
   - Score repeated or near-repeated response patterns across enough answered items.
4. Open-end quality
   - Find open-ended text fields.
   - Use two stages: deterministic gibberish/noise filtering, then dimension evaluation.
   - Evaluate effort, relevance, and completeness separately.
   - Score obvious low-effort text and optional topic mismatch only when evidence is transparent.
   - Send nuanced semantic quality through second-pass disposition instead of hard-coding brittle text rules; survivor rows should produce keep rationale and survey-question recommendations.
5. Brand consistency
   - Find brand, preference, consideration, recommendation, purchase, or awareness candidates.
   - Mark as `needs_mapping` until the project defines which fields conflict.
6. AI/open-end authenticity
   - Use helper likelihood fields if already present.
   - Do not require helper fields for unannotated runs.

## Pattern Discovery

Look for repeated row patterns, not only single-row defects:

- supplier/source concentration among severe rows
- repeated duplicate technical values
- repeated straightline grid groups
- open-end fields that produce many topic mismatches
- analysis families that are unavailable and block stronger scoring

Report pattern-level issues to the Data Quality Lead when they suggest a fielding or supplier problem. Do not convert individual survivor rows into discard escalations unless row-level converging evidence supports that decision.

## Dynamic-Data Rule

Survey response data may change by wave, client, audience, language, and question design. Do not assume the same criteria apply everywhere. First discover the shape of the data, then propose candidate analyses, then evaluate whether each analysis is safe to score.

Prefer:

- discovered analysis families
- dimension-level open-end evaluation
- project-specific mappings
- held-out adjudicated evals
- survivor recommendations that improve question framing

Avoid:

- global column-name assumptions
- fixed point totals without validation
- automatic rejection from semantic judgments
- escalation for rows that merely need clearer survey-question design
- treating helper columns as required raw inputs
