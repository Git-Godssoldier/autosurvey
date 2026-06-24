# Report Templates

These templates define the minimum artifact shape. They are not the analysis. The report should be majority agent-written insight and minority fixed template. Use the structure below so every run is complete, but write the conclusions from the workbook, Datamap, response chains, audit outputs, demographic summaries, and prior learning.

Keep annotated methodology development separate from blank Decipher runtime reporting. Status-labeled artifacts belong in calibration reports. Normal Autosurvey reports should apply the learned signal questions to the current blank workbook and should not cite hidden status labels as decision evidence.

Before using client, PM, or survey-quality shorthand, read `../../cleaning-survey-quality/references/client-terminology-glossary.md` and define ambiguous terms in the report.

For reruns and multi-dataset cycles, read `../../cleaning-survey-quality/references/dataset-cycle-loop.md`. Report the terminal state and learning records in the workflow improvement log. Keep client-facing prose focused on findings, recommendations, evidence, and next actions.

Before writing final prose, read `analyst-prose-standard.md`. The report must use statistics to support a finding, not replace the finding. Helper scripts can stage evidence, but they cannot satisfy the prose artifacts by themselves.

Generated evidence packets should tell the agent what to inspect and what to explain. They should not decide the final wording. Final reports must be written after the agent reads the workbook exploration, field-role map, full response-chain artifacts, final judgment table, discard set, retained-row synthesis, demographic summary, and dashboard.

## PM Operations Summary

Title: Survey Quality Cleaning Summary

Sections:

1. Review volume
   - Respondents reviewed
   - Keep
   - Light review
   - Review closely
2. Severity and escalation
   - severity level
   - owner
   - count
   - percent of completes
3. Second-pass disposition
   - `discard_candidate`
   - `keep_with_recommendation`
   - `keep_no_issue`
   - count and percent of completes
   - note that only `discard_candidate` rows enter the escalation queue
4. Discovery, candidate analyses, and generated criteria
   - analysis id
   - status
   - candidate columns
   - mapping needs
   - Datamap-derived field roles
   - generated criterion id
   - tags
   - rationale
   - whether the criterion is scorable, needs context, needs mapping, or needs feedback
5. Flag breakdown
   - criterion id
   - count
   - percent of completes
   - action impact
6. Evidence examples
   - respondent key
   - criterion
   - observed value
   - justification
7. Agent semantic annotations
   - respondent key
   - second-pass decision
   - semantic analysis
   - linguistic fluency assessment
   - trust rationale
   - recommended next step
8. Survivor recommendations
   - recommendation text
   - survivor row count
   - representative kept respondent keys
   - why these rows were kept
   - how the survey question should be strengthened to prevent fuzzy or gameable answers
9. Discard escalation queue
   - respondent key
   - severity
   - owner
   - score
   - trigger pattern
   - discard rationale
   - agent semantic analysis
   - agent trust rationale
10. Generated model status
   - stable on this evaluation set, proposed change, or needs adjudication
   - metric impact
   - rollback condition
11. Evaluation metrics when labels exist
   - exact agreement
   - precision and recall for review routing
   - Cohen's kappa
   - ordinal action disagreement
   - over-escalation and under-escalation counts
12. Agentic fraud-signal training when annotated `status = 3/5` labels exist
   - training objective: rejected corpus and accepted antisignal corpus
   - ground-truth limits: client rejection is not proof of fraud
   - blind tier distribution before label reveal
   - label-aware contrast outcomes
   - signal-family lift and accepted-row exposure
   - signal interactions that outperform individual checks
   - accepted-row protective evidence and antisignals
   - blind-miss rows that reveal new semantic checks
   - detector upgrade plan for naive unannotated reruns
   - readiness statement for unannotated transfer
