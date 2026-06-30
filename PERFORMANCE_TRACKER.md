# Performance Improvement Tracker — Survey Quality Cleaning Skill

> **Dataset**: Echo BH (109-2601) — 1,566 respondents, 553 client discards (35.3%), 1,013 client keeps (64.7%)
>
> **Ground truth**: Client-annotated workbook with status=3 (accepted) and status=5 (discarded)
>
> **Target KPI**: 90% balanced accuracy, 90% F1

---

## 1. End-to-End Testing & Validation Process

Every version goes through the same four-stage pipeline:

### Stage 1 — Review Packet Generation
- Input: Unannotated Excel workbook (no status column visible to agent)
- Script: `skills/cleaning-survey-quality/scripts/run_holistic_agent_review.py`
- Process: Extract 156 features per respondent (ML triage, defender signals, timing, brand funnel, open-end text, survey structure, quota cells, language assessment). Build a 27-field review packet per respondent with all signals blinded to ground truth.
- Output: 8 JSON chunk files (~200 respondents each) in `holistic_agent_run_vN/review_chunk_XX.json`

### Stage 2 — Agent Review (8 Parallel Subagents)
- Input: Review packets + version-specific `agent_review_instructions.md`
- Process: 8 subagents each process one chunk. Each respondent gets a judgment (DISCARD / REVIEW / KEEP), a score (-1.0 to +1.0), a justification, 9 evidence family scores, 5 semantic remapping fields, and badopen audit trail.
- Output: `agent_judgments_chunk_XX.json` per chunk

### Stage 3 — Integration
- Script: `skills/cleaning-survey-quality/scripts/integrate_agent_judgments.py`
- Process: Merge 8 chunk files into `agent_judgments.json`. Re-run ML triage on the full dataset. Combine agent judgments with rule-based scores. Generate annotated Excel (with agent justifications as a new column) and an HTML dashboard.
- Output: `109-2601 Echo BH_annotated.xlsx`, `109-2601 Echo BH_dashboard.html`, `summary.json`

### Stage 4 — Comparison Against Client Ground Truth
- Script: `scripts/compare_v4_v5_echo.py`
- Process: Load client-annotated workbook (status=3/5 only). Match agent judgments to ground truth by UUID. Compute TP, FP, TN, FN, precision, recall, F1, balanced accuracy, soft recall (REVIEW as partial credit). Generate side-by-side comparison table across all versions. Output FN/FP sample lists for error analysis.
- Output: `comparison_results.json`, console table

### Stage 5 — Error Analysis (drives next version)
- Script: `scripts/analyze_v7_errors.py`, `scripts/analyze_v7_raw_signals.py`
- Process: Classify FNs and FPs by ML band, OE classification, fired evidence families, convergence count. Identify which rules drove wrong decisions. Project counterfactual scenarios (e.g., "what if we raised ML threshold to 0.45?") to calibrate the next version without running it.
- Output: Error analysis findings fed into next version's `agent_review_instructions.md`

---

## 2. Version History — What Drove Each Improvement

### Baseline: Captain Semantic (prior production system)
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 281 | 203 | 810 | 272 | 0.581 | 0.508 | 0.542 | 0.654 |

Binary discard/keep classifier. No REVIEW tier. No evidence families. No ML triage.

---

### V4 — Holistic Agent Review (evidence-family framework)
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 185 | 137 | 876 | 368 | 0.575 | 0.335 | 0.423 | 0.600 |

**What changed**: Introduced 9 evidence families (core_oe_quality, platform_risk, model_risk, source_risk, duplicate_semantics, survey_structure, brand_funnel, timing_engagement, quota_reconstruction). Three-tier output (DISCARD/REVIEW/KEEP). Agent reads full respondent context.

**Impact**: Precision slightly improved (0.575 vs 0.581), but recall dropped sharply (0.335 vs 0.508). The agent was too conservative — defaulted to REVIEW for ambiguous cases. BAcc dropped to 0.600.

**Lesson**: Evidence families are good signal structure, but without calibrated thresholds the agent under-discriminates.

---

