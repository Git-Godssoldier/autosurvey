---
name: cleaning-survey-quality
description: Cleans and scores Decipher-style survey quality workbooks for market research datasets. Use when reviewing survey completes, fraud, inattentive respondents, open-end AI suspicion, straightlining, inconsistent brand answers, short completes, duplicate IPs, respondent flags, survey quality files, normalized survey datasets, or SQLite-backed quality analysis. The primary flow is a three-layer holistic agent review (semantic remapping + ML analysis + two-stage agent review) that produces DISCARD/REVIEW/KEEP judgments with three-component scoring (authenticity_risk, quality_discard_risk, client_reject_probability), a disposition layer separating removal reasons, badopen audit trails, and evidence-family convergence scoring across 9 independent signal families.
---

# Cleaning Survey Quality

Run a reproducible survey quality pass on unannotated Decipher-style survey exports. The output is a per-respondent DISCARD/REVIEW/KEEP judgment with a -1 to +1 score, three-component risk scores, a disposition layer classifying the removal reason, and a natural-language justification citing specific evidence.

## Three-Layer Review (v7)

AutoQuality operates through three linked layers:

### Layer 0 — Semantic Remapping (before scoring)

Each workbook is semantically remapped before scoring. We do NOT treat fields as generic columns. We reconstruct the survey contract: which fields are screeners, quotas, brand funnels, matrices, timing fields, vendor fields, open ends, review markers, and final status fields. Coded values are translated into their real survey meaning (e.g., CLASSIFY=1 → "professional"), so the review is based on what the respondent actually said or selected, not just raw codes.

### Layer 1 — ML Analysis (statistical guide, not final answer)

ML models are trained across all annotated files (13,388 respondents, 11 datasets) to identify which signals statistically separate accepted and rejected respondents at scale. The ML score guides the review but is NOT the final answer. It shows where evidence is statistically strong or weak.

Cross-corpus signal correlations are injected into every review packet so agents can calibrate their evidence-family weighting:
- **Platform risk** (RD_Searchr1): mean correlation +0.086 with client discard (strongest)
- **Timing** (qtime, low_total_duration): +0.073 (fires in 10/11 datasets)
- **Duplicate semantics**: +0.042 (moderate)
- **Survey structure** (CLASSIFY): +0.023 (weak positive)
- **Core OE quality** (thin_open_end): -0.030 (NEGATIVE — client does NOT primarily discard on OE quality)

### Layer 2 — Two-Stage Agent Review

**Stage 1 — Fraud Detection**: Is this respondent authentic? (bots, AI, platform flags, gibberish, non-English, duplicate chains, TERMFLAGS) → `authenticity_risk`

**Stage 2 — PM Quality Assessment**: Does this respondent meet the quality bar for this survey? (substantive engagement, brand funnel consistency, classification coherence, on-topic depth, survey-structure fit) → `quality_discard_risk`

### Layer 3 — Client Rejection Probability

Separate from authenticity and quality: would the client's own process discard this respondent? The client may discard for quota, badopen, eligibility, or admin reasons that are NOT quality failures. → `client_reject_probability`

**Key principle**: A respondent can be authentic (low authenticity_risk) AND substantive (low quality_discard_risk) but still discarded by the client (high client_reject_probability) due to quota balancing or badopen triggers. Conversely, a respondent can be inauthentic but kept by the client if they passed the client's review process.

## Disposition Layer (v7)

We no longer treat every removal as a "bad respondent" signal. We separate:

- `quality_auth_failure` — OE fails role test, off-topic, gibberish, AI text, platform fraud
- `quota_balancing` — respondent in over-filled quota cell, marginal quality
- `eligibility_screenout` — fails screener, wrong classification branch
- `partial_incomplete` — missing required fields, abandoned survey
- `vendor_source` — supplier reject rate, RD_Search threat
- `manual_admin` — human reviewer judgment, not detectable from data
- `unknown_mixed` — converging signals but no single clear cause
- `none` — no removal reason (KEEP)

This lets us learn separate models for true quality/auth failures, quota exclusions, eligibility cases, partial responses, vendor removals, manual decisions, and unknown/mixed cases.

## Badopen Audit Trail (v7)

Every "badopen" decision is auditable. Instead of just seeing badopen, we capture the trigger:
- `duplicate_text`, `too_short`, `pasted_text`, `wrong_topic`, `profanity`, `ai_like_similarity`, `nonresponsive`, `human_reviewer`, `none`

This makes open-end review decisions traceable and calibratable.

## The Normal Input Is an Unannotated Workbook

In most runs, the only input is a raw Decipher export (`.xlsx`) with respondent data and a Datamap sheet. There are no `status` labels, no client annotations, no accepted/rejected examples, and no helper columns. The pipeline must work without any of these.

The ML triage model is **pre-trained and bundled** (`models/survey_quality_model.pkl`). It was trained on historical annotated data, but it runs on unannotated data at runtime. You do not need annotations to run the pipeline.

