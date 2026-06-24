# autosurvey

Reusable Opulent skills for autonomous survey-quality cleaning, rubric evolution, and reporting.

This repository contains only reusable skill instructions, scripts, and methodology docs. It intentionally excludes client source data, generated outputs, workbooks, row-level exports, dashboards, and PDFs.

## Skills

- `skills/cleaning-survey-quality`: profiles unannotated survey exports, discovers candidate quality analyses, generates criteria and provisional weights, writes row-level evidence, and prepares agent semantic review surfaces.
- `skills/evolving-survey-rubrics`: compares generated recommendations against adjudicated PM review and proposes bounded methodology, criteria, weight, or escalation improvements.
- `skills/reporting-survey-quality`: builds PM/client briefs and final visual review packages with criteria, semantic decisions, survey-design recommendations, charts, citations, and artifact indexes.
- `skills/external-validation-survey-authenticity`: runs sealed one-shot external validation for a previously blinded workbook after client decisions become available, with pre-registration, prediction sealing, respondent reconciliation, accuracy profiling, leakage audits, and benchmark consumption tracking.

## Data Safety

Do not commit source survey files or generated client artifacts. `.gitignore` blocks common data and output formats by default.

Use `skills/cleaning-survey-quality/references/project-context-template.md` for private client context in a downstream workspace.

## Basic Flow

Autosurvey has two separate paths.

1. **Methodology development from annotated data.** Use TFG cleaning-answer workbooks to discover correlated authenticity signals, false-positive guardrails, and signal interactions. Keep these outputs in a calibration folder. Use the labels to improve reusable natural-language instructions. Do not treat annotated data as a normal runtime input.
2. **Blind Autosurvey runtime on blank Decipher exports.** Run Autosurvey on the current unannotated respondent file, Datamap, codebook, prior signal bank, and learned natural-language signal questions. Do not use `status = 3`, `status = 5`, client flags, or hidden cleaning outcomes.

The normal path is the blank Decipher runtime. The annotated path exists so the method can improve.

Before running the scoring script, explore the workbook. Read the sheet names,
row count, column count, Datamap or codebook, and examples from every response
family. Map field roles first. Do not run topic mismatch or low-effort scoring
until you know whether a field is a job-role screener, brand list, narrative
open end, other-specify field, survey-feedback field, timing field,
supplier/source field, identifier field, or review/helper field.

Field-role mapping must adapt to the workbook. Do not assume that role context
is always named `qcoe1`. A study may use fields such as `qIndustry`, `CLASSIFY`,
buyer-role fields, use-case fields, or product-involvement fields. Treat those
as role and qualification context before scoring topic relevance. If the prompt
asks for a physical item, location, product use, or short factor, short noun
phrases can be valid answers. Build a project-specific topic and answer map
from the Datamap and sampled accepted responses before treating short text as
weak.

The run must also build question and response chains. First stitch the ordered
question chain from the Datamap or codebook when it is present. If prompt text is
not available, use the ordered source columns. Then stitch each respondent's full
response chain from all nonempty answer fields. The final agent semantic review
must review that full chain before it writes a structured discard decision.

The run must also examine all question sets before scoring semantic quality.
Write an agent-authored `question_set_authenticity_map.md` that explains the
intended respondent universe, field role, expected evidence type, authentic
answer patterns, fabricated-response warning signs, and learned guardrails
for each major survey section. This is the central natural-language bridge
between annotated-data learning and future unannotated datasets. Scripts can stage
evidence, but the agent must author this map from the Datamap, source rows,
accepted counterexamples, and rejected-row patterns.

The run must audit the whole respondent population, not only the rows surfaced
by the first-pass scorer. `independent_full_response_audit.csv` must contain one
row for every source respondent and must carry the stitched full response chain
for each row. Signal discovery can decide which rows need deeper narrative
writeups first, but it cannot replace the all-row read. If source rows,
`row_scores.csv`, `respondent_review_table.csv`, and
`independent_full_response_audit.csv` do not reconcile, the run is blocked.

