# Building self-improving survey quality agents with Opulent

How Opulent can help research teams turn unannotated survey exports, PM review, semantic response analysis, and graded feedback into a measurable data-quality improvement loop.

## Measurable survey-quality improvement

Real survey data does not arrive with clean labels. It arrives as Decipher exports with respondent IDs, timestamps, supplier markers, IP addresses, matrix answers, open-ended text, brand columns, fielding metadata, and project-specific question codes. The work is not just to flag bad rows. The work is to discover which analyses are meaningful for the current file, explain the evidence clearly enough that PMs trust the review queue, and improve the criteria from one wave to the next.

For market research teams, that matters because data quality is part of the product. PMs already review completes closely, but AI-assisted workflows can still leave them spending an hour or more checking whether poor-quality respondents were missed. Opulent’s role is to make that loop faster, more consistent, and more auditable while preserving the PM’s authority over final business judgment.

The system starts with raw, unannotated data. It profiles the export, discovers available analysis families, generates criteria with tags and rationale, proposes provisional weights only after inspecting the current evidence, uses scoring to find review candidates, gives every possible discard an extra semantic pass, and produces a cited dashboard and findings report. Later PM decisions become the measurement surface for improving the methodology, criteria, weights, escalation rules, and survey-question design.

This design follows the same broad pattern as self-improving agents: production traces reveal failures, those failures become eval targets, and the system improves through bounded, measurable changes rather than one-off prompt edits.[^openai-self-improving] It also borrows from AutoResearch thinking: discovery, validation, provenance, reporting, and revision are all first-class steps, not afterthoughts.[^autoresearch]

## The problem

The hard part of survey cleaning is not one individual rule. It is the gap between raw survey artifacts and trusted PM judgment.

A fast complete may be a bad respondent, but only if the duration field is reliable and the surrounding evidence agrees. A matrix may look straightlined, but only if the columns are correctly grouped and the pattern is not an artifact of a long or poorly designed grid. An open-ended answer may be off-topic, low-effort, incomplete, incoherent, or fluent but evasive, but that judgment has to be grounded in the survey context. A brand answer may be inconsistent, but the relationship between awareness, usage, preference, consideration, and recommendation fields is project-specific.

If those signals are not captured as structured evidence, every project becomes a manual reread. If they are captured as fixed rules without discovery and review, the system becomes brittle. The right loop has to support both: autonomous discovery of candidate analyses and expert correction that becomes measurable improvement.

The newest version of the process treats criteria as generated hypotheses rather than preset policy. It asks what can be scored in this file, what needs survey mapping, what needs PM feedback, what should only route a row into review, and what evidence is strong enough for an Opulent agent to decide that a response should be discarded.

## The Opulent approach: a three-part loop

Opulent’s survey-quality loop has three parts:

1. Stay close to PM review: PMs decide what actually counts as poor quality. Their final decisions are the calibration signal, not an inconvenience to automate away.
2. Make every raw export produce evidence and judgment: The system profiles the file, discovers candidate analyses, generates criteria with tags and rationale, records the source column and observed value for each finding, gives every possible discard an extra pass, and then uses Opulent to write semantic annotations that explain what the evidence means.
3. Turn traces and graded examples into evals: Once PM decisions exist, Opulent compares generated criteria, provisional weights, survivor recommendations, discard-candidate routing, final review, and survey-design recommendations. Repeated misses become bounded methodology changes with precision, recall, examples, citations, and rollback conditions.

That means the first pass works on unannotated files, while the graded set becomes the measurement surface that helps the methodology, generated criteria, generated tags, generated weights, and escalation instructions get better.

The process is deliberately discovery-first. Research on data-to-dashboard systems points to modular agents that detect domains, extract concepts, generate multi-perspective analyses, and self-reflect before publishing visual outputs.[^data-to-dashboard] Research on insight agents points to manager-and-worker patterns, routing, planning, dynamic domain knowledge, and human evaluation as production constraints.[^insight-agents] Opulent applies those ideas to survey quality: one part of the system discovers and scores candidate evidence, another part makes semantic judgments, and another part writes the report that PMs and client stakeholders can review.

## Unannotated survey example

A new Decipher export arrives during fielding. It has no `Respondent Score`, no `Recommended_Action`, and no hand-annotated flag columns. Opulent inspects the workbook and identifies the usable signals:

