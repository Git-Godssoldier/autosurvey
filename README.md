# autosurvey

Reusable Opulent skills for autonomous survey-quality cleaning, rubric evolution, and reporting.

This repository contains only reusable skill instructions, scripts, and methodology docs. It intentionally excludes client source data, generated outputs, workbooks, row-level exports, dashboards, and PDFs.

## Skills

- `skills/cleaning-survey-quality`: profiles unannotated survey exports, discovers candidate quality analyses, generates criteria and provisional weights, writes row-level evidence, and prepares agent semantic review surfaces.
- `skills/evolving-survey-rubrics`: compares generated recommendations against adjudicated PM review and proposes bounded methodology, criteria, weight, or escalation improvements.
- `skills/reporting-survey-quality`: builds PM/client briefs and final visual review packages with criteria, semantic decisions, survey-design recommendations, charts, citations, and artifact indexes.

## Data Safety

Do not commit source survey files or generated client artifacts. `.gitignore` blocks common data and output formats by default.

Use `skills/cleaning-survey-quality/references/project-context-template.md` for private client context in a downstream workspace.

## Basic Flow

Before running the scoring script, explore the workbook. Read the sheet names,
row count, column count, Datamap or codebook, and examples from each open-ended
field family. Map field roles first. Do not run topic mismatch or low-effort
scoring until you know whether a field is a job-role screener, brand list,
narrative open end, other-specify field, survey-feedback field, timing field,
supplier/source field, identifier field, or review/helper field.

The run must also build question and response chains. First stitch the ordered
question chain from the Datamap or codebook when it is present. If prompt text is
not available, use the ordered source columns. Then stitch each respondent's full
response chain from all nonempty answer fields. The final agent semantic review
must review that full chain before it writes a structured discard decision.

The final agent review is a critic and verifier layer. The criteria create the
case file, but they do not decide discard on their own. The agent must look for
semantic counterevidence in the full response chain, including meaningful but
awkward wording, enthusiastic repeated characters, and short answers that are
valid for the prompt.

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

python3 skills/reporting-survey-quality/scripts/build_next_pass_review_artifacts.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_deep_findings_analysis.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_visual_dashboard.py \
  --run-dir /path/to/private_outputs/run
```

The run is not complete until an agent has reviewed the flagged rows and the output
folder contains:

- `question_chain_map.csv`
- `agent_review_judgment_table.csv`
- `agent_discard_set.csv`
- `agent_findings_essay.md`
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

Before the final assistant response, preview the main artifacts so the user can follow the work. At minimum, inspect the findings essay, escalation packet, internal signal bank, dashboard, visual findings report, discard set, final judgment table, kept synthesis, next-pass inventory, demographic summary, and deep semantic sample.

The final assistant response must be client-facing and email-ready. It should read as one cohesive survey-quality review, not as a list of tool runs or internal agent steps. Use "we discovered," "we reviewed," and "we recommend" for conclusions. Do not write phrases such as "the agent final pass" or "the agent reviewed" in client-facing copy unless the user asks for internal implementation detail.

The final assistant response must include:

- a clear narrative of the core discoveries
- core discard recommendations with respondent keys and row or cell-level citations when source coordinates are available
- key statistical analysis from the run, including totals, review rate, discard rate, top review themes, supplier or source patterns, timing findings, and demographic context
- brief natural-language descriptions of the important artifacts and where to open them
- a statement that every required artifact was verified, or a precise list of missing or inconclusive items
- a short note on what should feed the next first-pass analysis

The response should be ready to paste into a client email after removing local file paths if needed. It should summarize what was found, what should be done, and why the evidence supports the recommendation.

Use `next_pass_signal_inventory.csv` and `next_pass_first_pass_config.json`
before the next scoring run. These files record which signals should be scored,
which signals should stay review-only, and what extra evidence is needed.

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