The final review is an intelligent critic layer. The criteria create the case
file, but they do not decide discard on their own. The reviewer must look for
semantic counterevidence in the full response chain, including meaningful but
awkward wording, enthusiastic repeated characters, and short answers that are
valid for the prompt. If an early pass over-reviews or over-discards because the
topic map was incomplete, rerun the review after improving the map and record
the correction in the internal signal bank.

Every raw discovery must be expanded before it receives decision weight. A
straightline check must include question similarity and answer-time context when
available. A speed check must include page, section, question, and response-chain
context when available. An open-end check must evaluate prompt fit, semantic
authenticity, respondent-universe fit, adjacent-topic validity, and accepted-row
guardrails. Scripts may stage counts, repeated patterns, timing buckets, and
candidate similarities; the agent must decide the weight and explain it in
plain language.

The skills use a majority skill, minority template standard. Templates define
required artifacts, citations, and proof gates. They do not replace agent
analysis. Final prose must be written after reading the workbook, Datamap,
response chains, all-row audit, judgment tables, demographic summaries, signal
bank, and prior-run lessons. If a report reads like placeholders or fields were
stitched together, rewrite it before delivery.

Use `skills/cleaning-survey-quality/references/client-terminology-glossary.md`
before final reporting. Client-specific terms, PM shorthand, survey field names,
quality terms, and internal criteria should be explained in plain language when
they affect interpretation or decisions.

Use `skills/cleaning-survey-quality/references/dataset-cycle-loop.md` for
reruns, next-dataset passes, and workflow hardening. Each cycle should observe
fresh evidence, choose one high-value action, act, verify, record the lesson,
and stop or continue under a named terminal state. The valid terminal states
are success, clean no-op, blocked, approval required, and no-progress stop.
Errors and missing artifacts are not success.

```bash
python3 skills/cleaning-survey-quality/scripts/run_quality_loop.py \
  --input-file /path/to/unannotated_export.xlsx \
  --topic-keywords "topic,brand,category" \
  --output-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_quality_brief.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_independent_full_response_audit.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_agent_review_artifacts.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_full_chain_analyst_readout.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_positive_insights_report.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_next_pass_review_artifacts.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_deep_findings_analysis.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_visual_dashboard.py \
  --run-dir /path/to/private_outputs/run
```

Methodology-development commands for annotated TFG workbooks are separate from normal blank runs:

```bash
python3 skills/reporting-survey-quality/scripts/build_annotated_authenticity_discovery.py \
  --annotated-dir /path/to/Data-Sets-with-Cleaning-Answer \
  --client-root /path/to/client-package-root \
  --blinded-workbook /path/to/blinded-test-workbook.xlsx \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration/authenticity_discovery_loop

python3 skills/reporting-survey-quality/scripts/build_status_signal_derivation.py \
  --input /path/to/tfg_status_labeled_workbooks_or_zip \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration

python3 skills/reporting-survey-quality/scripts/build_tfg_discard_rulebook.py \
  --input /path/to/tfg_status_labeled_workbooks_or_zip \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration

python3 skills/reporting-survey-quality/scripts/build_status_semantic_review_packets.py \
  --input /path/to/tfg_status_labeled_workbooks_or_zip \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration

python3 skills/reporting-survey-quality/scripts/build_semantic_authenticity_loop.py \
  --annotated-dir /path/to/Data-Sets-with-Cleaning-Answer \
  --client-root /path/to/client-package-root \
  --prior-run-dir /path/to/private_outputs/status-ground-truth-calibration/authenticity_discovery_loop \
  --blinded-workbook /path/to/blinded-test-workbook.xlsx \
  --output-dir /path/to/private_outputs/status-ground-truth-calibration/authenticity_semantic_loop
```

The semantic loop must report two outcomes separately. `client_reject_probability`
estimates how closely a row resembles the client's labeled removals.
`semantic_risk_score` records authenticity concerns from blind full-chain
reading. Do not collapse those into one claim. A row can match the client
cleaning process without proving fabrication, and a row can carry authenticity
risk without matching every client process rule.

Sealed external validation is a third path. It is used only when a formerly
blinded workbook receives client decisions. Run discovery and prediction before
opening labels, then seal predictions before reconciliation:

```bash
python3 skills/reporting-survey-quality/scripts/discover_external_validation_inputs.py --output-dir /path/to/private_outputs/external-validation/run
python3 skills/reporting-survey-quality/scripts/run_blind_autosurvey_prediction.py --output-dir /path/to/private_outputs/external-validation/run
python3 skills/reporting-survey-quality/scripts/seal_external_predictions.py --output-dir /path/to/private_outputs/external-validation/run
python3 skills/reporting-survey-quality/scripts/reconcile_client_labels.py --output-dir /path/to/private_outputs/external-validation/run
python3 skills/reporting-survey-quality/scripts/evaluate_external_accuracy.py --output-dir /path/to/private_outputs/external-validation/run
python3 skills/reporting-survey-quality/scripts/audit_external_validation_integrity.py --output-dir /path/to/private_outputs/external-validation/run
```

Once a label file is opened after a valid seal, that benchmark is consumed. It
cannot be reused as an untouched holdout for future Autosurvey changes.

Continuous evolution is the development-validation path for the 11 existing
TFG original and cleaning-answer workbook pairs. These pairs are development
data because their labels have already been used for methodology work. Do not
describe their results as untouched external validation.

```bash
python3 skills/reporting-survey-quality/scripts/build_continuous_evolution_loop.py \
  --original-dir "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets" \
  --graded-dir "/Users/jeremyalston/Perfect/Annnotated and test'/Data Sets with Cleaning Answer" \
  --output-dir "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/continuous-evolution"
```

The public output folder from that command must contain exactly two files:

- `AUTOSURVEY_RESULTS.xlsx`
- `AUTOSURVEY_EVOLUTION.md`

Detailed hashes, fold assignments, predictions, leakage audits, metrics, and
error ledgers belong under `.autosurvey-internal/`, not in the public folder.
See `docs/autosurvey-output-contract.md` for the reusable output schema.
The terminal state must be honest. Use `TARGET_MET` only when the nested
dataset-level metrics and the future untouched external benchmark gates are
both satisfied. Otherwise use `IMPROVING_NOT_MET`,
`PLATEAU_REQUIRES_NEW_SIGNAL`, `BLOCKED_REQUIRES_NEW_UNTOUCHED_HOLDOUT`,
`BLOCKED_LABEL_AMBIGUITY`, `FAILED_RECONCILIATION`, or
`FAILED_INTEGRITY_AUDIT`.

The run is not complete until an agent has reviewed the flagged rows and the output
folder contains:

- `question_chain_map.csv`
- `question_set_authenticity_map.md`
- `semantic_signal_expansion_notes.md`
- `agent_review_judgment_table.csv`
- `agent_discard_set.csv`
- `agent_findings_essay.md`
- `agent_positive_insights_report.md`
- `agent_escalation_packet.md`
- `internal_quality_signal_bank.md`
- `agent_kept_review_synthesis_table.csv`
- `full_chain_analyst_readout.md`
- `full_chain_best_worst_examples.csv`
- `next_pass_signal_inventory.csv`
- `next_pass_first_pass_config.json`
- `deep_semantic_review_sample.md`
- `independent_full_response_audit.md`
- `deep_findings_analysis.md`
- `agent_final_review_dashboard.html`
- `agent_final_visual_findings_report.md`

When the task is methodology development from annotated TFG workbooks, the calibration folder must also contain:

- `input_inventory.csv`
- `input_hashes.json`
- `split_manifest.json`
- `leakage_exclusions.json`
- `blinded_test_freeze_manifest.json`
- `labeled_row_manifest.csv`
- `discard_rows_raw.parquet` or the documented `.csv` and `.parquet.pkl` fallback when no Parquet engine is installed
- `accepted_rows_raw.parquet` or the documented `.csv` and `.parquet.pkl` fallback when no Parquet engine is installed
- `column_profile_discard_vs_accept.csv`
- `column_profile_discard_vs_accept.xlsx`
- `canonical_question_map.csv`
- `univariate_signal_ranking.csv`
- `cross_dataset_meta_signals.csv`
- `question_contracts/`
- `route_graphs/`
- `row_reviews_blind/`
- `row_reconciliations/`
- `matched_case_pairs.parquet` or the documented `.csv` and `.parquet.pkl` fallback when no Parquet engine is installed
- `rejected_phenotypes.csv`
- `accepted_guardrails.csv`
- `pairwise_interactions.csv`
- `higher_order_patterns.csv`
- `question_relation_graph.json`
- `signal_candidates.yaml`
- `signal_bank.yaml`
- `signal_matrix.parquet` or the documented `.csv` and `.parquet.pkl` fallback when no Parquet engine is installed
- `family_scores.parquet` or the documented `.csv` and `.parquet.pkl` fallback when no Parquet engine is installed
- `model_artifacts/`
- `validation_report.md`
- `contrastive_casebook.md`
- `interaction_casebook.md`
- `residual_casebook.md`
- `iteration_report.md`
- `annotated_authenticity_discovery_report.md`
- `skill_change_log.md`
- `freeze_manifest.json`
- `status_dataset_summary.csv` when TFG status-labeled workbooks are available
- `status_respondent_signal_map.csv` when TFG status-labeled workbooks are available
- `status_signal_derivation.csv` when TFG status-labeled workbooks are available
- `status_signal_derivation.md` when TFG status-labeled workbooks are available
- `blind_authenticity_review_table.csv` when TFG status-labeled workbooks are available
- `label_aware_contrast_table.csv` when TFG status-labeled workbooks are available
- `authenticity_signal_family_lift.csv` when TFG status-labeled workbooks are available
- `protective_human_evidence.md` when TFG status-labeled workbooks are available
- `agentic_fraud_training_report.md` when TFG status-labeled workbooks are available
- `tfg_rejected_row_rule_ledger.csv` when TFG status-labeled workbooks are available
- `tfg_rejected_semantic_discovery_backlog.csv` when TFG status-labeled workbooks are available
- `tfg_accepted_guardrail_ledger.csv` when TFG status-labeled workbooks are available
- `tfg_discard_rule_evidence.csv` when TFG status-labeled workbooks are available
- `tfg_discard_rulebook_dataset_summary.csv` when TFG status-labeled workbooks are available
- `tfg_discard_signal_rulebook.md` when TFG status-labeled workbooks are available
- `status_semantic_reading_protocol.md` when TFG status-labeled workbooks are available
- `semantic_review_packet_index.csv` when TFG status-labeled workbooks are available
- `semantic_review_packets/` when TFG status-labeled workbooks are available
- `semantic_packet_notes/` when TFG status-labeled workbooks are available
- `semantic_loop_provenance.json` when running the full annotated semantic loop
- `prior_run_verification.md` when running the full annotated semantic loop
- `blinded_test_freeze_verification.json` when running the full annotated semantic loop
- `semantic_leakage_audit.json` when running the full annotated semantic loop
- `question_contracts.jsonl` when running the full annotated semantic loop
- `question_contract_coverage.csv` when running the full annotated semantic loop
- `seed_field_semantic_map.md` when running the full annotated semantic loop
- `unresolved_question_contracts.csv` when running the full annotated semantic loop
- `respondent_claim_graphs/` when running the full annotated semantic loop
- `respondent_semantic_features.parquet` or documented fallback when running the full annotated semantic loop
- `claim_relation_evidence.csv` when running the full annotated semantic loop
- `semantic_feature_coverage.csv` when running the full annotated semantic loop
- `blind_full_chain_reviews.jsonl` when running the full annotated semantic loop
- `blind_review_coverage.csv` when running the full annotated semantic loop
- `contrastive_pair_reviews.jsonl` when running the full annotated semantic loop
- `accepted_guardrail_casebook.jsonl` when running the full annotated semantic loop
- `semantic_panel_disagreements.csv` when running the full annotated semantic loop
- `full_chain_casebook.md` when running the full annotated semantic loop
- `semantic_signal_candidates.csv` when running the full annotated semantic loop
- `semantic_pairwise_interactions.csv` when running the full annotated semantic loop
- `semantic_higher_order_patterns.csv` when running the full annotated semantic loop
- `contrastive_proposition_clusters.jsonl` when running the full annotated semantic loop
- `population_coordination_clusters.parquet` or documented fallback when running the full annotated semantic loop
- `accepted_counterexample_matrix.csv` when running the full annotated semantic loop
- `accepted_guardrail_bank.yaml` when running the full annotated semantic loop
- `accepted_guardrail_metrics.csv` when running the full annotated semantic loop
- `guardrail_casebook.md` when running the full annotated semantic loop
- `signal_after_guardrail_ablation.csv` when running the full annotated semantic loop
- `semantic_model_comparison.csv` when running the full annotated semantic loop
- `leave_one_dataset_out_semantic_results.csv` when running the full annotated semantic loop
- `calibration_results.csv` when running the full annotated semantic loop
- `family_ablation_results.csv` when running the full annotated semantic loop
- `tier_volume_and_precision.csv` when running the full annotated semantic loop
- `signal_promotion_decisions.yaml` when running the full annotated semantic loop
- `semantic_validation_report.md` when running the full annotated semantic loop
- `semantic_false_negatives.csv` when running the full annotated semantic loop
- `semantic_false_positives.csv` when running the full annotated semantic loop
- `semantic_disagreement_cases.csv` when running the full annotated semantic loop
- `residual_clusters.jsonl` when running the full annotated semantic loop
- `residual_loop_changes.md` when running the full annotated semantic loop
- `unexplained_client_decisions.csv` when running the full annotated semantic loop
- `semantic_methodology_freeze_manifest.json` when running the full annotated semantic loop