- `qtime` as completion duration
- `ipAddress` as a duplicate technical signal
- `q32_Lr...` columns as rating-grid groups
- `qEthnicr8oe`, `qcoe1`, `q9r10oe`, `q43r11oe`, and `outro` as open-ended fields
- possible brand fields such as `POSSIBLEBRANDSr1` through `POSSIBLEBRANDSr9`
- supplier, date, and respondent-key fields that can support trend and source analysis

Opulent then generates candidate criteria rather than assuming a fixed scoring policy. For this export, the current process can generate:

- `short_duration::qtime`, tagged `timing`, `speeding`, and `attention`
- `duplicate_technical_identifier::ipAddress`, tagged `technical_duplicate`, `possible_repeat_entry`, and `supplier_quality`
- `matrix_straightlining::q32_Lr1` through `matrix_straightlining::q32_Lr9`, tagged `straightlining`, `grid_quality`, and `attention`
- `open_end_effort::*`, `open_end_relevance::*`, and `open_end_completeness::*` criteria for discovered open-ended fields
- `brand_consistency::project_mapping`, tagged `brand_consistency`, `logic_mapping`, and `survey_specific`
- trend, supplier concentration, and fielding-window observations for reporting rather than direct discard

Each criterion has a status: `scorable`, `needs_context`, `needs_mapping`, or `needs_feedback`. The system generates provisional weights only after it sees the current dataset, observed support, evidence type, available adjudication, and PM feedback. Those weights are trial artifacts, not permanent policy.

The shape of a generated criterion matters as much as the number attached to it. Each criterion should carry:

- a criterion ID and human-readable name
- tags that explain the quality family
- source columns and any grouping logic
- observed support count and support rate
- provisional weight, threshold, and decision role
- evidence examples with respondent metadata
- semantic interpretation guidance
- escalation trigger and discard threshold
- keep-with-recommendation rule
- known failure modes and anti-patterns
- citation to the local artifact or external method source that supports the claim

This is a direct response to the main risk in survey cleaning: flat scoring can look precise while hiding weak assumptions. Open-ended response research supports separating effort, relevance, and completeness rather than collapsing every text issue into one bad-response label.[^reference-free-survey] Research on LLMs as judges also warns that model judgment is useful but not ground truth; subtle, context-specific nuance still requires careful calibration and human review.[^llm-judges]

## 1. A PM correction reveals a failure

After the first pass, a PM may discard a row Opulent kept, keep a row Opulent treated as a discard candidate, or point out that a survivor pattern should change future question design. That difference is not automatically a model failure. It might reflect a project nuance, a missing generated criterion, a bad generated weight, an unmapped brand relationship, a fuzzy answer framework, a supplier-specific artifact, or a judgment that should remain human.

The useful part is that the correction is now structured. Opulent can see which generated criterion fired, which tags were attached, what evidence triggered the score, what provisional weight was used, what the agent concluded, what the PM changed, and which final action was accepted. That converts PM review from a terminal clean-up step into a training signal for the next quality pass.

The escalation rule is intentionally narrow. Scoring can route rows for review, but only the Opulent agent makes the final discard judgment. It investigates the review-tagged candidates, reads the relevant raw text and metadata, and writes a discard set only when the evidence supports throwing the row out. Rows that survive the extra pass are kept with recommendations, not buried. Those survivor patterns are aggregated into survey-design guidance: clearer prompts, structured reason codes, minimum exposure timers, better matrix design, better brand mapping, and stricter follow-up requirements when vague answers can be gamed.

This distinction matters. A keyword mismatch can be useful as a discovery signal, but it should not become the final semantic decision. A single straightlined matrix can be useful as a review signal, but it should not automatically remove a respondent when open-ended context is recoverable. A short duration can be useful as a timing signal, but it should not decide the case without corroborating evidence.

## 2. Review traces become eval targets

Each run produces a trace:

- raw workbook and sheet
- discovered signal profile
- generated candidate criteria with tags and rationale
- generated scoring model with provisional weights and thresholds
- response-criteria evidence table with one row per triggered criterion
- row-level scores and justifications
- second-pass disposition
- Opulent semantic analysis
- linguistic fluency assessment
- trust rationale
- survivor rationales and survey-question recommendations
- discard-candidate escalation routing
- agent discard set
- recommended actions
- PM final actions when available
- methodology config version
- cited final dashboard and findings report

