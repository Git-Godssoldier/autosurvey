---
name: cleaning-survey-quality
description: Cleans and scores Decipher-style survey quality workbooks for market research datasets. Use when reviewing survey completes, fraud, inattentive respondents, open-end AI suspicion, straightlining, inconsistent brand answers, short completes, duplicate IPs, respondent flags, or survey quality files. The primary flow is a multi-agent holistic review that produces DISCARD/REVIEW/KEEP judgments with evidence-family convergence scoring.
---

# Cleaning Survey Quality

Run a reproducible survey quality pass on unannotated Decipher-style survey exports before PM review. The output is a per-respondent DISCARD/REVIEW/KEEP judgment with a -1 to +1 score and a natural-language justification citing specific evidence.

## Critical: Use the Holistic Agent Review Pipeline

**Do NOT run `run_quality_loop.py` or `survey_pipeline.py` alone.** These are the old scripted pipelines that produce only Keep/Light review with zero discards. They are data-staging tools, not the review pipeline.

The production flow is the **holistic agent review** with three scripts:

```
Stage 1: run_holistic_agent_review.py  → generates review packets + agent instructions
Stage 2: subagent review               → one subagent per chunk reads packets, writes judgments
Stage 3: integrate_agent_judgments.py  → merges judgments into annotated Excel + dashboard
```

## Quick Start

```bash
# Install dependencies
pip3 install -r skills/cleaning-survey-quality/requirements.txt

# Stage 1: Generate review packets (parses Datamap, extracts features, ML triage, AI text detection)
python3 skills/cleaning-survey-quality/scripts/run_holistic_agent_review.py /path/to/survey.xlsx \
  --output-dir /path/to/holistic_output --chunk-size 200

# Stage 2: Spawn subagents to review each chunk
# Each subagent reads review_chunk_XX.json and writes agent_judgments_chunk_XX.json
# The instructions file (agent_review_instructions.md) is auto-generated with the evidence-family framework

# Stage 3: Integrate judgments into annotated Excel + dashboard
python3 skills/cleaning-survey-quality/scripts/integrate_agent_judgments.py /path/to/survey.xlsx /path/to/holistic_output
```

## What Each Stage Does

### Stage 1: Data Staging + Review Packet Generation (`run_holistic_agent_review.py`)

Scripts parse the Datamap, map response fields to question text and value labels, compute population-level statistics, and build structured JSON review packets. Scripts do NOT make discard decisions.

Each packet contains:
- Full answer chain with question text and value labels for every field
- All open-end fields with their prompt text
- Per-grid straightlining analysis
- Timing (minutes + percentile)
- Supplier reject rate
- ML triage score (0-1 risk probability from Gradient Boosting model trained on 13,388 respondents)
- Survey defender signals (TERMFLAGS, qc, RD_Search, LangAssess, vlist, decLang, vdropout)
- Cross-respondent AI text similarity detection (`ai_text_suspicion` score)
- Duplicate text counts per OE field
- Answer entropy
- `defender_summary` — human-readable consolidation of all platform signals

The script also generates `agent_review_instructions.md` with the evidence-family framework rules (see below).

### Stage 2: Subagent Review

Each subagent reads one `review_chunk_XX.json` file (~200 respondents) and applies the evidence-family framework to produce `agent_judgments_chunk_XX.json` with:
- `respondent_id`
- `agent_score` (-1.0 to +1.0)
- `agent_judgment` (DISCARD / REVIEW / KEEP)
- `agent_justification` (2-4 sentences citing specific evidence)

### Stage 3: Integration (`integrate_agent_judgments.py`)

Merges all chunk judgments, re-runs feature extraction, and writes:
- **Annotated Excel** with 9 added columns: ML_Triage_Score, Agent_Score, Final_Score, Final_Judgment (color-coded), Agent_Justification, Key_Signals, Reassessment_Notes, Defender_Summary, AI_Text_Suspicion
- **Dashboard HTML** with summary cards, score distribution, supplier analysis, and discard table with agent justifications
- **Summary JSON** with aggregate statistics

## The Evidence-Family Framework (v4)

The agent instructions use an evidence-family convergence model, not discrete signal labels. The master rule:

**A row is discard-like when the core open end fails its question role, lacks grounded chain evidence, and converges with at least one independent risk family.**

