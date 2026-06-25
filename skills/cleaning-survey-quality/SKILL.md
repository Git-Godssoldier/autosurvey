---
name: cleaning-survey-quality
description: Cleans and scores Decipher-style survey quality workbooks for market research datasets. Use when reviewing survey completes, fraud, inattentive respondents, open-end AI suspicion, straightlining, inconsistent brand answers, short completes, duplicate IPs, respondent flags, or survey quality files.
---

# Cleaning Survey Quality

Use this skill to run a reproducible survey quality pass on unannotated Decipher-style survey exports before PM review. Treat annotated helper columns and final-review files as calibration examples, not required inputs.

The default input is raw respondent data. The skill autonomously discovers meaningful candidate analyses, evaluates which analyses are safe to score, writes row-level justifications, generates agent annotations for intelligence and linguistic fluency, and reports which criteria need project-specific mapping.

Keep methodology development and runtime execution separate. Annotated TFG workbooks are used to develop the method and update reusable natural-language signal instructions. Normal Autosurvey runs are blind runs on blank Decipher exports. A blank run must not depend on `status = 3`, `status = 5`, client flags, or hidden cleaning outcomes.

This skill must favor data-analysis discovery and rigorous evaluation over flat scripted rubric scoring. Scoring is one output of the process, not the method itself.

## Progressive Filtering Order

The review must follow a strict ordering. Each layer filters the population progressively. Do not jump to observational or cross-population signals before the chain layer is complete, because chain validity changes the meaning of every downstream signal.

### Layer 1: Datamap to response-question mapping

The first step is always mapping the Datamap to the actual response fields. Before any scoring or signal extraction:

- Parse the Datamap or codebook. Extract prompt text, value labels, field groups, response options, and routing rules for every field.
- Build the Question Contract: for each field, record the question text, the expected evidence type (reason, brand, location, rating, use case, allocation, demographic, feedback), the response type (coded, open text, matrix cell, numeric), and the field role (screener, funnel, matrix, open end, demographic, technical, helper).
- Build the question-relation graph: connect awareness→consideration→use→preference→recommendation→satisfaction→purchase→open-ended explanation. Classify each relationship as parallel, inverse, prerequisite, funnel progression, mutually exclusive, temporal, numerical, routing, or open/closed contradiction.
- Map field roles before scoring. Separate job-role screeners, brand-list fields, narrative open ends, other-specify fields, survey-feedback fields, timing fields, supplier/source fields, respondent identifiers, IP/device fields, and review/helper fields.
- Do not score any field until its role and prompt text are known. A field scored without its Datamap context is a guess, not evidence.

### Layer 2: Per-field chain validity

After the Datamap is mapped, review each respondent's full response chain field by field. For every answered field, the agent must judge whether the answer is on-topic and credible for that specific prompt.

**The agent must semantically interpret each and every row.** Regex and scripted rules are used only for population-level signal staging — after Datamap mapping and propositional identity construction, they prepare inputs for the agent. The final discard decision for each row must come from agent intelligence reading the self-claim profile as a narrative, not from a regex match or threshold. In production there are no annotations, no status labels, and no answer bank. The agent must exploit semantic understanding to make final decisions in each case for each row without scripting.

#### Multi-agent architecture for production scoring

The production pipeline uses a multi-agent architecture with four stages. Scripts only stage raw data. Agents do all semantic work.

**Stage 1 — Script: Data staging (no semantic work)**
Scripts parse the Datamap, map response fields to question text and value labels, and compute population-level statistics (timing distributions, supplier cohorts, duplicate text detection, cross-respondent clustering). Scripts output structured JSON packets containing: the question text for each field, the value label for each coded answer (e.g., q15=4 → "Very concerned"), the raw open-end text, the timing, the supplier, and the duplicate group membership. Scripts do NOT score, do NOT classify open-ends, do NOT judge coherence. They stage raw materials only.

**Stage 2 — Agent: Respondent identity construction (natural language, not scripts)**
A subagent reads each staged packet and writes a natural-language respondent identity profile. This is NOT a proposition template — the agent reads the full answer chain and writes who this respondent claims to be, in plain English, including ALL signals translated to natural language:
- "I responded in 4 minutes" (qtime=240)
- "I have no supplier recorded" (missing SUPNAME)
- "I am very concerned about water quality" (q15=4 → label lookup)
- "I said about the survey: 'Thank you so much'" (outro verbatim)
- "I am aware of Delta, Brita, and PUR" (q26 checked items → label lookup)
- "I decided to buy because of bad taste" (q14 open text)
- "I gave the same outro text as 55 other respondents" (duplicate group membership)

The agent writes this identity profile using its own intelligence, reading the question text and answer meaning together. The agent decides how to phrase each claim based on the question context. No script template generates these profiles. The agent reads the question, reads the answer, and writes what the respondent is claiming about themselves.