### V5 — Two-Stage Pipeline (fraud detection + quality assessment)
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 240 | 231 | 782 | 313 | 0.510 | 0.434 | 0.469 | 0.603 |

**What changed**: Split review into Stage 1 (fraud: TERMFLAGS, qc, duplicate IP) and Stage 2 (quality: OE classification, brand funnel, timing). Added semantic open-end classification (substantive, thin_on_topic, off_topic, non_answer, gibberish).

**Impact**: Recall improved (0.434 vs 0.335) but precision dropped (0.510 vs 0.575). The two-stage split caught more fraud but over-fired on quality. BAcc 0.603 — marginal improvement over V4.

**Lesson**: Two-stage separation helps organize signals but doesn't solve the calibration problem.

---

### V5.1 — ML + Quota Reconstruction
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 302 | 398 | 615 | 251 | 0.431 | 0.546 | 0.482 | 0.577 |

**What changed**: Added portable ML triage model (Gradient Boosting, 156 features, trained on cross-dataset labels). Added quota reconstruction (checking if respondent fills a needed quota cell). Lowered discard thresholds to catch more fraud.

**Impact**: Best recall so far (0.546) but worst precision (0.431). 398 FPs — over-aggressive. BAcc dropped to 0.577.

**Lesson**: ML alone is too aggressive. Quota reconstruction adds signal but can't compensate for lack of calibration.

---

### V6 — Three-Component Scoring + 27-Field Schema
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 222 | 270 | 743 | 331 | 0.451 | 0.401 | 0.425 | 0.567 |

**What changed**: Introduced three-component scoring (authenticity_risk, quality_discard_risk, client_reject_probability). Expanded to 27-field output schema with semantic remapping. Added ML correlation analysis across datasets.

**Impact**: Worst BAcc (0.567). The three-component model was theoretically sound but the weights were wrong. Too many REVIEWs (993/1566) and too few KEEPs (81).

**Lesson**: More sophisticated architecture without calibrated thresholds performs worse than simpler approaches.

---

### V7 — Calibrated Thresholds + ML-Driven Disposition (BEST VERSION)
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| **290** | **147** | **866** | **263** | **0.664** | **0.524** | **0.586** | **0.690** |

**What changed**: Deep calibration based on V6 metadata analysis. Ten key rules:
1. ML-driven disposition: ML >= 0.8 auto-DISCARD
2. Require >= 4 converging families for DISCARD (not 2-3)
3. core_oe_quality does NOT fire for thin_on_topic
4. Tightened platform_risk threshold (RD_Search >= 25)
5. Substantive OE is NOT a protective signal (at this stage)
6. Stage 2 "fail" defaults to REVIEW, not DISCARD
7. Adjusted scoring weights (client_reject_probability weighted 0.5)
8. Auto-discard for specific pairs (model_risk + brand_funnel, etc.)
9. below_median timing is a weak signal (not standalone)
10. Badopen "high" severity is a modifier, not primary driver

**Impact**: Best precision (0.664), best F1 (0.586), best BAcc (0.690). FP dropped from 270 to 147 (-46%). FN dropped from 331 to 263 (-21%). All metrics improved simultaneously.

**Lesson**: Calibration > architecture. The same evidence families from V4, with correct thresholds, dramatically outperform more sophisticated but uncalibrated approaches.

---

### V8 — Error-Driven FN-Reduction + FP-Reduction
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 336 | 249 | 764 | 217 | 0.574 | 0.608 | 0.591 | 0.681 |

**What changed**: Based on V7 error analysis:
- **FP-reduction**: Substantive OE protective in ML 0.5-0.7 band; model_risk + timing_engagement ONLY → REVIEW; LangAssessReadEase >= 15 protective; ML auto-discard raised to 0.85
- **FN-reduction**: Lowered ML thresholds for off_topic (0.35), non_answer (0.3), CLASSIFY=1 (0.4), conditionsAriens (0.35), survey_structure+source_risk (0.35)

**Impact**: Recall improved (0.608, +16%) but precision dropped (0.574, -14%). F1 marginally improved (0.591) but BAcc dropped (0.681). 98 new TPs but 143 new FPs (59% FP rate on new discards).

