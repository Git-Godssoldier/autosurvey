# Escalation Reporting

PM reports must make escalation operational and narrow. Escalation means the extra pass found a discard candidate, not that a row has any review signal.

## Required Sections

1. Action counts
2. Severity and escalation counts
3. Second-pass disposition counts
4. Discovery profile
5. Candidate analyses
6. Top flag patterns
7. Review queue sample
8. Survivor recommendations
9. Discard escalation queue
10. Rubric status
11. Final dashboard with charts and visual decision summaries

## Escalation Queue Fields

For each `discard_candidate` row include:

- respondent key
- severity level
- escalation owner
- computed score
- triggering criteria
- discard rationale
- agent semantic analysis
- agent linguistic fluency assessment
- agent trust rationale
- agent recommended next step
- respondent metadata needed for adjudication

Do not include `keep_with_recommendation` or `keep_no_issue` rows in the escalation queue. Report kept rows in survivor recommendations with an explanation of why they survived and how the survey question could be strengthened.

The escalation queue should read like an expert judgment memo, not a score dump. Use the deterministic score as supporting evidence, then explain the semantic pattern, language quality, why alternative benign interpretations are weak, and what exact decision the reviewer needs to make.

For text-driven escalations, include the Opulent agent's semantic adjudication. The report should distinguish "script surfaced a possible topic mismatch" from "agent verified that the answer is substantively off-topic or non-responsive."

In the final dashboard, use the agent review judgment table as the source of truth for discard decisions. Raw `discard_candidate` scoring rows can be shown as candidate evidence, but the final visual queue must reflect the agent-created discard set.

## Owner Routing

- No escalation: survivor rows, including rows with weak or ambiguous evidence.
- Data Quality Lead: row-level discard candidates after second-pass analysis.
- Senior PM / Research Lead: aggregate methodology, question-design, or supplier/source pattern decisions, not routine individual survivor rows.
- Client Strategy Lead: only for aggregate client-facing implications, not individual row triage.

## Wave-Level Escalation

Escalate the whole run, not just individual rows, when:

- `Review closely` exceeds 2% of completes.
- any single supplier/source dominates the severe queue.
- duplicate technical signals appear in clusters.
- a required analysis family is unavailable because source data is missing.

Wave-level escalation should include aggregate recommendations for clearer question framing, structured answer formats, follow-up prompts, or fielding controls. It should not reclassify individual survivor rows as discard candidates without row-level converging evidence.

## Dashboard Requirements

The final visual review package must include:

- counts and proportions for response volume, review-tagged rows, agent discards, and kept review rows
- Recharts charts for scoring actions, second-pass disposition, agent decisions, review themes, fielding trends, review candidate clusters, supplier stacked outcomes, kept-review themes, and supplier/source concentrations
- discovery and criteria sections that explain how the review candidates were found
- cited observations about semantic patterns, trend behavior, and supplier/source concentration
- a focused agent discard table
- a semantic decision table covering all rows the agent investigated
- a kept-review synthesis chart or table that turns retained review rows into survey-question and parameter improvements
- links or filenames for all supporting CSV and Markdown artifacts
- editorial report structure: publication header, figure captions, source notes, short decision callouts, and dense readable tables
