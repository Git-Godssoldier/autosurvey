# Authenticity-first calibration

Use this reference for methodology-development runs that include TFG `status` labels or client annotations. Use `decipher-blind-authenticity-review.md` for normal Autosurvey runs on blank Decipher exports.

Annotated datasets are the lab for developing Autosurvey. They teach signal questions, evidence weights, and false-positive guardrails. They are not runtime inputs for blank survey cleaning. A normal blank run must not use `status = 3`, `status = 5`, client flags, or hidden cleaning outcomes.

## Core frame

Autosurvey evaluates respondent authenticity. Generic quality is secondary.

Model two outcomes separately:

- **Client rejection probability**: the chance that TFG or the PM would remove or review the row based on the client process. `status = 5` is evidence of this outcome.
- **Fabrication or authenticity risk**: the chance that the respondent was not faithfully, personally, and consistently answering as a qualified human respondent. `status = 5` can teach this risk, but it is not proof of a bot, LLM, or fraud.

Do not write as if all rejected rows are bots. Learn what the client removed, then decide which removals indicate fabrication risk, qualification mismatch, inattentiveness, survey-design ambiguity, or ordinary quality concern.

After each labeled calibration cycle, carry durable learnings into `decipher-blind-authenticity-review.md`, the internal signal bank, and the next-pass signal inventory as natural-language detection questions. Do not carry labels, status-specific rules, or client-only outcomes into blank runtime execution.

## Blind-then-contrast workflow

For labeled datasets, review every respondent twice:

1. **Blind semantic pass**
   - Hide `status`, client flags, helper labels, and final-review fields.
   - Read the Question Contract, question-relation graph, full response chain, timing, routing, brand funnel, matrix patterns, open ends, duplicate context, and protective human evidence.
   - Assign a five-tier recommendation with evidence family weights and plain-language rationale.

2. **Label-aware contrastive pass**
   - Reveal `status = 3` and `status = 5`.
   - Compare the blind recommendation to the client decision.
   - For each status-5 row, determine whether the blind pass missed a real signal, whether the client likely used a signal not yet captured, or whether the row reflects a non-authenticity removal.
   - For each status-3 row, record protective evidence and false-positive guardrails.

This prevents the agent from inventing explanations merely because it already knows the outcome.

## Frozen learning loop

Run the calibration loop in this order. Do not score a blinded dataset until the loop has produced stable transferable instructions.

1. Freeze inputs and eliminate label leakage.
   - Record workbook names, row counts, label counts, hashes, and the held-out blinded dataset name.
   - Hide labels and client flags from the first semantic review.
   - Treat helper fields as unavailable to the blind reviewer. Exclude `status`, marker and quota fields, client action fields, final decisions, review notes, condition assignment helpers, no-answer helper fields, QC helper fields, channel tracking fields, tokens, hidden cleaning fields, and formulas or formatting that reveal cleaning outcomes.
   - If a field nearly reproduces `status = 5`, inspect the field name and workbook role before calling it a signal. A perfect or near-perfect signal from a helper field is usually leakage, not transferable intelligence.
2. Reconstruct the survey.
   - Map every question, scale, matrix, route, brand or product entity, quota, timing field, identifier field, and cross-question relationship.
3. Read every labeled respondent with status hidden.
   - Build the full response chain before assigning a tier.
   - Write the blind record before labels are revealed.
   - Write one agent-authored row judgment for every respondent. A scripted score is not a blind semantic review.
4. Use three perspectives.
   - The forensic investigator looks for fabrication, automation, duplication, wrong universe, and chain incoherence.
   - The human advocate looks for legitimate rough wording, valid short answers, real tradeoffs, non-native English, and plausible extreme opinions.
   - The evidence judge decides the tier after weighing both sides.
5. Reveal labels only after the blind record is frozen.
   - Compare the frozen blind tier to `status = 3` and `status = 5`.
   - Write a row-level contrast note for every respondent. For rejected rows, explain the learned signal if the blind pass missed it. For accepted rows, explain the protective guardrail if the blind pass overflagged it.
6. Match controls.
   - Match every rejected row to similar accepted rows before promoting a signal.
   - Match every suspicious accepted row to rejected rows to discover protective guardrails.
7. Cluster residual errors.
   - Cluster unexplained rejections, false negatives, false positives, duplicate patterns, and synthetic response families.
8. Specify signals.
   - Turn recurring distinctions into falsifiable signal specifications with evidence needed, counterexamples, alternative explanations, and expected transfer conditions.
9. Attack signals.
   - Try to disprove each signal with accepted counterexamples and benign explanations.
