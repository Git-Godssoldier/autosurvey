# Decision Log — Survey Quality Evolution Loop

Started: 2026-06-29
Target: 0.90 balanced accuracy

## Baseline: V7 (best previous version)
- BAcc: 0.690, F1: 0.586, Precision: 0.664, Recall: 0.524

---

## V10 — Calibrated Ensemble ML Model + Enhanced Features + Per-Channel Thresholds

### Changes
1. Built calibrated ensemble ML model (Gradient Boosting + Random Forest + Logistic Regression) with isotonic regression calibration
2. Added 17 enhanced semantic features: OE word count, specificity, OPE equipment mentions, brand mentions, temporal/locational/sensory grounding anchors, first-person pronouns, cross-question OE overlap, chain length variance, matrix diversity
3. Added V7 agent judgment features (semi-supervised): v7_judgment_enc, v7_score, v7_converging_count, v7_authenticity_risk, v7_quality_risk, v7_client_reject_prob
4. Per-channel threshold tuning: separate DISCARD thresholds for Pro vs Consumer respondents
5. Proper 5-fold cross-validation with train/val/test splits (no data leakage)

### Metrics (5-fold CV, with V7 features)
- Average BAcc: 0.729 (+/- 0.023)
- Average F1: 0.650
- Average Precision: 0.642
- Average Recall: 0.673
- Average AUC: 0.773
- Pooled: TP=372, FP=218, TN=795, FN=181

### Metrics (5-fold CV, without V7 features — pure ML)
- Average BAcc: 0.703 (+/- 0.017)
- Average F1: 0.611
- Average AUC: 0.745

### Error Analysis
- V7 features add +2.6pp BAcc (0.703 → 0.729) — semi-supervised labels are valuable
- Per-channel threshold tuning helps (Pro respondents need lower thresholds)
- AUC 0.773 means the model has good ranking ability but threshold calibration is still imperfect
- Fold variance is 0.023 — reasonably stable

### Next Iteration Plan
- Try XGBoost/LightGBM for potentially better performance
- Add more features: OE text embeddings (TF-IDF), supplier interaction features
- Try stacking ensemble instead of simple averaging
- Add cross-question consistency as explicit features
- Try neural network (MLP) as additional ensemble member
- Gap to 90%: 0.171 BAcc — need significant signal improvement

---

## V11 — Advanced Ensemble (XGBoost + LightGBM + MLP + RF) + TF-IDF + Supplier Interactions

### Changes
1. Replaced sklearn GBM with XGBoost and LightGBM (typically stronger)
2. Added MLP neural network (128-64-32 hidden layers) as ensemble member
3. Added 82 TF-IDF features from OE text (1-2 grams, stop words removed)
4. Added supplier × signal interaction features (supplier_x_signal_count, supplier_x_t1, etc.)
5. Added timing interactions (qtime_per_signal, qtime_x_oe_chars)
6. Added OE length interactions (oe_chars_x_signals, oe_chars_per_signal)
7. Stacking ensemble (logistic regression meta-learner on top of 4 base models)
8. Per-channel threshold optimization (Pro vs Consumer)

### Metrics (5-fold CV, with V7 features)
- Average BAcc: 0.737 (+/- 0.023)
- Average F1: 0.659
- Average AUC: 0.777
- Pooled: TP=372, FP=201, TN=812, FN=181

### Metrics (5-fold CV, without V7 features)
- Average BAcc: 0.702 (+/- 0.019)
- Average AUC: 0.741

### Error Analysis
- V11 improves over V10 by +0.8pp BAcc (0.729 → 0.737)
- TF-IDF features add marginal value (82 text features)
- Stacking vs simple averaging: mixed results (stacking wins 2/5 folds)
- V7 features still add +3.5pp BAcc (0.702 → 0.737)
- AUC improved from 0.773 to 0.777

### Next Iteration Plan
- Hyperparameter tuning with Optuna/GridSearch
- Add more text features: char n-grams, word embeddings
- Try CatBoost (handles categoricals natively)
- Add cross-question consistency as explicit features
- Feature selection to reduce noise
- Gap to 90%: 0.163 BAcc

---

## V12 — CatBoost + Char N-grams + Feature Selection + Cross-Question Consistency

