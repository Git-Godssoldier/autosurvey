# Autonomous Discovery

The discovery pass should find meaningful candidate analyses before applying or evolving a rubric.

## Required Discovery Output

For each analysis, output:

- `analysis_id`
- status: `scorable`, `needs_mapping`, or `not_available`
- candidate columns or column groups
- business meaning
- scoring readiness
- semantic expansion needed before weighting
- provisional weight basis after agent review, when available

## Analysis Families

1. Completion-time quality
   - Find qtime, duration, elapsed, or completion-time fields.
   - Stage raw times under four minutes as review-routing evidence.
   - Look for page, section, or question-level duration fields when available.
   - Ask whether the timing is plausible given the question mix, answer type, and open-ended response quality.
   - Flag missing or ambiguous timing fields in the report.
2. Fielding start/date pattern quality
   - Find start date, start time, timestamp, completion date, or comparable fielding-time fields.
   - Aggregate odd starts between 22:00 and 04:00, concentrated start bursts, and date/time clustering by supplier/source when available.
   - Treat fielding-time patterns as reportable context by default. They become row-level evidence only with project approval or corroborating respondent-quality evidence.
3. Duplicate technical signal
   - Find IP or comparable respondent technical identifiers.
   - Score repeated values as review signals, not automatic fraud proof.
4. Matrix straightlining
   - Group repeated grid column prefixes such as `q32_Lr1r1...q32_Lr1r20`.
   - Stage repeated or near-repeated response patterns across enough answered items.
   - Also inspect question similarity, reverse-coded or contrast items, answer-option meaning, and page or question answer time when available.
   - Treat repeated answers across semantically similar items as weaker evidence than repeated answers across unrelated constructs.
   - Require open-ended chain review before treating straightlining as a strong authenticity concern.
5. Open-end quality
   - Find open-ended text fields.
   - Use two stages: deterministic gibberish/noise filtering, then dimension evaluation.
   - Evaluate effort, relevance, and completeness separately.
   - Score obvious low-effort text and optional topic mismatch only when evidence is transparent.
   - Send nuanced semantic quality through second-pass disposition instead of hard-coding brittle text rules; survivor rows should produce keep rationale and survey-question recommendations.
   - Add semantic authenticity review: prompt fit, respondent-universe fit, requested evidence type, lived detail, chain coherence, adjacent-topic fit, wrong-universe language, survey-meta answers, generic filler, and semantic drift.
6. Brand consistency
   - Find brand, preference, consideration, recommendation, purchase, or awareness candidates.
   - Mark as `needs_mapping` until the project defines which fields conflict.
7. AI/open-end authenticity
   - Use helper likelihood fields if already present.
   - Do not require helper fields for unannotated runs.
   - Treat helper fields as routing evidence. The agent must read the open-ended response chain and decide whether the answer is fabricated, bot-like, LLM-assisted, merely polished, or acceptable.

8. Semantic similarity and answer-chain authenticity
   - Compare related question sets and response fields for copied text, adjacent-topic answers, wrong-universe answers, and contradictions.
   - Use scripts only to stage likely repeated or similar text. The agent decides semantic fit from the Datamap, question-set authenticity map, and full response chain.
   - For every promoted signal, state the weight basis and accepted-row guardrail.

## Pattern Discovery

Look for repeated row patterns, not only single-row defects:

- supplier/source concentration among severe rows
- start-date, odd-hour, or burst concentrations by supplier/source
- repeated duplicate technical values
- repeated straightline grid groups
- straightline grid groups where repeated answers span semantically different questions or implausibly fast page time
- open-end fields that produce many topic mismatches
- open-end fields where answers are fluent but do not provide the requested evidence type
- answer chains where a related topic is acceptable in one question set but wrong-universe in another
- analysis families that are unavailable and block stronger scoring

Report pattern-level issues to the Data Quality Lead when they suggest a fielding or supplier problem. Do not convert individual survivor rows into discard escalations unless row-level converging evidence supports that decision.

## Dynamic-Data Rule

Survey response data may change by wave, client, audience, language, and question design. Do not assume the same criteria apply everywhere. First discover the shape of the data, then propose candidate analyses, then evaluate whether each analysis is safe to score.

Prefer:

- discovered analysis families
- dimension-level open-end evaluation
- semantic signal expansion before weighting
- project-specific mappings
- held-out adjudicated evals
- survivor recommendations that improve question framing

Avoid:

- global column-name assumptions
- fixed point totals without validation
- treating a raw flag as a final weight without agent-authored semantic expansion
- automatic rejection from semantic judgments
- escalation for rows that merely need clearer survey-question design
- treating helper columns as required raw inputs