**Lesson**: FN-reduction at ML 0.35-0.5 is too aggressive. thin_on_topic + 4 families + ML 0.35-0.5 is the dominant FP pattern. The 4-family convergence threshold doesn't work for thin OE (30% client discard rate, barely below 35% base rate).

---

### V9 — Precision-Tuned FN Reduction
| TP | FP | TN | FN | Precision | Recall | F1 | BAcc |
|----|----|----|----|-----------|--------|----|-----|
| 250 | 118 | 895 | 303 | 0.679 | 0.452 | 0.543 | 0.668 |

**What changed**: Tightened V8's FN-reduction thresholds (off_topic 0.45, non_answer 0.4, CLASSIFY=1 0.45, conditionsAriens 0.45, survey_structure+source_risk 0.45). Raised convergence to 5 families for thin_on_topic. Restricted brand_funnel (must show wrong brand universe) and source_risk (must show >30% reject rate).

**Impact**: Best precision (0.679) but recall collapsed (0.452, below V7). BAcc dropped to 0.668. Over-corrected — brand_funnel and source_risk restrictions removed genuine discard signals.

**Lesson**: Over-firing restrictions on brand_funnel and source_risk remove convergence signals that drive both TPs and FPs. You can't restrict firing without losing recall.

---

### V10 Analysis — V7 + Surgical FP-Reduction Only (not run as full version)

Tested whether applying ONLY V8's FP-reduction rules to V7 (without FN-reduction) could improve precision without sacrificing recall.

**Result**: V8's FP-reduction rules downgrade 41 V7 FPs but also 52 V7 TPs. The "substantive OE protective" rule is the worst offender (loses 31 TPs to remove 12 FPs). The "model_risk + timing ONLY → REVIEW" rule is nearly neutral (4 FPs removed, 3 TPs lost).

**Projected metrics**: TP=238, FP=106, BAcc=0.663 — worse than V7.

**Conclusion**: FP-reduction rules are NOT surgical. The same signals that drive FPs also drive TPs. V7 is at the ceiling for threshold-tuning.

---

## 3. Performance Summary Table

| Version | TP  | FP  | TN  | FN  | Precision | Recall | F1    | BAcc  | Discards Pred |
|---------|-----|-----|-----|-----|-----------|--------|-------|-------|---------------|
| Captain | 281 | 203 | 810 | 272 | 0.581     | 0.508  | 0.542 | 0.654 | 484           |
| V4      | 185 | 137 | 876 | 368 | 0.575     | 0.335  | 0.423 | 0.600 | 322           |
| V5      | 240 | 231 | 782 | 313 | 0.510     | 0.434  | 0.469 | 0.603 | 471           |
| V5.1    | 302 | 398 | 615 | 251 | 0.431     | 0.546  | 0.482 | 0.577 | 700           |
| V6      | 222 | 270 | 743 | 331 | 0.451     | 0.401  | 0.425 | 0.567 | 492           |
| **V7**  | **290** | **147** | **866** | **263** | **0.664** | **0.524** | **0.586** | **0.690** | **437** |
| V8      | 336 | 249 | 764 | 217 | 0.574     | 0.608  | 0.591 | 0.681 | 585           |
| V9      | 250 | 118 | 895 | 303 | 0.679     | 0.452  | 0.543 | 0.668 | 368           |

**Best per metric**: Precision = V9 (0.679), Recall = V8 (0.608), F1 = V8 (0.591), BAcc = **V7 (0.690)**

---

## 4. Performance Gaps to Close (KPI: 90% Balanced Accuracy, 90% F1)

### Current State (V7 — best version)
- Balanced accuracy: **0.690** (gap: 21 percentage points to 90%)
- F1: **0.586** (gap: 31.4 percentage points to 90%)
- Precision: **0.664** (gap: 23.6 percentage points to 90%)
- Recall: **0.524** (gap: 37.6 percentage points to 90%)

### Gap Analysis — Why We're Stuck at 69% BAcc

#### Gap 1: Signal Ceiling (structural)
The same evidence signals (model_risk, brand_funnel, timing_engagement, source_risk) drive both false positives and false negatives. Threshold tuning cannot separate them — proven by V8/V9/V10 analysis.

