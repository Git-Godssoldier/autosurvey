# Full Workflow Specification

This file contains the detailed workflow steps for a full run. The normal input is an unannotated Decipher export. Steps marked **[EVOLUTION]** are only relevant when client-annotated data (with `status` labels) is available for improving the pipeline.

## Pre-Run Framing

Before writing or running scoring scripts:

1. Read `references/production/agentic-escalation-path.md`.
2. Read `references/production/client-terminology-glossary.md` and use it to define client, PM, survey, and quality terms before writing final artifacts.
3. Read `references/production/decipher-blind-authenticity-review.md` for every normal Autosurvey run on a blank Decipher export.
4. Read `references/production/agent-authored-row-review.md` before any respondent-level scoring, validation, or final review.
5. **[EVOLUTION]** Read `references/evolution/authenticity-first-calibration.md` when TFG status labels, client annotations, or calibration against accepted/rejected rows are in scope.
6. Read `references/production/semantic-signal-expansion.md` before evaluating straightlining, speed, open ends, duplicate technical signals, semantic similarity, topic fit, bot suspicion, LLM suspicion, or fabricated-response detection.
7. **[EVOLUTION]** Read `references/evolution/tfg-status-derived-detection-methodology.md` when TFG status-labeled training workbooks, status-derived rules, bot suspicion, LLM suspicion, or fabricated-response detection are part of the task.
8. **[EVOLUTION]** Read `references/evolution/dataset-cycle-loop.md` when the run is part of an improvement cycle, a rerun, a multi-dataset pass, or a workflow-hardening request.
9. State the definition of done for this dataset in plain words.
10. Identify the source files, expected final artifacts, and what would block final delivery.
11. **[EVOLUTION]** If the run includes internal comments, PM notes, client annotations, or prior criteria, read `references/evolution/internal-signal-learning.md`.
12. Start a short decision trail for non-obvious choices.
13. **[EVOLUTION]** If a client annotated workbook exists, treat it as methodology-development data. In TFG cleaning-answer workbooks, `status = 3` means accepted, `status = 5` means rejected.
14. **[EVOLUTION]** Separate client rejection probability from fabrication or authenticity risk. A `status = 5` row is an observed client rejection, not proof of bot behavior, LLM use, or fraud.
15. **[EVOLUTION]** In annotated methodology runs, exclude leakage before feature extraction. Treat marker or quota fields, client action fields, final decision fields, review helper fields, condition assignment fields, no-answer helper fields, QC helper fields, channel tracking fields, token fields, hidden cleaning fields, and formulas or formatting that reveal cleaning decisions as unavailable to the blind reviewer.

## Workbook Exploration

Before writing or running scoring scripts:

1. Read the sheet names, row count, column count, and Datamap or codebook when present.
2. Inspect representative raw rows and nonempty examples from every open-ended field family.
3. Read any internal comments, review notes, prior quality essays, prior escalation packets, prior signal inventories, and prior signal banks that are available for the same client, survey family, or product area.
4. Parse the Datamap before scoring. Extract prompt text, value labels, field groups, and response options.
5. Map field roles before scoring. At minimum, separate job-role screeners, brand-list fields, narrative open ends, other-specify fields, survey-feedback fields, timing fields, supplier/source fields, respondent identifiers, IP/device fields, and review/helper fields.
6. Field-role mapping must adapt to the workbook's actual language. Do not assume that role context is always named `qcoe1`.
7. Map demographics separately from quality evidence. Required demographic fields include `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, and `qPolitics` when present.
8. Stitch the full question chain before scoring. Use the Datamap or codebook prompt text when available.
9. Plan for a whole-population read from the start. The final package must include an independent full-response audit with one row per source respondent and a stitched chain for every row.
10. Plan for row-level agent authorship from the start. Every source respondent must receive an agent-written semantic judgment.
11. Build an agent-authored question-set authenticity map before scoring text quality. For every major question set, state the intended respondent universe, the field role, what an authentic answer should sound like, what a fabricated or bot-like answer might sound like, what learned guardrails apply, and which source fields support that interpretation.
12. Build a Question Contract and question-relation graph before respondent analysis.
13. Build a semantic signal expansion plan before final weighting.
14. Decide which fields can be scored in the first pass, which fields need PM mapping, and which fields should only produce review notes.
15. Do not run topic mismatch or low-effort scoring until the field role is clear.
16. Build a project-specific topic and answer map from the Datamap, prompt wording, value labels, and sampled open ends before topic or answer-depth scoring.

## Quality Hypothesis Building

1. State which fabricated, bot-like, LLM-assisted, inattentive, or otherwise unauthentic response patterns are plausible in this dataset.
2. State what evidence would confirm each pattern and what evidence would make it a false positive.
3. Turn annotated-data learnings into semantic reading questions, not keyword rules.
4. Treat learned labels such as `badopen` as boundaries to understand, not fields to imitate.
5. Give every discovery a provisional weight with a plain-language rationale.
6. Aggregate evidence by family before routing. Multiple straightlining metrics count as one matrix-behavior family unless another independent family also supports concern.
7. Separate row-level authenticity evidence from wave-level context and survey-design findings.
8. Add relevant internal comments or criteria as hypotheses, not as automatic rules.

## Per-Field Chain Validity

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

## Why Ordering Matters

The Delta t=5 analysis proved that 55.7% of rejected rows have a perfectly valid on-topic outro. Their rejection was not driven by open-end semantic content alone. The driver was found in the full chain — funnel inconsistency, brand awareness anomalies, supplier concentration, or technical evidence. If the review had stopped at the open-end layer, it would have missed the majority of rejection drivers.

Conversely, the Delta analysis proved that classic straightlining (same-answer across all matrix rows) separated zero rejected rows from accepted rows. If the review had led with matrix straightlining, it would have produced zero signal. The chain layer correctly down-weighted this signal to zero because the 7 matrix rows are semantically distinct product categories and no one actually flat-lined all of them.

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

## Agent Annotation Layer

Generate annotations as a separate judgment pass after scoring and second-pass disposition. The annotation pass should use the score, tags, source evidence, respondent metadata, and open-ended text context, but it should not simply restate deterministic criteria.

The final review layer must act as a critic and analyst, not as a rubber stamp for criteria. Static checks create the case file. The agent then reads the full response chain, looks for benign explanations, expressive language, recoverable context, and semantic patterns that static rules cannot see, and only then decides whether discard is justified.

Before finalizing any text-driven discard:

1. Read the stitched full response chain, including the prompt context for each answered field when available.
2. Treat the criteria as the initial case file, not the final decision.
3. Look for counterevidence, such as substantive answers elsewhere in the chain, enthusiastic or expressive wording, recoverable role context, or answers that are short but valid for the question.
4. Decide whether a reasonable PM would treat the answer as substantively off-topic or merely awkward/variant phrasing.
5. Check whether the text concern independently strengthens another quality signal, such as straightlining or speed.
6. Downgrade rows where semantic evidence is plausible or only weakly ambiguous; keep them with a survey-question recommendation instead.
7. Escalate only rows where the agent can explain, in fluent business language, why the response should be discarded after critic verification.

## Escalation Policy

Generate severity thresholds from the generated provisional weights for the current dataset. Then run an extra pass on all possible escalations before routing:

- Escalate only rows where the extra pass determines `second_pass_decision = discard_candidate`.
- A discard candidate must have converging evidence strong enough that the operational question is whether it should be thrown out, not whether it needs more ordinary review.
- When one of the converging signals is semantic or linguistic, the agent must verify the semantic judgment before escalation. Do not let a keyword-based topic mismatch create a discard by itself.
- Rows that survive the extra pass must not be escalated. Mark them `keep_with_recommendation` when some evidence remains.
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

## Raw-Data Discovery

On unannotated files, the script can score:

- raw qtime under four minutes
- duplicate IP address
- repeated matrix-grid answers
- obvious low-effort open ends
- optional topic mismatch when `--topic-keywords` is supplied

These scripted checks are routing evidence. Duplicate IP, device, or session evidence is not enough by itself. Treat it as independent context unless multiple supposedly independent respondents share the same weak chain pattern or another quality signal.

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

## Delivery Verification

Before calling the run complete:

1. Verify that the annotated Excel has the same row count as the source file.
2. Verify that every row has a `Final_Score` and `Final_Judgment`.
3. Verify that the dashboard renders without unreadable tables or overlapping prose.
4. Verify that discard rows in the Excel match the discard table in the dashboard.
5. Assign a terminal state: success, clean no-op, blocked, approval required, or no-progress stop.

Before starting the next run, review the prior run's discard set and key signals. Decide which signals can be added to the first-pass context, which signals need PM examples, which signals are false-positive guardrails, and which signals should remain agent-only.
