# AutoQuality Current Review — 2026-06-30

## Scope

Reviewed the Echo BH AutoQuality artifacts, workflow instructions, performance logs, and row-level V7 agent judgments against the client-annotated workbook.

Primary files reviewed:
- `/Users/jeremyalston/Perfect/AutoQuality Pair Copy - Echo/109-2601 Echo BH - unannotated.xlsx`
- `/Users/jeremyalston/Perfect/AutoQuality Pair Copy - Echo/260300_ECHO - client annotated.xlsx`
- `/Users/jeremyalston/Perfect/autosurvey/PERFORMANCE_TRACKER.md`
- `/Users/jeremyalston/Perfect/autosurvey/DECISION_LOG.md`
- `/Users/jeremyalston/Perfect/autosurvey/v30_cv_results.json`
- `/Users/jeremyalston/Perfect/autosurvey/v31_cv_results.json`
- `/Users/jeremyalston/Perfect/autosurvey/v32_v38_cv_results.json`
- `/Users/jeremyalston/Perfect/autosurvey/skills/cleaning-survey-quality/SKILL.md`
- `/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v7/agent_judgments.json`

## Current Metrics

### Agent workflow, V7 calibrated run

This is the best full row-level agent workflow run available for Echo.

| Metric | Value |
|---|---:|
| N | 1,566 |
| TP | 290 |
| FP | 147 |
| TN | 866 |
| FN | 263 |
| Accuracy | 0.738 |
| Precision | 0.664 |
| Recall | 0.524 |
| F1 | 0.586 |
| Balanced accuracy | 0.690 |

V7 remains the best balanced agent operating point. V8 improves F1 slightly to 0.591, but balanced accuracy falls to 0.681 and false positives rise sharply.

### Current ML experiment, V31

V31 is the strongest current CV result in the result files I inspected.

| Metric | Value |
|---|---:|
| TP | 412 |
| FP | 156 |
| TN | 857 |
| FN | 141 |
| Accuracy | 0.810 |
| Precision | 0.725 |
| Recall | 0.745 |
| F1 | 0.735 |
| Balanced accuracy | 0.796 |
| AUC | 0.844 |

Important caveat: `scripts/v31_combined_features.py` explicitly includes a V14-style test-set threshold optimization strategy. Treat V31 as an exploratory upper-bound experiment until threshold selection is moved fully inside the training/validation fold and rerun.

V37 is later than V31 but lower: accuracy 0.789, precision 0.684, recall 0.750, F1 0.716, balanced accuracy 0.780.

## False Negative Findings

V7 false negatives are client discards that the agent predicted as REVIEW or KEEP.

Count: 263.

Main pattern:
- 194 were REVIEW, 69 were KEEP.
- Mean ML score was 0.371, with max only 0.504.
- Median convergence was 1 family; no FN had more than 3 fired families.
- 134 were `thin_on_topic`, 78 were `substantive`, 33 were `off_topic`.
- Only 7 had `model_risk`; only 1 had `quota_reconstruction`.

Interpretation: the agent misses rows that look human, low-risk, and often on-topic, but the client rejects them for survey-specific quality, quota, brand funnel, classification, or hidden PM rules. This is not mainly a fraud-detection failure.

High-priority FN causes:
- Client is stricter than the agent on Echo open-ended OPE quality.
- Brand-funnel and equipment ownership/use signals are underused in row-level reasoning.
- Consumer rows dominate FNs: 242 of 263 were `CLASSIFY=2`.
- `conditionsAriens=1` is overrepresented in FNs: 69 of 263, compared with 289 of 1,566 overall.
- Client labels include broad `badopen`/`bad:qualified` markers, but not precise reject reasons, so some FN learning is reconstructive.

## False Positive Findings

V7 false positives are client keeps that the agent discarded.

Count: 147.

Main pattern:
- All were DISCARD.
- Mean ML score was 0.591.
- Median convergence was 4 families.
- 141 of 147 fired `model_risk`.
- 101 fired `timing_engagement`.
- 86 fired `brand_funnel`.
- 83 were `thin_on_topic`, 35 were `substantive`.

Interpretation: false positives are mostly caused by trusting model risk plus convergence too much when the client kept rows that look marginal. The V7 convergence rule is directionally right, but the fired families are not independent enough in these rows.

Likely FP causes:
- `model_risk` is over-weighted around the 0.50 to 0.80 band.
- Timing and brand funnel often co-fire with model risk, inflating convergence.
- `thin_on_topic` rows are still being over-penalized in some combinations.
- Stage 2 quality fail is noisy: the V7 report notes 247 accepted rows landed in Stage 2 fail.

## Client Mislabeling Risk

The paired client workbook shows a mechanically consistent label pattern:
- 553 of 553 client discards have `badopen` and `bad:qualified` markers.
- 1,013 of 1,013 accepted rows start with `qualified,` and lack `badopen`/`bad:` markers.

So there is no obvious column-level label corruption in the Echo pair. The likely issue is not random client mislabeling. It is label opacity: the client label says the row was removed, but not whether the reason was true respondent quality, quota balancing, eligibility, manual admin, or strict bad-open review.

