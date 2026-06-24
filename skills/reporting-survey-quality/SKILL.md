---
name: reporting-survey-quality
description: Creates PM-facing and client-facing survey quality reports from respondent scoring outputs. Use when summarizing data cleaning, explaining respondent flags, sharing scoring criteria with justifications, reporting quality trends, or preparing survey quality updates.
---

# Reporting Survey Quality

Use this skill after running `cleaning-survey-quality` or `evolving-survey-rubrics`.

Reports should make clear whether the run was:

- raw unannotated scoring
- candidate-vs-final rubric calibration
- final PM adjudication summary
- methodology development from annotated TFG workbooks

Before writing PM-facing or client-facing prose, read `../cleaning-survey-quality/references/client-terminology-glossary.md`. Define any client-specific shorthand, study fields, quality terms, PM terms, or internal criteria before using them in final artifacts.

When reporting a rerun, next-dataset pass, or workflow-hardening cycle, also read `../cleaning-survey-quality/references/dataset-cycle-loop.md`. Use it to state the terminal state, learning records, and next action without turning the client-facing report into an internal log.

Before writing final prose, read `references/analyst-prose-standard.md`. Use its standard for blending statistics, evidence, and readable explanation. This is an agent authoring requirement, not a script-generation requirement.

Before reporting labeled calibration, status comparisons, authenticity risk, five-tier routing, Question Contracts, or protective accepted-row evidence, read `../cleaning-survey-quality/references/authenticity-first-calibration.md`.

Before reporting annotated fraud-signal discovery, status-derived training, antisignals, blind-vs-label contrast, or a naive unannotated rerun plan, read `references/agentic-fraud-training-reporting.md`. These outputs must read as agentic fraud-model training reports, not generic quality summaries.

When reporting the full annotated semantic loop, keep client-process fit and authenticity risk separate. `client_reject_probability` describes how much a row resembles the client's labeled removals. `semantic_risk_score` describes what the blind full-chain reviewer saw about faithful human response behavior. The report must not say that either score alone proves bot activity, LLM use, or fraud.

Before explaining weights, semantic similarity, straightlining, speed, open-end authenticity, duplicate technical evidence, or convergence, read `../cleaning-survey-quality/references/semantic-signal-expansion.md`. Reports must show how raw checks became weighted evidence after agent reasoning.

## Report Shape

Produce three report layers:

1. PM operations report:
   - rows reviewed
   - rows by action
   - rows by severity, second-pass disposition, and discard-only escalation owner
   - candidate-analysis discovery inventory
   - rows by criterion
   - top evidence examples
   - rows needing review, ordered by severity
   - agent semantic annotations for escalations and high-value survivor examples
   - survivor rationales and aggregated survey-question strengthening recommendations
   - discard escalation queue containing only `discard_candidate` rows
   - rubric changes proposed or rejected
2. Client-facing quality summary:
   - concise description of the quality checks
   - aggregate counts only unless row detail is approved
   - defensible rationale for exclusions or review flags
   - note that final decisions remain human-adjudicated unless explicitly automated
   - when annotated status labels are used, explain that the system is learning client-rejection signals and authenticity-risk signals separately