The five independent risk families:
1. **Model risk** — ML triage score >= 0.7
2. **Platform risk** — TERMFLAGS=1, qc flag, RD_Search elevated, non-English
3. **Source risk** — high supplier reject rate, elevated RD_Search threat
4. **Duplicate semantics** — text similarity to other respondents, paraphrase clusters
5. **Weak outro behavior** — generic praise, off-topic, incoherent, or chain-inconsistent outro

### Core Open-End Quality (the anchor)

The core OE field is the one asking for personal motivation, experience, or job role. Read the question text to identify it. Apply these tests:

- **Answer-Role Test**: Does the answer actually answer the question? "Water filtration systems" names the topic but fails a motivation question. "My water started smelling like chlorine after the city changed treatment" passes.
- **Grounded First-Person Test**: First-person pronouns are NOT protective by themselves. AI uses first-person too. The test is whether the content is grounded in lived experience (concrete events, household conditions, sensory issues, health concerns, named places, chain references).
- **Synthetic Detail Detection**: Some details sound specific but are common fake clusters ("my skin", "my family", "chlorine"). Genuinely specific details are idiosyncratic (named conditions, named events, unusual sensory details, specific brand comparisons).
- **Product-Copy Register**: Marketing-like language ("multi-stage filtration", "contaminant removal technologies") is suspicious, especially without lived context.
- **Paraphrase-Level Duplicate Detection**: Check if the answer tells the same story frame as many others, even with different surface text.

### Platform Signal Override Logic

- **TERMFLAGS=1**: Strong discard (-0.7), NOT automatic. Override to REVIEW only when the core OE has unusually strong human evidence (specific named event/place/condition + chain-consistent + no AI markers). The client overrides in ~25% of cases.
- **qc=8 or qc=9**: Automatic discard (-1.0)
- **Non-English in US survey**: Automatic discard

### Outro-Only Suspicion Guardrail

AI text suspicion on the outro field ONLY is downweighted. Generic topic restatements ("water filtration systems") trigger high similarity because many respondents write the same thing — that's topical inevitability, not fraud. Only treat as a strong signal when the core OE field itself is flagged.

### Short Non-Answer Rule

Short answers (<25 chars) to a motivation question are almost always role failures. "It's essential", "Because I need one" are NOT motivations. When paired with ANY risk family signal, this becomes a discard.

### Typo Laundering Guard

Typos are NOT protective unless the surrounding answer is grounded and coherent. A typo inside generic content is neutral. "I was concerned about the filteration" with no other detail = not protective.

## Progressive Filtering Order

The review follows a strict ordering. Each layer filters the population progressively.

1. **Datamap mapping** — Parse the Datamap, extract prompt text, value labels, field groups, response options. Build the Question Contract. Map field roles before scoring.
2. **Per-field chain validity** — For each respondent, judge whether each answer is on-topic and credible for that specific prompt. Classify as responsive, partially responsive, nonresponsive, wrong semantic dimension, off-topic, or invalid.
3. **Observational signals** — Timing, supplier/source cohort, technical (IP, device), platform helpers (TERMFLAGS, RD_Search). These refine the chain layer, they do not replace it.
4. **Cross-population signals** — Duplicate open text, response vector clustering, timing clusters, matrix pattern clustering, shared rare phrases. These are the strongest convergence evidence.

See `references/progressive-chain-filtering.md` for the full specification.

## What Scripts Do vs What Agents Do

**Scripts DO:**
- Parse the Datamap into question text and value labels
- Look up coded values to get their label meanings
- Compute timing distributions and percentiles
- Detect exact duplicate text across respondents
- Detect duplicate IP addresses
- Compute supplier cohort distributions
- Run the ML triage model
- Detect cross-respondent AI text similarity
- Assemble structured JSON packets for the agents

**Scripts do NOT:**
- Classify open-end text as "meta_praise" or "templated"
- Detect contradictions between fields
- Make final discard decisions
- Generate proposition templates
- Apply regex rules to open-end text for semantic classification

## Blind Runs vs Methodology Development

**Blind runs** (production): Run on blank Decipher exports. Do NOT use `status`, client flags, helper labels, or final-review fields as decision evidence. The pipeline must work without any annotations.

