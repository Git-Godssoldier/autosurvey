# No-ML production signal table mode

Use this mode when a production run cannot use the bundled ML model, model scores, or a same-dataset training step.

## Required flow

1. Normalize the workbook into SQLite.
2. Reconstruct the survey contract from the Datamap.
3. Build `signal_dictionary`.
4. Build `signal_matrix`.
5. Review the full dataset using the signal matrix and the raw answer chain.
6. Write final judgments.
7. If labels arrive later, write `signal_lift` and error analysis for evolution.

## Signal dictionary

Each signal must have:

- `signal_name`
- `family`
- `source`
- `description`
- `production_safe`
- `leakage_risk`
- `agent_marking_instruction`

Only use a signal when `production_safe` is true and `leakage_risk` is false.

## Signal matrix

The matrix must have one row per respondent and one Boolean column per signal.

The agent must mark every signal present or absent before assigning DISCARD, REVIEW, or KEEP.

Do not hide signal evidence only in prose. The prose explanation should cite the signal columns that fired.

## Full dataset review lane

In production no-ML mode, the review lane is the full dataset. Do not route only a middle score band to agent review.

The signal matrix is the row case file and memory layer. It can support proposed auto gates and prioritization, but it does not replace row-level agent authorship.

Every source respondent must receive:

- a completed Boolean signal row;
- a raw answer-chain review;
- an agent-authored final judgment;
- a short justification that cites the signal columns and answer evidence that mattered.

Label-tuned thresholds found during perturbation, such as a minimum review band needed to reach 90% on an annotated dataset, are diagnostic lower bounds for planning. They are not production routing rules until validated on another dataset without label leakage.

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

## Devin Stage 2 runtime

Run production row-review agents through Devin CLI print mode with GLM 5.2 using Devin model id `glm-5-2`. Do not use Codex CLI for row review.

Process one chunk at a time unless the run log explicitly allows more concurrency.

For each chunk:

```bash
PROMPT_FILE="/path/to/holistic_output/prompts/review_chunk_XX.prompt.md"
OUTPUT_JSON="/path/to/holistic_output/agent_judgments_chunk_XX.json"
devin --model "glm-5-2" --prompt-file "$PROMPT_FILE" -p > "$OUTPUT_JSON"
python3 -m json.tool "$OUTPUT_JSON" >/dev/null
```

Append the command, output path, JSON validation result, retry count, and next action to `workledger.md` before starting the next chunk.

## Evaluation rule

When labels are available after the run, evaluate three metrics separately:

- fully automated DISCARD versus KEEP accuracy;
- REVIEW workflow accuracy, assuming reviewed rows are resolved by a human;
- review volume needed to reach a target such as 90% final workflow accuracy.

Do not report a label-tuned review threshold as a proven production rule until it has been tested on another dataset.