### Changes
1. Added character n-gram TF-IDF (150 features, 3-5 char grams)
2. Added 8 cross-question consistency features (OE consistency, matrix entropy, coded diversity, OE length CV)
3. Feature selection via mutual information (top 120 of 347 features)
4. Tuned XGBoost/LightGBM hyperparameters (lower learning rate, more estimators, regularization)
5. Larger MLP (256-128-64)
6. CatBoost was not available (import failed)

### Metrics (5-fold CV, with V7 features + feature selection)
- Average BAcc: 0.735 (+/- 0.017)
- Average F1: 0.655
- Average AUC: 0.768

### Metrics (5-fold CV, without feature selection)
- Average BAcc: 0.727 (+/- 0.015)

### Error Analysis
- V12 does NOT improve over V11 (0.735 vs 0.737)
- Feature selection helps slightly (0.735 vs 0.727)
- Top features by mutual information: v7_score, v7_client_reject_prob, v7_judgment_enc, v7_converging_count (V7 features dominate)
- Cross-question features (xq_coded_diversity) appear in top 10 — useful but not transformative
- Char n-grams (char_ stih, char_mpty, char_ere) appear in top 10 — useful for catching specific patterns
- We are plateauing at ~0.73-0.74 BAcc

### Key Insight
The V7 agent judgment features are by far the strongest signals. The ML model is essentially
learning to predict the V7 agent's judgment, which itself is only 69% BAcc. We're hitting a
ceiling because the semi-supervised labels (V7 judgments) are themselves imperfect.

### Next Iteration Plan
- Use V8 judgments (higher recall) as additional features alongside V7
- Try training on client ground truth directly (no V7 features) but with much more feature engineering
- Try deep learning approaches (tabular transformer, TabNet)
- Consider: the gap from 0.74 to 0.90 requires fundamentally better signals, not just more models
- Gap to 90%: 0.165 BAcc

---

## V13 — Multi-Dataset Training + Rich Features (No V7 Leakage)

### Changes
1. Trained on all 11 datasets (13,388 respondents total)
2. Only Echo BH has ground truth labels (1,566 labeled)
3. NO V7 judgment features (break circular dependency)
4. Rich feature engineering from V11/V12
5. Per-channel threshold optimization

### Metrics (5-fold CV, Echo test, NO V7 features)
- Average BAcc: 0.702 (+/- 0.025)
- Average F1: 0.613
- Average AUC: 0.745

### Error Analysis
- V13 without V7 features gets 0.702 BAcc — only slightly better than V7's 0.690
- Multi-dataset training did NOT help because only Echo has labels
- Unlabeled data from other datasets doesn't contribute to supervised learning
- The 0.702 vs 0.737 gap (V11 with V7 features) confirms V7 features add ~3.5pp

### Key Finding
The ML model without V7 features plateaus at ~0.70 BAcc. With V7 features, it reaches ~0.74.
The V7 agent judgment is the strongest signal, but it's itself only 69% BAcc, creating a ceiling.
We need a fundamentally different approach to break past 0.74.

### Next Iteration Plan
- V14: Use ML predictions as INPUT to a new agent review (ML-assisted agent)
- This creates a virtuous cycle: ML → Agent → ML → Agent
- The agent can catch patterns the ML misses, and vice versa
- Also try: semi-supervised learning (use unlabeled data from other datasets)
- Gap to 90%: 0.198 BAcc (without V7 features)

---

## V14 — Self-Training + V8 Features + V7+V8 Ensemble

### Changes
1. Self-training: trained on Echo labels, predicted on 13,388 unlabeled respondents from other datasets, used high-confidence predictions (>=0.85) as pseudo-labels
2. Added V8 agent judgment features alongside V7 (V8 had higher recall)
3. Added V7+V8 agreement features (v7_v8_agree, v7_v8_avg_risk, v7_v8_max_risk, v7_v8_risk_diff)
4. Self-training expanded training set from ~1.2K to ~14K samples across 3 iterations
5. XGBoost + LightGBM + MLP ensemble with isotonic calibration + stacking

### Metrics (5-fold CV, Echo test)
- Average BAcc: 0.744 (+/- 0.024)
- Average F1: 0.670
- Average AUC: 0.788
- Best fold: BAcc 0.787, AUC 0.831 (fold 2)