10. Validate by dataset.
   - Validate on held-out entire datasets or future waves, not only random rows.
11. Promote carefully.
   - Promote only transferable, documented, regression-tested signals.
12. Refit separate interpretations.
   - Keep client-rejection probability, authenticity risk, and model-error or audit risk separate.
13. Audit every Tier 5 row.
   - No Tier 5 row is final until the full response chain has been reviewed.
14. Update the system.
   - Update the skills, signal bank, code, tests, schemas, reports, and dashboard requirements.
15. Repeat.
   - Continue from residual errors until no stable new signal remains.
16. Freeze before blinded scoring.
   - Freeze the signal specifications and instructions before scoring the blinded dataset.

The loop explicitly learns from both sides. Rejected rows reveal possible fraud, gaming, qualification, or authenticity patterns. Accepted rows reveal legitimate human behaviors that must be protected.

## Five tiers

Keep these tiers exactly separated:

- **Tier 1: Accept**
  No meaningful concern after full-chain review.
- **Tier 2: Accept with protective note**
  Surface anomaly exists, but human evidence, prompt context, or accepted-row precedent explains it.
- **Tier 3: Review low-confidence**
  Some concern exists, but it is weak, ambiguous, design-driven, or not independent.
- **Tier 4: Review high-confidence**
  Multiple independent evidence families suggest serious authenticity or client-removal risk, but exclusion still needs final review.
- **Tier 5: Exclude candidate**
  Strong converging evidence supports removal review. Only Tier 5 is the discard set.

The expected client review volume may be calculated across Tiers 2-5 or Tiers 3-5. Do not inflate the discard set by mixing review tiers with exclusion candidates.

## Question Contract

Build a Question Contract before analyzing respondents. It should cover:

- respondent universe and qualification assumptions
- field roles
- expected answer type
- valid short-answer patterns
- required open-ended depth
- timing burden
- routing prerequisites
- connected fields in the same chain
- protective human evidence
- signals that would raise authenticity concern

Question families include awareness, preference, use, consideration, recommendation, satisfaction, purchase, allocation, brand funnels, matrices, open-ended explanations, demographics, timing, source, and technical identifiers.

## Question-relation graph

Automatically propose related questions, then classify the relationship before scoring consistency:

- **parallel**: questions should usually move together
- **inverse**: higher answer on one should usually imply lower or different answer on another
- **prerequisite**: one answer must be true before another answer is plausible
- **funnel progression**: awareness, familiarity, use, consideration, preference, recommendation, purchase, satisfaction
- **mutually exclusive**: answers cannot both be true without explanation
- **temporal**: prior behavior should precede later behavior
- **numerical**: allocations, ranks, or totals should reconcile
- **routing**: skip logic determines whether later answers should exist
- **open/closed contradiction**: text contradicts a structured response, or text provides protective context

Do not score raw similarity. Score the respondent against the correct relationship.

## Evidence families

Aggregate within families before making a tier decision. Ten correlated straightlining metrics are one matrix-behavior family, not ten independent reasons.

Core families:

- **Question-time elasticity**: time should generally increase with question complexity, matrix size, answer length, conflict, calculation burden, and recall burden.
- **Content-aware straightlining**: modal proportion, longest run, entropy, response variability, transitions, cyclic patterns, matrix time per cell, reverse-coded contradictions, and brand differentiation.
- **Answer-time and text coupling**: long, detailed, polished, or pasted-looking answers produced in implausibly little time; abrupt paste-like production; major style changes across open ends.
- **Semantic consistency and grounding**: open ends should connect to prior selections, brands, product use, role, time periods, and facts already established by the respondent.
- **Brand and product funnels**: awareness, use, consideration, preference, recommendation, satisfaction, purchase, and open explanations should form plausible chains.
- **Cross-respondent synthetic clustering**: near-duplicate open ends, repeated rhetorical templates, shared rare phrases, matching response vectors, matching timing vectors, identical matrix patterns, and burst submissions.
- **Full-chain nonresponse and route integrity**: resolve skip logic before treating blanks as suspicious. Detect missing prerequisites, populated downstream answers after "never," unexplained section omission, default-value chains, and export defects separately.
- **Duplicate technical/routing evidence**: shared IP, device, session, supplier/source, start burst, or routing pattern. Treat this as context unless response-chain evidence also converges.
- **AI-assistance concern**: polished prose, formality, low typo rate, em dashes, and generic fluency are weak supporting cues only. They never determine exclusion by themselves.

## Lessons from the first full annotated-corpus loop