Annotated workbooks (`status = 3` accepted, `status = 5` rejected) are used only for **evolution** — improving the model and rules after client feedback is received. See `commands/evolution-cycle.md`.

## No-ML Production Signal Table Mode

Some production runs cannot use the bundled ML model or any training step. In those runs, build an explicit signal table before row assessment and use it as the agent's working memory.

Read `references/production/no-ml-signal-table-mode.md` and `references/production/no-ml-row-signal-decision-criteria.md` before starting the run.

Required tables or artifacts:
- `signal_dictionary` — one row per allowed production signal, with signal name, family, source field or agent assessment source, description, and leakage status.
- `signal_matrix` — one row per respondent and one Boolean column per signal. The agent must mark each signal present or absent for every respondent before final judgment.
- `signal_profile` — one row per signal with present count, absent count, present rate, and decision weight. Near-universal signals must be marked `context_only`.
- `signal_lift` — optional when labels exist after the run. Use it only for evaluation and evolution, never during blind scoring.

No-ML production mode must not use:
- client `status`;
- raw client `markers`;
- `bad:` marker tokens;
- training labels;
- same-dataset fitted models;
- prior-loop prediction scores.

No-ML production mode may use:
- workbook-derived fields normalized into SQLite;
- Datamap question text and coded value labels;
- timing, matrix, duplicate, platform, language, brand funnel, quota, and survey-structure reconstructions;
- agent-authored semantic signal columns such as wrong topic, nonresponsive, thin on topic, brand-chain mismatch, and quota concern;
- cross-dataset signal definitions stored in this skill and its references.

In no-ML production mode, the review lane is the full dataset. The signal table is the case file and memory layer for row assessment; it is not a filter that removes rows from agent review. Every source respondent must receive an agent-authored assessment after the Boolean signal matrix is built. Label-tuned score bands from perturbation runs are diagnostic planning evidence only, not a production routing rule.

Treat fully automated no-ML discard as conservative. Automated gates may provide a proposed disposition, but the full dataset still goes through row-level agent review before final delivery.

Every no-ML judgment must include `signal_assessments` with one present/absent entry per production-safe signal. Each entry must include the criterion, row evidence, decision weight, decision effect, and confidence. Reject the chunk if a signal is missing or if the present value does not match `signal_matrix`.

## Dataset Normalization Store

For full production runs, benchmark runs, residual analysis, or any run where metrics must be reproducible, normalize the workbook into SQLite before scoring. Read `references/production/dataset-normalization-sqlite.md` and write the store under `{output_dir}/normalized/survey_quality.sqlite`.

Do this after semantic field-role mapping and before review-packet generation. The SQLite store must preserve raw workbook values, field roles, Datamap metadata, long-form answers, optional client labels, optional agent judgments, and saved SQL used for metrics or FP/FN analysis. Skip this only for quick smoke tests, and state that SQLite normalization was skipped.

## Run Control: Todo List And Workledger

After reading the task-specific command file and references, create both files before running scripts or reviewing rows:
- `{output_dir}/run_todolist.md` — checklist of required stages, gates, tests, artifacts, owners, and current status.
- `{output_dir}/workledger.md` — append-only log of actions, commands, inputs, outputs, metric snapshots, issues, decisions, and next steps.

Use these two files to drive the entire run. Update the todo list when a stage starts, completes, changes scope, or is blocked. Append to the workledger after every meaningful action: field mapping, SQLite normalization, packet generation, each chunk review, integration, metric comparison, FP/FN analysis, rule change, test, and performance check.

Do not mark the run complete until the todo list shows every required item complete and the workledger records the evidence: artifact paths, command results, validation outputs, metrics, remaining risks, and recommended next actions.

## Critical: Use the Holistic Agent Review Pipeline

**Do NOT run `run_quality_loop.py` or `survey_pipeline.py` alone.** These are the old scripted pipelines that produce only Keep/Light review with zero discards. They are data-staging tools, not the review pipeline.

**Use Devin CLI print mode for Stage 2 agent runs.** Do not use Codex CLI for row review. Run Devin one chunk at a time with GLM 5.2 using Devin model id `glm-5-2`, capture raw JSON, validate it, and log the command, output path, validation result, and any retry in `workledger.md`.

The production flow is the **holistic agent review** with three stages:

```
Stage 1: scripts/run_holistic_agent_review.py  → generates review packets + agent instructions
Stage 2: Devin CLI chunk review agents         → one chunk at a time unless the run log allows more
Stage 3: scripts/integrate_agent_judgments.py  → merges judgments into annotated Excel + dashboard
```

## Quick Start

```bash
# Install dependencies
pip3 install -r skills/cleaning-survey-quality/requirements.txt

# Stage 1: Generate review packets (parses Datamap, extracts features, ML triage, AI text detection,
#           survey-structure fields, brand funnel fields)
python3 skills/cleaning-survey-quality/scripts/run_holistic_agent_review.py /path/to/survey.xlsx \
  --output-dir /path/to/holistic_output --chunk-size 200
```

