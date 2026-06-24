# Accepted-Respondent Guardrails

Every suspicious respondent must be tested against human explanations. Accepted-row learning is as important as rejected-row learning.

## Protect These Patterns Unless Evidence Converges

- Concise but direct answers that name the actual product, brand, concern, or preference.
- Fast respondents whose closed answers and open ends form a coherent chain.
- Non-native English, spelling errors, grammar mistakes, or rough phrasing with clear meaning.
- Emotional, enthusiastic, angry, repetitive, or informal language that still answers the prompt.
- Ordinary copyediting, restatements, and small revisions in open ends.
- Legitimate extreme opinions, including all-high or all-low ratings, when the explanation supports them.
- Coherent “do not know,” “none,” or low-awareness behavior across the survey.
- Accessibility, mobile, fatigue, or device context that could explain short answers.
- Uniform matrices when items are similar and no contradiction appears.
- Shared household or workplace technical identifiers when responses are semantically distinct.

## Limits On Protection

Protective evidence must be local and field-specific. A plausible brand funnel, normal timing, or coherent persona does not automatically protect an invalid answer elsewhere in the row.

Do not overprotect:

- Numeric or placeholder text in open-end fields unless the prompt clearly asked for a number.
- Retailers, platforms, or generic category nouns entered where a brand, product, reason, or memory was requested.
- “None,” “NA,” “good,” “quality,” or one-word category terms when they do not answer the field and no other respondent-specific grounding exists.
- Long completion times when the response chain still contains off-category text, all-brand selection, fully uniform grids, or route-incoherent detail.
- A single grounded answer surrounded by multiple invalid or nonresponsive fields.

## Required Counterfactual

Before exclusion, ask:

If this respondent were real, what would explain the evidence?

If that explanation fits the whole chain better than fabrication does, keep or review the row rather than excluding it.

## Similar Accepted Controls

After labels are available, every proposed signal should be attacked with accepted respondents who share part of the pattern. The final signal must explain why the rejected rows are different from those accepted controls.