3. Final visual review package:
   - publication-quality KPI dashboard for total responses, review-tagged rows, agent discard rows, and kept review rows
   - Recharts visualizations for action counts, second-pass disposition, agent review decisions, review themes, trend analysis, candidate clusters, stacked supplier outcomes, kept-review themes, and supplier/source concentrations
   - discovery section showing new candidate analyses, field groups, open-end fields, mapping needs, and unavailable analyses
   - Datamap-derived field-role section showing how the workflow mapped key fields before scoring
   - question-set authenticity map explaining each major question family, expected evidence type, fabricated-response risks, and accepted-row guardrails
   - Question Contract and question-relation graph explaining funnel, prerequisite, inverse, parallel, routing, numerical, temporal, and open/closed relationships
   - expanded scorer criteria section showing criterion id, tags, source columns, generated weight, support, decision role, rationale, and citation
   - response analysis criteria section showing which criteria actually fired, how many rows they touched, and how to read each criterion
   - semantic signal expansion section explaining how straightlining, speed, open-end, duplicate technical, and topic-fit discoveries were weighted after question-set review
   - blind authenticity tier and label-aware contrast section when labels exist
   - protective human evidence section showing accepted-row guardrails
   - fraud-signal training section showing learned signals, antisignals, blind misses, false-exclude risk, and transfer plan for naive unannotated reruns
   - dataset observations section with a cited list of semantic patterns, trend findings, supplier/source patterns, and survey-design implications
   - structured discard table with agent rationale and source evidence
   - full semantic decision table for all rows the agent investigated, including the number of fields reviewed from the stitched full response chain, early screening recommendation, full-chain counterevidence, and semantic discard basis
   - all-row semantic judgment artifact with one agent-authored decision per respondent, including the strongest concern, strongest protective evidence, and evidence-judge rationale
   - full-chain analyst readout that turns best and worst response-chain examples into readable prose, not just tables
   - positive findings report that explains strong retained responses, useful research findings, false-positive guardrails, and what good data looks like in the run
   - agent escalation packet that completes the PM review path, including discard rows, hard kept cases, uncertain cases, citations, and next actions
   - internal quality signal bank that captures comments, criteria, bad-response patterns, fabricated-response patterns, false positives, and next-run signal status
   - compact learning records for lessons that change the next dataset cycle
   - kept-review synthesis table with survey-question and parameter recommendations
   - next-pass signal inventory that states what should change before the next first-pass scoring run
   - deep semantic review sample that shows a subset of reviewed rows with the full reasoning and next-pass learning
   - independent full-response audit that checks every row, not just rows surfaced by the scorer
   - demographic and aggregate insights for `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, and `qPolitics` when present
   - deep findings memo that states the main findings, limits, discard recommendations, and workflow changes
   - annotated-workbook benchmark coverage: qtime, fielding start/date patterns, brand consistency, grid straightlining, open-end topic relevance, duplicate technical signals, respondent flags, respondent score, and recommended action
   - editorial figure captions, source notes, callouts, and artifact navigation for fast content review
   - artifact index linking the CSV, Markdown, and dashboard outputs

## Required Artifacts

Use outputs from `run_quality_loop.py`:

- `quality_report.md`
- `quality_summary.json`
- `row_scores.csv`
- `question_chain_map.csv`
- `question_set_authenticity_map.md`
- `question_contract.md`
- `question_relation_graph.csv`
- `semantic_signal_expansion_notes.md`
- `blind_authenticity_review_table.csv` when TFG status-labeled training workbooks are available
- `label_aware_contrast_table.csv` when TFG status-labeled training workbooks are available
- `authenticity_signal_family_lift.csv` when TFG status-labeled training workbooks are available
- `protective_human_evidence.md` when TFG status-labeled training workbooks are available
- `agentic_fraud_training_report.md` when TFG status-labeled training workbooks are available
- `frozen_input_manifest.json` when TFG status-labeled training workbooks are available
- `agentic_calibration_loop_report.md` when TFG status-labeled training workbooks are available
- `transferable_signal_specifications.csv` when TFG status-labeled training workbooks are available
- `control_match_backlog.csv` when TFG status-labeled training workbooks are available
- `demographic_summary.csv`
- `demographic_summary.md`
- `discovery_profiles.json`
- `generated_scoring_models.json`
- `methodology_config.json`
- `generated_criteria_catalog.csv`
- `respondent_review_table.csv`
- `response_criteria_evidence_table.csv`
- `agent_annotation_table.csv`
- `agent_review_judgment_table.csv`
- `agent_discard_set.csv`
- `agent_findings_essay.md`
- `agent_positive_insights_report.md`
- `agent_escalation_packet.md`
- `internal_quality_signal_bank.md`
- `agent_kept_review_synthesis.md`
- `agent_kept_review_synthesis_table.csv`
- `full_chain_analyst_readout.md`
- `full_chain_best_worst_examples.csv`
- `next_pass_signal_inventory.csv`
- `next_pass_signal_inventory.md`
- `next_pass_first_pass_config.json`
- `deep_semantic_review_sample.csv`
- `deep_semantic_review_sample.md`
- `independent_full_response_audit.csv`
- `independent_full_response_audit.md`
- `agent_row_semantic_judgments.csv` or `.jsonl`
- `client_annotation_validation.csv` when a client annotated workbook is available
- `client_annotation_validation_summary.json` when a client annotated workbook is available
- `client_annotation_validation.md` when a client annotated workbook is available
- `input_inventory.csv` when TFG status-labeled training workbooks are available
- `input_hashes.json` when TFG status-labeled training workbooks are available
- `split_manifest.json` when TFG status-labeled training workbooks are available
- `leakage_exclusions.json` when TFG status-labeled training workbooks are available
- `blinded_test_freeze_manifest.json` when a blinded test workbook is present
- `labeled_row_manifest.csv` when TFG status-labeled training workbooks are available
- `column_profile_discard_vs_accept.csv` when TFG status-labeled training workbooks are available
- `column_profile_discard_vs_accept.xlsx` when TFG status-labeled training workbooks are available
- `univariate_signal_ranking.csv` when TFG status-labeled training workbooks are available
- `cross_dataset_meta_signals.csv` when TFG status-labeled training workbooks are available
- `matched_case_pairs.parquet` or documented CSV and pickle fallback when no Parquet engine is installed
- `pairwise_interactions.csv` when TFG status-labeled training workbooks are available
- `higher_order_patterns.csv` when TFG status-labeled training workbooks are available
- `signal_bank.yaml` when TFG status-labeled training workbooks are available
- `validation_report.md` when TFG status-labeled training workbooks are available
- `residual_casebook.md` when TFG status-labeled training workbooks are available
- `annotated_authenticity_discovery_report.md` when TFG status-labeled training workbooks are available
- `status_dataset_summary.csv` when TFG status-labeled training workbooks are available
- `status_respondent_signal_map.csv` when TFG status-labeled training workbooks are available
- `status_signal_derivation.csv` when TFG status-labeled training workbooks are available
- `status_signal_derivation.md` when TFG status-labeled training workbooks are available
- `tfg_rejected_row_rule_ledger.csv` when TFG status-labeled training workbooks are available
- `tfg_rejected_semantic_discovery_backlog.csv` when TFG status-labeled training workbooks are available
- `tfg_accepted_guardrail_ledger.csv` when TFG status-labeled training workbooks are available
- `tfg_discard_rule_evidence.csv` when TFG status-labeled training workbooks are available
- `tfg_discard_rulebook_dataset_summary.csv` when TFG status-labeled training workbooks are available
- `tfg_discard_signal_rulebook.md` when TFG status-labeled training workbooks are available
- `status_semantic_reading_protocol.md` when TFG status-labeled training workbooks are available
- `semantic_review_packet_index.csv` when TFG status-labeled training workbooks are available
- `semantic_review_packets/` when TFG status-labeled training workbooks are available
- `semantic_packet_notes/` when TFG status-labeled training workbooks are available
- `semantic_loop_provenance.json` when the full annotated semantic loop is run
- `prior_run_verification.md` when the full annotated semantic loop is run
- `blinded_test_freeze_verification.json` when the full annotated semantic loop is run
- `semantic_leakage_audit.json` when the full annotated semantic loop is run
- `question_contracts.jsonl` when the full annotated semantic loop is run
- `question_contract_coverage.csv` when the full annotated semantic loop is run
- `seed_field_semantic_map.md` when the full annotated semantic loop is run
- `unresolved_question_contracts.csv` when the full annotated semantic loop is run
- `respondent_claim_graphs/` when the full annotated semantic loop is run
- `respondent_semantic_features.parquet` or documented CSV and pickle fallback when no Parquet engine is installed
- `claim_relation_evidence.csv` when the full annotated semantic loop is run
- `semantic_feature_coverage.csv` when the full annotated semantic loop is run
- `blind_full_chain_reviews.jsonl` when the full annotated semantic loop is run
- `blind_review_coverage.csv` when the full annotated semantic loop is run
- `contrastive_pair_reviews.jsonl` when the full annotated semantic loop is run
- `accepted_guardrail_casebook.jsonl` when the full annotated semantic loop is run
- `semantic_panel_disagreements.csv` when the full annotated semantic loop is run
- `full_chain_casebook.md` when the full annotated semantic loop is run
- `semantic_signal_candidates.csv` when the full annotated semantic loop is run
- `semantic_pairwise_interactions.csv` when the full annotated semantic loop is run
- `semantic_higher_order_patterns.csv` when the full annotated semantic loop is run
- `contrastive_proposition_clusters.jsonl` when the full annotated semantic loop is run
- `population_coordination_clusters.parquet` or documented CSV and pickle fallback when no Parquet engine is installed
- `accepted_counterexample_matrix.csv` when the full annotated semantic loop is run
- `accepted_guardrail_bank.yaml` when the full annotated semantic loop is run
- `accepted_guardrail_metrics.csv` when the full annotated semantic loop is run
- `guardrail_casebook.md` when the full annotated semantic loop is run
- `signal_after_guardrail_ablation.csv` when the full annotated semantic loop is run
- `semantic_model_comparison.csv` when the full annotated semantic loop is run
- `leave_one_dataset_out_semantic_results.csv` when the full annotated semantic loop is run
- `calibration_results.csv` when the full annotated semantic loop is run
- `family_ablation_results.csv` when the full annotated semantic loop is run
- `tier_volume_and_precision.csv` when the full annotated semantic loop is run
- `signal_promotion_decisions.yaml` when the full annotated semantic loop is run
- `semantic_validation_report.md` when the full annotated semantic loop is run
- `semantic_false_negatives.csv` when the full annotated semantic loop is run
- `semantic_false_positives.csv` when the full annotated semantic loop is run
- `semantic_disagreement_cases.csv` when the full annotated semantic loop is run
- `residual_clusters.jsonl` when the full annotated semantic loop is run
- `residual_loop_changes.md` when the full annotated semantic loop is run
- `unexplained_client_decisions.csv` when the full annotated semantic loop is run
- `semantic_methodology_freeze_manifest.json` when the full annotated semantic loop is run
- `deep_findings_analysis.md`
- `workflow_improvement_log.md`
- `respondent_review_table.md`

Build PM and client briefs:

```bash
python3 scripts/build_quality_brief.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