After Stage 1 completes, the output directory contains `review_chunk_00.json` through `review_chunk_XX.json` and `agent_review_instructions.md`.

**Stage 2 — run Devin chunk review agents.** For each chunk file, build a prompt file that includes the generated instructions, the chunk path, the output path, and the requirement to return raw JSON only. Then run:

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

Each Devin chunk agent must:
1. Read `agent_review_instructions.md`
2. Read `review_chunk_XX.json`
3. Apply the evidence-family framework to each respondent
4. Write `agent_judgments_chunk_XX.json` to the same output directory

Use the active run concurrency policy. For traceable improvement runs, concurrency is 1: process one chunk, log its start/completion/output path/JSON validation/exception/follow-up action, then move to the next chunk. Only use parallel chunk review when the run log explicitly allows it.

```bash
# Stage 3: Integrate judgments into annotated Excel + dashboard
python3 skills/cleaning-survey-quality/scripts/integrate_agent_judgments.py /path/to/survey.xlsx /path/to/holistic_output
```

For the full step-by-step workflow, see `commands/blind-run.md`.

## Reference routing

Read only the references needed for the current task:

| Need | Read |
|---|---|
| Running a blind production run | `commands/blind-run.md` |
| Improving the pipeline from client feedback | `commands/evolution-cycle.md` |
| Output format specs (Excel, dashboard, JSON) | `templates/output-format-spec.md` |
| Full four-layer progressive filtering specification | `references/production/progressive-chain-filtering.md` |
| Dataset normalization, SQLite store, SQL analysis standards | `references/production/dataset-normalization-sqlite.md` |
| No-ML production signal table and Boolean row-signal matrix | `references/production/no-ml-signal-table-mode.md` |
| No-ML per-row signal criteria and discard gates | `references/production/no-ml-row-signal-decision-criteria.md` |
| Blind authenticity review rules | `references/production/decipher-blind-authenticity-review.md` |
| Signal weighting, semantic similarity, convergence logic | `references/production/semantic-signal-expansion.md` |
| V7 calibrated disposition rules and benchmark lessons | `references/production/v7-calibration-and-guardrails.md` |
| Preventing rigid checklist behavior | `references/production/agent-authored-row-review.md` |
| Escalation routing for full dataset runs | `references/production/agentic-escalation-path.md` |
| Client, PM, survey, and quality term definitions | `references/production/client-terminology-glossary.md` |
| Verified generalizable ML signals | `references/production/generalizable-signals.md` |
| Per-dataset ML signal priorities | `references/production/per-dataset-ml-signals.md` |
| Calibrated discard exemplars (TP, FP, TN, FN) | `references/production/discard-exemplar-library.md` |
| TIER 1/2/3 signal system and combination lift tables | `references/production/combinatorial-discard-signal-profile.md` |
| Open-end evaluation and validation metrics | `references/production/evaluation-methodology.md` |
| Severity bands and escalation owners | `references/production/escalation-policy.md` |
| Discovery behavior changes | `references/production/autonomous-discovery.md` |
| Complete procedural workflow specification | `references/production/full-workflow-specification.md` |
| Adapting to a specific client or survey program | `references/production/project-context-template.md` |
| Client-process reconstruction gaps (ECHO FN/FP analysis) | `references/evolution/client-process-reconstruction-gaps.md` |
| ECHO residual signal mining (field-family lift, derived signals) | `references/evolution/echo-signal-mining/skill_improvement_recommendations.md` |
| Cross-dataset signal synthesis (10 workbooks, 12,384 respondents) | `references/evolution/cross-dataset-signal-synthesis.md` |
| Cross-corpus ML signal correlation (11 datasets, 13,388 respondents) | `evolution/ml-signal-correlation/signal_correlation_summary.md` |
| Multi-workbook signal mining artifacts (raw field, derived, markers) | `references/evolution/multiworkbook-signal-mining/multiworkbook_skill_recommendations.md` |
| Five-tier routing and label-aware contrast (evolution) | `references/evolution/authenticity-first-calibration.md` |
| Status-derived detection rules (evolution) | `references/evolution/tfg-status-derived-detection-methodology.md` |
| Internal comments and PM notes learning (evolution) | `references/evolution/internal-signal-learning.md` |
| Improvement cycle specification (evolution) | `references/evolution/dataset-cycle-loop.md` |
| ML building process and per-dataset results (evolution) | `references/evolution/ml-pipeline-report.md` |
| Agent architecture and reporting/evolution loop (evolution) | `references/evolution/research-grounding.md` |
| Historical rubric seed context (evolution) | `references/evolution/rubric-seed.md` |

## What Each Stage Does

### Stage -1: Run Control

