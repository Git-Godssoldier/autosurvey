# Report Templates

## PM Operations Summary

Title: Survey Quality Cleaning Summary

Sections:

1. Review volume
   - Respondents reviewed
   - Keep
   - Light review
   - Review closely
2. Severity and escalation
   - severity level
   - owner
   - count
   - percent of completes
3. Second-pass disposition
   - `discard_candidate`
   - `keep_with_recommendation`
   - `keep_no_issue`
   - count and percent of completes
   - note that only `discard_candidate` rows enter the escalation queue
4. Discovery, candidate analyses, and generated criteria
   - analysis id
   - status
   - candidate columns
   - mapping needs
   - generated criterion id
   - tags
   - rationale
   - whether the criterion is scorable, needs context, needs mapping, or needs feedback
5. Flag breakdown
   - criterion id
   - count
   - percent of completes
   - action impact
6. Evidence examples
   - respondent key
   - criterion
   - observed value
   - justification
7. Agent semantic annotations
   - respondent key
   - second-pass decision
   - semantic analysis
   - linguistic fluency assessment
   - trust rationale
   - recommended next step
8. Survivor recommendations
   - recommendation text
   - survivor row count
   - representative kept respondent keys
   - why these rows were kept
   - how the survey question should be strengthened to prevent fuzzy or gameable answers
9. Discard escalation queue
   - respondent key
   - severity
   - owner
   - score
   - trigger pattern
   - discard rationale
   - agent semantic analysis
   - agent trust rationale
10. Generated model status
   - stable on this evaluation set, proposed change, or needs adjudication
   - metric impact
   - rollback condition
11. Evaluation metrics when labels exist
   - exact agreement
   - precision and recall for review routing
   - Cohen's kappa
   - ordinal action disagreement
   - over-escalation and under-escalation counts
12. Table artifact index
   - generated criteria catalog
   - respondent review table
   - criterion evidence table
   - agent annotation table
   - agent review judgment table
   - agent discard set
   - kept-review synthesis table
   - PM-facing Markdown sample
13. Final visual review package
   - KPI cards: total responses, review-tagged rows, agent discard rows, kept review rows
   - bar charts: action counts, second-pass disposition, agent review decisions, kept-review themes, supplier/source concentrations
   - discard table with agent rationale and source evidence
   - kept-review synthesis table with survey-question and parameter recommendations
   - final guidance on what to discard, what to keep, and what to improve in the survey instrument

## Required Table Fields

`respondent_review_table.csv` should include:

- respondent key
- respondent metadata available in source data: record, date, status, supplier/source, RID, IP address, qtime, geography, quota/marker fields
- computed action, score, severity, owner, and escalation reason
- second-pass decision: `discard_candidate`, `keep_with_recommendation`, or `keep_no_issue`
- discard rationale when the row should be reviewed for removal
- survivor rationale when the row is kept
- survey-question-strengthening recommendation when the row is kept with evidence
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step
- generated tags
- all triggered criteria
- observed evidence
- criterion explanations

`response_criteria_evidence_table.csv` should include one row per respondent criterion:

- respondent key and metadata
- criterion id
- source column
- observed value
- generated points
- criterion explanation
- generated-weight rationale
- second-pass decision
- discard rationale
- survivor rationale
- survey-question-strengthening recommendation
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step

`agent_annotation_table.csv` should include one row per respondent:

- respondent key and core metadata
- computed action and score as supporting context
- second-pass decision
- triggered criteria and observed evidence
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step

`generated_criteria_catalog.csv` should include:

- generated criterion id
- scoring id
- status
- tags
- source columns
- criterion rationale
- generated weight
- weight rationale
- support rows and support rate

`agent_review_judgment_table.csv` should include:

- every row tagged for review by the scoring pass
- agent final decision: discard or keep with review note
- agent semantic judgment
- discard or keep rationale
- next step
- respondent metadata and observed evidence

`agent_kept_review_synthesis_table.csv` should include:

- kept review theme
- count of retained review rows
- example respondent keys
- why kept
- survey-question recommendation
- quality parameter recommendation
- issue pattern

`agent_final_review_dashboard.html` and `agent_final_visual_findings_report.md` should include:

- publication-style visual KPI summary
- Recharts charts for action counts, second-pass disposition, agent decisions, review themes, fielding trends, review candidate clusters, supplier stacked outcomes, kept-review themes, and supplier/source concentrations
- new discoveries from the raw export
- expanded scorer criteria shape
- response analysis criteria table
- cited semantic observations and trend observations
- editorial figure numbers, source notes, concise narrative callouts, and a readable report hierarchy
- agent discard set
- full semantic decision table for every agent-reviewed row
- kept-review synthesis
- citations for all run-specific and method-specific claims
- clear artifact index for content review

## Client-Facing Summary

Title: Survey Data Quality Review

Recommended language:

"We reviewed completed responses using a structured quality process covering completion time, answer consistency, straightlining, topic relevance of open-ended responses, duplicate signals, and open-end authenticity indicators. Scores and counts were computed from auditable evidence. Reader-facing annotations were generated as a separate Opulent semantic-judgment layer, explaining what the response pattern means, how the language should be interpreted, and why the recommendation is trustworthy. Only rows with converging evidence are escalated as discard candidates; rows that survive the extra pass are retained with rationale and used to improve future survey-question framing."

Avoid:

- "The AI removed respondents."
- "This respondent is fake."
- "AI-likelihood proves fraud."

Prefer:

- "Recommended for review."
- "Discard candidate after second-pass analysis."
- "Kept with survey-question recommendation."
- "Agent semantic analysis indicates..."
- "Trust rationale..."
- "Potential quality concern."
- "Flagged by the rubric and reviewed against source evidence."
