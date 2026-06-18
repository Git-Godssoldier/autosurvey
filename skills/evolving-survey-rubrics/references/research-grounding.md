# Research Grounding For Rubric Evolution

Use AutoResearch as the operating model:

- Grounding: collect source workbooks, PM labels, column definitions, and existing rubrics.
- Hypothesis: propose a concrete rubric change.
- Experiment: replay the scoring script on adjudicated data.
- Validation: compare precision, recall, mismatch examples, and PM-review burden.
- Reporting: publish the proposed rubric with evidence and provenance.

Use Data-to-Dashboard as the analysis model:

- Start with profiling and concept extraction before asking model-generated questions.
- Use multi-perspective analysis: respondent-level, criterion-level, supplier/source-level, and wave-level.
- Add self-reflection by checking whether the proposed change is simpler than the failure it fixes.

Use Insight Agents as the orchestration model:

- Manager routes between profile, compare, evolve, and report.
- Worker agents should produce deterministic artifacts, not freeform decisions.
- Out-of-domain requests should be rejected or handed back to the user.

Use the Databricks pattern:

- Agents reason about which analyses to run.
- Scripts compute the numbers.
- Every result is auditable.

Use reference-free open-end evaluation:

- Open-end quality should be decomposed into gibberish/noise, effort, relevance, and completeness.
- Do not evolve one broad "bad open end" criterion when the failure mode is more specific.
- Treat nuanced semantic judgments as review candidates until validated against PM labels.

Use LLM/Opulent-judge reliability controls:

- Human PM adjudication is the calibration baseline.
- Percent agreement is insufficient by itself; include precision, recall, Cohen's kappa, and ordinal disagreement severity when labels exist.
- Watch for verbosity, position/order, recency, confirmation, anchoring, and overestimation failures.
- A judge that agrees with another judge more than with PMs is not automatically better.