Do not require the status-labeled calibration artifacts for a normal blank Decipher run.

Before the final assistant response, preview the main artifacts so the user can follow the work. At minimum, inspect the findings essay, positive insights report, escalation packet, internal signal bank, dashboard, visual findings report, discard set, final judgment table, kept synthesis, next-pass inventory, demographic summary, and deep semantic sample.

When a client annotated workbook exists, treat it as methodology-development or benchmark data. For TFG cleaning-answer workbooks, the `status` column is the primary label: `status = 3` means TFG accepted the respondent, and `status = 5` means TFG rejected the respondent because of quality or authenticity concerns. Build `client_annotation_validation.md`, `client_annotation_validation.csv`, and `client_annotation_validation_summary.json` before making benchmark claims. The run is blocked if the benchmark reports disagree with the discard set, if TFG `status = 5` rows were not semantically reviewed or explained, if autosurvey discards TFG `status = 3` rows without an analyst explanation, or if a client signal family has low coverage without a next-pass fix.

The final assistant response must be client-facing and email-ready. It should read as one cohesive survey-quality review, not as a list of tool runs or internal agent steps. Use "we discovered," "we reviewed," and "we recommend" for conclusions. Do not write phrases such as "the agent final pass" or "the agent reviewed" in client-facing copy unless the user asks for internal implementation detail.

The final assistant response must include:

- a clear narrative of the core discoveries
- core discard recommendations with respondent keys and row or cell-level citations when source coordinates are available
- positive research findings, strong retained response examples, and the guardrails that protected good data
- key statistical analysis from the run, including totals, review rate, discard rate, top review themes, supplier or source patterns, timing findings, and demographic context
- brief natural-language descriptions of the important artifacts and where to open them
- a statement that every required artifact was verified, or a precise list of missing or inconclusive items
- a short note on what should feed the next first-pass analysis

The response should be ready to paste into a client email after removing local file paths if needed. It should summarize what was found, what should be done, and why the evidence supports the recommendation.

Client-facing prose must combine statistics with interpretation. Scripts can stage evidence, but every final artifact must be agent-authored after reading the run artifacts. This includes the findings essay, positive findings report, escalation packet, internal signal bank, deep findings memo, dashboard prose, visual findings report, and final assistant response. Do not ship parameterized text such as `best_score=`, `risk=`, `narrative=`, `support_rate=`, or raw internal status labels. Dense criteria tables must be preceded by a short analyst readout that explains what the table means and what should happen next.

