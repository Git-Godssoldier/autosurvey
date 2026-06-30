# Command: blind-run

Run the holistic agent review pipeline on an unannotated Decipher survey export.

## When to use

This is the normal production flow. The input is a raw `.xlsx` file with respondent data and a Datamap sheet. No annotations, no `status` labels, no client flags.

## Steps

### 1. Install dependencies (first run only)

```bash
pip3 install -r skills/cleaning-survey-quality/requirements.txt
```

### 2. Stage 0 — Normalize workbook to SQLite

For production, benchmark, or traceable improvement runs, read `references/production/dataset-normalization-sqlite.md` and create:
- `{output_dir}/normalized/survey_quality.sqlite`
- `{output_dir}/normalized/schema_summary.md`
- `{output_dir}/normalized/field_roles.csv`
- `{output_dir}/normalized/import_report.json`
- `{output_dir}/normalized/analysis_queries.sql`

Complete this before scoring. Verify respondent counts, field-role mapping coverage, UUID uniqueness, label distributions when present, timing ranges, and open-end blank rates. Skip this only for quick smoke tests and state the skip in the run log.

### 3. Stage 1 — Generate review packets

```bash
python3 skills/cleaning-survey-quality/scripts/run_holistic_agent_review.py /path/to/survey.xlsx \
  --output-dir /path/to/holistic_output --chunk-size 200
```

This parses the Datamap, extracts features, runs ML triage, detects AI text similarity, and generates:
- `review_chunk_XX.json` — one review packet per chunk (~200 respondents each)
- `agent_review_instructions.md` — the evidence-family framework instructions

Before Stage 2, read the generated instructions and confirm they preserve the current V7 calibration:
- ML >= 0.8 can drive DISCARD.
- ML >= 0.6 requires at least one independent evidence family for DISCARD.
- 4 or more independent evidence families can drive DISCARD without strong ML.
- `thin_on_topic` does not fire `core_oe_quality`.
- Stage 2 quality failure and badopen severity default to REVIEW unless ML or family convergence supports DISCARD.

### 4. Stage 2 — Chunk review agents

Run Stage 2 through Devin CLI print mode with GLM 5.2. Do not use Codex CLI for row review. The review lane is the full packet set generated in Stage 1, not only a score band.

For each `review_chunk_XX.json` file, create a prompt file that tells Devin to:
- read `agent_review_instructions.md`;
- read the specific `review_chunk_XX.json`;
- apply the V7 evidence-family framework to each respondent;
- write raw JSON only to `agent_judgments_chunk_XX.json`, as an array with `respondent_id`, `agent_score` (-1 to +1), `agent_judgment` (DISCARD/REVIEW/KEEP), and `agent_justification` (2-4 sentences).

Run each chunk with:

```bash
PROMPT_FILE="/path/to/holistic_output/prompts/review_chunk_XX.prompt.md"
OUTPUT_JSON="/path/to/holistic_output/agent_judgments_chunk_XX.json"
devin --model "glm-5.2" --prompt-file "$PROMPT_FILE" -p > "$OUTPUT_JSON"
python3 -m json.tool "$OUTPUT_JSON" >/dev/null
```

Use the active run concurrency policy. For traceable improvement runs, concurrency is 1: process one chunk, log its start/completion/output path/JSON validation/exception/follow-up action, then move to the next chunk. Only use parallel chunk review when the run log explicitly allows it.

### 5. Stage 3 — Integrate judgments

```bash
python3 skills/cleaning-survey-quality/scripts/integrate_agent_judgments.py /path/to/survey.xlsx /path/to/holistic_output
```

This merges all chunk judgments and writes:
- `{dataset}_annotated.xlsx` — Original Excel + 9 annotation columns
- `{dataset}_dashboard.html` — Self-contained HTML dashboard
- `summary.json` — Aggregate statistics

### 6. Verify output

- Check that the SQLite normalized store exists for production, benchmark, or traceable improvement runs
- Check that the annotated Excel has the same row count as the source file
- Check that every row has a `Final_Score` and `Final_Judgment`
- Check that the dashboard renders correctly
- Check that discard rows in the Excel match the discard table in the dashboard

## References to read before running

- `references/production/progressive-chain-filtering.md` — Full four-layer progressive filtering specification
- `references/production/dataset-normalization-sqlite.md` — SQLite normalization and SQL analysis standards
- `references/production/decipher-blind-authenticity-review.md` — Blind authenticity review rules
- `references/production/v7-calibration-and-guardrails.md` — Current calibrated disposition thresholds
- `references/production/agent-authored-row-review.md` — Prevents the pipeline from becoming a rigid checklist
- `references/production/discard-exemplar-library.md` — Calibrated exemplars of true positives, false positives, true negatives, and false negatives