13. Table artifact index
   - generated criteria catalog
   - demographic summary
   - respondent review table
   - criterion evidence table
   - agent annotation table
   - agent review judgment table
   - agent discard set
   - kept-review synthesis table
   - full-chain analyst readout
   - full-chain best and worst examples table
   - next-pass signal inventory
   - next-pass first-pass config
   - deep semantic review sample
   - independent full-response audit
   - client annotation validation when a client annotated workbook exists
   - agentic fraud training report when annotated `status = 3/5` labels exist
   - blind authenticity review table when annotated `status = 3/5` labels exist
   - label-aware contrast table when annotated `status = 3/5` labels exist
   - authenticity signal family lift when annotated `status = 3/5` labels exist
   - protective human evidence when annotated `status = 3/5` labels exist
   - deep findings analysis
   - PM-facing Markdown sample
14. Final visual review package
   - KPI cards: total responses, review-tagged rows, agent discard rows, kept review rows
   - bar charts: action counts, second-pass disposition, agent review decisions, kept-review themes, supplier/source concentrations
   - discard table with agent rationale and source evidence
   - kept-review synthesis table with survey-question and parameter recommendations
   - next-pass signals to feed into the next first-pass analysis
   - deep semantic sample with row-level reasoning and learning for the next pass
   - independent full-response audit comparing all source rows to autosurvey decisions
   - full-chain analyst readout explaining the best and worst examples in prose
   - deep findings memo with final interpretation and workflow audit
   - final guidance on what to discard, what to keep, and what to improve in the survey instrument
15. Annotated-workbook benchmark coverage
   - qtime speeders and long-duration outliers
   - fielding start/date patterns, odd-hour starts, and concentrated start bursts
   - grid straightlining or near-straightlining
   - brand/preference/consideration/recommendation consistency, with mapping status
   - open-end topic relevance and open-end authenticity concerns
   - duplicate IP or comparable technical identifiers, with independent-cluster context
   - respondent flags, score, and recommended action equivalents
   - explanation of where autosurvey went beyond the annotated workbook through full-chain semantic reasoning, counterevidence, kept-row learning, and next-pass signal updates
16. Demographic and aggregate insights
   - `qGender`
   - `qager1` and `age`
   - `qEthnic*`
   - `qEd`
   - `qStateVer`
   - `qEmploy`
   - `qUSHHI`
   - `q44`
   - `q45`
   - `qPolitics`
   - value counts and averages where the field supports them
   - a clear note that demographic summaries are context, not discard evidence by themselves

## Required Table Fields

`respondent_review_table.csv` should include:

- respondent key
- respondent metadata available in source data: record, date, status, supplier/source, RID, IP address, qtime, geography, quota/marker fields
- computed action, score, severity, owner, and escalation reason
- second-pass decision: `discard_candidate`, `keep_with_recommendation`, or `keep_no_issue`
- discard rationale when the row should be reviewed for removal
- survivor rationale when the row is kept
- survey-question-strengthening recommendation when the row is kept with evidence
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step
- generated tags
- all triggered criteria
- observed evidence
- criterion explanations

`response_criteria_evidence_table.csv` should include one row per respondent criterion:

- respondent key and metadata
- criterion id
- source column
- observed value
- generated points
- criterion explanation
- generated-weight rationale
- second-pass decision
- discard rationale
- survivor rationale
- survey-question-strengthening recommendation
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step

`agent_annotation_table.csv` should include one row per respondent:

- respondent key and core metadata
- computed action and score as supporting context
- second-pass decision
- triggered criteria and observed evidence
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step

`generated_criteria_catalog.csv` should include:

- generated criterion id
- scoring id
- status
- tags
- source columns
- criterion rationale
- generated weight
- weight rationale
- support rows and support rate
- report-only candidate criteria such as odd-hour starts and start bursts when timestamp fields exist

`agent_review_judgment_table.csv` should include:

- every row tagged for review by the scoring pass
- agent final decision: discard or keep with review note
- agent semantic judgment
- discard or keep rationale
- next step
- respondent metadata and observed evidence
- full response chain field count
- focused semantic review chain and field count for the key review sections
- early screening discard recommendation
- full-chain counterevidence
- semantic discard basis

`full_chain_analyst_readout.md` should include:

- a plain-language read-this-first section
- a summary of what the best full response chains show
- a summary of what the worst full response chains show
- readable answer excerpts, not raw coded chain dumps
- explicit judgment about why strong rows are strong
- explicit judgment about why bad rows remain bad after full-chain review
- callouts where the workflow should challenge or revise itself
- workflow learning for the next pass

`agent_findings_essay.md` should be written after reading the run artifacts. It is the main reasoning artifact, not a structured export. It should be a natural prose essay with citations to the local run materials.

The essay should be client-facing by default. It should read as one cohesive review system. Use "we discovered," "we reviewed," and "we recommend." Avoid internal process language such as "the agent final pass," "the agent decided," or "script output shows" unless the user specifically asks for implementation detail.

The essay should do the following in whatever structure best serves the dataset:

- state the real quality conclusion, not just the counts
- explain what we discovered during data exploration and field-role mapping
- explain how the Datamap and stitched response chains changed the final read
- explain any project-specific field-role discoveries, including role or qualification fields that were not named like prior surveys
- explain the project-specific topic and answer map, especially when short physical-item, location, brand, product-use, or factor-list answers are valid
- state that the independent full-response audit covered every source row, or explain why the run is blocked
- summarize what the all-row audit found outside the first-pass review queue
- interpret the strongest semantic patterns found in the full chains
- describe the best retained rows and why they improve confidence in the data
- describe the weakest retained rows and why they are calibration cases rather than discards
- explain any true discard logic, including the benign alternative the agent considered before recommending removal
- include demographic and aggregate context that affects survey interpretation, while keeping it separate from row-level discard evidence
- explain next-pass improvements and why they matter before the next first-pass scoring run
- critique the workflow itself, including places where static checks were too broad, too narrow, or too dependent on missing field-role mapping
- describe any rerun or correction cycle in plain language: what the first pass misunderstood, how the final review caught it, what changed, and how the next dataset should benefit

Do not turn this essay into a list of required fields. The point is to let the agent reason in prose after reading the evidence. Tables can support the essay, but they are not the analysis.

`agentic_fraud_training_report.md` is required when annotated `status = 3/5` training data is used. It should read as an agentic model-training memo, not as a generic survey-quality report.

It should explain:

- how rejected rows are used as the client-removal corpus
- how accepted rows are used as the antisignal and protective-evidence corpus
- why `status = 5` is not automatically proof of fraud
- what the blind pass found before labels were revealed
- what the label-aware contrast taught after labels were revealed
- which evidence families have lift and which are too broad
- which accepted rows prevent overfitting
- which blind misses reveal new semantic checks
- which signals should be promoted, held as agent-only, demoted, or retired
- whether the detector is ready for naive unannotated reruns

The report should explicitly distinguish client rejection probability from fabrication/authenticity risk. It should never imply that every rejected respondent is a bot, LLM user, or fraudulent respondent.

The essay should include a short glossary or definitions paragraph when the run uses client-specific shorthand, survey field names, PM terms, or quality terms that a new reviewer may not know. Do not over-explain common words. Explain only terms that affect interpretation or decisions.

The essay should also include at least one run-specific discovery that was not already present in the template. If the evidence does not support a new discovery, say that the run confirmed prior expectations and cite the artifacts that support that conclusion.

`agent_positive_insights_report.md` should be written as the companion to the discard and escalation materials. It exists because a great survey-quality review should preserve and explain good data, not only find removals.

The report should explain:

- what strong retained response chains look like in this dataset
- which specific retained respondents are useful calibration examples, with concise response-chain excerpts and local artifact citations
- what positive research findings, demographic patterns, aggregate patterns, and survey-design signals emerged from the run
- why suspicious-looking rows were kept when full-chain context made them defensible
- which false-positive guardrails protected good data, such as valid short answers, misspellings, shared technical context, speed-only plausible answers, keyword-map misses, or energetic wording
- whether the current discard set still looks right after comparing the final judgment table, discard set, escalation packet, and independent all-row audit
- what the next pass should learn from the good rows, not only from the weak rows

A helper script can seed this file from the run artifacts, but the agent is responsible for reading it and improving the prose before delivery. The agent may discard seeded text when it reads as a template. It should not sound like a table was stitched into paragraphs. It should read like a senior analyst explaining why the usable data is usable and how that improves confidence in the review.

Use this report to prove that quality review did not become discard-only. It should explain what was learned from usable responses, what good response chains look like, and which false-positive guardrails should remain active.

The positive report must not expose parameter strings from helper tables. Do not write `best_score=`, `risk=`, `narrative=`, `keep_no_issue_from_independent_audit`, or similar raw status labels. Translate them into clear language about why the row is usable, what statistic matters, and what the next pass should learn.

`agent_escalation_packet.md` should be written by the agent after final semantic review. It is the PM-ready operational artifact. It should let a reviewer act without reading every CSV.

The packet should explain:

- which rows are in the final discard set and why
- which suspicious rows were kept and why
- which rows were hard to decide and what evidence was missing
- what internal comments, client criteria, PM notes, or prior signals affected the review
- what evidence was decisive
- what evidence was inconclusive
- what the reviewer should do next

If the final discard set is empty, the packet still exists. It should explain why the path ended with no row-level removals.

`internal_quality_signal_bank.md` should be written for internal use after each run. It is a learning artifact for future datasets, not client copy.

The bank should preserve:

- useful internal comments and criteria
- suspected bad-response or fabricated-response patterns
- false-positive guardrails
- PM-approved discard signals
- review-routing signals
- survey-design signals
- signals that need more examples before they can affect scoring

The bank can be free-form prose. The agent should retire or demote misleading signals instead of keeping an append-only list.

The bank should also include compact learning records when a run changes future behavior. Each record should state what changed, why it matters, and what the next run should do differently, with an artifact, row key, field, or count citation. Do not turn learning records into an activity log.

`full_chain_best_worst_examples.csv` should include:

- respondent key
- best or worst group
- selection type
- rank basis
- final agent decision
- review theme
- open-end focus
- full-chain counterevidence
- semantic discard basis
- response chain field count
- full response chain

`agent_kept_review_synthesis_table.csv` should include:

- kept review theme
- count of retained review rows
- example respondent keys
- why kept
- survey-question recommendation
- quality parameter recommendation
- issue pattern

`next_pass_signal_inventory.csv` should include:

- theme
- support rows
- critical signal
- first-pass change
- analysis factor
- evidence needed
- default status
- escalation rule

`client_annotation_validation.md` should include:

- client workbook and row count
- client action counts
- top client flag counts
- autosurvey reviewed rows and discard rows
- coverage by client signal family
- client review rows that autosurvey missed
- autosurvey review rows that the client marked `No concerns`
- autosurvey discard rows that the client marked `Keep`
- consistency check between final Markdown reports and `agent_discard_set.csv`
- analyst note on whether autosurvey matched the client baseline and where it went further

`demographic_summary.csv` should include:

- source workbook
- field
- Datamap question text when available
- respondent count
- nonempty count
- missing count
- mean, median, min, and max when numeric
- top values with Datamap labels when available
- survey-question or parameter recommendation

`deep_semantic_review_sample.md` should include:

- respondent key
- final agent decision
- review theme
- observed evidence
- raw text reviewed
- semantic analysis
- language assessment
- trust basis
- next action
- learning for the next pass

`workflow_improvement_log.md` should include:

- terminal state for the cycle
- checks that passed
- checks that failed or remained inconclusive
- smallest repair made after challenge review
- compact learning records or links to the internal signal bank
- handoff paragraph for interrupted or long-running work, with artifact paths and next action

`independent_full_response_audit.csv` should include:

- respondent key
- role class
- brand answer quality
- duplicate IP count
- timing risk
- independent risk factors
- independent suggested action
- whether autosurvey reviewed the row
- whether autosurvey left the row in the discard set

`independent_full_response_audit.md` should include:

- all-row audit scope
- proof that audited rows match the source row count
- independent classification counts
- comparison to autosurvey reviewed rows
- missed review candidates
- possible missed discard or escalation rows
- audit conclusion

`deep_findings_analysis.md` should include:

- executive readout
- final row decisions
- review themes
- discard recommendations
- critical next-pass signals
- what the run teaches about the survey
- deep semantic sample
- flow audit

`agent_final_review_dashboard.html` and `agent_final_visual_findings_report.md` should include:

- publication-style visual KPI summary
- Recharts charts for action counts, second-pass disposition, agent decisions, review themes, fielding trends, review candidate clusters, supplier stacked outcomes, kept-review themes, and supplier/source concentrations
- new discoveries from the raw export
- expanded scorer criteria shape
- response analysis criteria table
- cited semantic observations and trend observations
- editorial figure numbers, source notes, concise narrative callouts, and a readable report hierarchy
- agent discard set
- full semantic decision table for every agent-reviewed row
- kept-review synthesis
- next-pass signal inventory
- deep semantic review sample
- cited agent findings essay
- positive findings report with strong retained response examples and guardrails that protected good data
- agent escalation packet
- internal quality signal bank for long-term learning
- citations for all run-specific and method-specific claims
- clear artifact index for content review

Dashboard rules:

- The dashboard is a research publication, not a table export. It must include or link to agent-authored prose from `agent_findings_essay.md`.
- Long explanations must not appear in wide tables. Use prose sections, cards, or linked Markdown artifacts for reasoning. Use tables only as compact ledgers.
- Selected row examples should read as analyst prose. They can be written directly in the essay or in any companion artifact the agent chooses. Do not require a rigid row-note schema.
- Raw full response chains belong in CSV or audit artifacts. Dashboard-visible chain content must be summarized into short readable observations.
- Any dashboard that wraps prose into one-character columns, overlaps sections, or requires the reviewer to infer meaning from flags is not deliverable.

Cycle rules:

- Read the previous findings essay, escalation packet, internal signal bank, and next-pass inventory before the next dataset.
- Carry promoted signals into first-pass context only when they survived full-chain review.
- Keep false-positive guardrails active, especially for speed-only rows, keyword topic misses, short but valid answers, shared IP context, and enthusiastic repeated characters.
- Promote direct non-response or repeated placeholder patterns only when the full chain does not recover useful context.
- End each cycle with a plain critique of what improved, what still failed, and whether the next dataset should rerun with changed first-pass context.

## Client-Facing Summary

Title: Survey Data Quality Review

Recommended language:

"We reviewed completed responses using a structured quality process covering completion time, answer consistency, straightlining, topic relevance of open-ended responses, duplicate signals, and open-end authenticity indicators. Scores and counts were computed from auditable evidence. Reader-facing annotations were generated as a separate Opulent semantic-judgment layer, explaining what the response pattern means, how the language should be interpreted, and why the recommendation is trustworthy. Only rows with converging evidence are escalated as discard candidates; rows that survive the extra pass are retained with rationale and used to improve future survey-question framing."

Avoid:

- "The AI removed respondents."
- "This respondent is fake."
- "AI-likelihood proves fraud."

Prefer:

- "Recommended for review."
- "Discard candidate after second-pass analysis."
- "Kept with survey-question recommendation."
- "Agent semantic analysis indicates..."
- "Trust rationale..."
- "Potential quality concern."
- "Flagged by the rubric and reviewed against source evidence."
