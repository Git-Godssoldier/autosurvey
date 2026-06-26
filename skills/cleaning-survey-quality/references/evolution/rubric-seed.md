# Historical Seed Context

Seeded from a historical adjudicated survey-quality workbook.

This file is historical context from the graded example. Do not treat these as fixed weights or closed criteria. The active process should generate candidate criteria, tags, provisional weights, thresholds, and rationale from each dataset and then evolve them through PM feedback and adjudicated evaluations.

## Historical Signals

| Signal | Source signal | PM justification |
|---|---|---|
| qtime under 4 minutes | `qtime_Under_4_Minutes == Yes` | Very short completes are unlikely to reflect attentive survey completion. |
| preferred brand inconsistency | `Preferred_Brand_Inconsistent_With_Consideration_Recommendation == Yes` | Preferred brand conflicts with consideration or recommendation answers. |
| matrix straightlining | `Q32_Straightline == Yes` | Repeated or near-repeated matrix answers suggest inattentive responding. |
| topic relevance concern | `outro_Topic_Relevance` contains off-topic or not gas/C-store relevant | Open-end answer does not address the survey topic or target context. |
| duplicate technical signal | `Duplicate_IP == Yes` | Potential duplicate/fraud signal; review before removal. |
| open-end authenticity concern | `*_AI_Likelihood` or inherited open-end concern flags | Open-ended response shows AI-like or low-authenticity traits, but this should route to review rather than automatic removal. |

## Historical Discovery Ideas

These are examples of discovery ideas the agent may regenerate, split, merge, or reject based on the active dataset:

- raw duration/speeding from discovered qtime or elapsed-time columns
- matrix straightlining from discovered grid groups
- duplicate technical identifiers from IP or comparable respondent technical fields
- open-end effort from placeholders, nonsense, repeated characters, or very low-information text
- open-end relevance from survey-topic context
- open-end completeness from PM-defined expectations for the question
- brand consistency from project-specific brand/preference/consideration/recommendation mappings

Brand consistency discovery is intentionally conservative. The loop finds likely brand, preference, consideration, and recommendation columns, but a project-specific mapping must define which answers conflict before points are assigned.

## Generated Thresholds

Action thresholds must be generated from the current run's generated weights and observed support. Do not copy thresholds from the historical graded file into a new survey.

## Generated Escalation Bands

Escalation bands must be generated from the run's generated thresholds and evidence patterns, then narrowed by a second pass.

Escalate to Data Quality Lead only when the second pass marks the row as a `discard_candidate`. Rows with evidence that survive the extra pass should be kept with rationale and aggregated into survey-question or fielding-control recommendations.

## Evolution Guardrails

- Prefer methodology/discovery improvements over point changes when the same evidence is already available.
- Promote a generated criterion only when it improves review precision, recall, discard-candidate routing, survivor recommendations, or discovery coverage on adjudicated examples.
- Never optimize against unreviewed model output alone.
- Never require annotated helper columns for a raw quality pass.
- Keep generated scoring models, methodology configs, and evolution records with version dates.
- Require row-level examples for every proposed change.
