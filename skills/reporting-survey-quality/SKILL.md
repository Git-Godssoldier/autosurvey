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
3. Final visual review package:
   - publication-quality KPI dashboard for total responses, review-tagged rows, agent discard rows, and kept review rows
   - Recharts visualizations for action counts, second-pass disposition, agent review decisions, review themes, trend analysis, candidate clusters, stacked supplier outcomes, kept-review themes, and supplier/source concentrations
   - discovery section showing new candidate analyses, field groups, open-end fields, mapping needs, and unavailable analyses
   - Datamap-derived field-role section showing how the workflow mapped key fields before scoring
   - expanded scorer criteria section showing criterion id, tags, source columns, generated weight, support, decision role, rationale, and citation
   - response analysis criteria section showing which criteria actually fired, how many rows they touched, and how to read each criterion
   - dataset observations section with a cited list of semantic patterns, trend findings, supplier/source patterns, and survey-design implications
   - structured discard table with agent rationale and source evidence
   - full semantic decision table for all rows the agent investigated, including the number of fields reviewed from the stitched full response chain, programmatic discard recommendation, verifier counterevidence, and semantic discard basis
   - full-chain analyst readout that turns best and worst response-chain examples into readable prose, not just tables
   - agent escalation packet that completes the PM review path, including discard rows, hard kept cases, uncertain cases, citations, and next actions
   - internal quality signal bank that captures comments, criteria, bad-response patterns, fabricated-response patterns, false positives, and next-run signal status
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

Then do the agent essay pass before the dashboard is built. This is not a rote script step and it is not a form to fill out. The agent must read the Datamap field-role mapping, discovery profile, demographic summary, scorer criteria, independent full-response audit, full-chain analyst readout, deep semantic sample, agent judgment table, kept review synthesis, and next-pass signal inventory. The agent must then write:

- `agent_findings_essay.md`: a natural prose essay with citations. It should explain what happened in the run, what the agent discovered, what the field-role mapping changed, what the best and worst response chains reveal, what the final discard or keep decisions mean, what demographic and aggregate context matters, what should change in the next pass, and where the workflow should challenge itself.

The essay can have whatever sections the agent believes best explain the run. Do not force the agent to populate a fixed set of row-note fields. Scripts may carry this prose into HTML, but scripts must not be treated as the author of the reasoning. If this essay is missing, the run is not ready for client or PM review.

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
- Explain that criteria and provisional weights were generated from discovery, trial evidence, findings, and feedback.
- Include justifications for each scoring criterion.
- Include respondent metadata in review tables wherever source fields are available.
- Include the stitched question chain and full response chain before final semantic review. The final agent judgment table must carry `response_chain_field_count`, `full_response_chain`, `semantic_review_chain_field_count`, and `semantic_review_chain`. The final discard decision must be based on those chains plus the surfaced evidence.
- Parse the Datamap into field roles before scoring or reporting. The final report should show that the workflow understood the role of `qcoe1`, `q9`, `q10`, `q32`, `q43`, and `outro` before making semantic decisions.
- Include demographic and aggregate insights from source data. These are report context, not quality-discard evidence by themselves.
- Treat client-annotated Excel review files as the minimum audit surface. The report should match their practical columns and counts where relevant, then go further with prose analysis, chain-level semantic judgment, verifier counterevidence, kept-row learning, and next-pass signal updates.
- Always report fielding start/date/timestamp discoveries when the source file contains them. Odd-hour starts and start bursts are fielding-context findings unless corroborating evidence or project rules make them row-level evidence.
- Treat scoring criteria as the initial case file. The final agent layer must act as a critic and verifier that can supersede static checks when the full chain gives a meaningful semantic explanation.
- Treat the dashboard and final report as agent-authored research products, not formatted log output. The agent must personally synthesize the exploration, field-role mapping, response chains, programmatic signals, counterevidence, demographics, and next-pass learning into clear prose before publishing.
- Do not let scripted string assembly substitute for analysis. A script can assemble charts, ledgers, citations, and HTML, but the deciding prose must come from `agent_findings_essay.md`, written after the agent studies the run materials.
- Write `agent_escalation_packet.md` as the complete operational answer. It must say which rows should be reviewed for exclusion, which suspicious rows were kept, which internal comments or criteria shaped the decision, what evidence was decisive, what evidence was inconclusive, and what the PM should do next. If no rows should be discarded, the packet must still explain why.
- Write `internal_quality_signal_bank.md` as an internal learning artifact. It should preserve useful comments, criteria, false-positive guardrails, and recurring bad-response or fabricated-response patterns for later runs. It is not client copy.
- Show verifier counterevidence and semantic discard basis for final decisions. A row should not be discarded only because a programmatic check fired.
- Produce readable prose analysis for the best and worst full response chains. The prose must explain what the agent saw, why strong rows are strong, why bad rows remain bad after full-chain review, and where the workflow should challenge itself.
- Do not treat generated tables, charts, or flags as the final communication layer. They support analysis, but the report must include agent-written interpretation for the human reviewer.
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
- Reconcile the escalation packet against the agent discard set and agent judgment table. Every discard row must appear in the packet. Every packet discard must appear in the discard set. Any mismatch blocks delivery until the agent resolves it.
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

## When To Read References

- Read `references/report-templates.md` before writing PM or client summaries.
- Read `references/client-annotation-benchmark.md` when using client-provided annotated workbooks as examples or calibration material.
- Read `references/escalation-reporting.md` before changing escalation sections.
- Read `references/visual-dashboard-design.md` before changing final dashboard or chart generation.