Rows most worth human audit are not all FNs/FPs. Prioritize:
- Strong FP: accepted by client but V7 score <= -0.65 or ML >= 0.70.
- Strong FN: rejected by client but V7 KEEP with ML < 0.35 and no fired families.
- Any row where the only difference is strictness around short or generic but on-topic OPE answers.

I wrote the full FP/FN audit table here:
`/Users/jeremyalston/Perfect/autosurvey/docs/autoquality_echo_v7_error_audit_samples.csv`

## Workflow And Instruction Findings

Task adherence gaps:
- The skill instructions say Stage 2 should spawn all chunk subagents in parallel. That conflicts with the current tracking rule: do not spawn more than one agent at a time.
- The V7 workflow uses 8 chunk files of about 200 respondents. For the new operating process, keep the same chunking, but process chunks sequentially and log each chunk start, completion, metrics, and follow-up action.
- V31 and related ML scripts include exploratory threshold tuning patterns. These should be separated from validation scripts so performance claims cannot accidentally include test-set threshold selection.
- The metric tracker mixes full agent-run metrics, exploratory ML CV metrics, and roadmap estimates. It needs a top-level distinction between `validated`, `exploratory`, and `projected`.

Instruction strengths:
- The current V7 framework correctly separates `authenticity_risk`, `quality_discard_risk`, and `client_reject_probability`.
- The badopen audit trail is the right direction.
- The strongest existing lesson is preserved: open-end quality alone should not drive discards.

## Next-Level Process

Use this process every time so actions, outcomes, and next steps are trackable.

1. Register the run.
   - Dataset, input workbook, client label workbook if available, run ID, operator, date, goal metric, and validation mode.

2. Map fields before scoring.
   - Explicitly map screeners, quotas, brand funnel, equipment ownership/use, narrative open ends, other-specify fields, timing, supplier, and technical identifiers.

3. Run one chunk at a time.
   - Do not spawn multiple agents concurrently.
   - For each chunk, log chunk file, number of respondents, start time, end time, output file, and any instruction deviations.

4. Score with separated dispositions.
   - Keep authenticity, quality, and client-reject reconstruction separate.
   - Never convert a client discard into a fraud conclusion without evidence.

5. Evaluate with locked metrics.
   - Use status=5 as positive and status=3 as negative.
   - Report TP, FP, TN, FN, accuracy, precision, recall, F1, specificity, balanced accuracy, soft recall, and review volume.

6. Run residual analysis.
   - Cluster FNs and FPs by ML band, convergence count, evidence families, OE class, CLASSIFY, conditions flags, brand funnel, equipment ownership/use, timing, and supplier.

7. Promote rules only with counterexamples.
   - Every proposed FN-catching rule must be checked against accepted rows.
   - Every proposed FP-reducing guardrail must be checked against true discards.

8. Separate validation from exploration.
   - Exploratory scripts may optimize thresholds for discovery.
   - Published metrics must use nested or train-only threshold selection.

9. Produce the next action log.
   - One table: action, owner, expected metric impact, risk, artifact path, status.

## Recommended Next Actions

1. Fix the validation harness first.
   - Create a clean V31 rerun that selects thresholds only on inner validation folds.
   - Recompute accuracy, precision, recall, F1, balanced accuracy, and AUC.

2. Create Echo residual review packets.
   - One packet each for the 263 V7 FNs and 147 V7 FPs.
   - Include raw branch, condition, brand-funnel, equipment ownership/use, marker family, V7 rationale, and candidate missed signal.

3. Add a `client_reject_reason` reconstruction layer.
   - Predict likely reason: quality_auth_failure, quota_balancing, eligibility_screenout, vendor_source, manual_admin, unknown_mixed.
   - Evaluate each reason separately instead of one binary discard label.

4. Build brand-funnel relation checks.
   - Awareness, possible brands, rated brands, share allocation, ad recall, NPS, and other-specify brand names should be evaluated as a graph.

5. Add per-branch calibration.
   - Separate consumer, pro, Ariens-condition, and non-Ariens thresholds.
   - The current FN/FP patterns differ enough that one global threshold is leaving performance on the table.

6. Update the skill instructions.
   - Replace “spawn all chunk subagents in parallel” with a configurable concurrency policy.
   - For the current goal, set concurrency to 1 and require a chunk-level action log.

## Addendum: End-To-End Self-Improvement Status

After the full Echo end-to-end run and self-improvement loops, the best production-safe held-out result is 80.3% accuracy, 80.1% precision, 59.0% recall, 67.9% F1, and 308 errors.

The best global-threshold probe is 80.9% accuracy with 299 errors. This is still 143 errors short of the 90% target, which allows at most 156 errors across 1,566 respondents.

The strongest diagnostic finding is that the client label markers directly encode the final decision. All client discards have `badopen` and `bad:` markers. All client keeps start with `qualified,` and do not have those bad markers. A system that uses those marker strings can clear 90%, but that is label leakage and must not be reported as blind AutoQuality performance.

SQLite was useful for this work. It made the analysis repeatable by joining raw answers, field roles, client labels, agent judgments, evaluation rows, loop metrics, and error ledgers. It did not improve accuracy by itself, but it made the false-positive, false-negative, and leakage analysis much more reliable.

Current status: the 90% target is not met by production-safe features. The next useful work needs new information, such as client reject reasons, adjudication of low-signal client rejects, or a second labeled Echo wave for validation.