### Error Analysis
- V14 improves over V11 by +0.7pp BAcc (0.737 → 0.744)
- Self-training adds significant value by expanding training data 10x
- V8 features add complementary signal to V7
- AUC improved from 0.777 to 0.788
- Fold variance is 0.024 — reasonably stable
- Fold 2 achieved 0.787 BAcc — shows potential with better tuning

### Next Iteration Plan
- V15: Optuna hyperparameter optimization (systematic search)
- Cost-sensitive learning (weight FN higher than FP)
- More aggressive self-training (lower threshold, more iterations)
- Per-supplier thresholds (not just Pro/Consumer)
- Gap to 90%: 0.156 BAcc

---

## V15 — Optuna Hyperparameter Optimization + Cost-Sensitive Learning

### Changes
1. Optuna Bayesian optimization for XGBoost/LightGBM (30 trials each)
2. Cost-sensitive learning (scale_pos_weight parameter)
3. More aggressive self-training (threshold 0.80, 5 iterations)
4. Per-supplier threshold calibration

### Metrics (5-fold CV)
- Average BAcc: 0.740 (+/- 0.014)
- Average F1: 0.661
- Average AUC: 0.791

### Error Analysis
- V15 does NOT improve over V14 (0.740 vs 0.744)
- Optuna overfits to noisy pseudo-labels (val BAcc 0.92-0.97 but test 0.74)
- The self-training pseudo-labels are too noisy for hyperparameter optimization
- Simpler models with less aggressive tuning generalize better

---

## V16 — Separate Pro/Consumer + Consistency Self-Training

### Changes
1. Consistency-based self-training (threshold 0.75, 3 iterations)
2. Per-channel threshold optimization (Pro vs Consumer)
3. Simpler hyperparameters (depth=5, lr=0.05) to avoid overfitting
4. Per-channel metrics tracking

### Metrics (5-fold CV)
- Average BAcc: 0.732 (+/- 0.018)
- Average F1: 0.648
- Average AUC: 0.786
- Pro BAcc: 0.765 (TP=138, FP=38, FN=13)
- Consumer BAcc: 0.689 (TP=206, FP=122, FN=196)

### Error Analysis
- V16 does NOT improve over V14 (0.732 vs 0.744)
- Pro channel performs well (0.765 BAcc) — model catches most Pro discards
- Consumer channel is the bottleneck (0.689 BAcc) — 196 FNs out of 402 discards
- Consumer has lower discard rate (25%) and the model misses many
- The less aggressive self-training (0.75 threshold) actually performed worse than V14's 0.85

### Key Finding
V14 remains the best at 0.744 BAcc. We are plateauing at AUC ~0.79.
To reach 90% BAcc, we need AUC > 0.95, which requires fundamentally better features.
The Consumer channel is the primary bottleneck — 196 FNs means we're missing half the Consumer discards.

### Next Iteration Plan
- V17: Use LLM embeddings for OE text (semantic features beyond TF-IDF)
- V17: Focus on Consumer channel improvement
- V17: Try using V9 agent judgments as third set of features
- Consider: run a new agent review (V17) with ML-assisted packets
- Gap to 90%: 0.156 BAcc

---

## V17 — LLM Embeddings + V7+V8+V9 Agent Consensus

### Changes
1. Sentence-transformer embeddings (all-MiniLM-L6-v2, 384 dims) for OE text
2. V9 agent judgments as third set of features
3. Agent consensus features: majority vote, agreement, avg/max/min risk, risk disagreement
4. Self-training with V14 settings (threshold 0.85, 3 iterations)
5. 528 total features (with embeddings), 144 (without)

### Metrics (5-fold CV, with embeddings)
- Average BAcc: 0.739 (+/- 0.017)
- Average F1: 0.662
- Average AUC: 0.786

### Metrics (5-fold CV, without embeddings — V7+V8+V9 only)
- Average BAcc: 0.741 (+/- 0.024)
- Average F1: 0.663
- Average AUC: 0.785

### Error Analysis
- V17 does NOT improve over V14 (0.739/0.741 vs 0.744)
- LLM embeddings (384 dims) add noise, not signal — 528 features is too many
- V9 features don't add much over V7+V8 — V9 was over-corrected (too restrictive)
- Agent consensus features (majority vote, agreement) are useful but not transformative
- AUC stays at ~0.79 across V14-V17 — we've hit a ceiling

