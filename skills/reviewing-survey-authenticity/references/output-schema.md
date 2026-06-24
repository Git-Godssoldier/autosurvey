# Output Schema

The pre-seal artifacts must be authored by the agent and complete for every respondent.

## Sealed Decision Ledger

One row per respondent:

- `respondent_stable_id`
- `source_row_reference`
- `decision_tier`
- `discard_recommendation`
- `authenticity_risk`
- `client_rejection_probability`
- `reviewer_confidence`
- `forensic_rationale`
- `human_advocate_countercase`
- `evidence_judge_summary`
- `suspicious_signal_families`
- `protective_evidence`
- `question_chain_citations`
- `open_end_citations`
- `matrix_or_scale_citations`
- `timing_or_route_citations`
- `technical_context_citations`
- `near_control_needed`
- `learning_notes`

## Narrative Report

Write a client-facing research essay that explains:

- What the review discovered.
- What kinds of records are most likely fabricated or bad-faith.
- What kinds of suspicious-looking records should be protected.
- Which survey structures made review easier or harder.
- How the next pass should improve.
- Which cases best illustrate the boundary, with row and field citations.

The prose should be cohesive, specific, and readable. It must not be a list of generated feature labels.

## Public Output

For a deliverable run, public outputs should be limited to:

- A client-facing workbook containing the original rows plus appended review columns.
- A client-facing narrative report.

Internal artifacts may include the question contract, sealed ledger, seal manifest, label comparison, residual-error notes, and skill-evolution notes.
