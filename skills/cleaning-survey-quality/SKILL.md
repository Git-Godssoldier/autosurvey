---
name: cleaning-survey-quality
description: Cleans and scores Decipher-style survey quality workbooks for market research datasets. Use when reviewing survey completes, fraud, inattentive respondents, open-end AI suspicion, straightlining, inconsistent brand answers, short completes, duplicate IPs, respondent flags, or survey quality files. The primary flow is a two-stage holistic agent review (fraud detection + PM quality assessment) that produces DISCARD/REVIEW/KEEP judgments with evidence-family convergence scoring across 8 independent signal families.
---

# Cleaning Survey Quality

Run a reproducible survey quality pass on unannotated Decipher-style survey exports. The output is a per-respondent DISCARD/REVIEW/KEEP judgment with a -1 to +1 score and a natural-language justification citing specific evidence.

## Two-Stage Review (v5)

Every respondent passes through two stages:

**Stage 1 — Fraud Detection**: Is this respondent authentic? (bots, AI, platform flags, gibberish, non-English, duplicate chains, TERMFLAGS)

**Stage 2 — PM Quality Assessment**: Does this respondent meet the quality bar for this survey? (substantive engagement, brand funnel consistency, classification coherence, on-topic depth, survey-structure fit)

A respondent can pass Stage 1 (not fraudulent) but fail Stage 2 (low quality). Both result in DISCARD or REVIEW. This separation is critical because client discard processes are primarily quality-driven, not fraud-driven. On ECHO, fraud signals (TERMFLAGS, AI text) cover only 2.2% of discards; the remaining 98% are `badopen` — PM quality judgments.

## The Normal Input Is an Unannotated Workbook

In most runs, the only input is a raw Decipher export (`.xlsx`) with respondent data and a Datamap sheet. There are no `status` labels, no client annotations, no accepted/rejected examples, and no helper columns. The pipeline must work without any of these.

The ML triage model is **pre-trained and bundled** (`models/survey_quality_model.pkl`). It was trained on historical annotated data, but it runs on unannotated data at runtime. You do not need annotations to run the pipeline.

Annotated workbooks (`status = 3` accepted, `status = 5` rejected) are used only for **evolution** — improving the model and rules after client feedback is received. See `commands/evolution-cycle.md`.

## Critical: Use the Holistic Agent Review Pipeline

**Do NOT run `run_quality_loop.py` or `survey_pipeline.py` alone.** These are the old scripted pipelines that produce only Keep/Light review with zero discards. They are data-staging tools, not the review pipeline.

**Do NOT use external CLI tools (Codex, etc.) for Stage 2.** Stage 2 is performed by the agent itself spawning subagents using its own subagent infrastructure. No external tool installation is required.

The production flow is the **holistic agent review** with three stages:

```
Stage 1: scripts/run_holistic_agent_review.py  → generates review packets + agent instructions
Stage 2: YOU spawn subagents                   → one subagent per chunk reads packets, writes judgments
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

**Stage 2 — YOU spawn subagents.** For each chunk file, spawn a subagent (using your own subagent/tool infrastructure) that:
1. Reads `agent_review_instructions.md`
2. Reads `review_chunk_XX.json`
3. Applies the evidence-family framework to each respondent
4. Writes `agent_judgments_chunk_XX.json` to the same output directory

Spawn all chunk subagents in parallel. Wait for all to complete before proceeding to Stage 3.

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
| Blind authenticity review rules | `references/production/decipher-blind-authenticity-review.md` |
| Signal weighting, semantic similarity, convergence logic | `references/production/semantic-signal-expansion.md` |
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
| Multi-workbook signal mining artifacts (raw field, derived, markers) | `references/evolution/multiworkbook-signal-mining/multiworkbook_skill_recommendations.md` |
| Five-tier routing and label-aware contrast (evolution) | `references/evolution/authenticity-first-calibration.md` |
| Status-derived detection rules (evolution) | `references/evolution/tfg-status-derived-detection-methodology.md` |
| Internal comments and PM notes learning (evolution) | `references/evolution/internal-signal-learning.md` |
| Improvement cycle specification (evolution) | `references/evolution/dataset-cycle-loop.md` |
| ML building process and per-dataset results (evolution) | `references/evolution/ml-pipeline-report.md` |
| Agent architecture and reporting/evolution loop (evolution) | `references/evolution/research-grounding.md` |
| Historical rubric seed context (evolution) | `references/evolution/rubric-seed.md` |

## What Each Stage Does

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
- **`key_answers`** — all coded single-choice fields with labels (dynamically discovered, not hardcoded)

The script also generates `agent_review_instructions.md` with the evidence-family framework rules (see below).

### Stage 2: Subagent Review (YOU spawn the subagents)

**The agent running this skill performs Stage 2 itself** by spawning subagents using its own subagent infrastructure. No external CLI tool (Codex, etc.) is needed.

For each `review_chunk_XX.json` file, spawn a subagent that:
1. Reads `agent_review_instructions.md` (the evidence-family framework)
2. Reads `review_chunk_XX.json` (~200 respondent packets)
3. Applies the framework to each respondent
4. Writes `agent_judgments_chunk_XX.json` to the same output directory

Spawn all chunk subagents in parallel. Each subagent produces a JSON array with:
- `respondent_id`
- `agent_score` (-1.0 to +1.0)
- `agent_judgment` (DISCARD / REVIEW / KEEP)
- `agent_justification` (2-4 sentences citing specific evidence)

### Stage 3: Integration (`scripts/integrate_agent_judgments.py`)

Merges all chunk judgments, re-runs feature extraction, and writes:
- **Annotated Excel** with 9 added columns (see `templates/output-format-spec.md`)
- **Dashboard HTML** with summary cards, score distribution, supplier analysis, and discard table
- **Summary JSON** with aggregate statistics

## The Evidence-Family Framework (v5)

The agent instructions use an evidence-family convergence model with two stages and eight independent signal families. The master rule:

**A row is discard-like when the core open end fails its question role, lacks grounded chain evidence, and converges with at least one independent risk family — OR when the respondent fails the PM quality bar (thin engagement, brand funnel incoherence, classification mismatch, off-topic content).**

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

Short answers (<25 chars) to a motivation/project question are almost always role failures. "It's essential", "Snow Blower", "Home Depot" are NOT project descriptions. When paired with ANY risk family signal, this becomes a discard.

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

### Known Performance Gaps (v4 → v5)

The v4 holistic review caught fraud well (precision ~0.60) but missed the PM's quality bar (recall ~0.31 on ECHO). The v5 framework addresses this by adding survey-structure and brand-funnel evidence families. Key findings from ECHO residual signal mining and cross-dataset synthesis (10 workbooks, 12,384 respondents):

**ECHO-specific findings:**
- **Brand funnel** is the strongest field family (signal score 2345.5), far exceeding semantic content fields
- **Equipment ownership/use** is second (896.3) — q11 other-specify fields carry strong signal
- **CLASSIFY=1 (pro)** rejects at 60.4% vs 30.5% for consumer — pro-branch respondents are held to a higher standard
- **conditionsAriens=1** rejects at 59.2% — channel-condition fields carry 2x+ lift
- **Brand share fragmentation** (8+ brands with nonzero share) rejects at 52.0%
- **Fast completion** (<5 min) rejects at 100% (15/15)
- **TERMFLAGS=1** rejects at 66.7% but covers only 15/553 discards (2.7%)
- Standard fraud signals (duplicate OE, matrix straightline) have lift 1.00 — zero discrimination on ECHO
- `very_short_required_open_end` is **protective** (lift 0.58) — short answers are LESS likely to be discarded

**Cross-dataset findings (all 10 workbooks):**
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