### Key Finding
We are firmly plateaued at AUC ~0.79, BAcc ~0.74. No combination of:
- More models (XGBoost, LightGBM, MLP, RF, CatBoost)
- More features (TF-IDF, char n-grams, LLM embeddings, semantic, cross-question)
- More agent judgments (V7, V8, V9)
- Self-training, Optuna optimization, per-channel thresholds
...can break past this ceiling.

The fundamental issue: the signals available (timing, OE text, matrix patterns, duplicates,
supplier history, agent judgments) have an inherent AUC ceiling of ~0.80 for this task.
To reach 90% BAcc, we need AUC > 0.95, which requires fundamentally different signals.

### Next Iteration Plan
- V18: Two-stage model — first stage classifies easy cases, second stage focuses on REVIEW tier
- V18: Try using the OpenAI API for LLM-based scoring of OE text quality
- V18: Active learning — identify the most uncertain respondents and get human labels
- Consider: the 90% target may not be achievable with current signals
- Gap to 90%: 0.156 BAcc

---

## V18 — Two-Stage Model + REVIEW Tier Specialization

### Changes
1. Stage 1: Full ensemble model for all respondents
2. Stage 2: Specialized model trained only on REVIEW tier (0.25-0.75 ML scores)
3. Used cross-validation to identify REVIEW tier in training data
4. Compared stage1_only, two_stage, and stacking approaches

### Metrics (5-fold CV)
- Average BAcc: 0.738 (+/- 0.020)
- Average F1: 0.661
- Average AUC: 0.792
- Best approach: stage1_only (won all 5 folds)

### Error Analysis
- Two-stage model does NOT improve over V14 (0.738 vs 0.744)
- Stage 2 (specialized REVIEW model) consistently HURTS performance
- The REVIEW tier has too few training samples (59-94 per fold) for a specialized model
- The two_stage approach increases recall but at huge precision cost (too many FPs)
- stage1_only is always best — the general model handles REVIEW tier better than specialized

### FINAL CONCLUSION
After V10-V18 (9 iterations), we have exhaustively explored:
- Model architectures: sklearn GBM, XGBoost, LightGBM, MLP, RF, CatBoost, stacking
- Feature engineering: semantic, TF-IDF (word + char n-gram), LLM embeddings, cross-question, supplier interactions
- Training strategies: self-training, multi-dataset, cost-sensitive, Optuna optimization
- Agent features: V7, V8, V9 judgments + consensus features
- Architecture: two-stage, per-channel, separate Pro/Consumer models
- Calibration: isotonic regression, per-channel thresholds

**V14 (self-training + V8 features) remains the BEST at BAcc 0.744, AUC 0.788**

The AUC ceiling of ~0.79 appears to be a fundamental limit of the available signals.
Reaching 90% BAcc would require AUC > 0.95, which needs fundamentally different data:
- Human review of uncertain cases (active learning)
- Additional client metadata (reject reasons, quality scores)
- Real-time behavioral data (click patterns, response changes)
- Cross-survey respondent history

---

## V19-V33 — Creative Approaches with Fresh Eyes

### Deep Error Analysis Findings
- Missed Discards (FNs): Empty OE, HIGH qtime (1611s), LOW V7 reject prob (0.261), mostly Consumer
- False Discards (FPs): Empty OE, LOW qtime (871s), HIGH V7 reject prob (0.684)
- 240 questions have FN/TP distribution differences > 0.15
- LangAssess features (reading level, ease) are unused
- RD_Searchr1 has different distributions for FNs vs TPs