**Methodology development**: Annotated TFG workbooks (`status = 3` = accepted, `status = 5` = rejected) are used to develop and calibrate the method. Use `references/authenticity-first-calibration.md` for the five-tier routing model and label-aware contrast.

## Output Artifacts

After Stage 3, the output directory contains:

1. **`{dataset}_annotated.xlsx`** — Original Excel + 9 annotation columns
2. **`{dataset}_dashboard.html`** — Self-contained HTML dashboard
3. **`summary.json`** — Aggregate statistics
4. **`agent_judgments.json`** — Merged agent judgments (all chunks)
5. **`review_chunk_XX.json`** — Review packets (one per chunk)
6. **`agent_judgments_chunk_XX.json`** — Per-chunk judgments
7. **`agent_review_instructions.md`** — The evidence-family framework instructions

## ML Model

A Gradient Boosting classifier trained on 13,388 annotated respondents across 11 datasets provides a risk probability (0-1). It is a **triage tool** that flags high-risk respondents for agent review — not a standalone classifier.

The model achieves AUC 0.48-0.88 across datasets. It cannot set per-dataset discard thresholds without calibration. Use it as one input to the evidence-family framework, not as the final decision.

Key signals (by importance): LangAssessReadLevel, supplier_x_signals, supplier_reject_rate, answer_entropy, matrix straightlining, oe_total_chars. See `references/per-dataset-ml-signals.md` for per-dataset signal priorities and `references/generalizable-signals.md` for verified generalizable signals.

## Package Requirements

```bash
pip3 install -r skills/cleaning-survey-quality/requirements.txt
```

Required: `openpyxl>=3.1.0`, `scikit-learn>=1.3.0`, `pandas>=2.0.0`, `numpy>=1.24.0`, `scipy>=1.10.0`, `xgboost>=2.0.0`, `lightgbm>=4.0.0`

## When To Read References

- `references/progressive-chain-filtering.md` — Full four-layer progressive filtering specification. Read before running the full-chain review.
- `references/decipher-blind-authenticity-review.md` — Read before every blind run on a blank Decipher export.
- `references/authenticity-first-calibration.md` — Read when using TFG status labels, client annotations, or calibration against accepted/rejected rows.
- `references/semantic-signal-expansion.md` — Read before changing signal weighting, semantic similarity, or convergence logic.
- `references/combinatorial-discard-signal-profile.md` — Read before applying client quality signals or signal tiering. Contains the empirically validated TIER 1/2/3 signal system from 13,388 annotated respondents.
- `references/discard-exemplar-library.md` — Read before making discard decisions on individual respondents. Contains calibrated exemplars of true positives, false positives, true negatives, and false negatives.
- `references/per-dataset-ml-signals.md` — Read before analyzing a new dataset. Contains the strongest predictive signals for each of the 11 annotated datasets.
- `references/generalizable-signals.md` — Read before using ML features in production. Lists 7 verified generalizable signals and signals that need caution.
- `references/agent-authored-row-review.md` — Read before any respondent-level scoring or final review. Prevents the pipeline from becoming a rigid checklist.
- `references/agentic-escalation-path.md` — Read before running a full dataset from raw export to final discard choices.
- `references/client-terminology-glossary.md` — Read to define client, PM, survey, and quality terms before writing final artifacts.
- `references/internal-signal-learning.md` — Read when internal comments, PM notes, or prior criteria are available.
- `references/evaluation-methodology.md` — Read before changing open-end evaluation or validation metrics.
- `references/escalation-policy.md` — Read before changing severity bands or owners.
- `references/ml-pipeline-report.md` — Full report on the ML building process, three-part pipeline, and per-dataset evaluation results.
- `references/research-grounding.md` — Read when changing the agent architecture or reporting/evolution loop.
- `references/dataset-cycle-loop.md` — Read when the run is part of an improvement cycle or multi-dataset pass.
- `references/autonomous-discovery.md` — Read before changing discovery behavior.
- `references/rubric-seed.md` — Historical seed context only, not a source of fixed weights.
- `references/full-workflow-specification.md` — Read for the complete procedural specification: pre-run framing, workbook exploration, quality hypothesis building, per-field chain validity, generated criteria policy, evidence rules, agent annotation layer, escalation policy, kept review synthesis, raw-data discovery, autonomous candidate analysis, and delivery verification.
- `references/project-context-template.md` — Read when adapting the workflow to a specific client or survey program.
