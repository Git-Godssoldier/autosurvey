# Evaluation Methodology

Use this file when changing survey-quality methodology, especially open-ended response evaluation. The goal is adaptive data-analysis discovery plus rigorous evaluation, not a brittle flat rubric.

## Research Grounding

Sources:

- Transparent Reference-free Automated Evaluation of Open-Ended User Survey Responses: https://arxiv.org/abs/2510.06242 and https://www.alphaxiv.org/abs/2510.06242
- Potential and Perils of Large Language Models as Judges of Unstructured Textual Data: https://arxiv.org/abs/2501.08167 and https://www.alphaxiv.org/abs/2501.08167

## Tactics

### Dynamic Survey Discovery

- Profile each incoming survey before scoring; do not assume question names or available fields are stable.
- Discover analysis families first, then decide which are scorable, which need mapping, and which are unavailable.
- Treat every candidate analysis as a hypothesis with evidence, not as a permanent rule.
- Include survey-level context: project topic, target audience, fielding source, supplier/source, quotas, and known survey-specific traps.
- Report missing signals as blockers. A missing qtime, absent respondent key, or unmapped brand relationship is a finding.

### Open-Ended Response Evaluation

Use a two-stage approach:

1. Gibberish and noise filtering:
   - remove or flag nonsensical text, symbol-only answers, repeated characters, obvious placeholders, and non-response strings.
   - keep this deterministic and transparent where possible.
2. Reference-free quality dimensions:
   - effort: did the respondent provide enough substantive content for the question?
   - relevance: does the answer address the asked topic and respondent role?
   - completeness: does the answer satisfy the requested scope, such as explaining why or giving a usable example?

For open ends, prefer dimension-level evidence over a single "bad open end" label.

### LLM/Opulent Judge Evaluation

- Treat LLM-style judgments as proxy evaluators, not ground truth.
- Use human PM adjudication as the calibration baseline when available.
- Evaluate agreement with multiple metrics: exact agreement, precision, recall, Cohen's kappa, and ordinal disagreement severity.
- Track where Opulent overestimates quality or severity, not only where it misses bad rows.
- Use blind or held-out adjudicated examples before accepting any new semantic rule.
- Consider multi-judge or model-disagreement review for nuanced open ends when the project risk is high.

### Generalization

- Validate across waves, survey topics, supplier/source groups, and question designs before calling a rule stable.
- Prefer analysis families and dimension scoring over exact column-specific rules.
- Keep rubric changes reversible and require a rollback condition.
- Separate candidate discovery, scoring, evaluation, and reporting artifacts so each can be audited independently.

## Anti-Patterns

- Flat rubric scoring: adding points from static rules without checking whether those rules fit the current survey design.
- Helper-column dependence: requiring fields such as `Respondent Score`, `Recommended_Action`, or `*_AI_Likelihood` for a raw survey pass.
- Semantic overconfidence: treating a model's judgment of relevance or authenticity as proof of fraud.
- Single-metric validation: reporting only percent agreement or match rate without chance-adjusted or ordinal agreement checks.
- Model-agreement trap: assuming models are right because they agree with each other; model-model agreement can exceed human-model agreement while still missing context-specific nuance.
- Verbosity bias: rewarding long open ends even when they are generic, evasive, or off-topic.
- Position/order bias: judging examples differently because of their order in a prompt or report.
- Recency, confirmation, and anchoring bias: letting previous flags, supplier reputation, or prior wave decisions predetermine the current judgment.
- Overgeneralization: carrying a rule from one survey category, language, or audience into another without evals.
- Hidden prompt rule: changing prompt wording or model behavior without a corresponding versioned criterion, examples, and evaluation result.

## Acceptance Standard

A methodology change is acceptable only when it:

- improves a measured outcome on adjudicated data or clearly improves discovery coverage;
- includes row-level examples and source evidence;
- reports precision/recall and at least one agreement metric beyond percent agreement when labels exist;
- preserves PM override and escalation pathways;
- documents where the rule should not apply.
