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

```bash
python3 skills/cleaning-survey-quality/scripts/run_quality_loop.py \
  --input-file /path/to/unannotated_export.xlsx \
  --topic-keywords "topic,brand,category" \
  --output-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_quality_brief.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_next_pass_review_artifacts.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_independent_full_response_audit.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_deep_findings_analysis.py \
  --run-dir /path/to/private_outputs/run

python3 skills/reporting-survey-quality/scripts/build_visual_dashboard.py \
  --run-dir /path/to/private_outputs/run
```

The run is not complete until an agent has reviewed the flagged rows and the output
folder contains:

- `agent_review_judgment_table.csv`
- `agent_discard_set.csv`
- `agent_kept_review_synthesis_table.csv`
- `next_pass_signal_inventory.csv`
- `next_pass_first_pass_config.json`
- `deep_semantic_review_sample.md`
- `independent_full_response_audit.md`
- `deep_findings_analysis.md`

Use `next_pass_signal_inventory.csv` and `next_pass_first_pass_config.json`
before the next scoring run. These files record which signals should be scored,
which signals should stay review-only, and what extra evidence is needed.
