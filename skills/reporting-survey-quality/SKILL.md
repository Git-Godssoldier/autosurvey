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
   - expanded scorer criteria section showing criterion id, tags, source columns, generated weight, support, decision role, rationale, and citation
   - response analysis criteria section showing which criteria actually fired, how many rows they touched, and how to read each criterion
   - dataset observations section with a cited list of semantic patterns, trend findings, supplier/source patterns, and survey-design implications
   - structured discard table with agent rationale and source evidence
   - full semantic decision table for all rows the agent investigated
   - kept-review synthesis table with survey-question and parameter recommendations
   - next-pass signal inventory that states what should change before the next first-pass scoring run
   - deep semantic review sample that shows a subset of reviewed rows with the full reasoning and next-pass learning
   - deep findings memo that states the main findings, limits, discard recommendations, and workflow changes
   - editorial figure captions, source notes, callouts, and artifact navigation for fast content review
   - artifact index linking the CSV, Markdown, and dashboard outputs

## Required Artifacts

Use outputs from `run_quality_loop.py`:

- `quality_report.md`
- `quality_summary.json`
- `row_scores.csv`
- `discovery_profiles.json`
- `generated_scoring_models.json`
- `methodology_config.json`
- `generated_criteria_catalog.csv`
- `respondent_review_table.csv`
- `response_criteria_evidence_table.csv`
- `agent_annotation_table.csv`
- `agent_review_judgment_table.csv`
- `agent_discard_set.csv`
- `agent_kept_review_synthesis.md`
- `agent_kept_review_synthesis_table.csv`
- `next_pass_signal_inventory.csv`
- `next_pass_signal_inventory.md`
- `next_pass_first_pass_config.json`
- `deep_semantic_review_sample.csv`
- `deep_semantic_review_sample.md`
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
- Return a subset of reviewed rows with deeper semantic analysis. Include the final decision, raw evidence, language assessment, trust basis, next action, and the learning that should change the next pass.
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
- Read `references/escalation-reporting.md` before changing escalation sections.
- Read `references/visual-dashboard-design.md` before changing final dashboard or chart generation.