Complete this stage after reading the command file and required references. It is complete only when `run_todolist.md` and `workledger.md` exist in the output directory and list the expected end-to-end flow, SQLite normalization gate, chunk-review concurrency policy, tests, metric checks, and deliverables.

### Stage 0: Dataset Normalization (`references/production/dataset-normalization-sqlite.md`)

For production, benchmark, and evolution runs, normalize the source workbook into a run-local SQLite store before generating review packets. Complete this stage only when:
- Field roles are mapped and saved to `normalized/field_roles.csv`.
- The SQLite database exists at `normalized/survey_quality.sqlite`.
- `schema_summary.md`, `import_report.json`, and `analysis_queries.sql` exist.
- Respondent counts, label counts when present, UUID uniqueness, open-end blank rates, timing ranges, and unmapped fields have been sanity checked.

### Stage 1: Data Staging + Review Packet Generation (`scripts/run_holistic_agent_review.py`)

Scripts parse the Datamap, map response fields to question text and value labels, compute population-level statistics, and build structured JSON review packets. Scripts do NOT make discard decisions.

Each packet contains:
- Full answer chain with question text and value labels for every field
- All open-end fields with their prompt text
- Per-grid straightlining analysis
- Timing (minutes + percentile)
- Supplier reject rate
- ML triage score (0-1 risk probability from pre-trained Gradient Boosting model)
- Survey defender signals (TERMFLAGS, qc, RD_Search, LangAssess, vlist, decLang, vdropout)
- Cross-respondent AI text similarity detection (`ai_text_suspicion` score)
- Duplicate text counts per OE field
- Answer entropy
- `defender_summary` — human-readable consolidation of all platform signals
- **`survey_structure`** — CLASSIFY, PROAGE, CONAGE, conditions (Ariens/HD/channel), list/source, dcua, FIRMREV
- **`brand_funnel`** — awareness, rating, consideration, recommendation, NPS, satisfaction, share allocation fields
- **`quota_reconstruction`** — quota cell membership (CLASSIFYQuota, RegionQuota, GenderQuota, ChannelQuota, BRANDS2RATEQuota, TotalQuota) + population counts per cell
- **`ml_signal_correlations`** — cross-corpus ML findings (family correlations, universal signals, global top features) from 13,388 respondents across 11 datasets
- **`key_answers`** — all coded single-choice fields with labels (dynamically discovered, not hardcoded)

The script also generates `agent_review_instructions.md` with the evidence-family framework rules (see below).

### Stage 2: Chunk Review Agents

Stage 2 row review is run through Devin CLI print mode with GLM 5.2 using Devin model id `glm-5-2`. Do not use Codex CLI for row review. Process review chunks sequentially unless the run log explicitly allows a higher concurrency.

For each `review_chunk_XX.json` file, create a prompt file and run:

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

Each chunk review agent must:
1. Read `agent_review_instructions.md` (the evidence-family framework)
2. Read `review_chunk_XX.json` (~200 respondent packets)
3. Apply the framework to each respondent
4. Write `agent_judgments_chunk_XX.json` to the same output directory

Use the active run concurrency policy. For traceable improvement runs, process chunks sequentially with concurrency = 1 and record the command, output file, validation result, retry count, and next action in `workledger.md`. Each chunk review agent produces a JSON array with:
- `respondent_id`
- `agent_score` (-1.0 to +1.0)
- `agent_judgment` (DISCARD / REVIEW / KEEP)
- `agent_justification` (2-4 sentences citing specific evidence)

### Stage 3: Integration (`scripts/integrate_agent_judgments.py`)

Merges all chunk judgments, re-runs feature extraction, and writes:
- **Annotated Excel** with 9 added columns (see `templates/output-format-spec.md`)
- **Dashboard HTML** with summary cards, score distribution, supplier analysis, and discard table
- **Summary JSON** with aggregate statistics

### Stage 4: End-To-End And Performance Verification

Test the full flow before reporting completion. At minimum:
- Verify all expected artifacts exist: todo list, workledger, normalized SQLite store when required, review chunks, chunk judgments, merged judgments, annotated Excel, dashboard, and summary JSON.
- Run the integration and comparison checks for any run with ground truth labels.
- Report accuracy, precision, recall, F1, specificity, balanced accuracy, soft recall, review volume, FP count, FN count, and runtime/performance notes.
- Compare performance against the current benchmark or prior run when one exists.
- Append the final command outputs, metric table, artifact paths, failures, and next steps to `workledger.md`.

## The Evidence-Family Framework (v7)

The agent instructions use an evidence-family convergence model with two stages and nine independent signal families. The v7 master rule (calibrated from V6 ground truth):

**A row is discard-like when ML risk is high (>= 0.6) AND converges with at least one independent risk family — OR when >= 4 evidence families fire — OR when platform fraud is certain (TERMFLAGS=1, qc=8/9). OE quality alone is NOT a discard signal (negative correlation with client discard).**