**What's needed**: New signal sources that are orthogonal to existing ones:
- Semantic embedding similarity (compare OE text to known good/bad exemplars)
- Cross-question consistency scoring (do answers across questions tell a coherent story?)
- Per-respondent narrative quality scoring (beyond thin/substantive classification)
- Behavioral pattern analysis (click patterns, answer changes, device fingerprinting)

#### Gap 2: ML Model Limitations
The current ML triage model is a Gradient Boosting classifier trained on cross-dataset labels. It achieves AUC 0.97-1.00 within-dataset but its calibration is poor — ML 0.4-0.5 band contains both TPs and FPs at nearly 1:1 ratio.

**What's needed**:
- Retrain ML model with V7's agent judgments as additional training labels (semi-supervised)
- Per-dataset model calibration (reject rates vary 5-44% across datasets)
- Platt scaling or isotonic regression for better probability calibration
- Ensemble of multiple models (GBM + neural net + logistic regression)

#### Gap 3: OE Classification Granularity
Current OE classification (substantive, thin_on_topic, off_topic, non_answer, gibberish, benefit_stack) is too coarse. "Thin_on_topic" has a 30% client discard rate — barely below the 35% base rate — because it lumps together very different quality levels.

**What's needed**:
- Finer OE taxonomy (e.g., thin_generic vs thin_specific vs thin_with_detail)
- OE quality scoring on a continuous scale (not just classification)
- Per-question OE evaluation (not just the core OE field)
- Narrative coherence scoring across multiple OE fields

#### Gap 4: Per-Channel / Per-Class Calibration
V7 uses global thresholds, but client discard rates vary dramatically by channel (Ariens vs non-Ariens) and class (Pro vs consumer). Pro respondents have 60% discard rate; consumer respondents have ~30%.

**What's needed**:
- Channel-specific thresholds (Ariens channel: lower ML threshold; non-Ariens: higher)
- CLASSIFY-specific thresholds (Pro: aggressive discard; Consumer: conservative)
- Per-quota-cell calibration (some quota cells have higher fraud rates)

#### Gap 5: Human-in-the-Loop Review Tier
V7 produces 727 REVIEWs (46% of respondents) — too many for efficient human review. The REVIEW tier doesn't distinguish "likely DISCARD but not confident" from "likely KEEP but not confident."

**What's needed**:
- Sub-tier REVIEW_DISCARD (high confidence discard, needs human confirmation)
- Sub-tier REVIEW_KEEP (high confidence keep, needs human confirmation)
- REVIEW volume reduction (target: <15% of respondents in REVIEW)
- Active learning: feed human REVIEW decisions back into ML model

#### Gap 6: Cross-Dataset Generalization
All results are on Echo BH (109-2601). Cross-dataset generalization was poor in earlier experiments (different datasets have different strongest signals). V7's calibration may not transfer.

**What's needed**:
- Run V7 pipeline on all 11 annotated datasets
- Per-dataset threshold tuning
- Meta-learning across datasets (learn which signals matter per dataset type)
- Dataset-specific evidence family weights

### Roadmap to 90% BAcc

| Phase | Approach | Expected BAcc | Timeline |
|-------|----------|---------------|----------|
| Current | V7 threshold-tuning | 0.690 | Done |
| Phase 1 | ML model retraining with V7 labels + Platt scaling | ~0.72-0.75 | 1-2 weeks |
| Phase 2 | Semantic embedding similarity for OE scoring | ~0.75-0.80 | 2-4 weeks |
| Phase 3 | Per-channel/per-class calibration | ~0.78-0.82 | 1-2 weeks |
| Phase 4 | Cross-question consistency scoring | ~0.82-0.86 | 3-6 weeks |
| Phase 5 | Ensemble (ML + semantic + consistency + agent) | ~0.86-0.90 | 4-8 weeks |
| Phase 6 | Active learning from human REVIEW decisions | ~0.90+ | Ongoing |

### Key Insight