Build next-pass learning artifacts:

```bash
python3 scripts/build_next_pass_review_artifacts.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

Build the deep findings memo:

```bash
python3 scripts/build_independent_full_response_audit.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

Build agent review artifacts from the scorer and independent audit:

```bash
python3 scripts/build_agent_review_artifacts.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

Build the full-chain analyst readout:

```bash
python3 scripts/build_full_chain_analyst_readout.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

Build the positive findings report:

```bash
python3 scripts/build_positive_insights_report.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

When a client annotated workbook exists, build the client-annotation validation report before the final essay and dashboard:

```bash
python3 scripts/build_client_annotation_validation.py \
  --run-dir /path/to/outputs/rubric-evolution-seed \
  --client-workbook /path/to/client_annotated_final_review.xlsx
```

When TFG status-labeled training workbooks exist, build the supervised status signal derivation before the next scoring pass:

```bash
python3 scripts/build_annotated_authenticity_discovery.py \
  --annotated-dir /path/to/Data-Sets-with-Cleaning-Answer \
  --client-root /path/to/client-package-root \
  --blinded-workbook /path/to/blinded-test-workbook.xlsx \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration/authenticity_discovery_loop

python3 scripts/build_status_signal_derivation.py \
  --input /path/to/status_labeled_workbooks_or_zip \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration

python3 scripts/build_semantic_authenticity_loop.py \
  --annotated-dir /path/to/Data-Sets-with-Cleaning-Answer \
  --client-root /path/to/client-package-root \
  --prior-run-dir /path/to/private_outputs/status-ground-truth-calibration/authenticity_discovery_loop \
  --blinded-workbook /path/to/blinded-test-workbook.xlsx \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration/authenticity_semantic_loop
```

Build the complete rejected-row rulebook:

```bash
python3 scripts/build_tfg_discard_rulebook.py \
  --input /path/to/status_labeled_workbooks_or_zip \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration
```

Then build semantic review packets for literal row reading:

```bash
python3 scripts/build_status_semantic_review_packets.py \
  --input /path/to/status_labeled_workbooks_or_zip \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration
```

Then freeze the calibration loop and write transferable signal specifications:

```bash
python3 scripts/build_agentic_calibration_loop.py \
  --annotated-input /path/to/status_labeled_workbooks_or_zip \
  --calibration-dir /path/to/private_outputs/status-ground-truth-calibration \
  --heldout-input /path/to/blinded_holdout.xlsx
```

The status derivation and rulebook must iterate every labeled row. Read all `status = 5` rows to derive likely fabricated, bot-like, LLM-assisted, inattentive, or unauthentic response signals. Read all `status = 3` rows to derive stronger false-positive guardrails. Do not treat script-staged signals as final truth. The final signal bank must explain each promoted signal in plain language, give supporting examples, give accepted-row counterexamples, and say whether the signal affects review routing, final discard escalation, or only the analyst report.

The annotated authenticity discovery loop is the first mandatory pass for status-labeled corpora. It must inventory and hash inputs, freeze the blinded workbook without inspecting respondent values, reconcile every status-3 and status-5 row, exclude leakage fields, profile every non-leaking comparable column, write matched accepted controls, search pairwise and higher-order patterns, fit leave-one-dataset-out validation, and write a residual casebook. Treat a weak transfer score after leakage removal as a finding. It means the next loop needs deeper question-aware semantic features before the blinded workbook is scored.

Leakage inspection is mandatory. Exclude direct and indirect helper fields before any ranking or model claim. This includes `status`, marker or quota fields, client action fields, final decision fields, review helper fields, condition assignment fields, no-answer helper fields, QC helper fields, channel tracking fields, token fields, and any formula, comment, hidden sheet, or formatting that reveals a cleaning outcome. If a high-performing signal uses one of these fields, quarantine it and rerun the profile.

The semantic packet workflow is mandatory when the goal is to build the detection methodology. The agent must read the packets across multiple turns if needed, write packet notes, and then update the internal signal bank and next-pass configuration. This is how autosurvey builds detection muscle for unannotated datasets. The labeled `status` field is training evidence only. It must not be required or available when scoring the blinded or future unannotated files.

The agentic calibration loop report is mandatory before scoring the blinded dataset. It must freeze inputs, name held-out files, summarize blind-vs-label contrast, list transferable signal specifications, and state which residual errors still need review. If stable residual errors remain, continue methodology development instead of scoring the blinded file.

Before using status labels in the final interpretation, report the blind-then-contrast sequence. The report must say what the review found with `status` and client flags hidden, then what changed after the label-aware contrast. Do not reverse-engineer explanations from `status = 5`. Say plainly when a client rejection appears to reflect authenticity risk, ordinary quality risk, routing or survey-design ambiguity, or a client-only rule not yet learned.

When the run uses annotated `status = 3/5` files, write `agentic_fraud_training_report.md`. This is the main training narrative. It should explain that Autosurvey is using rejected rows as the client-removal corpus and accepted rows as the antisignal corpus, then show which evidence families and interactions are likely to transfer to unannotated data. It must include blind-vs-label contrast, false-exclude risk, accepted-row protective evidence, blind misses, and the detector upgrade plan before the naive rerun.

Before the final essay or dashboard, write `question_set_authenticity_map.md` in natural language. Do not delegate this to a script-generated table. The map should explain every major survey section, what evidence the question asks for, what authentic answers can look like, what fabricated or unqualified answers can look like, and which accepted-row guardrails prevent over-discarding. Use the map to interpret TFG-derived signals as semantic questions. For example, ask whether a polished answer lacks lived detail, whether a survey-meta answer replaced a personal answer, whether a personal-home example violates a professional respondent universe, whether a coherent answer belongs to the wrong domain, and whether a list is acceptable for that prompt.

Also write `question_contract.md` and `question_relation_graph.csv`. The contract should explain the intended respondent universe, valid answer types, timing burden, routing prerequisites, brand or product funnels, and protective human evidence. The graph should classify relationships as parallel, inverse, prerequisite, funnel progression, mutually exclusive, temporal, numerical, routing, or open/closed contradiction.

Also write `semantic_signal_expansion_notes.md`. This is an agent-authored evidence-weighting memo, not a script output. It should explain how each major discovery changed after semantic review. Straightlining notes must discuss question similarity and answer-time context when available. Speed notes must discuss page, section, question, or total duration context when available. Open-end notes must discuss prompt fit, respondent-universe fit, semantic authenticity, and accepted-row guardrails. Duplicate technical notes must distinguish one repeated technical fact from independent repeated response chains. Topic-fit notes must distinguish direct fit, adjacent fit, wrong universe, survey meta-answer, generic filler, and semantic drift.

Then do the findings essay pass before the dashboard is built. This is not a rote script step and it is not a form to fill out. Read the Datamap field-role mapping, discovery profile, demographic summary, scorer criteria, independent full-response audit, full-chain analyst readout, deep semantic sample, final judgment table, kept review synthesis, and next-pass signal inventory. Also read the prior run's findings essay, escalation packet, internal signal bank, and next-pass inventory when they exist, so this run can test whether earlier signals improved or failed. Then write:

- `agent_findings_essay.md`: a natural prose essay with citations. It should explain what we discovered in the run, what the field-role mapping changed, what the best and worst response chains reveal, what the final discard or keep recommendations mean, what demographic and aggregate context matters, what should change in the next pass, and where the workflow should challenge itself.
- `agent_positive_insights_report.md`: a companion prose report that highlights strong retained responses, positive research signals, demographic and aggregate insights, false-positive guardrails, and why the review preserved good data. A script can seed this report from artifacts, but the agent must read it, revise it when the run needs more nuance, and make sure it complements the discard-focused escalation packet.

The essay can have whatever sections best explain the run. Do not force it into fixed row-note fields. Scripts may carry this prose into HTML, but scripts must not be treated as the author of the reasoning. The prose should explain the exploration, field-role discoveries, response-chain reading, discard recommendations, kept-row lessons, demographic and aggregate context, and any correction cycles where the first pass was too broad or too narrow. If this essay is missing, the run is not ready for client or PM review.

Use a majority skill, minority template standard. The required artifact list, citation requirements, and proof gates are fixed. The content must be authored from the run evidence. A report fails review if it only fills slots such as theme, score, or next action without explaining what the evidence means and why the recommendation is trustworthy.

Then:

```bash
python3 scripts/build_deep_findings_analysis.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