The V7 release improved every hard benchmark metric on ECHO against both V6 and the Captain semantic baseline. It raised precision to 0.664, recall to 0.524, F1 to 0.586, balanced accuracy to 0.690, and cut false positives from 270 to 147 versus V6. Preserve the pattern that produced that gain:

1. Use ML as a calibrated disposition gate, not as a replacement for reasoning.
2. Require 4 or more independent evidence families for discard when ML is not strong.
3. Do not fire `core_oe_quality` for `thin_on_topic`.
4. Treat Stage 2 quality failures and badopen severity as modifiers unless ML or family convergence supports them.
5. Protect accepted-row guardrails before expanding discard rules.

### Stage 1: Fraud Detection Families

1. **Platform risk** — TERMFLAGS=1, qc flag, RD_Search elevated, non-English
2. **Model risk** — ML triage score >= 0.7
3. **Source risk** — high supplier reject rate, elevated RD_Search threat
4. **Duplicate semantics** — text similarity to other respondents, paraphrase clusters

### Stage 2: PM Quality Assessment Families

5. **Core OE Quality** — answer-role test, substantive engagement, grounded detail, off-topic detection
6. **Survey Structure** — CLASSIFY (pro/consumer), PROAGE/CONAGE, channel conditions, list/source coherence
7. **Brand Funnel Consistency** — awareness → rating → consideration → NPS chain, brand name quality, share allocation
8. **Timing & Engagement** — speed, straightlining, matrix patterns
9. **Quota Reconstruction** — quota cell membership (CLASSIFYQuota, RegionQuota, GenderQuota, ChannelQuota, BRANDS2RATEQuota), over-filled cell detection, quota-aware quality bar

### Core Open-End Quality (the anchor)

The core OE field is the one asking for personal motivation, experience, or project description. Read the question text to identify it. Apply these tests:

- **Answer-Role Test**: Does the answer actually answer the question? "Water filtration systems" names the topic but fails a motivation question. "My water started smelling like chlorine after the city changed treatment" passes.
- **Substantive Engagement Test** (PM quality bar): Does the answer demonstrate substantive engagement with the survey's specific topic? "Mowing and blowing" is on-topic but thin — it names generic tasks without equipment, project narrative, or personal detail. For strict clients, this is a quality failure. Without calibration data, treat thin-but-on-topic as REVIEW, not KEEP.
- **Grounded First-Person Test**: First-person pronouns are NOT protective by themselves. The test is whether the content is grounded in lived experience (concrete events, household conditions, sensory issues, health concerns, named places, chain references).
- **Off-Topic Detection**: Is the described project in the right domain? (OPE survey → chainsaws, mowers, trimmers — NOT gardening, pest control, indoor projects). Off-topic core OE is a quality failure even if authentic.
- **Product-Copy Register**: Marketing-like language ("multi-stage filtration", "contaminant removal technologies") is suspicious, especially without lived context.
- **Synthetic Detail Detection**: Some details sound specific but are common fake clusters ("my skin", "my family", "chlorine"). Genuinely specific details are idiosyncratic (named brands, named conditions, unusual sensory details).

### Survey Structure (Stage 2 signal family)

Survey-structure fields carry 2x+ discrimination power but are NOT semantic content. They are classification, quota, and channel fields:

- **CLASSIFY=1 (pro)**: Pro respondents are held to a higher standard. A pro who answers like a consumer is a quality failure. Reject rate: 60.4% vs 30.5% for consumer.
- **PROAGE/CONAGE**: Pro-branch respondents should show professional experience. Consumer-branch should show consumer experience.
- **Channel conditions**: `conditionsAriens=1` → brand answers should include Ariens. `conditionsHD_or_OPE_dealers=1` → Home Depot / OPE dealer channel. Channel-brand mismatch is a quality concern. Reject rate: 59.2% for Ariens channel.
- **list/source**: Different suppliers have different reject rates (list 25: 45.3% vs list 139: 30.0%). Context, not proof.

### Brand Funnel Consistency (Stage 2 signal family)

Brand funnel fields are the strongest raw predictors of client discards (total signal score 2345.5 on ECHO, far exceeding any other family):

- **Awareness → Consideration → Recommendation chain**: Does the respondent claim awareness of brands they later cannot rate? Do they recommend brands they did not claim awareness of?
- **Brand name quality in OE fields**: Real OPE brands (Stihl, Husqvarna, Echo, Honda, Ryobi, Toro, Craftsman) vs garbled/wrong-universe brands ("Harmmer", "china", "Mercedes" for OPE).
- **Share allocation**: Equal share to all brands = potential straightlining. Many zero allocations = disengaged (47.2% reject rate). Fragmented share (8+ brands) = 52.0% reject rate.
- **NPS verbatim**: Should be brand-specific, not generic praise. "Effective work and power" = generic. "They put their name in VERY LARGE letters" = brand-specific.

### Platform Signal Override Logic