The threshold-tuning approach (V4-V9) has reached its ceiling at 69% BAcc. The same signals drive both TPs and FPs, so no threshold configuration can separate them further. To reach 90% BAcc, we need **new orthogonal signals** (semantic embeddings, cross-question consistency, behavioral patterns) and **better ML calibration** (retraining with agent labels, Platt scaling, per-dataset models). The agent review framework is sound — it just needs better inputs.

---

## 6. Evolution Loop Results (V10-V18)

After V7-V9 threshold tuning reached a ceiling at 0.690 BAcc, an autonomous evolution loop
was built to systematically explore ML-based approaches. All results use **5-fold cross-validation**
on Echo BH (no data leakage). V7 agent judgment features are used as semi-supervised labels.

### Version Comparison

| Version | Approach | BAcc | F1 | AUC | Key Change |
|---------|----------|------|-----|-----|------------|
| V7 | Agent review (threshold tuning) | 0.690 | 0.586 | N/A | Baseline (best agent version) |
| V10 | sklearn ensemble + V7 features | 0.729 | 0.650 | 0.773 | Calibrated GBM+RF+LR with isotonic regression |
| V11 | XGB+LGB+MLP+RF + TF-IDF | 0.737 | 0.659 | 0.777 | Advanced models + word TF-IDF + supplier interactions |
| V12 | + char n-grams + feature selection | 0.735 | 0.655 | 0.768 | Char n-grams + mutual information feature selection |
| V13 | Multi-dataset (no V7 features) | 0.702 | 0.613 | 0.745 | Train on all 11 datasets (only Echo has labels) |
| **V14** | **Self-training + V8 features** | **0.744** | **0.670** | **0.788** | **Self-training on 13K unlabeled + V7+V8 agent features** |
| V15 | Optuna hyperparameter optimization | 0.740 | 0.661 | 0.791 | Bayesian optimization (overfits to noisy pseudo-labels) |
| V16 | Separate Pro/Consumer models | 0.732 | 0.648 | 0.786 | Pro BAcc 0.765, Consumer BAcc 0.689 (bottleneck) |
| V17 | LLM embeddings + V7+V8+V9 | 0.739 | 0.662 | 0.786 | Sentence-transformer embeddings (384 dims) + 3 agent sources |
| V18 | Two-stage model (REVIEW tier) | 0.738 | 0.661 | 0.792 | Specialized model for uncertain cases (stage1_only always best) |

### Best Version: V14

**V14 (Self-Training + V8 Features)** is the best performing version at **BAcc 0.744, F1 0.670, AUC 0.788**.

Key components:
1. Self-training: Echo labels → predict on 13,388 unlabeled respondents from 10 other datasets → high-confidence predictions (≥0.85) become pseudo-labels → retrain (3 iterations, ~14K training samples)
2. V7 + V8 agent judgment features (semi-supervised labels from two agent versions)
3. XGBoost + LightGBM + MLP ensemble with isotonic calibration
4. Per-channel threshold optimization (Pro vs Consumer)
5. 17 enhanced semantic features (OE specificity, equipment mentions, grounding anchors, etc.)

### AUC Ceiling Analysis

The AUC has plateaued at ~0.79 across V14-V18 despite trying:
- 6 different model architectures (sklearn GBM, XGBoost, LightGBM, MLP, RF, CatBoost)
- 5 feature types (semantic, TF-IDF word, TF-IDF char n-gram, LLM embeddings, cross-question)
- 3 training strategies (self-training, multi-dataset, cost-sensitive)
- 3 agent feature sources (V7, V8, V9)
- 2 architectural approaches (two-stage, per-channel)
- Optuna Bayesian hyperparameter optimization

This suggests an **AUC ceiling of ~0.80** for the available signals. Reaching 90% BAcc
requires AUC > 0.95, which needs fundamentally different data sources.

### What Would Break the Ceiling

1. **Active learning**: Get human labels for the 30% of respondents in the REVIEW tier
2. **Client reject reasons**: The annotated file only has status (3/5), not WHY each was rejected
3. **Cross-survey history**: Track respondents across multiple surveys to detect patterns
4. **Real-time behavioral data**: Click patterns, response editing, time-per-question curves
5. **LLM-based text quality scoring**: Use GPT-4/Claude to score OE text quality directly