**Stage 3 — Agent: Cross-respondent similarity comparison (natural language, not scripts)**
A subagent reads all respondent identity profiles and compares them to find:
- Respondents with identical or near-identical identity profiles (synthetic response families)
- Respondents sharing unusual claims, phrasing, or contradiction patterns
- Respondents whose identity profile is incoherent (claims that don't form a real person)
- Clusters of respondents from the same supplier with similar weak profiles

The agent writes a similarity report identifying clusters, shared patterns, and outlier profiles. This is a semantic act — the agent reads profiles as narratives and judges whether two respondents sound like the same person, a copied response, or a synthetic identity.

**Stage 4 — Agent: Final determination per row (natural language, not scripts)**
For each row, a subagent reads:
1. The respondent identity profile (from Stage 2)
2. The cross-respondent similarity findings (from Stage 3)
3. The static analysis signals (from Stage 1: timing percentile, supplier cohort, duplicate membership)

The agent makes a final determination: discard, review, or keep. The agent writes a one-paragraph justification explaining the decision in natural language, citing the specific identity claims, similarity findings, and signals that drove the decision. No scripted threshold determines the outcome. The agent weighs all evidence together and decides whether this specific respondent is authentic.

**What scripts do NOT do:**
- Scripts do NOT classify open-end text as "meta_praise" or "templated"
- Scripts do NOT detect contradictions between fields
- Scripts do NOT score rows or make discard decisions
- Scripts do NOT generate proposition templates
- Scripts do NOT apply regex rules to open-end text for semantic classification

**What scripts DO do:**
- Parse the Datamap into question text and value labels
- Look up coded values to get their label meanings
- Compute timing distributions and percentiles
- Detect exact duplicate text across respondents
- Detect duplicate IP addresses
- Compute supplier cohort distributions
- Assemble structured JSON packets for the agents to read

This architecture is mandatory for production runs. Scripted scoring produces false positives because regex cannot read context. The agent can. See `references/progressive-chain-filtering.md` for the full production pipeline specification.

For each answered field, the agent must judge:

- Does the answer give the evidence type the prompt requested?
- Does the answer fit the qualified respondent universe?
- Is the answer responsive to the exact question, or does it answer a different question?
- Is the answer a valid short noun phrase (acceptable for brand/location/factor prompts) or a nonresponsive placeholder?
- Does the answer contradict the respondent's own answers to adjacent or related fields?
- Does an open-end contain lived detail when the prompt asks for experience, or does it stay generic?
- Does an other-specify field name a real entity in the correct category?

Classify each field answer as: responsive, partially responsive, nonresponsive, wrong semantic dimension, off-topic, invalid type, impossible value, route-inconsistent, unsupported other-specify, mechanically repeated, or locally protected.

Separate hard invalidity from soft concern. Hard invalidity includes wrong-question answers, wrong semantic dimension, unsupported other-specifies, off-category entities, impossible allocations, route violations, copied text from another prompt, or invalid matrix structure. Soft concern includes speed, shortness, generic text, broad selection, straightlining, repetition, high positivity, or weak detail.

This layer is the primary authenticity surface. Most rejection drivers should be findable here. If a row has no chain-validity concern at this layer, its rejection driver is observational or cross-population, not semantic.

### Layer 3: Observational signals

Only after chain validity is established, filter in observational signals that contextualize the chain:

- Timing: total qtime, page/section/question answer time when available, fielding timestamps, odd-hour starts. Read timing probabilistically against cognitive burden, matrix size, answer length, and chain evidence. Fast time carries more weight when the chain is also weak.
- Supplier/source cohort: supplier concentration, source cohort anomalies, missing supplier. A missing supplier is context, not proof. Supplier concentration becomes evidence when multiple respondents from the same supplier share weak chains.
- Technical: IP address, device, user agent, session. Treat as independent context unless multiple supposedly independent respondents share the same technical evidence and weak chains.
- Platform helpers: TERMFLAGS, SCRUTINYFLAGS, Research Defender fields. Confirm meaning from the Datamap, then inspect the chain.

Observational signals refine the chain layer. They do not replace it. A fast respondent with a coherent, on-topic chain is a keep. A fast respondent with a weak chain is a discard candidate.

### Layer 4: Cross-population signals

Only after observational signals are layered in, filter in cross-population signals that reveal synthetic response families:

- Duplicate open text: text that appears in multiple respondents, especially rejected-only duplicates (text that appears more than once overall and only in rejected rows, never in accepted rows).
- Response vector clustering: respondents with identical or near-identical coded-answer vectors across many fields.
- Timing vector clustering: respondents with matching timing profiles or burst submissions.
- Matrix pattern clustering: respondents with identical matrix patterns across semantically distinct items.
- Shared rare phrases: repeated rhetorical templates or unusual phrasing across respondents.
- Copied chains: full response chains that are near-duplicates of other respondents.

Cross-population signals are the strongest convergence evidence. A single row with a weak chain is a review candidate. A single row with a weak chain that is also part of a duplicate cluster is a strong discard candidate.

### Why this ordering matters

The Delta t=5 analysis proved that 55.7% of rejected rows have a perfectly valid on-topic outro. Their rejection was not driven by open-end semantic content alone. The driver was found in the full chain — funnel inconsistency, brand awareness anomalies, supplier concentration, or technical evidence. If the review had stopped at the open-end layer, it would have missed the majority of rejection drivers.

Conversely, the Delta analysis proved that classic straightlining (same-answer across all matrix rows) separated zero rejected rows from accepted rows. If the review had led with matrix straightlining, it would have produced zero signal. The chain layer correctly down-weighted this signal to zero because the 7 matrix rows are semantically distinct product categories and no one actually flat-lined all of them.

The ordering is: understand what each field asks, judge whether each answer is credible for that field, then progressively layer in timing, supplier, technical, and cross-population evidence. Each layer refines the previous one. No layer is sufficient alone.

## Workflow

1. Frame the run before writing or running scoring scripts:
   - Read `references/agentic-escalation-path.md`.
   - Read `references/client-terminology-glossary.md` and use it to define client, PM, survey, and quality terms before writing final artifacts.
   - Read `references/decipher-blind-authenticity-review.md` for every normal Autosurvey run on a blank Decipher export. Use it to apply learned signal questions without using labels.
   - Read `references/agent-authored-row-review.md` before any respondent-level scoring, validation, or final review. This is the rule that prevents Autosurvey from becoming a rigid checklist.
   - Read `references/authenticity-first-calibration.md` when TFG status labels, client annotations, fraud suspicion, bot suspicion, LLM-assistance suspicion, or calibration against accepted/rejected rows are in scope.
   - Read `references/semantic-signal-expansion.md` before evaluating straightlining, speed, open ends, duplicate technical signals, semantic similarity, topic fit, bot suspicion, LLM suspicion, or fabricated-response detection.
   - Read `references/tfg-status-derived-detection-methodology.md` when TFG status-labeled training workbooks, status-derived rules, bot suspicion, LLM suspicion, or fabricated-response detection are part of the task.
   - Read `references/dataset-cycle-loop.md` when the run is part of an improvement cycle, a rerun, a multi-dataset pass, or a workflow-hardening request.
   - State the definition of done for this dataset in plain words.
   - Identify the source files, expected final artifacts, and what would block final delivery.
   - If the run includes internal comments, PM notes, client annotations, or prior criteria, read `references/internal-signal-learning.md`.
   - Start a short decision trail for non-obvious choices. The trail can be Markdown or TSV, but it must cite the artifact or command that supports each decision.
   - If a missing decision would change safety, scope, or final authority, ask one short question with a recommended default. If the answer can be discovered from available files, discover it instead of asking.
   - If a client annotated workbook exists, treat it as methodology-development data. The run must later compare autosurvey rows against the client actions, flags, review families, and TFG status labels before any benchmark claim. In TFG cleaning-answer workbooks, `status = 3` means the respondent was accepted, and `status = 5` means the respondent was rejected by TFG because of quality or authenticity concerns.
   - Separate client rejection probability from fabrication or authenticity risk. A `status = 5` row is an observed client rejection, not proof of bot behavior, LLM use, or fraud.
   - In annotated methodology runs, exclude leakage before feature extraction. Treat marker or quota fields, client action fields, final decision fields, review helper fields, condition assignment fields, no-answer helper fields, QC helper fields, channel tracking fields, token fields, hidden cleaning fields, and formulas or formatting that reveal cleaning decisions as unavailable to the blind reviewer. If those fields dominate a profile, quarantine the finding and rerun without them.
2. Explore the workbook before writing or running scoring scripts:
   - Read the sheet names, row count, column count, and Datamap or codebook when present.
   - Inspect representative raw rows and nonempty examples from every open-ended field family.
   - Read any internal comments, review notes, prior quality essays, prior escalation packets, prior signal inventories, and prior signal banks that are available for the same client, survey family, or product area. Read client annotations and TFG status labels only when the task is a methodology-development or benchmark task, not during a blind runtime pass.
   - Parse the Datamap before scoring. Extract prompt text, value labels, field groups, and response options. Treat Datamap parsing as the source of truth for field-role mapping when it is available.
   - Map field roles before scoring. At minimum, separate job-role screeners, brand-list fields, narrative open ends, other-specify fields, survey-feedback fields, timing fields, supplier/source fields, respondent identifiers, IP/device fields, and review/helper fields.
   - Field-role mapping must adapt to the workbook's actual language. Do not assume that role context is always named `qcoe1`. Treat fields such as `qIndustry`, `CLASSIFY`, buyer-role fields, product-involvement fields, use-case fields, and eligibility fields as role or qualification context when the Datamap shows that is their purpose.
   - Map demographics separately from quality evidence. Required demographic fields include `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, and `qPolitics` when present.
   - Stitch the full question chain before scoring. Use the Datamap or codebook prompt text when available. Fall back to ordered source columns when prompt text is not available.
   - Stitch each respondent's full response chain from all nonempty respondent-answer fields before final semantic review. Also build a focused semantic chain around `qcoe1`, `q9`, `q9r10oe`, `q10`, `q32`, `q43`, and `outro` when those fields exist. The final discard decision must review these chains, not just the field that triggered a flag.
   - Plan for a whole-population read from the start. The final package must include an independent full-response audit with one row per source respondent and a stitched chain for every row. Signal discovery can prioritize deeper review, but it cannot be the only review surface.
   - Plan for row-level agent authorship from the start. Every source respondent must receive an agent-written semantic judgment that uses the full response chain, the question contract, discovered signals, and protective accepted-row guardrails. Scripts may prefill candidate evidence, but they do not make the final row judgment.
   - Build an agent-authored question-set authenticity map before scoring text quality. For every major question set, state the intended respondent universe, the field role, what an authentic answer should sound like, what a fabricated or bot-like answer might sound like, what learned guardrails apply, and which source fields support that interpretation. This is natural-language analyst work, not a scripted template.
   - Build a Question Contract and question-relation graph before respondent analysis. Connect awareness, preference, use, consideration, recommendation, satisfaction, purchase, matrices, allocations, and open-ended explanations into relationship chains such as parallel, inverse, prerequisite, funnel progression, mutually exclusive, temporal, numerical, routing, or open/closed contradiction.
   - Build a semantic signal expansion plan before final weighting. For each discovered check, write how the agent will expand it beyond the raw flag. Straightlining must include question similarity and answer-time context when available. Speed must include page, section, question, and chain context when available. Open-end concerns must include semantic authenticity, prompt fit, respondent-universe fit, and learned false-positive guardrails.
   - Decide which fields can be scored in the first pass, which fields need PM mapping, and which fields should only produce review notes.
   - Do not run topic mismatch or low-effort scoring until the field role is clear. A job-role screener should not be scored like a product-topic open end. An unaided brand-list field should not penalize short valid brand names.
   - Build a project-specific topic and answer map from the Datamap, prompt wording, value labels, and sampled open ends before topic or answer-depth scoring. If a prompt asks for a physical item, location, product use, brand, simple reason, or short factor, short noun phrases may be complete answers. Protect those rows unless the full chain remains non-responsive, nonsensical, or contradicted by other strong evidence.
3. Build quality hypotheses from exploration:
   - State which fabricated, bot-like, LLM-assisted, inattentive, or otherwise unauthentic response patterns are plausible in this dataset.
   - State what evidence would confirm each pattern and what evidence would make it a false positive.
   - Turn annotated-data learnings into semantic reading questions, not keyword rules. Ask whether each respondent sounds like the qualified survey audience, whether the answer fits the prompt's requested evidence type, whether polished prose has lived detail, whether a coherent answer belongs to the wrong domain, whether survey-meta language replaced a respondent answer, and whether the full chain recovers or contradicts the concern.
   - Treat learned labels such as `badopen` as boundaries to understand, not fields to imitate. The agent must read the rejected rows and accepted controls to explain the semantic distinction. A concise answer can be human and acceptable. A polished answer can be fabricated when it lacks personal grounding, prompt fit, or chain support.
   - Give every discovery a provisional weight with a plain-language rationale. The weight should reflect prompt fit, question similarity, time plausibility, semantic authenticity, cross-chain coherence, signal independence, recurrence, learned false-positive guardrails, and survey-design ambiguity. Do not let a script assign the meaning of the weight.
   - Aggregate evidence by family before routing. Multiple straightlining metrics count as one matrix-behavior family unless another independent family also supports concern.
   - Separate row-level authenticity evidence from wave-level context and survey-design findings.
   - Add relevant internal comments or criteria as hypotheses, not as automatic rules.
4. Profile the workbook:
   - Identify the main respondent sheet, usually `A1`.
   - Confirm respondent key columns such as `uuid`, `record`, or `RID`.
   - Discover raw quality signals: qtime/duration, fielding start/date/timestamp fields, IP address, matrix grids, open-ended columns, brand/preference/recommendation candidates, and AI-likelihood columns when present.
   - Detect and ignore graded/review helper columns when building the raw-data discovery profile.
5. Run the scoring loop:
   ```bash
   python3 scripts/run_quality_loop.py \
     --data-dir /path/to/source-data \
     --output-dir /path/to/outputs/latest-quality-loop
   ```
   For one unannotated file:
   ```bash
   python3 scripts/run_quality_loop.py \
     --input-file /path/to/unannotated_export.xlsx \
     --topic-keywords "construction,contractor,building,gas,c-store" \
     --output-dir /path/to/outputs/raw-quality-pass
   ```
6. Review the generated `quality_report.md`, `row_scores.csv`, and `quality_summary.json`.
7. Review the generated table artifacts:
   - `question_chain_map.csv`: ordered source-field map with field roles, prompt text when available, and the fields used for full response-chain review.
   - `demographic_summary.csv` and `.md`: demographic and aggregate insights from the source data, using Datamap labels where available.
   - `generated_criteria_catalog.csv`: all generated criteria, tags, source columns, rationale, generated weights, and support.
   - `respondent_review_table.csv`: one row per respondent with metadata, triggered criteria, explanations, second-pass disposition, agent semantic analysis, linguistic fluency assessment, trust rationale, survivor rationale, discard rationale, and escalation routing.
   - `response_criteria_evidence_table.csv`: one row per respondent criterion with observed value, source column, generated points, explanation, weight rationale, second-pass disposition, and agent annotation context.
   - `agent_annotation_table.csv`: focused Opulent annotation surface for semantic analysis, linguistic fluency assessment, trust rationale, and next steps.
   - `respondent_review_table.md`: PM-facing Markdown sample sorted by severity/score.
8. Review `discovery_profiles.json` to confirm detected qtime, fielding timestamp, IP, matrix, open-end, brand-consistency, and AI-authenticity candidate analyses.
9. Route rows using `second_pass_decision` first, then `severity_level`, `escalation_owner`, and `escalation_reason`.
   - Escalate only rows marked `discard_candidate` after the extra pass.
   - Keep rows marked `keep_with_recommendation` or `keep_no_issue`; aggregate their survivor rationales and survey-question recommendations.
10. Run the agent critic review over every possible discard and read the all-row audit before finalizing:
   - Treat the generated criteria as the case file.
   - For normal blank runs, do not use `status`, client flags, helper labels, or final-review fields as decision evidence. Apply the learned signal questions from `decipher-blind-authenticity-review.md` directly to the current workbook.
   - For methodology-development runs only, first conduct a blind semantic review with `status`, client flags, helper labels, and final-review fields hidden. Assign one of five tiers before reading the label.
   - For methodology-development runs only, reveal `status` after blind review and run a label-aware contrastive pass that explains misses, false positives, protective evidence, and non-authenticity client rejection patterns.
   - For methodology-development runs only, keep two scores separate after the blind record is frozen. `client_reject_probability` estimates similarity to the client cleaning process. `semantic_risk_score` estimates authenticity concern from full-chain review. Do not use the client-process score as proof of fraud, and do not use the semantic score as a complete model of every client removal.
   - Read the full response chain and focused semantic chain for each candidate.
   - Write a respondent-level semantic judgment for every row, not only the first-pass candidates. For rows that are not risky, the judgment can be concise, but it must still name the protective reason, such as valid short answer, coherent chain, plausible timing, or accepted-row precedent.
   - Read enough of the all-row audit to understand every response family, not just the rows surfaced by the first pass.
   - Compare each possible discard against the question-set authenticity map. The final call should explain how the respondent's answer fits or violates the expected evidence type for that exact prompt family.
   - Consider the strongest benign explanation.
   - Decide whether evidence is verified, not verified, or inconclusive.
   - Promote rows into the final discard set only when the agent can explain the discard in plain language with citations.
   - Read the independent full-response audit across all rows before finalizing. Look for missed bad-response patterns, copied chains, direct non-responses, weak repeated placeholders, and false positives that the scorer either missed or over-weighted.
   - If the final read exposes a bad first-pass assumption, such as a missing field-role map or incomplete topic map, rerun the review with corrected context and write the correction into the internal signal bank.
   - Challenge the run before final delivery. Try to disprove the discard set, the kept-row rationale, the topic map, the field-role map, and the dashboard narrative. Repair the smallest material weakness and rerun only the checks affected by the repair.
11. After the agent has investigated review-tagged rows, generate a final visual review package through `reporting-survey-quality`:
   - `agent_review_judgment_table.csv`: all review-tagged rows with agent decisions.
   - `agent_discard_set.csv`: only rows the agent judged should be escalated for removal.
   - `agent_escalation_packet.md`: the final PM-ready escalation path, including discard rows, hard kept cases, difficult calls, internal criteria used, citations, and next actions. This file exists even when there are no discards.
   - `internal_quality_signal_bank.md`: internal lessons, comments, criteria, false positives, and next-pass signal status. This file is internal and should not be treated as client copy.
   - `agent_kept_review_synthesis.md` and `.csv`: synthesis of kept review-flagged candidates into survey-question and parameter improvements.
   - `full_chain_analyst_readout.md` and `full_chain_best_worst_examples.csv`: readable prose analysis of the best and worst full response chains, with explicit reasoning about what the agent saw.
   - `agent_positive_insights_report.md`: readable prose analysis of strong retained response chains, positive findings, false-positive guardrails, and what good data looks like in this dataset.
   - `next_pass_signal_inventory.csv`: critical signals that should shape the next first-pass analysis.
   - `next_pass_first_pass_config.json`: proposed next-pass rules, evidence needs, and escalation guardrails.
   - `question_contract.md` and `question_relation_graph.csv`: question families, relation types, timing burden, funnel logic, routing, contradiction rules, and guardrails.
   - `semantic_signal_expansion_notes.md`: agent-authored explanation of how raw checks became weighted evidence or stayed review-only.
   - `deep_semantic_review_sample.md`: a small set of reviewed rows with deeper semantic reasoning and next-pass learning.
   - `agent_row_semantic_judgments.csv` or `.jsonl`: one row per source respondent, authored after full-chain reading, with the semantic judgment, strongest discard signal, strongest protective signal, final tier, and next-pass learning.
   - `agent_findings_essay.md`: cited natural prose analysis of the run, discoveries, decisions, demographic context, and workflow learning.
   - `agent_final_review_dashboard.html` and `agent_final_visual_findings_report.md`: final dashboard, charts, tables, findings, and artifact index for content review.
   - Use `build_agent_review_artifacts.py` after the independent full-response audit to create the agent judgment table, discard set, kept-review synthesis, and verified quality brief.
12. Prove the package before calling the run complete:
   - Check that the required artifacts exist.
   - Verify that source rows, `row_scores.csv`, `respondent_review_table.csv`, and `independent_full_response_audit.csv` have the same row count. If they do not, stop and fix the run.
   - Verify that the independent audit contains a `full_response_chain` field and that the final judgment table was built after that audit.
   - Verify that the row semantic judgment artifact has one record per source respondent. If a run only contains scored flags, counts, or templated explanations, it has not completed the agent review.
   - Reconcile counts across respondent review, agent judgment, discard set, kept synthesis, essay, escalation packet, and dashboard.
   - Verify that every discard row appears in the escalation packet.
   - If the task is methodology development against annotated data, verify that `blind_authenticity_review_table.csv`, `label_aware_contrast_table.csv`, `authenticity_signal_family_lift.csv`, `protective_human_evidence.md`, and `agentic_fraud_training_report.md` exist. Do not require these artifacts for normal blank Decipher runs.
   - If the task is full annotated-corpus discovery, also verify that `input_inventory.csv`, `leakage_exclusions.json`, `labeled_row_manifest.csv`, `column_profile_discard_vs_accept.csv`, `univariate_signal_ranking.csv`, `cross_dataset_meta_signals.csv`, `matched_case_pairs`, `pairwise_interactions.csv`, `higher_order_patterns.csv`, `signal_bank.yaml`, `validation_report.md`, `residual_casebook.md`, and `freeze_manifest.json` exist and are populated. Do not score the blinded workbook if leakage-driven signals were found or if transfer validation remains weak without a documented residual plan.
   - If the task is the full annotated semantic loop, also verify `semantic_loop_provenance.json`, `semantic_leakage_audit.json`, `question_contracts.jsonl`, `question_relation_graph.json`, `blind_full_chain_reviews.jsonl`, `contrastive_pair_reviews.jsonl`, `accepted_guardrail_bank.yaml`, `semantic_signal_candidates.csv`, `semantic_model_comparison.csv`, `leave_one_dataset_out_semantic_results.csv`, `semantic_validation_report.md`, `semantic_false_negatives.csv`, `semantic_false_positives.csv`, `residual_loop_changes.md`, and `semantic_methodology_freeze_manifest.json`. Confirm that all labeled rows have blind reviews and that every rejected row has matched accepted controls before promoting any signal.
   - If a client annotated workbook exists for benchmark work, verify that `client_annotation_validation.md`, `.csv`, and `_summary.json` exist and that their blocking findings are resolved or named plainly.
   - Verify that the dashboard renders without unreadable tables or overlapping prose.
   - Assign a terminal state from `references/dataset-cycle-loop.md`: success, clean no-op, blocked, approval required, or no-progress stop. Do not treat missing artifacts, unreconciled counts, unreadable dashboards, or errors as success.
   - Preview the main artifacts before responding to the user. Inspect the findings essay, positive insights report, escalation packet, internal signal bank, dashboard, visual findings report, discard set, final judgment table, kept synthesis, next-pass inventory, demographic summary, and deep semantic sample.
   - The final assistant response must be client-facing and email-ready. It should read as one cohesive review system, using language such as "we discovered," "we reviewed," and "we recommend." Do not describe the close-out as tool execution or as "the agent final pass."
   - The final assistant response must include a clear narrative of core discoveries, core discard recommendations with respondent keys and row or cell-level citations when available, positive findings and strong-response examples, key statistics from the run, brief descriptions of important artifacts, a verified-artifact statement, and the next-pass signals.
13. Before starting the next run, read the prior `agent_findings_essay.md`, `agent_escalation_packet.md`, `next_pass_signal_inventory.csv`, and `internal_quality_signal_bank.md`. Decide which signals can be added to the first-pass context, which signals need PM examples, which signals are false-positive guardrails, and which signals should remain agent-only. Keep cycling through new datasets and reruns until the row-count gates, artifact gates, dashboard checks, prose checks, and escalation reconciliation checks pass without defects.
   - Each cycle should record one to five compact learning records in the signal bank or workflow improvement log when the run changes future behavior. Do not write activity logs. Write only lessons that change the next pass.

## Generated Criteria And Scoring Policy

Do not provide fixed weights or closed criteria ahead of time. The methodology defines discovery procedures, evidence standards, evaluation requirements, and escalation paths. The run generates candidate criteria and provisional weights from the data.

Each run must produce:

- generated candidate criteria with tags, source columns, and rationale
- Datamap-derived field roles, question-chain context, full response-chain context, and focused semantic-chain context for final semantic review
- an agent-authored question-set authenticity map that explains each major question family before scoring or final review
- a Question Contract and question-relation graph before respondent scoring
- blind authenticity tiering and label-aware contrast when labels exist
- semantic signal expansion notes that explain how each raw discovery was weighted after agent review
- independent full-response audit of every source row, not just sampled or first-pass rows
- agent-authored row semantic judgment for every source row, not just sampled or first-pass rows
- provisional weights with support counts and rationale
- generated action thresholds
- second-pass disposition and discard-only escalation routing
- agent-generated semantic annotations for escalations and survivor decisions
- prose analyst readout that blends pattern evidence with full-chain agent reasoning
- cited agent findings essay
- final escalation packet, even when the discard set is empty
- internal signal bank for comments, criteria, false positives, and next-run learning
- decision trail for non-obvious choices in long or high-stakes runs
- next-pass signal inventory from agent-reviewed rows
- deep semantic review sample for a subset of reviewed rows
- evaluation metrics when adjudicated labels exist

Weights are trial artifacts, not policy. They should evolve from discoveries, semantic expansion, PM findings, adjudicated examples, accepted-row guardrails, and feedback. Do not auto-remove respondents from this skill alone. Output discard-candidate escalations with evidence and row-level justifications only after a second pass has found converging discard evidence. Treat scripted scoring as the evidence substrate, not the reader-facing judgment.

Every generated weight must be explainable. A higher weight needs a stronger reason than "the check fired." It should say why the question context, timing context, semantic chain, and false-positive guardrails make the evidence more or less probative. If the agent cannot explain the weight after reading the response chain, keep the signal as review routing.

## Research-Grade Analysis Standard

The agent should reason like a careful investigator. It should collect evidence first, then decide what story the evidence supports.

For each major finding, the agent should state:

- what was observed
- where it was observed
- what alternate explanation could fit
- what evidence supports the final interpretation
- what remains uncertain
- what the next pass should do with the lesson

Do not over-polish uncertainty into confidence. If a claim is indirect, say that it appears likely or needs PM review. If a source was unavailable, name the gap.

The final discard call should be stronger than the initial score. It should reflect the score, the Datamap, the response chain, internal comments, counterevidence, and the agent's own semantic read.

The row judgment should be stronger than the first-pass feature vector. It should explain what the row means after the agent has read the answer chain. It should not say only that a criterion fired.

Use the five-tier routing model from `references/authenticity-first-calibration.md`. Only Tier 5, Exclude candidate, is the discard set. Tiers 2-4 are review or protection surfaces, not exclusion.

Definitions of done must be checkable and demanding. A phase is not done because a script finished. It is done when the expected artifact exists, the count or citation gate passes, and the agent has read the material needed to make the next decision.

## Majority Skill, Minority Template

The workflow should be mostly agent judgment and writing, with a small fixed artifact contract. Required files, row counts, citations, and reconciliation checks are fixed. The analysis inside those artifacts is not a form to fill in.

Use templates only to define:

- which artifacts must exist
- the minimum evidence a reviewer needs
- which local tables or rows must be cited
- which delivery gates block completion

Do not use templates to replace the analyst's own reading. The agent must read the workbook, Datamap, field-role map, full response chains, independent audit, judgment table, demographic summary, signal bank, and prior-run lessons, then write the findings in natural prose. If a report sounds like fields stitched into paragraphs, rewrite it before delivery.

Each final run should include at least one discovery that was not prewritten in a template. It may be a field-role discovery, a false-positive guardrail, a respondent-chain pattern, a demographic or aggregate interpretation, a survey-design weakness, or a next-pass signal. If no new discovery exists, say so and explain what evidence made the run straightforward.

## Evidence Rules

Every flag must include:

- criterion id
- generated tags
- respondent metadata such as respondent id, source/vendor, status, timestamp, IP, qtime, geography, and quota markers when present
- demographic summary outputs for `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, and `qPolitics` when present
- source column or open-end field
- observed value
- generated/provisional point contribution when available
- explanation suitable for PM review
- rationale for the generated criterion or generated weight
- second-pass disposition: `discard_candidate`, `keep_with_recommendation`, or `keep_no_issue`
- discard rationale when the response should be decisively reviewed for removal
- survivor rationale and survey-question-strengthening recommendation when the row is kept
- agent semantic analysis that explains the judgment in fluent business language
- agent linguistic fluency assessment for any open-end or text-quality concern
- agent trust rationale explaining why the reader should accept the recommendation without redoing the analysis
- agent recommended next step

If the workbook already contains `Respondent Flags` but lacks raw helper columns, use those flags only as inherited evidence and mark the source as `existing_review_field`.

Internal comments and criteria must be cited separately from raw respondent evidence. They can explain what to look for, but they do not prove that a row is bad. If an internal note changes a decision, the agent must say how it applied to the actual response chain.

## Agent Annotation Layer

Generate annotations as a separate Opulent judgment pass after scoring and second-pass disposition. The annotation pass should use the score, tags, source evidence, respondent metadata, and open-ended text context, but it should not simply restate deterministic criteria.

The final review layer must act as a critic and analyst, not as a rubber stamp for criteria. Static checks create the case file. The agent then reads the full response chain, looks for benign explanations, expressive language, recoverable context, and semantic patterns that static rules cannot see, and only then decides whether discard is justified. For example, repeated characters or punctuation should not trigger discard when the full answer is an enthusiastic or spirited but meaningful response.

The workflow fails if it stops at scripted execution. Scores, flags, tables, and charts are only the evidence substrate. The deliverable must include prose analysis that explains the patterns, gives examples, challenges weak discard calls, and teaches the next pass what should change.

For each row with evidence, especially every possible `discard_candidate`, write:

- `agent_semantic_analysis`: a concise but rich judgment about what the evidence means in context.
- `agent_linguistic_fluency_assessment`: whether the respondent's language is fluent, generic, evasive, off-topic, low-information, or otherwise suspicious, without treating polish alone as quality.
- `agent_trust_rationale`: why the recommendation is defensible from source evidence and not just a rigid score.
- `agent_recommended_next_step`: what the PM or Data Quality Lead should do next.
- review fields that show whether early screening recommended discard, what counterevidence the agent found, and what semantic basis remains for discard.

Escalation annotations must give readers enough trust and depth that they can adjudicate the discard decision directly. They should not force the reader to reconstruct the reasoning from flags and points.

Semantic relevance and linguistic-quality calls must be made by the Opulent agent, not solved as rigid keyword matching in the scoring script. The script may surface candidate evidence such as a possible topic mismatch, but the agent must read the response in survey context and decide whether the text is actually off-topic, evasive, generic, low-information, or acceptable. A row should not remain a discard candidate when the only semantic problem is a brittle keyword miss.

Before finalizing any text-driven discard:

1. Read the stitched full response chain, including the prompt context for each answered field when available.
2. Treat the criteria as the initial case file, not the final decision.
3. Look for counterevidence, such as substantive answers elsewhere in the chain, enthusiastic or expressive wording, recoverable role context, or answers that are short but valid for the question.
4. Decide whether a reasonable PM would treat the answer as substantively off-topic or merely awkward/variant phrasing.
5. Check whether the text concern independently strengthens another quality signal, such as straightlining or speed.
6. Downgrade rows where semantic evidence is plausible or only weakly ambiguous; keep them with a survey-question recommendation instead.
7. Escalate only rows where the agent can explain, in fluent business language, why the response should be discarded after critic verification.

After finalizing discard decisions, write the escalation packet. The packet is complete only when a PM can read it and know which rows to review for exclusion, which rows survived, which criteria shaped the choice, and what remains uncertain.

## Raw-Data Discovery

On unannotated files, the script can score:

- raw qtime under four minutes
- duplicate IP address
- repeated matrix-grid answers
- obvious low-effort open ends
- optional topic mismatch when `--topic-keywords` is supplied

These scripted checks are routing evidence. Duplicate IP, device, or session
evidence is not enough by itself. Treat it as independent context unless
multiple supposedly independent respondents share the same weak chain pattern
or another quality signal. Speed-only evidence is review routing only when the
response chain is coherent. Keyword topic mismatch is review routing only until
the agent builds a project-specific semantic topic map from the Datamap,
accepted answers, and sampled open ends.

Straightlining is also routing evidence until expanded. The agent must compare the semantic similarity of the grid questions, inspect answer-time or page-time context when available, and decide whether the repeated pattern is a plausible uniform opinion, a survey-design artifact, review routing, or a contributor to discard. Repeated answers across similar questions should carry less weight than repeated answers across clearly different or reverse-coded concepts, especially when the open-ended chain shows authentic engagement.

Open-ended authenticity is the central semantic review surface. For each important open end, the agent must compare the answer to the prompt's requested evidence type and the respondent universe. Related-but-not-identical topics should be classified carefully. For example, a home-renovation prompt can validly include construction language when the answer clearly addresses renovation work, materials, contractors, costs, or homeowner decision-making. It becomes suspicious when the answer drifts into generic construction management, unrelated commercial projects, or polished business language with no lived respondent detail.

The script also discovers brand/preference/recommendation columns, but it reports those as candidate mappings unless a project-specific consistency rule exists. Do not infer brand inconsistency from column names alone.

The script also discovers fielding timestamp fields such as `date`, `start_date`, `start_time`, `started_at`, or comparable export fields. Odd-hour starts and concentrated start bursts are fielding-pattern evidence by default. Report them by supplier/source and timestamp bucket, but do not turn them into row-level discard evidence unless the final agent sees corroborating respondent-quality problems or the project has an approved fielding rule.

Client-annotated workbooks are the minimum benchmark, not the target. If a prior workbook contains columns such as `qtime_Under_4_Minutes`, brand inconsistency, grid straightline detail, open-end topic relevance, duplicate IP, `Respondent Flags`, `Respondent Score`, or `Recommended_Action`, autosurvey must preserve the equivalent audit surface and then surpass it with full-chain semantic reasoning, counterevidence, kept-row learning, survey-improvement guidance, and readable analyst prose. If a TFG cleaning-answer workbook contains `status`, treat `status = 3` as an accepted training label and `status = 5` as a rejected training label for methodology development. The workflow should learn why TFG rejected those respondents, not merely memorize the status field. The agent must read rejected and accepted response chains, derive the detection methodology, and then convert the learning into general signal questions that can run on blank Decipher workbooks. The blinded test dataset and all future blank datasets must be scored without using any hidden status label.

The larger method is question-set semantic detection. For each dataset, examine all question sets before scoring: screeners, role qualifiers, brand or product lists, matrices, allocation tasks, use-case prompts, other-specify fields, narrative open ends, and final feedback. For each set, decide what kind of real-world evidence the prompt asks for. Then look for the learned TFG authenticity failures inside that prompt context: abstract business language without lived detail, survey-meta answers, role mismatch, personal-home answers in professional contexts, generic project claims, sentence drift, bare lists where examples were required, off-domain professional claims, contradictions, copied chains, and low-attention behavior. These are reasoning lenses. They become discard evidence only after the agent reads the full response chain and accepted-row guardrails.

Status-labeled training is how the methodology improves. Use rejected rows to discover likely fabricated, bot-like, LLM-assisted, inattentive, contradictory, or unauthentic response patterns. Use accepted rows to discover guardrails that protect real respondents from over-flagging. A promoted signal must explain both sides before it affects blank Decipher scoring.

The discard rulebook must cover every TFG rejected row. Build `tfg_rejected_row_rule_ledger.csv` from all `status = 5` rows and `tfg_accepted_guardrail_ledger.csv` from all `status = 3` rows that fire any staged rule. Rows with no script-staged rule are not misses to hide. They are semantic-discovery rows that require full-chain reading and packet notes before the methodology is considered mature.

## Open-End Evaluation Method

For open-ended responses:

1. Filter gibberish/noise first with transparent evidence.
2. Evaluate effort, relevance, and completeness as separate dimensions.
3. Use semantic judgments as review evidence unless validated against PM labels.
4. Report the failure mode, not just an aggregate score.

Do not reward length alone. Do not treat a polished answer as high quality if it is generic, incomplete, or off-topic.

## Autonomous Candidate Analysis

Every raw-data run must produce a candidate-analysis inventory:

- analysis id
- status: `scorable`, `needs_mapping`, or `not_available`
- candidate columns or column groups
- why the analysis matters for respondent quality
- whether it can safely contribute points now

Every raw-data run must also produce generated candidate criteria:

- generated criterion id
- tags such as `speeding`, `straightlining`, `open_end`, `effort`, `relevance`, `technical_duplicate`, or `brand_consistency`
- source columns
- rationale
- status: `scorable`, `needs_context`, `needs_mapping`, or `needs_feedback`

Required analysis families:

- completion-time quality
- fielding start/date pattern quality
- duplicate technical signals
- matrix straightlining
- open-end quality
- brand consistency
- AI/open-end authenticity when helper fields exist

Do not stop after identifying obvious columns. Look for meaningful combinations, repeated patterns, and analyses that should be escalated for mapping before they can be scored.

## Escalation Policy

Generate severity thresholds from the generated provisional weights for the current dataset. Then run an extra pass on all possible escalations before routing:

- Escalate only rows where the extra pass determines `second_pass_decision = discard_candidate`.
- A discard candidate must have converging evidence strong enough that the operational question is whether it should be thrown out, not whether it needs more ordinary review.
- When one of the converging signals is semantic or linguistic, the Opulent agent must verify the semantic judgment before escalation. Do not let a keyword-based topic mismatch create a discard by itself.
- Rows that survive the extra pass must not be escalated. Mark them `keep_with_recommendation` when some evidence remains, explain why they were kept, and aggregate recommendations for strengthening survey questions so vague or easily gamed answers are forced into a clearer framework.
- Rows with no material evidence should be marked `keep_no_issue`.
- Wave-level supplier/source or question-design patterns can be reported separately, but they should not turn individual survivor rows into discard escalations.

## Kept Review Synthesis

After the agent creates the discard set, synthesize all review-tagged rows that were kept. This synthesis is required because retained review rows are the strongest signal for improving response quality without over-discarding respondents.

The synthesis must include:

- why each class of kept row survived
- counts and example respondent keys by pattern
- survey-question improvements, such as shorter grids, clearer prompts, concrete-example requirements, structured reason codes, reverse-coded items, and follow-up prompts
- survey parameter improvements, such as section-level timers, attention checks, soft warnings, minimum exposure requirements, and thresholds that remain review-only unless corroborated
- explicit guardrail that keyword mismatch is only a candidate review signal; semantic relevance must be agent-adjudicated

The synthesis must always preserve these reusable patterns when they appear:

- weak or unclear narrative answers: add PM examples of acceptable and unacceptable answers to the next first-pass context
- speed-only plausible answers: keep qtime as routing evidence and require another quality issue before discard
- short factor-list answers: create a minimum-depth rule only after PM decides whether short factor lists are acceptable
- semantic keyword false positives: build a project-specific topic map from the Datamap and sampled open ends before scoring topic mismatch
- survey-feedback wording: classify feedback about the survey or idea separately from substantive prompt answers
- direct non-response, repeated placeholder, or hostile text in a required high-value open end: route to exclusion review only when the full response chain does not recover useful context
- duplicate IP or device clusters: treat as context unless multiple supposedly independent rows share weak chains or converging quality signals

## ML Model — Trained on 11 Annotated Datasets

A Gradient Boosting classifier trained on 13,388 annotated respondents across 11 datasets provides a **risk ranking** that complements the agent rules. The model uses 156 features extracted from raw Excel files including: timing, open-end text statistics, matrix straightlining, supplier risk, LangAssess NLP scores, RD_Search metadata, cross-respondent duplicates, coded answer diversity, and client signal counts.

### Package Requirements

Install before first use:

```bash
pip3 install -r skills/cleaning-survey-quality/requirements.txt
```

Required packages: `openpyxl>=3.1.0`, `scikit-learn>=1.3.0`, `pandas>=2.0.0`, `numpy>=1.24.0`, `scipy>=1.10.0`, `xgboost>=2.0.0`, `lightgbm>=4.0.0`

### Training Data

The model is trained on annotated datasets in `/Users/jeremyalston/Perfect/Annnotated and test'/Data Sets with Cleaning Answer/`. Each file has a `status` column where `3 = accepted` and `5 = rejected`. The `markers` column contains quota outcomes (`bad:` = quota failure) and is **excluded from features** to prevent label leakage.

### Scripts

- `scripts/survey_quality_ml.py train` — Trains model with leave-one-dataset-out CV, saves to `models/survey_quality_model.pkl`
- `scripts/survey_quality_ml.py predict <xlsx_path>` — Predicts on unseen dataset
- `scripts/predict_quality.py <xlsx_path>` — Full prediction pipeline (ML + agent rules + semantic parsing)

### LODO Cross-Validation Results

The model achieves good **ranking** (AUC 0.48-0.88 across datasets) but **cannot set per-dataset discard thresholds** without calibration data. This is because reject rates vary from 5% to 44% across datasets, and the model's probability scores don't directly map to a fixed discard proportion.

**Key insight**: The model provides a risk ranking. The agent rules provide specific discard reasons. Together they produce a combined determination:
- **DISCARD (HIGH)**: Both ML and rules agree, OR TIER 1 signal present
- **DISCARD (MEDIUM)**: ML score above threshold + 0.1
- **REVIEW**: Either ML or rules flag the respondent
- **KEEP**: Neither flags

### How to Use

For a new unseen dataset:

```bash
# Full prediction with ML + agent rules
python3 skills/cleaning-survey-quality/scripts/predict_quality.py path/to/dataset.xlsx

# With custom threshold
python3 skills/cleaning-survey-quality/scripts/predict_quality.py path/to/dataset.xlsx --threshold 0.6
```

Output: CSV + NDJSON with per-respondent `determination`, `confidence`, `ml_score`, `rule_risk_score`, `combined_risk`, and `reasons`.

### Retraining

To retrain with new annotated data:

```bash
python3 skills/cleaning-survey-quality/scripts/survey_quality_ml.py train
```

This runs LODO CV on all 11 datasets, reports accuracy/precision/recall/F1 per dataset, and saves the final model trained on all data.

### What the ML Model Cannot Do

The model **cannot** achieve 90% accuracy on unseen datasets because:
1. Reject rates vary 5%-44% across datasets — no single threshold works
2. Client reject decisions use information not in the Excel files (panelist history, cross-survey patterns)
3. 8 of 11 datasets have AUC < 0.7, meaning the model barely ranks better than random

The model is best used as a **triage tool**: flag the top 10-20% highest-risk respondents for agent review, then let the agent rules + semantic parsing make the final determination.

## When To Read References

- Read `references/agentic-escalation-path.md` before running a full dataset from raw export to final discard choices.
- Read `references/decipher-blind-authenticity-review.md` before every normal Autosurvey run on a blank Decipher export.
- Read `references/authenticity-first-calibration.md` before using TFG status labels, client annotations, blind/label-aware calibration, five-tier routing, question contracts, or authenticity risk modeling.
- Read `references/semantic-signal-expansion.md` before changing or applying signal weighting, semantic similarity, straightlining, duration, open-end authenticity, or convergence logic.
- Read `references/progressive-chain-filtering.md` before running the full-chain review layer. It defines the four-layer progressive filtering order (Datamap mapping → per-field chain validity → observational signals → cross-population signals) and the agent reasoning each layer requires.
- Read `references/internal-signal-learning.md` when internal comments, PM notes, client annotations, prior criteria, prior findings essays, or recurring bad-response patterns are available.
- Read `references/rubric-seed.md` only as historical seed context, not as a source of fixed weights.
- Read `references/autonomous-discovery.md` before changing discovery behavior.
- Read `references/evaluation-methodology.md` before changing open-end evaluation, judge behavior, or validation metrics.
- Read `references/escalation-policy.md` before changing severity bands or owners.
- Read `references/project-context-template.md` when adapting the workflow to a specific client, survey program, or stakeholder group.
- Read `references/research-grounding.md` when changing the agent architecture or reporting/evolution loop.
- Read `references/combinatorial-discard-signal-profile.md` before applying client quality signals, signal tiering, supplier risk calibration, or per-dataset discard rate calibration. Contains the empirically validated signal tier system (TIER 1/2/3), pair/triple combination lift tables, supplier risk thresholds, and the refined discard decision rules derived from 13,388 annotated respondents across 11 datasets.
- Read `references/discard-exemplar-library.md` before making discard decisions on individual respondents. Contains calibrated exemplars of true positives (correctly discarded), false positives (wrongly discarded), true negatives (correctly kept), and false negatives (missed) from the Delta v2 annotated run. Includes the short open-end decision tree, demographic incoherence false-positive patterns, supplier-specific precision calibration, and the key lesson that TIER 3 signals + moderate-risk supplier should almost never trigger discard.
- Read `references/per-dataset-ml-signals.md` before analyzing a new dataset. Contains the strongest predictive signals for each of the 11 annotated datasets, extracted from per-dataset Gradient Boosting models. For each dataset: top 15 features by model importance, top 15 features by discrimination (Cohen's d), and auto-generated agent analysis notes. Use the most similar training dataset's top signals as priority checks when analyzing a new unseen dataset. The agent must independently verify each signal against the respondent's full answer chain — the ML signals tell you WHERE to look, not WHAT to conclude.
- Read `references/ml-pipeline-report.md` for the full report on the ML building process, the three-part pipeline (ML model plus agent rules plus semantic parsing), per-dataset train/test/val evaluation results, the leakage audit, the verified results (TFG Q1 at 96 percent and ODL at 97 percent with raw data), the self-improving loop design, and what the system can and cannot do. Written in plain style following the plain-writing skill rules.
- Read `references/generalizable-signals.md` before using any ML features in production. Lists the 7 verified generalizable signals (LangAssess readability, open-end text length, matrix straightlining, completion time, coded answer diversity, cross-respondent duplicates, Decipher review metadata) and the signals that need caution (supplier reject rate) or are excluded (markers, status, signal map sig_* features). Includes per-dataset signal priority table for analyzing new datasets.