- **TERMFLAGS=1**: Strong discard (-0.7), NOT automatic. Override to REVIEW only when the core OE has unusually strong human evidence (specific named event/place/condition + chain-consistent + no AI markers).
- **qc=8 or qc=9**: Automatic discard (-1.0)
- **Non-English in US survey**: Automatic discard

### Outro-Only Suspicion Guardrail

AI text suspicion on the outro field ONLY is downweighted. Generic topic restatements ("water filtration systems") trigger high similarity because many respondents write the same thing — that's topical inevitability, not fraud. Only treat as a strong signal when the core OE field itself is flagged.

### Short Non-Answer Rule

Short answers (<25 chars) to a motivation/project question can be role failures, but only when they do not answer the prompt type. "It's essential", "Snow Blower", and "Home Depot" are not project descriptions. A short answer that names the right topic and has no other concern is review or keep, not discard. Upgrade only when ML is at least 0.6 or when multiple independent families converge.

### Typo Laundering Guard

Typos are NOT protective unless the surrounding answer is grounded and coherent. A typo inside generic content is neutral. "I was concerned about the filteration" with no other detail = not protective.

## Progressive Filtering Order

The review follows a strict ordering. Each layer filters the population progressively.

1. **Datamap mapping** — Parse the Datamap, extract prompt text, value labels, field groups, response options. Build the Question Contract. Map field roles before scoring.
2. **Per-field chain validity** — For each respondent, judge whether each answer is on-topic and credible for that specific prompt. Classify as responsive, partially responsive, nonresponsive, wrong semantic dimension, off-topic, or invalid.
3. **Observational signals** — Timing, supplier/source cohort, technical (IP, device), platform helpers (TERMFLAGS, RD_Search). These refine the chain layer, they do not replace it.
4. **Cross-population signals** — Duplicate open text, response vector clustering, timing clusters, matrix pattern clustering, shared rare phrases. These are the strongest convergence evidence.

See `references/production/progressive-chain-filtering.md` for the full specification.

## What Scripts Do vs What Agents Do

**Scripts DO:**
- Parse the Datamap into question text and value labels
- Normalize workbook data into SQLite for production, benchmark, and evolution runs
- Look up coded values to get their label meanings
- Compute timing distributions and percentiles
- Detect exact duplicate text across respondents
- Detect duplicate IP addresses
- Compute supplier cohort distributions
- Run the ML triage model (pre-trained, runs on unannotated data)
- Detect cross-respondent AI text similarity
- Extract survey-structure fields (CLASSIFY, PROAGE, conditions, list, FIRMREV)
- Extract brand funnel fields (awareness, rating, consideration, NPS, share)
- Assemble structured JSON packets for the agents

**Scripts do NOT:**
- Classify open-end text as "meta_praise" or "templated"
- Detect contradictions between fields
- Make final discard decisions
- Generate proposition templates
- Apply regex rules to open-end text for semantic classification

## ML Triage Model

A Gradient Boosting classifier is bundled as `models/survey_quality_model.pkl`. It was trained on 13,388 historical annotated respondents across 11 datasets. At runtime, it runs on **unannotated** data and produces a risk probability (0-1) for each respondent. No annotations are needed at runtime.

The ML score is a **triage input** to the evidence-family framework — not a standalone classifier. It flags high-risk respondents for closer agent review. Key signals (by importance): LangAssessReadLevel, supplier_x_signals, supplier_reject_rate, answer_entropy, matrix straightlining, oe_total_chars.

See `references/production/per-dataset-ml-signals.md` for per-dataset signal priorities and `references/production/generalizable-signals.md` for verified generalizable signals.

## Output Artifacts

After Stage 3, the output directory contains:

1. **`{dataset}_annotated.xlsx`** — Original Excel + 9 annotation columns
2. **`{dataset}_dashboard.html`** — Self-contained HTML dashboard
3. **`summary.json`** — Aggregate statistics
4. **`agent_judgments.json`** — Merged agent judgments (all chunks)
5. **`review_chunk_XX.json`** — Review packets (one per chunk)
6. **`agent_judgments_chunk_XX.json`** — Per-chunk judgments
7. **`agent_review_instructions.md`** — The evidence-family framework instructions

See `templates/output-format-spec.md` for the exact format of each artifact.

## Evolution (When Client Feedback Is Available)

After the PM reviews the output and the client provides accept/reject decisions, the annotated workbook can be used to improve the pipeline. This is a **separate activity** from the normal blind run. See `commands/evolution-cycle.md` for the full workflow.

### Known Performance Gaps (v4 to v5 to v5.1 to v6 to v7)