Fraud/authenticity training reports must be readable research memos, not pasted exports. Do not paste quota strings, redirect URLs, pipe-delimited response chains, or raw workbook dump text into client-facing prose. Convert examples into short authored chain readouts that say which workbook and row matter, what the respondent claimed, what evidence supports or weakens authenticity, what accepted-row antisignal prevents over-exclusion, and where the full chain can be audited.

Use `next_pass_signal_inventory.csv` and `next_pass_first_pass_config.json`
before the next scoring run. These files record which signals should be scored,
which signals should stay review-only, and what extra evidence is needed.

Each cycle starts by reading the prior findings essay, escalation packet,
internal signal bank, and next-pass inventory. The next run should carry forward
promoted signals, keep false-positive guardrails active, and retire signals that
proved misleading. Continue dataset cycles until all artifact gates pass, the
dashboard is readable, the prose is client-ready, every row has been audited,
and any remaining open questions are true PM or client judgment calls.

Each cycle should also write compact learning records into the internal signal
bank or workflow improvement log when a lesson changes future behavior. The
record should say what changed, why it matters, and what the next run should do
differently. Do not record routine script execution as a lesson.

TFG rejection labels are observed client outcomes for method development, not proof of fraud and not a replacement for analyst reasoning. The workflow should learn which combinations of timing, straightlining, duplicate technical evidence, open-end authenticity, cross-field contradiction, role mismatch, and full-chain incoherence explain client rejection. It should also learn which accepted rows protect against false positives. The blinded test dataset and all future blank Decipher datasets must be scored without using any hidden status label.

Helper-field leakage is a hard failure. Exclude `status`, marker or quota fields, review helper fields, client action fields, final decision fields, condition assignment helpers, no-answer helper fields, QC helper fields, channel tracking fields, tokens, and any formula or formatting that reveals cleaning decisions before profiling or modeling. If a top signal collapses after these fields are excluded, report that as a valid finding. It means the reusable method still needs deeper semantic features before scoring the blinded workbook.

The annotated-data semantic signals should be carried forward as questions the
agent asks of each new question set, not as fixed keyword recipes. Before
reviewing unannotated data, the agent should ask whether each prompt expects a
role claim, brand list, physical location, concrete project example, personal
reason, use case, matrix judgment, allocation, or feedback. Then it should look
for abstract business answers without lived detail, survey-meta answers,
role-universe mismatch, personal-home examples in professional contexts,
generic project claims, sentence drift, bare lists where explanation was
required, and coherent but off-domain professional claims.

For methodology-building runs, the agent must read the semantic review packets, not only the signal tables. Every rejected row should produce a rejected-row learning when a real authenticity pattern is present. Every accepted row should be checked for guardrails. Packet notes must feed the internal signal bank, `decipher-blind-authenticity-review.md`, and next-pass configuration so future unannotated runs inherit the detection method without needing status labels.

The TFG discard rulebook must cover the full client discard set. Every `status = 5` row must appear in `tfg_rejected_row_rule_ledger.csv`. Every `status = 3` row that triggers a staged rule must appear in `tfg_accepted_guardrail_ledger.csv`. Rejected rows with no staged rule must appear in `tfg_rejected_semantic_discovery_backlog.csv`; these rows must be read before the method is considered complete.

Kept review rows must feed the next run. The workflow now treats these patterns
as standard signals on any dataset:

- Weak or unclear narrative answers stay as PM examples unless another strong
  signal appears.
- Speed-only rows stay review-only when the substantive answer is plausible.
- Short factor-list answers stay review-only until PM defines the minimum depth
  required for the field.
- Keyword topic mismatch is only review routing until semantic relevance is
  confirmed.
- Survey-feedback wording is classified separately from substantive answers.
- Direct non-response, repeated placeholders, or hostile text in a required
  high-value open end should route to exclusion review when the full response
  chain does not recover useful context.
- Duplicate IP or device evidence is context by itself. It becomes stronger
  only when multiple supposedly independent responses share the same chain
  pattern, weak narratives, timing concerns, or other converging signals.
