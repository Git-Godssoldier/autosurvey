---
name: cleaning-survey-quality
description: Cleans and scores Decipher-style survey quality workbooks for market research datasets. Use when reviewing survey completes, fraud, inattentive respondents, open-end AI suspicion, straightlining, inconsistent brand answers, short completes, duplicate IPs, respondent flags, or survey quality files.
---

# Cleaning Survey Quality

Use this skill to run a reproducible survey quality pass on unannotated Decipher-style survey exports before PM review. Treat annotated helper columns and final-review files as calibration examples, not required inputs.

The default input is raw respondent data. The skill autonomously discovers meaningful candidate analyses, evaluates which analyses are safe to score, writes row-level justifications, generates agent annotations for intelligence and linguistic fluency, and reports which criteria need project-specific mapping.

This skill must favor data-analysis discovery and rigorous evaluation over flat scripted rubric scoring. Scoring is one output of the process, not the method itself.

## Workflow

1. Frame the run before writing or running scoring scripts:
   - Read `references/agentic-escalation-path.md`.
   - Read `references/client-terminology-glossary.md` and use it to define client, PM, survey, and quality terms before writing final artifacts.
   - Read `references/dataset-cycle-loop.md` when the run is part of an improvement cycle, a rerun, a multi-dataset pass, or a workflow-hardening request.
   - State the definition of done for this dataset in plain words.
   - Identify the source files, expected final artifacts, and what would block final delivery.
   - If the run includes internal comments, PM notes, client annotations, or prior criteria, read `references/internal-signal-learning.md`.
   - Start a short decision trail for non-obvious choices. The trail can be Markdown or TSV, but it must cite the artifact or command that supports each decision.
   - If a missing decision would change safety, scope, or final authority, ask one short question with a recommended default. If the answer can be discovered from available files, discover it instead of asking.