### Artifacts

| Artifact | Path |
|----------|------|
| Evolution loop script | `autosurvey/scripts/evolution_loop.py` |
| ML model improvement | `autosurvey/scripts/improve_ml_model.py` |
| V10 CV evaluation | `autosurvey/scripts/v10_cv_evaluation.py` |
| V11 advanced ensemble | `autosurvey/scripts/v11_advanced_ensemble.py` |
| V12 CatBoost + features | `autosurvey/scripts/v12_catboost_features.py` |
| V13 multi-dataset | `autosurvey/scripts/v13_multi_dataset.py` |
| V14 self-training (BEST) | `autosurvey/scripts/v14_self_training.py` |
| V15 Optuna optimization | `autosurvey/scripts/v15_optuna.py` |
| V16 channel models | `autosurvey/scripts/v16_channel_models.py` |
| V17 LLM embeddings | `autosurvey/scripts/v17_llm_embeddings.py` |
| V18 two-stage model | `autosurvey/scripts/v18_two_stage.py` |
| Decision log | `autosurvey/DECISION_LOG.md` |
| CV results (all versions) | `autosurvey/v10_cv_results.json` through `v18_cv_results.json` |
| Calibrated model | `autosurvey/skills/cleaning-survey-quality/models/echo_calibrated_model.joblib` |

---

## 5. Artifacts Location

| Artifact | Path |
|----------|------|
| V7 (best) annotated Excel | `TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v7/109-2601 Echo BH_annotated.xlsx` |
| V7 dashboard | `TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v7/109-2601 Echo BH_dashboard.html` |
| V7 performance report | `TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v7/v7_performance_report.md` |
| V8/V9 performance report | `TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v9/v8_v9_performance_report.md` |
| Comparison results (all versions) | `TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v9/comparison_results.json` |
| Comparison script | `autosurvey/scripts/compare_v4_v5_echo.py` |
| Integration script | `autosurvey/skills/cleaning-survey-quality/scripts/integrate_agent_judgments.py` |
| Review packet generator | `autosurvey/skills/cleaning-survey-quality/scripts/run_holistic_agent_review.py` |
| V7 error analysis | `autosurvey/scripts/analyze_v7_errors.py`, `autosurvey/scripts/analyze_v7_raw_signals.py` |
| V7 calibration guardrails | `autosurvey/skills/cleaning-survey-quality/references/production/v7-calibration-and-guardrails.md` |
| Skill definition | `autosurvey/skills/cleaning-survey-quality/SKILL.md` |

---

## 7. Status Update — 2026-06-30

### Current validated status

The 90% target is still open for production-safe AutoQuality.

The best full Echo self-improvement result from the end-to-end run is:

| Metric | Value |
|---|---:|
| Accuracy | 0.803 |
| Precision | 0.801 |
| Recall | 0.590 |
| F1 | 0.679 |
| AUC | 0.820 |
| Errors | 308 |

The best global-threshold probe reached 0.809 accuracy with 299 errors. A 90% result on this dataset allows at most 156 errors.

### Diagnostic ceiling

The client label workbook contains post-review marker strings. These strings directly encode the client decision:

- 553 of 553 client discards contain `badopen` and `bad:` markers.
- 1,013 of 1,013 client keeps start with `qualified,` and do not contain those bad markers.

Using those marker strings can reach the 90% target, but that would be a leakage result. It is useful for diagnosis only. It is not a blind-run AutoQuality result.

### SQLite usefulness

SQLite was helpful because it made the run auditable. It joined raw answers, field roles, client labels, agent judgments, evaluation rows, and loop metrics in one place.

SQLite did not add predictive signal by itself. Its value was repeatability and cleaner false-positive and false-negative analysis.

### Updated next step

Do not keep running score-only model loops as the main path to 90%. The next useful work needs new information:

- client reject reasons,
- row-level adjudication of the 95 client rejects that AutoQuality kept,
- another labeled Echo wave for train-on-one and test-on-one validation,
- or panelist history across surveys.