Build final dashboard and visual findings report:

```bash
python3 scripts/build_visual_dashboard.py \
  --run-dir /path/to/outputs/rubric-evolution-seed
```

## Reporting Rules

- Explain criteria in business language, not model language.
- Use statistics inside analyst prose. State what the count means before showing detailed tables. Do not dump rows, criteria, or parameter fields as the report itself.
- Explain that criteria and provisional weights were generated from discovery, trial evidence, findings, and feedback.
- Explain how each important weight was derived from semantic expansion, not only from a raw scripted flag. A report should say why the evidence became stronger, weaker, or stayed review-only after the agent checked question similarity, timing, open-ended authenticity, chain coherence, and accepted-row guardrails.
- Include justifications for each scoring criterion.
- Include respondent metadata in review tables wherever source fields are available.
- Include the stitched question chain and full response chain before final semantic review. The final agent judgment table must carry `response_chain_field_count`, `full_response_chain`, `semantic_review_chain_field_count`, and `semantic_review_chain`. The final discard decision must be based on those chains plus the surfaced evidence.
- The independent full-response audit is a blocking artifact. It must contain one row per source respondent. Before publishing, reconcile it against the source row count, `row_scores.csv`, and `respondent_review_table.csv`. If any count differs, stop and fix the run.
- Read the independent full-response audit as a whole-population review surface. The final report must say what the all-row audit found among unflagged rows, not only what happened to the first-pass review queue.
- The all-row semantic judgment artifact is also blocking. It must contain one agent-authored judgment per source respondent. If the file mostly repeats scores, rule names, or the same sentence with different ids, return to row review before writing the client-facing report.
- Parse the Datamap into field roles before scoring or reporting. The final report should show that the workflow understood the role of `qcoe1`, `q9`, `q10`, `q32`, `q43`, and `outro` when present, and should also identify project-specific equivalents such as `qIndustry`, `CLASSIFY`, buyer-role fields, product-involvement fields, and use-case fields.
- Examine all question sets and report the authenticity logic for each one before presenting discard findings. This includes screeners, role qualifiers, brand or product lists, matrices, allocation tasks, use-case prompts, other-specify fields, narrative open ends, final feedback, demographics, timing, supplier fields, and technical identifiers.
- Build and report a project-specific topic and answer map before scoring text relevance or answer depth. If the prompt asks for a physical item, location, product use, brand, simple reason, or short factor, the report must explain how short valid answers were protected from over-discard.
- Include demographic and aggregate insights from source data. These are report context, not quality-discard evidence by themselves.
- Treat client-annotated Excel review files as the minimum audit surface. The report should match their practical columns and counts where relevant, then go further with prose analysis, chain-level semantic judgment, full-chain counterevidence, kept-row learning, and next-pass signal updates.
- Treat TFG `status` labels as observed client outcomes for methodology development when they are present. `status = 3` means TFG accepted the respondent. `status = 5` means TFG rejected the respondent because of quality or authenticity concerns. Reports must state the status counts, the rejected rate, the strongest rejection signals, the strongest accepted-row guardrails, and what should be tested on the blinded dataset.
- Separately report client rejection probability and fabrication/authenticity risk. Do not call a respondent fraudulent only because `status = 5`.
- Frame annotated-set outputs as model-training artifacts, not normal Autosurvey runtime outputs. The main question is what the rejected set teaches, what the accepted set protects, and how those lessons transfer to blank Decipher detection.
- For blank Decipher runs, do not mention `status = 3`, `status = 5`, or hidden client outcomes in row-level decisions. Report the learned signal questions applied to the current workbook, the current workbook evidence, the final Tier 5 rows, and the protected rows.
- Keep the five tiers separated. Only Tier 5 is the discard set. Report Tiers 2-4 as protective notes or review volume, not exclusion.
- When a client annotated workbook exists, treat it as a baseline validation set. Build `client_annotation_validation.md` and read it before finalizing. The run must report client action counts, client flag-family counts, autosurvey coverage by client signal family, autosurvey rows the client marked `No concerns`, autosurvey discard rows the client kept, and any artifact count contradictions.
- When TFG status labels exist, the report must separately show status-5 recall and status-3 false-positive risk. A run cannot claim success because it finds a small high-confidence discard set if it misses most TFG-rejected rows. It also cannot claim success by catching many status-5 rows if it sweeps in large groups of status-3 respondents without a clear guardrail.
- Do not call a benchmark run complete when the final reports disagree with the discard set, when client `Review closely` rows were not semantically reviewed, or when a client signal family has low coverage without an analyst explanation and a next-pass fix.
- Always report fielding start/date/timestamp discoveries when the source file contains them. Odd-hour starts and start bursts are fielding-context findings unless corroborating evidence or project rules make them row-level evidence.
- Treat scoring criteria as the initial case file. The final review must act as a critic and analyst that can supersede static checks when the full chain gives a meaningful semantic explanation.
- Treat straightlining as a semantic and timing problem, not only a repeated-answer problem. Report whether repeated answers occurred across similar or dissimilar items, whether answer-time or page-time evidence made the behavior plausible, and whether open-ended responses supported or weakened the concern.
- Treat open ends as the primary authenticity readout. Reports must explain whether the respondent answered the requested evidence type and belonged to the expected respondent universe. Related topic language should not be penalized when the chain shows a real answer; polished but generic or off-domain language should not be rescued by fluency alone.
- Treat the dashboard and final report as client-facing research products, not formatted log output. The final prose must synthesize the exploration, field-role mapping, response chains, early screening signals, counterevidence, demographics, and next-pass learning before publishing.
- Do not let scripted string assembly substitute for analysis. A script can assemble charts, ledgers, citations, and HTML, but the deciding prose must come from `agent_findings_essay.md`, written after studying the run materials.
- Do not let the run become discard-only. The final package must also include `agent_positive_insights_report.md`, with strong retained response chains, useful aggregate findings, guardrails that protected good data, and next-pass learning that improves quality without over-excluding real respondents.
- Write `agent_escalation_packet.md` as the complete operational answer. It must say which rows should be reviewed for exclusion, which suspicious rows were kept, which internal comments or criteria shaped the decision, what evidence was decisive, what evidence was inconclusive, and what the PM should do next. If no rows should be discarded, the packet must still explain why.
- Write `internal_quality_signal_bank.md` as an internal learning artifact. It should preserve useful comments, criteria, false-positive guardrails, and recurring bad-response or fabricated-response patterns for later runs. It is not client copy.
- Show full-chain counterevidence and semantic discard basis for final decisions. A row should not be discarded only because an early screening check fired.
- Produce readable prose analysis for the best and worst full response chains. The prose must explain what the agent saw, why strong rows are strong, why bad rows remain bad after full-chain review, and where the workflow should challenge itself.
- Do not treat generated tables, charts, or flags as the final communication layer. They support analysis, but the report must include agent-written interpretation for the human reviewer.
- Treat templates as scaffolding, not the product. The final essay, escalation packet, positive insights report, and dashboard prose must include fresh run-specific insight, client terminology definitions where needed, and citations to the evidence that produced each claim.
- Treat TFG-derived semantic criteria as reusable detection questions, not fixed prose or keyword recipes. The report should explain how those questions changed the review of this dataset's actual question sets.
- Report every promoted signal with its weight basis: prompt fit, question similarity, time plausibility, semantic authenticity, chain coherence, independence, recurrence, accepted guardrail, and survey-design ambiguity. If the basis is weak, say it remains review-only.
- Aggregate correlated evidence within families before reporting convergence. Do not present many related straightlining or timing metrics as independent reasons.
- Treat AI-assistance concern as weak supporting evidence only. Polished prose, formality, low typo rate, or em dashes must never independently determine exclusion.
- Explicitly report broad or failed signals. If a signal catches many status-5 rows but also sweeps many status-3 rows, call it an overbroad training signal and document the required antisignal guardrail.
- Report blind misses as the highest-value source of new semantic rules. A status-5 row that looked acceptable blind should trigger careful reading, not automatic rationalization.
- Treat every script-produced prose block as draft evidence, not final copy. Scripts may stage counts, examples, citations, charts, and tables. The agent must author or rewrite the final findings essay, positive report, escalation packet, dashboard prose, and visual findings report after reading the run evidence.
- Apply the authorship rule to every PM-facing or client-facing artifact. No artifact passes because a script wrote a file. It passes only after the agent reads the evidence, decides the narrative, verifies the citations, and rewrites generated text into interpretable research prose.
- Do not solve poor prose by teaching scripts to fill nicer templates. The repair is agent authoring: read the artifacts, decide what the evidence means, write the explanation, and cite the supporting table or row.
- Do not solve weak row review by adding more static checks. The repair is agent reading: inspect the full chain, compare the row with accepted controls, decide what the semantic boundary is, and write the judgment.
- When maintaining scripts, keep them focused on evidence staging and display mechanics. They can name what evidence needs explanation. They must not hard-code final client conclusions beyond basic run counts and artifact availability.
- Never expose raw parameter strings in client-facing prose, such as `best_score=`, `risk=`, `narrative=`, `support_rate=`, `keep_no_issue_from_independent_audit`, or raw source-column dumps. Translate them into plain analyst language before delivery.
- Dense tables are allowed only after a short readout explains what the table proves and how the reviewer should use it.
- Keep long reasoning out of wide tables. Tables may summarize identifiers, decisions, themes, scores, and next action. Full explanations, response-chain interpretation, and workflow learning must appear in natural prose sections or linked Markdown artifacts.
- Never dump a raw stitched response chain into a dashboard card or visible wide table. Convert it into a focused chain read, then explain why those answers support discard, retention, calibration, or a next-pass rule.
- The dashboard must remain readable at desktop and mobile widths. If a section contains long prose, use publication prose blocks or cards with stable widths, not narrow table cells that force one-character wrapping.
- Include one row per triggered criterion in the evidence table so PMs can audit all criteria, observations, explanations, second-pass disposition, agent semantic analysis, survivor/discard rationale, and rationales.
- Treat annotation text as an Opulent semantic-judgment layer, not a deterministic score explanation. Reports should show what the response pattern means and why the recommendation is trustworthy.
- For raw-data runs, include discovery notes from `discovery_profiles.json`.
- Distinguish discovery findings, scoring decisions, evaluation results, and escalation routing.
- For calibration runs, include agreement metrics and explain failure modes rather than reporting only match rate.
- Include escalation ownership only for rows marked `discard_candidate` after second-pass analysis.
- For discard candidates, include rich semantic analysis, linguistic fluency assessment, and trust rationale; do not make readers reconstruct the judgment from flags and scores.
- If semantic relevance or linguistic quality contributes to discard, report the Opulent agent's adjudication of the text. Do not present keyword mismatch output as the final semantic decision.
- For rows that survive the extra pass, include why they were kept and aggregate recommendations for strengthening survey questions so vague or gameable answers are forced into a clearer framework.
- For every run, convert kept review rows into critical next-pass signals. Say which signals should be added to first-pass scoring, which signals need project mapping, and which signals must stay review-only.
- Always include these kept-row patterns in the next-pass workflow when they appear: weak or unclear narrative answers, speed-only plausible answers, short factor-list answers, semantic keyword false positives, and survey-feedback wording. Each pattern must produce both a survey-question or parameter recommendation and a suggested quality parameter.
- Return a subset of reviewed rows with deeper semantic analysis. Include the final decision, raw evidence, language assessment, trust basis, next action, and the learning that should change the next pass.
- Independently audit all source rows before final delivery. Compare the full-row audit against the scorer and agent review outputs. If the audit finds a missed possible discard, update the agent judgment artifacts and explain the fix.
- Treat all-row audit findings as a way to challenge the scoring pass. Call out rows or patterns the first pass missed, rows the first pass over-reviewed, and signals that should be promoted, demoted, or held for PM examples.
- Reconcile the escalation packet against the agent discard set and agent judgment table. Every discard row must appear in the packet. Every packet discard must appear in the discard set. Any mismatch blocks delivery until the agent resolves it.
- Reconcile all final prose artifacts against the discard set. If one artifact says the discard set is empty and another artifact or CSV contains discard rows, block delivery and rewrite the inconsistent artifacts.
- Reconcile the internal signal bank against the findings essay and next-pass signal inventory. The signal bank should keep long-term internal learning. The next-pass inventory should say what changes before the next run.
- Do not finalize `agent_review_judgment_table.csv` from an audit that lacks `full_response_chain`. Rerun the independent full-response audit first.
- Put the highest-severity rows before lower-priority review examples.
- Do not expose raw open-end responses externally unless approved.
- Do not claim respondents are fraudulent solely because of AI-likelihood scores.
- Separate "kept with recommendation," "discard candidate," and "disqualified."
- When labels match final PM review, say the current generated scoring model is stable for that evaluation set, not universally final.
- Always end with a final visual review package. The final dashboard should prefer agent judgment artifacts over raw scoring artifacts when both exist, because the agent judgment table is the source of truth for discard decisions.
- Use charts and dashboards to make review easy: counts, proportions, themes, supplier/source concentrations, and final action queues should be scannable without reopening CSV files.
- Design final artifacts as executive research publications, not internal debug pages. Use open-design-style craft: clear hierarchy, strong whitespace, restrained color, precise figure labels, readable tables, and narrative callouts that let a PM understand the decision logic at a glance.
- Prefer Recharts for HTML dashboards when React is available. Use `ResponsiveContainer`, `BarChart`, `PieChart`, `Tooltip`, `Legend`, and source-note text so charts remain readable across desktop and mobile review.
- Include deeper figures when the source data supports them: trend charts by fielding date, scatter or cluster plots for review candidates, stacked bars by supplier/source and decision, pie charts for decision shares, and theme charts for survey improvement patterns.
- The final visual package must include both the dashboard artifact and a Markdown findings report. The dashboard should carry the charts and decision tables; the Markdown report should preserve the same structure for sharing, copying, or review in non-browser contexts.
- Apply plain-writing rules to all narrative explanations: use everyday words, write complete sentences, avoid filler, avoid jargon unless it is explained, and state exactly why a row was discarded or kept.
- Cite every important claim. Use local artifact citations for run-specific claims, such as respondent counts, criteria support, discoveries, semantic judgments, and kept-row synthesis. Use external citations for design, charting, and writing-method guidance.
- The final citation list must include at least the respondent review table, generated criteria catalog, discovery profile, criterion evidence table, agent judgment table, kept review synthesis, visual design reference, plain-writing reference, and charting reference.
- Before the final assistant response, preview the main artifacts. Inspect the findings essay, positive insights report, escalation packet, internal signal bank, dashboard, visual findings report, discard set, final judgment table, kept synthesis, next-pass inventory, demographic summary, and deep semantic sample.
- Reject placeholder or stitched prose before delivery. Search the final Markdown and dashboard for unresolved placeholders, template notes, repeated boilerplate, one-character table wrapping, and row cards that merely concatenate field values. Rewrite those sections as coherent analyst prose before final response.
- Reject parameterized prose before delivery. Search for `best_score=`, `risk=`, `narrative=`, `support_rate=`, raw status values, and unconverted internal labels in client-facing files. Rewrite the section if any appear.
- If a script creates a client-facing artifact, inspect the script for leaked prose patterns before trusting the output. The script should produce evidence, counts, charts, links, and authoring prompts. It should not produce the final analysis in fixed sentences.
- Challenge the final package before delivery. Try to disprove the discard set, kept-row rationale, statistical interpretation, next-pass signal inventory, and dashboard readability. Repair the smallest material weakness and rerun only the affected checks.
- State the run's terminal state in the final assistant response. Use success, clean no-op, blocked, approval required, or no-progress stop. If the state is not success, name the exact artifact, decision, or approval that remains.
- The final assistant response must be client-facing and email-ready. It should read as one cohesive review system, using language such as "we discovered," "we reviewed," and "we recommend." Do not write "the agent final pass" or similar internal process language in client-facing copy.
- The final assistant response must include a clear narrative of core discoveries, core discard recommendations with respondent keys and row or cell-level citations when available, positive findings and strong-response examples, key statistics from the run, brief descriptions of important artifacts, a verified-artifact statement, and next-pass signals. Do not only say that scripts ran.
- Keep running cycles on the next available datasets when the user asks for improvement over time. Each cycle must begin by reading the prior findings essay, escalation packet, signal bank, and next-pass inventory. Each cycle must end by saying which signals improved the first pass, which failed, which false-positive guardrails protected good rows, and what should change before the next dataset.

## When To Read References

- Read `references/report-templates.md` before writing PM or client summaries.
- Read `references/analyst-prose-standard.md` before writing client-facing findings, positive insights, dashboard prose, or visual findings reports.
- Read `references/agentic-fraud-training-reporting.md` before writing annotated fraud-signal training reports, calibration dashboard prose, or naive-rerun readiness summaries.
- Read `../cleaning-survey-quality/references/client-terminology-glossary.md` before using client, PM, or survey-quality shorthand in final prose.
- Read `../cleaning-survey-quality/references/semantic-signal-expansion.md` before reporting weights, straightlining, speed, open-end authenticity, semantic similarity, or convergence logic.
- Read `../cleaning-survey-quality/references/dataset-cycle-loop.md` before summarizing reruns, next-dataset cycles, workflow hardening, terminal states, or learning records.
- Read `references/client-annotation-benchmark.md` when using client-provided annotated workbooks as examples or calibration material.
- Read `references/escalation-reporting.md` before changing escalation sections.
- Read `references/visual-dashboard-design.md` before changing final dashboard or chart generation.