Each run also ends with a visual review package. Opulent turns the trace into a publication-style dashboard with KPI cards, Recharts figures, source notes, cluster plots, pie charts, stacked bar charts, trend analysis, agent discard tables, kept-review synthesis, criteria inventories, and an artifact index. The goal is the same as the scoring loop: make the decision path easy to inspect. A PM should be able to see what was reviewed, what the agent decided to discard, what survived, what new criteria were discovered, and which survey questions or fielding parameters should improve without rereading every CSV.

Internal validation runs show why this matters. In a representative unannotated export, Opulent narrowed a large respondent file to a small review queue, recommended discard only where converging evidence supported removal, and kept the remaining review-tagged rows as survey improvement signals. The generated criteria catalog included duration, technical duplicate, matrix straightlining, open-end effort, open-end relevance, open-end completeness, and brand-consistency mapping candidates.

The response criteria evidence table surfaced broad topic-mismatch evidence, low-effort open ends, straightlined matrices, and sub-four-minute completes. The agent then corrected the risk of over-discarding: many script-surfaced topic mismatches were actually relevant after reading the language in context. Final discards were not removed because a flat score crossed a threshold. They were removed only when the agent found converging evidence, such as:

- one row combined matrix straightlining with a nonresponsive open-end answer
- one row combined very short completion time with incoherent open-end language

The kept rows produced the next layer of value. Some were single-signal matrix straightlining cases that should remain in the data but motivate better matrix design. Others were low-information open ends with recoverable context, topic-mismatch candidates that the agent judged contextually relevant, or short-duration rows without enough corroborating evidence to discard.

When a graded workbook is available, Opulent compares generated recommendations and final labels by respondent key. It evaluates exact agreement, precision, recall, Cohen’s kappa, ordinal action disagreement, discard-candidate misses, survivor over-escalations, and review burden. Repeated differences become eval targets. The goal is not to make the scorer harsher. The goal is to make the judgment more correct, more explainable, and easier to review.

## 3. The finding becomes a hill to climb for Opulent

Once a repeated failure is packaged as an eval target, Opulent can work on it directly:

- Inspect the raw columns, discovery profile, row evidence, semantic judgments, PM corrections, and report observations.
- Propose the smallest methodology, generated-criteria, generated-tag, generated-weight, escalation, or reporting change that explains the reviewed examples.
- Replay the scoring loop against the graded set and a fresh unannotated export.
- Measure precision, recall, agreement, review burden, discard-candidate escalation accuracy, survivor recommendation quality, citation coverage, and regression risk.
- Publish an evolution record with examples, rationale, citations, and a rollback condition.

If the evidence is weak, Opulent does not force a change. It reports that the current generated scoring model still needs calibration, that a generated criterion needs mapping or feedback, or that more adjudicated examples are needed.

The enhanced process makes the hill concrete. A finding can be:

- a missing criterion, such as open-ended completeness for a qualification-critical question
- a bad criterion shape, such as treating keyword mismatch as semantic failure
- a bad weight, such as assigning too much review severity to a single matrix block
- an escalation error, such as sending review-only rows as discard candidates
- a report gap, such as failing to show respondent metadata or source evidence
- a survey-design problem, such as a long matrix that invites uniform answers
- a fielding-parameter problem, such as pages that allow valuable questions to be completed too quickly

The agent’s job is not to blindly raise or lower scores. It is to discover the smallest change that improves the whole loop.

## How to use Opulent to build this loop

The practical task environment is small:

```text
/survey-quality-loop/
|
+-- source-data/
|   +-- raw Decipher exports
|   +-- optional graded workbooks
|
+-- skills/
|   +-- cleaning-survey-quality/
|   +-- evolving-survey-rubrics/
|   +-- reporting-survey-quality/
|
+-- outputs/
|   +-- discovery_profiles.json
|   +-- generated_criteria_catalog.csv
|   +-- generated_scoring_models.json
|   +-- response_criteria_evidence_table.csv
|   +-- row_scores.csv
|   +-- respondent_review_table.csv
|   +-- agent_annotation_table.csv
|   +-- agent_review_judgment_table.csv
|   +-- agent_discard_set.csv
|   +-- agent_kept_review_synthesis.md
|   +-- agent_kept_review_synthesis_table.csv
|   +-- methodology_config.json
|   +-- quality_report.md
|   +-- pm_quality_brief.md
|   +-- client_quality_summary.md
|   +-- agent_final_review_dashboard.html
|   +-- agent_final_visual_findings_report.md
```