The first full loop over the TFG labeled corpus showed that leakage removal changes the problem shape. Marker, quota, condition, no-answer, QC, channel, token, client, and review helper fields can look like extremely strong predictors. They must be excluded before the system makes any transfer claim.

After those fields are removed, broad scripted signals transfer weakly across whole held-out datasets. That is an important finding. It means generic timing, missingness, matrix, and simple open-end features are not enough to reproduce client rejection decisions or prove authenticity risk. The next loop must add deeper semantic features from full response chains.

The strongest non-leaking discoveries were:

- qualification and persona patterns in contractor classification fields;
- project or role specificity in open-ended qualification answers such as `qcoe1`;
- survey-specific open-end depth and answer specificity, such as ODL `q34`;
- rare combinations of polished open-end text, high missingness, and another weak family;
- timing signals only as support, because many accepted respondents are also fast;
- matrix uniformity only as context, because accepted respondents often show uniform patterns.

Treat these as prompts for semantic investigation. Do not promote them as fixed exclusion rules until accepted controls and residual errors support the distinction.

## Lesson from sealed Delta validation

The Delta Water Filtration validation showed why the agent must read every row. The frozen predictor over-weighted short generic answers and under-weighted the semantic boundary behind client `badopen` markers. Many accepted respondents gave short water-filter summaries, while many rejected respondents gave plausible but abstract or polished answers that lacked personal grounding.

The transferable lesson is not "short is good" or "polished is bad." The lesson is that open ends must be judged as respondent evidence. Ask whether the answer is grounded in the respondent's own chain, whether it answers the exact prompt, and whether similar accepted controls show the same surface pattern safely.

Future calibration must therefore treat concise accepted rows as guardrails and rejected polished rows as cases for deeper semantic reading. Do not use `badopen` as a runtime field. Learn the boundary it represents.

## Human protective evidence

Accepted rows are not background data. They are positive training examples.

Explicitly credit:

- ordinary revisions or self-corrections
- nuanced tradeoffs
- grounded idiosyncratic details
- legitimate extreme opinions
- non-native English or rough but coherent wording
- coherent "don't know" behavior
- accessibility or device context
- short answers that match the requested answer type
- accepted respondents with similar anomalies

Every suspicious rejected row should be compared with similar accepted respondents before promoting a signal.

## Required calibration outputs

For labeled methodology development, produce these calibration artifacts in a separate calibration output folder:

- `blind_authenticity_review_table.csv`: one row per labeled respondent, with status hidden during first pass.
- `label_aware_contrast_table.csv`: blind tier, status, disagreement type, learned signal, and protective evidence.
- `question_contract.md`: all question families, intended answer types, timing burden, relation graph, and protective evidence.
- `question_relation_graph.csv`: source field, related field, relation type, evidence expectation, contradiction rule, guardrail.
- `authenticity_signal_family_lift.csv`: family-level lift against `status = 5` and false-positive exposure against `status = 3`.
- `semantic_signal_expansion_notes.md`: agent-authored explanation of weighted evidence families.
- `protective_human_evidence.md`: accepted-row guardrails with cited examples.
- `input_inventory.csv`, `input_hashes.json`, `split_manifest.json`, `leakage_exclusions.json`, and `blinded_test_freeze_manifest.json`: input freeze and label-leakage proof.
- `labeled_row_manifest.csv`, `discard_rows_raw.parquet` or documented fallback, and `accepted_rows_raw.parquet` or documented fallback: all accepted and rejected rows reconciled.
- `column_profile_discard_vs_accept.csv`, `univariate_signal_ranking.csv`, and `cross_dataset_meta_signals.csv`: rejected-versus-accepted profile with within-dataset controls.
- `matched_case_pairs.parquet` or documented fallback, `accepted_guardrails.csv`, and `rejected_phenotypes.csv`: rejected rows paired with accepted controls and accepted false-positive guardrails.
- `pairwise_interactions.csv`, `higher_order_patterns.csv`, and `question_relation_graph.json`: interaction search and question relation scaffolding.
- `signal_bank.yaml`, `validation_report.md`, `residual_casebook.md`, `iteration_report.md`, and `freeze_manifest.json`: promoted and quarantined signals, validation, residual discovery backlog, and output freeze.

These artifacts can be staged by scripts, but the interpretation must be agent-authored from row reading.

Do not require these calibration artifacts for a normal blank Decipher run. Blank runs should instead produce the standard runtime artifacts, including the question-set authenticity map, Question Contract, semantic signal expansion notes, all-row audit, final judgment table, discard set, escalation packet, positive insights report, findings essay, dashboard, and next-pass signal inventory.