**v6 ECHO results (status=5 only):**
- TP=226, FP=293, FN=327, TN=720 | Precision=0.435, Recall=0.409, F1=0.422
- Soft recall=0.976 (REVIEW catches most client discards)
- The REVIEW bucket is the primary bottleneck — 969 in REVIEW, 314 are actual discards
- ML score is the strongest discriminator within REVIEW (mean 0.493 for discards vs 0.331 for keeps)
- Substantive OE has 36.1% client discard rate — NOT a protective signal
- core_oe_quality fires in 98% of both TPs and FPs — zero discrimination
- platform_risk fires equally in discards and keeps — over-firing at RD_Search >= 20
- model_risk has the highest discriminative gap (+0.34) — best calibrated family
- Converging family count >= 4 is the key threshold (FP:TP ratio flips favorable)

**v7 calibration addresses these gaps by:**
1. ML >= 0.8 → direct DISCARD; ML >= 0.6 → DISCARD with any convergence; ML >= 0.5 in REVIEW → upgrade only when a real independent family also fires
2. Require >= 4 converging families for DISCARD (was 2-3, caused 2:1 FP:TP ratio)
3. Stop firing core_oe_quality for thin_on_topic (was firing in 98% of both TPs and FPs)
4. Tighten platform_risk: RD_Search >= 25 fires (was >= 20, which fired in 58% of keeps)
5. Lower timing_engagement threshold: add below_median as weak signal (was bottom_25 only, missed 39.9% of FNs)
6. Substantive OE is NOT protective — score as REVIEW, not KEEP (36.1% client discard rate)
7. Auto-discard for model_risk + brand_funnel/survey_structure/quota_reconstruction (0.73-0.96 precision)
8. Stage 2 "fail" → default REVIEW (was DISCARD, 84.5% agent discard vs 44.3% client discard)
9. Badopen "high" severity → modifier, not driver (was 85.8% agent discard vs 42.3% client discard)
10. Scoring weights: client_reject_probability 0.5, authenticity_risk 0.3, quality_discard_risk 0.2 (was 0.4/0.4/0.2)

**v7 ECHO results after calibration:**
- TP=290, FP=147, FN=263, TN=866
- Precision=0.664, Recall=0.524, F1=0.586, Balanced Accuracy=0.690
- False positives dropped 46% versus V6 while true positives rose from 222 to 290
- V7 surpassed the Captain semantic baseline on precision, recall, F1, and balanced accuracy
- Soft recall dropped from 0.976 to 0.875 because the REVIEW bucket became smaller; this is an acceptable tradeoff only when the next pass continues to monitor missed discards

**The next improvement target:**
- Study the 263 false negatives for thin-on-topic rows with low ML and no convergence that the client still rejected.
- Study the 147 false positives to protect accepted rows where the quality bar is stricter than the client's actual bar.
- Study the 247 Stage 2 fail rows that the client accepted before turning any quality-stage finding into a stronger runtime rule.

**ECHO-specific findings (from residual signal mining):**
- **Brand funnel** is the strongest field family (signal score 2345.5), far exceeding semantic content fields
- **Equipment ownership/use** is second (896.3) — q11 other-specify fields carry strong signal
- **CLASSIFY=1 (pro)** rejects at 60.4% vs 30.5% for consumer — pro-branch respondents are held to a higher standard
- **conditionsAriens=1** rejects at 59.2% — channel-condition fields carry 2x+ lift
- **Brand share fragmentation** (8+ brands with nonzero share) rejects at 52.0%
- **Fast completion** (<5 min) rejects at 100% (15/15)
- **TERMFLAGS=1** rejects at 66.7% but covers only 15/553 discards (2.7%)
- Standard fraud signals (duplicate OE, matrix straightline) have lift 1.00 — zero discrimination on ECHO
- `very_short_required_open_end` is **protective** (lift 0.58) — short answers are LESS likely to be discarded

**Cross-dataset findings (10 workbooks, 12,384 respondents):**
- **Open-end text is the weakest family** (signal score 16.1 across all datasets) — confirms v4's OE-centric approach was misaligned
- **`badopen` is a universal discard marker** — 100% discard share across ALL 10 datasets, 3092 total mentions
- **`bad:qualified` is similarly universal** — 100% discard share, 3068 mentions
- **Demographic profile** is the strongest cross-dataset family (5703.8) — strongest in TFG-Contractor-Index
- **Brand funnel/ad** is second cross-dataset (4058.5) — strongest in ECHO
- **Quota markers are dataset-specific** — ECHO has BRANDS2RATEQuota/ChannelQuota, Masterlock has ProductBalancingQuota, TFG-CI has TradeQuota
- **Fast completion (<5 min) generalizes** — strong lift in SBD (+49.4%), ADDO (+29.8%), ECHO (+64.7%)
- **Missing supplier** is a strong signal in TFG-CI-Q2 (75.5% discard rate, +39.5% lift)
- **Discard rates vary widely** — 6.2% (THD-CX) to 44.5% (SBD); per-dataset calibration is essential

### Evolution Process