The writable surface is the methodology, generated criteria, generated scoring model, skills, and reports. The read-only evidence is the raw export, graded examples, PM decisions, and row-level trace. That separation keeps the loop auditable: Opulent can improve the process without mutating the source evidence.

The final reporting step is part of the method, not a presentation extra. Every run should produce:

- a PM operations report with rows by action, severity, criterion, evidence, escalation owner, and semantic rationale
- a client-facing summary with aggregate counts and defensible language
- a final visual review package with charts, dashboards, citations, semantic decision tables, generated criteria, response analysis criteria, and survey-question recommendations

The dashboard should be designed like an executive research artifact. It should use clear hierarchy, restrained color, figure captions, source notes, trend charts, cluster plots, pie charts, stacked bars, supplier/source views, and readable tables. The writing should use plain language: what the agent read, what it decided, and why the decision is defensible.[^cbre][^plain-writing][^recharts][^open-design]

## Expanding to new survey programs

The same pattern works across survey programs because it does not depend on a closed scoring policy. Each new survey starts from raw data discovery, then generates its own candidate criteria, tags, mappings, provisional weights, escalation logic, semantic review instructions, and reporting structure. Project-specific mappings for brand logic, category terminology, supplier behavior, respondent role, and open-end expectations become feedback into the methodology rather than one-off prompt edits.

Over time, the system should reduce PM review volume while preserving defensibility. PMs steer the process through the decisions they already make. Opulent turns those decisions into structured evidence, evals, skill updates, and measured reporting improvements.

This is also where the audience-intelligence pattern applies. Databricks describes the value of agentic audience systems as discovering unknown relationships in the data and bridging strategy with execution.[^databricks-audience] Survey quality needs the same bridge. PMs bring fielding context and client risk. Opulent brings broad discovery, repeatable analysis, semantic review, and cited reporting. The system gets stronger when those two sides stay connected.

The best survey-quality agents are not just faster reviewers. They are systems that make quality decisions easier to inspect, easier to contest, easier to improve, and easier to share with every fielding wave.

## Sources

[^openai-self-improving]: OpenAI, “Building self-improving tax agents with Codex,” May 27, 2026. https://openai.com/index/building-self-improving-tax-agents-with-codex/

[^autoresearch]: Guiyao Tie et al., “AutoResearch AI: Towards AI-Powered Research Automation for Scientific Discovery,” arXiv:2605.23204, submitted May 22, 2026. https://arxiv.org/abs/2605.23204

[^data-to-dashboard]: Ran Zhang and Mohannad Elhamod, “Data-to-Dashboard: Multi-Agent LLM Framework for Insightful Visualization in Enterprise Analytics,” arXiv:2505.23695, submitted May 29, 2025. https://arxiv.org/abs/2505.23695

[^insight-agents]: Jincheng Bai et al., “Insight Agents: An LLM-Based Multi-Agent System for Data Insights,” arXiv:2601.20048, last revised February 2, 2026. https://arxiv.org/abs/2601.20048

[^reference-free-survey]: Subin An et al., “Transparent Reference-free Automated Evaluation of Open-Ended User Survey Responses,” arXiv:2510.06242, submitted October 3, 2025. https://arxiv.org/abs/2510.06242

[^llm-judges]: Rewina Bedemariam et al., “Potential and Perils of Large Language Models as Judges of Unstructured Textual Data,” arXiv:2501.08167, last revised January 20, 2025. https://arxiv.org/abs/2501.08167

[^databricks-audience]: Bradley Munday and Tyler Hickey, “A multi-agent approach to audience intelligence,” Databricks Blog, April 6, 2026. https://www.databricks.com/blog/multi-agent-approach-audience-intelligence

[^cbre]: CBRE, “European Data Centres Figures,” visual reporting reference. https://mktgdocs.cbre.com/2299/12439527-d1a2-46eb-b485-4fd377f0d618-223048296/European_Data_Centres_Figures_.pdf

[^plain-writing]: Shreya Shankar, `plain-writing-skill`. https://github.com/shreyashankar/plain-writing-skill

[^recharts]: Recharts documentation. https://recharts.org/

[^open-design]: `nexu-io/open-design`. https://github.com/nexu-io/open-design
