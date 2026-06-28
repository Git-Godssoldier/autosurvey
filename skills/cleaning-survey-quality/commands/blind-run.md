# Command: blind-run

Run the holistic agent review pipeline on an unannotated Decipher survey export.

## When to use

This is the normal production flow. The input is a raw `.xlsx` file with respondent data and a Datamap sheet. No annotations, no `status` labels, no client flags.

## Steps

### 1. Install dependencies (first run only)

```bash
pip3 install -r skills/cleaning-survey-quality/requirements.txt
```

### 2. Stage 1 — Generate review packets

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

### 3. Stage 2 — Subagent review (YOU spawn the subagents)

**The agent running this skill performs Stage 2 itself** by spawning subagents using its own subagent/tool infrastructure. Do NOT use external CLI tools (Codex, etc.). No external tool installation is required.

For each `review_chunk_XX.json` file, spawn a subagent that:
1. Reads the `agent_review_instructions.md` file
2. Reads the `review_chunk_XX.json` file
3. Applies the V7 evidence-family framework to each respondent
4. Writes `agent_judgments_chunk_XX.json` to the same output directory, as a JSON array with `respondent_id`, `agent_score` (-1 to +1), `agent_judgment` (DISCARD/REVIEW/KEEP), and `agent_justification` (2-4 sentences)

**Spawn all chunk subagents in parallel.** Wait for all to complete before proceeding to Stage 3.

### 4. Stage 3 — Integrate judgments

```bash
python3 skills/cleaning-survey-quality/scripts/integrate_agent_judgments.py /path/to/survey.xlsx /path/to/holistic_output
```

This merges all chunk judgments and writes:
- `{dataset}_annotated.xlsx` — Original Excel + 9 annotation columns
- `{dataset}_dashboard.html` — Self-contained HTML dashboard
- `summary.json` — Aggregate statistics

### 5. Verify output

- Check that the annotated Excel has the same row count as the source file
- Check that every row has a `Final_Score` and `Final_Judgment`
- Check that the dashboard renders correctly
- Check that discard rows in the Excel match the discard table in the dashboard

## References to read before running

- `references/production/progressive-chain-filtering.md` — Full four-layer progressive filtering specification
- `references/production/decipher-blind-authenticity-review.md` — Blind authenticity review rules
- `references/production/v7-calibration-and-guardrails.md` — Current calibrated disposition thresholds
- `references/production/agent-authored-row-review.md` — Prevents the pipeline from becoming a rigid checklist
- `references/production/discard-exemplar-library.md` — Calibrated exemplars of true positives, false positives, true negatives, and false negatives