1. **Obtain annotated data** — Get the client-annotated workbook with status=3/5 labels
2. **Run residual signal mining** — Extract field-family lift, derived signals, error gap examples (see `references/evolution/echo-signal-mining/` for ECHO example)
3. **Build field-specific open-end contracts** — Per-field valid/invalid examples and accepted-row guardrails for qc5, q11 other-specifies, q17 brands, q19 other, q29 ad recall, q30-q32 switching/loyalty
4. **Build brand-funnel relation graphs** — Awareness/top/possible/rated/brand-share/ad/NPS as a connected system
5. **Build quota/classification contracts** — CLASSIFY, CONAGE, PROAGE, REGION, condition flags, list/source, brand-to-rate fields
6. **Create residual review packets** for every FN/FP — Include raw branch/condition/brand-funnel values, marker family, our rationale, and candidate missed signal. Promote only rules that survive accepted-row counterexamples.
7. **Split authenticity risk from client discard reconstruction** — Rows can be human-looking but client-discardable because of quota, classification, or bad-open standards.

See `references/evolution/client-process-reconstruction-gaps.md` for the full gap analysis and `references/evolution/echo-signal-mining/` for the ECHO signal mining artifacts.

## Package Requirements

```bash
pip3 install -r skills/cleaning-survey-quality/requirements.txt
```

Required: `openpyxl>=3.1.0`, `scikit-learn>=1.3.0`, `pandas>=2.0.0`, `numpy>=1.24.0`, `scipy>=1.10.0`, `xgboost>=2.0.0`, `lightgbm>=4.0.0`

## Directory Structure

```
cleaning-survey-quality/
├── SKILL.md                          (this file — routing table + core invariants)
├── requirements.txt
├── commands/                         (named workflows)
│   ├── blind-run.md                  (normal production run)
│   └── evolution-cycle.md            (improve from client feedback)
├── references/
│   ├── production/                   (read for blind runs)
│   │   ├── progressive-chain-filtering.md
│   │   ├── decipher-blind-authenticity-review.md
│   │   ├── semantic-signal-expansion.md
│   │   ├── v7-calibration-and-guardrails.md
│   │   ├── dataset-normalization-sqlite.md
│   │   ├── agent-authored-row-review.md
│   │   ├── agentic-escalation-path.md
│   │   ├── client-terminology-glossary.md
│   │   ├── generalizable-signals.md
│   │   ├── per-dataset-ml-signals.md
│   │   ├── per_dataset_ml_signals.json
│   │   ├── discard-exemplar-library.md
│   │   ├── combinatorial-discard-signal-profile.md
│   │   ├── evaluation-methodology.md
│   │   ├── escalation-policy.md
│   │   ├── autonomous-discovery.md
│   │   ├── full-workflow-specification.md
│   │   └── project-context-template.md
│   └── evolution/                    (read only when client feedback available)
│       ├── client-process-reconstruction-gaps.md  (ECHO FN/FP analysis + 5 process gaps)
│       ├── cross-dataset-signal-synthesis.md      (10-workbook cross-dataset synthesis)
│       ├── echo-signal-mining/                    (ECHO residual signal mining artifacts)
│       │   ├── skill_improvement_recommendations.md
│       │   ├── raw_field_signal_inventory.csv
│       │   ├── derived_signal_candidates.csv
│       │   ├── field_family_signal_summary.csv
│       │   ├── marker_family_summary.csv
│       │   └── error_gap_examples.csv
│       ├── multiworkbook-signal-mining/             (10-workbook signal mining artifacts)
│       │   ├── multiworkbook_skill_recommendations.md
│       │   ├── dataset_inventory.csv
│       │   ├── cross_dataset_family_summary.csv
│       │   ├── cross_dataset_raw_field_signals.csv
│       │   ├── cross_dataset_derived_signals.csv
│       │   ├── cross_dataset_marker_summary.csv
│       │   └── open_end_signal_examples.csv
│       ├── authenticity-first-calibration.md
│       ├── tfg-status-derived-detection-methodology.md
│       ├── internal-signal-learning.md
│       ├── dataset-cycle-loop.md
│       ├── ml-pipeline-report.md
│       ├── research-grounding.md
│       └── rubric-seed.md
├── templates/
│   └── output-format-spec.md         (output artifact format specifications)
├── scripts/                          (production scripts — only 3 files)
│   ├── run_holistic_agent_review.py  (Stage 1: generate review packets)
│   ├── integrate_agent_judgments.py  (Stage 3: merge judgments into Excel + dashboard)
│   ├── survey_pipeline.py            (shared utilities: Datamap parsing, features, ML triage)
│   └── training/                     (experimentation scripts, not for production)
│       ├── survey_quality_ml.py      (ML model training/retraining)
│       ├── train_v*.py               (30 experiment scripts)
│       ├── eval_harness.py
│       ├── experiment_loop.py
│       ├── agent_v2_features.py
│       └── ...
└── models/
    ├── survey_quality_model.pkl      (pre-trained ML model)
    └── results/                      (training results and evaluation data)
```