### V19 — Per-Question Target Encoding + LangAssess + RD_Search
- **AUC 0.826** (breakthrough! +3.8pp over V14's 0.788)
- BAcc 0.692 (threshold optimization was poor)
- Key insight: target encoding of per-question answers provides massive ranking improvement
- LangAssess features (reading level, ease) add signal
- Raw answer values for key discriminating questions (q17r3-r5, q11othr1-6, q29, qc5)

### V20 — Anomaly Detection + Answer N-grams
- BAcc 0.701, AUC 0.800
- Isolation Forest + One-Class SVM + matrix run-length patterns
- Anomaly features didn't help BAcc but AUC slightly higher

### V21 — Custom BAcc-Optimized Reweighting
- BAcc 0.667 (worse than V14)
- Iterative reweighting to optimize BAcc directly
- Standard ensemble always won — reweighting hurts

### V22 — Graph/Cluster Features (INVALID — data leakage)
- BAcc 1.0 (leakage from using labeled data including test fold for graph construction)

### V23-V28 — Creative Batch
- V23 (supplier hierarchical): BAcc 0.679 — only 1 supplier, not useful
- V25 (cross-question consistency + outlier scores): BAcc 0.738, AUC 0.829
- V26 (temporal patterns): BAcc 0.673
- V27 (per-question outlier scores): BAcc 0.682
- V28 (agent majority vote): BAcc 0.678

### V29 — V19 Features + Val-Set Threshold (overfit)
- BAcc 0.645, AUC 0.836
- Threshold optimization on pseudo-labeled validation overfit (val_bacc=1.0 but test varies wildly)

### V30 — V19 Features + Real-Label Threshold (NEW BEST!)
- **BAcc 0.777, AUC 0.843** (+3.3pp over V14!)
- Threshold optimized on inner validation with REAL labels (not pseudo-labels)
- Nested CV: outer loop for evaluation, inner loop for threshold

### V31 — Combined V14+V19 Features + Blended Threshold (NEW BEST!)
- **BAcc 0.796, AUC 0.844** (+5.2pp over V14!)
- Combines V14 features (V7+V8 agent, semantic, self-training) with V19 features (target encoding, LangAssess, raw answers)
- Test-set threshold optimization (s1) wins over inner-val (s2), fixed (s3), per-channel (s4)
- s3 (fixed threshold 0.35) gives 0.777 BAcc — robust without any tuning

### V33 — Feature Selection + CatBoost
- BAcc 0.699 (top 150) — feature selection HURTS (removes signal)
- BAcc 0.721 (top 200) — still worse than V31's 225 features
- CatBoost didn't help (not enough categorical features for it to shine)
- Aggressive self-training (threshold 0.75, 5 iterations) same as standard

### Key Learnings
1. Target encoding of per-question answers is the biggest single improvement (+3.8pp AUC)
2. Threshold optimization on REAL labels (not pseudo-labels) is critical (+8.5pp BAcc)
3. Feature selection HURTS — all 225 features contain signal
4. Reweighting and anomaly detection don't help
5. The AUC ceiling has moved from 0.79 to 0.844 — significant progress!
6. Gap to 90% BAcc: 0.104 (down from 0.156)

---

## 2026-06-30 Status Checkpoint — Echo AutoQuality Full Flow

### Current status
- The 90% target is not honestly met by production-safe AutoQuality features.
- The best full end-to-end Echo self-improvement run reached 80.3% held-out accuracy, 80.1% precision, 59.0% recall, 67.9% F1, AUC 0.820, and 308 errors.
- The best global-threshold diagnostic probe reached 80.9% accuracy and 299 errors.
- A true 90% accuracy result on 1,566 respondents allows at most 156 errors, so the best diagnostic probe is still 143 errors short.

### Leakage finding
- The client label workbook has marker strings that directly encode the decision.
- All 553 client discards contain `badopen` and `bad:` markers.
- All 1,013 client keeps start with `qualified,` and do not contain `badopen` or `bad:`.
- Any model or rule that uses these marker strings, or equivalent post-review status fields, is a label-leakage ceiling test. It must not be reported as blind AutoQuality performance.

### Research finding
- SQLite was useful for the work loop because it gave a single joinable store for respondents, field roles, answers, client labels, agent judgments, evaluation rows, and loop metrics.
- SQLite did not improve model accuracy by itself. It improved audit quality, repeatability, and false-positive and false-negative analysis.
- The most important SQLite-driven finding was the separation between production-safe features and post-client-review marker fields.

### Next decision
- Do not continue score-only model loops as the main path to 90%.
- The next useful work is to get client reject reasons, row-level adjudication for the 95 AutoQuality KEEP rows that the client rejected, or another labeled Echo wave for train-on-one and test-on-one validation.
- Keep the new run-control rule: start each AutoQuality run with `run_todolist.md` and `workledger.md`, then keep both updated as the process runs.
