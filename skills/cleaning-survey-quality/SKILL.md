---
name: cleaning-survey-quality
description: Cleans and scores Decipher-style survey quality workbooks for market research datasets. Use when reviewing survey completes, fraud, inattentive respondents, open-end AI suspicion, straightlining, inconsistent brand answers, short completes, duplicate IPs, respondent flags, or survey quality files.
---

# Cleaning Survey Quality

Use this skill to run a reproducible survey quality pass on unannotated Decipher-style survey exports before PM review. Treat annotated helper columns and final-review files as calibration examples, not required inputs.

The default input is raw respondent data. The skill autonomously discovers meaningful candidate analyses, evaluates which analyses are safe to score, writes row-level justifications, generates agent annotations for intelligence and linguistic fluency, and reports which criteria need project-specific mapping.

This skill must favor data-analysis discovery and rigorous evaluation over flat programmatic rubric scoring. Scoring is one output of the process, not the method itself.

## Workflow

1. Profile the workbook:
   - Identify the main respondent sheet, usually `A1`.
   - Confirm respondent key columns such as `uuid`, `record`, or `RID`.
   - Discover raw quality signals: qtime/duration, IP address, matrix grids, open-ended columns, brand/preference/recommendation candidates, and AI-likelihood columns when present.
   - Detect and ignore graded/review helper columns when building the raw-data discovery profile.
2. Run the scoring loop:
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
3. Review the generated `quality_report.md`, `row_scores.csv`, and `quality_summary.json`.
4. Review the generated table artifacts:
   - `generated_criteria_catalog.csv`: all generated criteria, tags, source columns, rationale, generated weights, and support.
   - `respondent_review_table.csv`: one row per respondent with metadata, triggered criteria, explanations, second-pass disposition, agent semantic analysis, linguistic fluency assessment, trust rationale, survivor rationale, discard rationale, and escalation routing.
   - `response_criteria_evidence_table.csv`: one row per respondent criterion with observed value, source column, generated points, explanation, weight rationale, second-pass disposition, and agent annotation context.
   - `agent_annotation_table.csv`: focused Opulent annotation surface for semantic analysis, linguistic fluency assessment, trust rationale, and next steps.
   - `respondent_review_table.md`: PM-facing Markdown sample sorted by severity/score.
5. Review `discovery_profiles.json` to confirm detected qtime, IP, matrix, open-end, brand-consistency, and AI-authenticity candidate analyses.
6. Route rows using `second_pass_decision` first, then `severity_level`, `escalation_owner`, and `escalation_reason`.
   - Escalate only rows marked `discard_candidate` after the extra pass.
   - Keep rows marked `keep_with_recommendation` or `keep_no_issue`; aggregate their survivor rationales and survey-question recommendations.
7. After the agent has investigated review-tagged rows, generate a final visual review package through `reporting-survey-quality`:
   - `agent_review_judgment_table.csv`: all review-tagged rows with agent decisions.
   - `agent_discard_set.csv`: only rows the agent judged should be escalated for removal.
   - `agent_kept_review_synthesis.md` and `.csv`: synthesis of kept review-flagged candidates into survey-question and parameter improvements.
   - `next_pass_signal_inventory.csv`: critical signals that should shape the next first-pass analysis.
   - `next_pass_first_pass_config.json`: proposed next-pass rules, evidence needs, and escalation guardrails.
   - `deep_semantic_review_sample.md`: a small set of reviewed rows with deeper semantic reasoning and next-pass learning.
   - `agent_final_review_dashboard.html` and `agent_final_visual_findings_report.md`: final dashboard, charts, tables, findings, and artifact index for content review.
8. Before starting the next run, read `next_pass_signal_inventory.csv` and decide which signals can be added to the first-pass context, which signals need PM examples, and which signals should remain review-only.

## Generated Criteria And Scoring Policy

Do not provide fixed weights or closed criteria ahead of time. The methodology defines discovery procedures, evidence standards, evaluation requirements, and escalation paths. The run generates candidate criteria and provisional weights from the data.

Each run must produce:

- generated candidate criteria with tags, source columns, and rationale
- provisional weights with support counts and rationale
- generated action thresholds
- second-pass disposition and discard-only escalation routing
- agent-generated semantic annotations for escalations and survivor decisions
- next-pass signal inventory from agent-reviewed rows
- deep semantic review sample for a subset of reviewed rows
- evaluation metrics when adjudicated labels exist

Weights are trial artifacts, not policy. They should evolve from discoveries, PM findings, adjudicated examples, and feedback. Do not auto-remove respondents from this skill alone. Output discard-candidate escalations with evidence and row-level justifications only after a second pass has found converging discard evidence. Treat programmatic scoring as the evidence substrate, not the reader-facing judgment.

## Evidence Rules

Every flag must include:

- criterion id
- generated tags
- respondent metadata such as respondent id, source/vendor, status, timestamp, IP, qtime, geography, and quota markers when present
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

## Agent Annotation Layer

Generate annotations as a separate Opulent judgment pass after scoring and second-pass disposition. The annotation pass should use the score, tags, source evidence, respondent metadata, and open-ended text context, but it should not simply restate deterministic criteria.

For each row with evidence, especially every possible `discard_candidate`, write:

- `agent_semantic_analysis`: a concise but rich judgment about what the evidence means in context.
- `agent_linguistic_fluency_assessment`: whether the respondent's language is fluent, generic, evasive, off-topic, low-information, or otherwise suspicious, without treating polish alone as quality.
- `agent_trust_rationale`: why the recommendation is defensible from source evidence and not just a rigid score.
- `agent_recommended_next_step`: what the PM or Data Quality Lead should do next.

Escalation annotations must give readers enough trust and depth that they can adjudicate the discard decision directly. They should not force the reader to reconstruct the reasoning from flags and points.

Semantic relevance and linguistic-quality calls must be made by the Opulent agent, not solved as rigid keyword matching in the scoring script. The script may surface candidate evidence such as a possible topic mismatch, but the agent must read the response in survey context and decide whether the text is actually off-topic, evasive, generic, low-information, or acceptable. A row should not remain a discard candidate when the only semantic problem is a brittle keyword miss.

Before finalizing any text-driven discard:

1. Read the full open-ended response and nearby respondent evidence.
2. Decide whether a reasonable PM would treat the answer as substantively off-topic or merely awkward/variant phrasing.
3. Check whether the text concern independently strengthens another quality signal, such as straightlining or speed.
4. Downgrade rows where semantic evidence is plausible or only weakly ambiguous; keep them with a survey-question recommendation instead.
5. Escalate only rows where the agent can explain, in fluent business language, why the response should be discarded.

## Raw-Data Discovery

On unannotated files, the script can score:

- raw qtime under four minutes
- duplicate IP address
- repeated matrix-grid answers
- obvious low-effort open ends
- optional topic mismatch when `--topic-keywords` is supplied

The script also discovers brand/preference/recommendation columns, but it reports those as candidate mappings unless a project-specific consistency rule exists. Do not infer brand inconsistency from column names alone.

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

## When To Read References

- Read `references/rubric-seed.md` only as historical seed context, not as a source of fixed weights.
- Read `references/autonomous-discovery.md` before changing discovery behavior.
- Read `references/evaluation-methodology.md` before changing open-end evaluation, judge behavior, or validation metrics.
- Read `references/escalation-policy.md` before changing severity bands or owners.
- Read `references/project-context-template.md` when adapting the workflow to a specific client, survey program, or stakeholder group.
- Read `references/research-grounding.md` when changing the agent architecture or reporting/evolution loop.
