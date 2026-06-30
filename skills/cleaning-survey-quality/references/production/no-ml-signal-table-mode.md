# No-ML production signal table mode

Use this mode when a production run cannot use the bundled ML model, model scores, or a same-dataset training step.

Read `no-ml-row-signal-decision-criteria.md` before building prompts or reviewing rows.

## Required flow

1. Normalize the workbook into SQLite.
2. Reconstruct the survey contract from the Datamap.
3. Build `signal_dictionary`.
4. Build `signal_matrix`.
5. Build a signal preflight profile from `signal_matrix`.
6. Review the full dataset using the signal matrix and the raw answer chain.
7. Write final judgments with per-signal assessments.
8. Validate final judgments against the chunk, signal dictionary, and signal matrix.
9. If labels arrive later, write `signal_lift` and error analysis for evolution.

## Signal dictionary

Each signal must have:

- `signal_name` or `signal`
- `family`
- `source`
- `description`
- `production_safe`
- `leakage_risk`
- `agent_marking_instruction`
- `positive_criteria`
- `negative_criteria`
- `decision_weight`
- `false_positive_guardrail`
- `false_negative_guardrail`

Only use a signal when `production_safe` is true and `leakage_risk` is false.

## Signal matrix

The matrix must have one row per respondent and one Boolean column per signal.

The agent must mark every signal present or absent before assigning DISCARD, REVIEW, or KEEP.

Do not hide signal evidence only in prose. The prose explanation should cite the signal columns that fired.

The agent output must include `signal_assessments`. This object must have one key per production-safe signal. Each key must include:

- `present`
- `criterion`
- `evidence`
- `decision_weight`
- `decision_effect`
- `confidence`

The output must also include `signals_present`, `signals_counted_for_discard`, `signals_context_only`, `signals_protective`, and `disposition_rule_id`.

## Full dataset review lane

In production no-ML mode, the review lane is the full dataset. Do not route only a middle score band to agent review.

The signal matrix is the row case file and memory layer. It can support proposed auto gates and prioritization, but it does not replace row-level agent authorship.

Every source respondent must receive:

- a completed Boolean signal row;
- a raw answer-chain review;
- an agent-authored final judgment;
- a short justification that cites the signal columns and answer evidence that mattered.

Label-tuned thresholds found during perturbation, such as a minimum review band needed to reach 90% on an annotated dataset, are diagnostic lower bounds for planning. They are not production routing rules until validated on another dataset without label leakage.

## Signal quality gate

Before row review, profile every signal in the matrix.

If a signal is present in more than 85 percent of rows, keep marking it for every row, but set `decision_weight` to `context_only` unless the row has a separate row-specific trigger.

If a signal is present in fewer than 1 percent of rows, treat it as sparse. It can support a hard failure when present, but absence does not protect the row.

Family rollups do not count as additional independent signals when their child signals are already counted.

In the Echo no-ML run, `matrix_near_straightline`, `matrix_many_straightlined_grids`, and `brand_low_awareness_count` were too broad to count toward discard by themselves.

## Allowed signal families

- platform risk
- timing and engagement
- matrix straightlining
- duplicate semantics
- language and readability
- open-end role fit
- survey structure
- brand funnel
- quota reconstruction
- source or supplier context when it is not label-derived

## Forbidden inputs

Do not use these during blind scoring:

- client `status`
- raw client `markers`
- `bad:` marker tokens
- same-dataset labels
- same-dataset fitted models
- prior prediction files
- post-review client notes that were not available at runtime

## Runtime rule

No-ML fully automated discard should be conservative.

Use DISCARD only when there is a hard platform failure, a clear semantic failure, or several independent signal families converge.

Use REVIEW for mixed signal evidence, but do not let this narrow the production review lane. The full dataset still receives agent review.

Use KEEP when hard failures are absent and the signal table shows no meaningful convergence.

Do not call outdoor-property answers hard wrong-topic only because they do not name outdoor power equipment. Sprinkler systems, decks, ponds, landscaping, mulch, weeds, flower beds, garden beds, irrigation, patios, fences, snow removal, yard cleanup, lawn work, trimming, and blowing leaves are outdoor-adjacent. Treat these as `REVIEW` unless another hard or strong signal is present.

## Devin Stage 2 runtime

Run production row-review agents through Devin CLI print mode with GLM 5.2 using Devin model id `glm-5-2`. Do not use Codex CLI for row review.

Process one chunk at a time unless the run log explicitly allows more concurrency.

For each chunk:

```bash
PROMPT_FILE="/path/to/holistic_output/prompts/review_chunk_XX.prompt.md"
OUTPUT_JSON="/path/to/holistic_output/agent_judgments_chunk_XX.json"
devin --model "glm-5-2" --prompt-file "$PROMPT_FILE" -p > "$OUTPUT_JSON"
python3 -m json.tool "$OUTPUT_JSON" >/dev/null
python3 skills/cleaning-survey-quality/scripts/validate_agent_judgments.py \
  "/path/to/holistic_output/review_chunk_XX.json" "$OUTPUT_JSON" \
  --signal-dictionary "/path/to/holistic_output/signal_dictionary.csv" \
  --signal-matrix "/path/to/holistic_output/signal_matrix.csv"
```

Append the command, output path, JSON validation result, retry count, and next action to `workledger.md` before starting the next chunk.

## Evaluation rule

When labels are available after the run, evaluate three metrics separately:

- fully automated DISCARD versus KEEP accuracy;
- REVIEW workflow accuracy, assuming reviewed rows are resolved by a human;
- review volume needed to reach a target such as 90% final workflow accuracy.

Do not report a label-tuned review threshold as a proven production rule until it has been tested on another dataset.