2. Explore the workbook before writing or running scoring scripts:
   - Read the sheet names, row count, column count, and Datamap or codebook when present.
   - Inspect representative raw rows and nonempty examples from every open-ended field family.
   - Read any internal comments, review notes, client annotations, prior quality essays, prior escalation packets, prior signal inventories, and prior signal banks that are available for the same client, survey family, or product area.
   - Parse the Datamap before scoring. Extract prompt text, value labels, field groups, and response options. Treat Datamap parsing as the source of truth for field-role mapping when it is available.
   - Map field roles before scoring. At minimum, separate job-role screeners, brand-list fields, narrative open ends, other-specify fields, survey-feedback fields, timing fields, supplier/source fields, respondent identifiers, IP/device fields, and review/helper fields.
   - Field-role mapping must adapt to the workbook's actual language. Do not assume that role context is always named `qcoe1`. Treat fields such as `qIndustry`, `CLASSIFY`, buyer-role fields, product-involvement fields, use-case fields, and eligibility fields as role or qualification context when the Datamap shows that is their purpose.
   - Map demographics separately from quality evidence. Required demographic fields include `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, and `qPolitics` when present.
   - Stitch the full question chain before scoring. Use the Datamap or codebook prompt text when available. Fall back to ordered source columns when prompt text is not available.
   - Stitch each respondent's full response chain from all nonempty respondent-answer fields before final semantic review. Also build a focused semantic chain around `qcoe1`, `q9`, `q9r10oe`, `q10`, `q32`, `q43`, and `outro` when those fields exist. The final discard decision must review these chains, not just the field that triggered a flag.
   - Plan for a whole-population read from the start. The final package must include an independent full-response audit with one row per source respondent and a stitched chain for every row. Signal discovery can prioritize deeper review, but it cannot be the only review surface.
   - Decide which fields can be scored in the first pass, which fields need PM mapping, and which fields should only produce review notes.
   - Do not run topic mismatch or low-effort scoring until the field role is clear. A job-role screener should not be scored like a product-topic open end. An unaided brand-list field should not penalize short valid brand names.
   - Build a project-specific topic and answer map from the Datamap, prompt wording, value labels, and sampled open ends before topic or answer-depth scoring. If a prompt asks for a physical item, location, product use, brand, simple reason, or short factor, short noun phrases may be complete answers. Protect those rows unless the full chain remains non-responsive, nonsensical, or contradicted by other strong evidence.
3. Build quality hypotheses from exploration:
   - State which bad-response or fabricated-response patterns are plausible in this dataset.
   - State what evidence would confirm each pattern and what evidence would make it a false positive.
   - Separate row-level discard evidence from wave-level context and survey-design findings.
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
   - Read the full response chain and focused semantic chain for each candidate.
   - Read enough of the all-row audit to understand every response family, not just the rows surfaced by the first pass.
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
   - `deep_semantic_review_sample.md`: a small set of reviewed rows with deeper semantic reasoning and next-pass learning.
   - `agent_findings_essay.md`: cited natural prose analysis of the run, discoveries, decisions, demographic context, and workflow learning.
   - `agent_final_review_dashboard.html` and `agent_final_visual_findings_report.md`: final dashboard, charts, tables, findings, and artifact index for content review.
   - Use `build_agent_review_artifacts.py` after the independent full-response audit to create the agent judgment table, discard set, kept-review synthesis, and verified quality brief.
12. Prove the package before calling the run complete:
   - Check that the required artifacts exist.
   - Verify that source rows, `row_scores.csv`, `respondent_review_table.csv`, and `independent_full_response_audit.csv` have the same row count. If they do not, stop and fix the run.
   - Verify that the independent audit contains a `full_response_chain` field and that the final judgment table was built after that audit.
   - Reconcile counts across respondent review, agent judgment, discard set, kept synthesis, essay, escalation packet, and dashboard.
   - Verify that every discard row appears in the escalation packet.
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
- independent full-response audit of every source row, not just sampled or first-pass rows
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

Weights are trial artifacts, not policy. They should evolve from discoveries, PM findings, adjudicated examples, and feedback. Do not auto-remove respondents from this skill alone. Output discard-candidate escalations with evidence and row-level justifications only after a second pass has found converging discard evidence. Treat scripted scoring as the evidence substrate, not the reader-facing judgment.

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

The script also discovers brand/preference/recommendation columns, but it reports those as candidate mappings unless a project-specific consistency rule exists. Do not infer brand inconsistency from column names alone.

The script also discovers fielding timestamp fields such as `date`, `start_date`, `start_time`, `started_at`, or comparable export fields. Odd-hour starts and concentrated start bursts are fielding-pattern evidence by default. Report them by supplier/source and timestamp bucket, but do not turn them into row-level discard evidence unless the final agent sees corroborating respondent-quality problems or the project has an approved fielding rule.

Client-annotated workbooks are the minimum benchmark, not the target. If a prior workbook contains columns such as `qtime_Under_4_Minutes`, brand inconsistency, grid straightline detail, open-end topic relevance, duplicate IP, `Respondent Flags`, `Respondent Score`, or `Recommended_Action`, autosurvey must preserve the equivalent audit surface and then surpass it with full-chain semantic reasoning, counterevidence, kept-row learning, survey-improvement guidance, and readable analyst prose.

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

## When To Read References

- Read `references/agentic-escalation-path.md` before running a full dataset from raw export to final discard choices.
- Read `references/internal-signal-learning.md` when internal comments, PM notes, client annotations, prior criteria, prior findings essays, or recurring bad-response patterns are available.
- Read `references/rubric-seed.md` only as historical seed context, not as a source of fixed weights.
- Read `references/autonomous-discovery.md` before changing discovery behavior.
- Read `references/evaluation-methodology.md` before changing open-end evaluation, judge behavior, or validation metrics.
- Read `references/escalation-policy.md` before changing severity bands or owners.
- Read `references/project-context-template.md` when adapting the workflow to a specific client, survey program, or stakeholder group.
- Read `references/research-grounding.md` when changing the agent architecture or reporting/evolution loop.
