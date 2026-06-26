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

Add an authenticity layer after the dimension read:

- prompt fit: whether the answer gives the kind of evidence requested
- respondent-universe fit: whether the answer sounds like the qualified audience
- adjacent-topic fit: whether related language is valid in context or from the wrong universe
- lived detail: whether the answer contains concrete role, project, product, material, supplier, location, cost, constraint, customer, or decision detail when the prompt asks for experience
- chain coherence: whether the open end aligns with screeners, role answers, brand answers, matrices, demographics, and other narratives
- fabricated-language risk: survey-meta answers, polished generic claims, off-domain professional claims, copied text, sentence drift, or evasive filler

Example: construction language inside a home-renovation prompt is not automatically wrong. It may be a direct fit when it refers to renovation work, contractors, materials, permits, costs, or homeowner decision-making. It becomes wrong-universe or generic filler when it never answers the home-renovation task and instead describes unrelated commercial construction or abstract business management.

### Weighted Evidence Expansion

Every candidate signal should receive an agent-derived weight basis before it affects final decisions.

Evaluate:

- prompt fit
- question similarity
- time plausibility
- semantic authenticity
- full-chain coherence
- signal independence
- recurrence across respondents or suppliers
- accepted-row guardrails
- survey-design ambiguity

Scripts may generate candidate scores, similarity candidates, timing buckets, and repeated-pattern counts. The agent must decide whether the evidence should become first-pass routing, final discard review, reporting context, or no future behavior.

### Straightlining Evaluation

Do not score straightlining as repeated answers alone. Assess:

- whether the grid items are semantically similar or clearly different
- whether answer options carry the same meaning across items
- whether reverse-coded or contrast items exist
- whether page, section, or question answer time was plausible
- whether open-ended responses show authentic engagement
- whether accepted rows show the same pattern as a valid uniform opinion

Straightlining becomes stronger when semantically different items receive the same answer under implausible timing and the response chain is weak. It becomes weaker when items are similar, the respondent plausibly feels the same way, or the open-ended chain is coherent.

### LLM/Opulent Judge Evaluation

- Treat LLM-style judgments as proxy evaluators, not ground truth.
- Treat semantic similarity judgments as proxy evaluations until grounded in the Datamap, question-set authenticity map, response chain, and accepted counterexamples.
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
- Straightline overconfidence: treating repeated grid answers as proof of low quality without assessing question similarity or answer-time plausibility.
- Weight laundering: presenting a numeric weight as objective when the agent has not explained the semantic expansion behind it.
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
