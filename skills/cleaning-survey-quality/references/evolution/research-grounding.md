# Research Grounding

Use these patterns when changing the cleaning loop.

## Data-to-Dashboard

Source: https://arxiv.org/abs/2505.23695 and https://www.alphaxiv.org/abs/2505.23695

Relevant pattern: modular agents should move from data profiling to domain/concept detection, multi-perspective analysis, evaluation, and self-reflection. For survey quality, this maps to:

1. Profile respondent data and detect available quality signals.
2. Extract survey-specific concepts such as qtime, straightlining, brand consistency, open-end relevance, duplicate IDs/IPs, and panel/source artifacts.
3. Generate multiple evidence views: respondent-level flags, aggregate quality summary, source/vendor concentration, and open-end risk review.
4. Reflect against adjudicated PM labels before changing any rubric.

## Insight Agents

Source: https://arxiv.org/abs/2601.20048 and https://www.alphaxiv.org/abs/2601.20048

Relevant pattern: hierarchical plan-and-execute agents with a manager/router and specialized workers improve coverage, accuracy, and latency. For survey quality:

- Manager: chooses profile, score, compare, evolve, or report task.
- Data presentation worker: produces row-level evidence tables and summaries.
- Insight generation worker: proposes rubric changes only when supported by adjudicated examples.
- OOD gate: reject tasks outside survey quality cleaning, respondent fraud, or PM reporting.

## Databricks Multi-Agent Audience Intelligence

Source: https://www.databricks.com/blog/multi-agent-approach-audience-intelligence

Relevant pattern: business users need natural-language access over curated data, but metrics must be computed by governed deterministic tools. For this skillset, let agents reason about which checks to run and generate reader-facing annotations, but compute scores, lift, counts, thresholds, and deltas in scripts.

Important implementation principles:

- Encode data expertise once through curated column definitions, examples, and scoring rules.
- Keep natural-language intent and generated outputs auditable.
- Separate LLM/Opulent reasoning from deterministic computation: scripts compute evidence and metrics; agents generate semantic analysis, linguistic fluency assessment, and trust rationale.
- Use feedback loops to build institutional knowledge over repeated survey waves.

## AutoResearch

Source: https://arxiv.org/abs/2605.23204 and https://www.alphaxiv.org/abs/2605.23204

Relevant pattern: workflow-level automation needs grounding, hypothesis formation, experimentation/tool use, validation/review, and reporting/communication. Apply the five evaluation dimensions:

- Novelty: does a proposed rubric catch a new real quality pattern?
- Validity: does the criterion match PM adjudication and survey intent?
- Impact: does it reduce review load or improve bad-respondent capture?
- Reliability: does it reproduce across waves and reruns?
- Provenance: can every decision be traced to columns, values, examples, and rubric version?

Do not claim full autonomy. This domain should operate as AI execution with human verification until enough adjudicated waves prove stable precision/recall.

## Reference-Free Open-End Evaluation

Source: https://arxiv.org/abs/2510.06242 and https://www.alphaxiv.org/abs/2510.06242

Relevant pattern: open-ended human survey responses should not be evaluated like LLM-generated text. Use a transparent two-stage process:

1. Filter gibberish and nonsensical responses.
2. Evaluate effort, relevance, and completeness as separate dimensions.

For survey quality, this means an open-end response should not receive a single opaque "bad" label. The report should show whether the concern is low effort, topic mismatch, incomplete answer, or obvious nonsensical text. Only transparent deterministic signals should directly affect the first-pass score; nuanced semantic judgments should be agent-generated annotations that explain meaning, language quality, and confidence before routing to review or later calibration.

## LLM/Opulent Judges For Unstructured Text

Source: https://arxiv.org/abs/2501.08167 and https://www.alphaxiv.org/abs/2501.08167

Relevant pattern: LLM-as-judge methods can scale text evaluation, but they are proxy evaluators and can diverge from human judgment. Agreement should be evaluated with multiple metrics, not just percent agreement. Humans may better detect subtle context-specific nuance, and model-model agreement can be misleadingly high.

Methodology implications:

- Use PM adjudication as the baseline when available.
- Report exact agreement, precision/recall, Cohen's kappa, and ordinal/severity disagreements where labels exist.
- Watch for overestimation, verbosity bias, position bias, recency bias, confirmation bias, and anchoring.
- Validate semantic criteria on held-out examples before accepting them as stable.
- Do not generalize a judge prompt or rubric across survey contexts without re-evaluation.
