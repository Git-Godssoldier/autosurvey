# Dataset Cycle Loop

Use this reference when a survey-quality run must improve from one dataset to the next. It adapts patterns from productivity skills and loop workflows without turning autosurvey into a rigid form.

## Principles to carry into autosurvey

- **Completion criteria**: Every phase needs a checkable finish line. "Review the data" is not enough. "Every source row appears in the independent full-response audit and row counts reconcile" is checkable.
- **Legwork before asking**: If a question can be answered from the workbook, Datamap, prior artifacts, source files, or repo, inspect those first. Ask the user only when the missing answer changes safety, scope, or final authority.
- **One-question escalation**: When a question is unavoidable, ask one short question and explain the recommended default.
- **Learning record**: Each run should preserve one to five compact lessons that change the next run. These lessons live in the internal signal bank or workflow improvement log, not in the client-facing report.
- **Artifact handoff**: Long runs should leave a handoff paragraph with paths to the decisive artifacts. Do not repeat material that already exists in reports, tables, or dashboards.
- **Bounded loop**: A dataset cycle should observe current evidence, choose one high-value improvement, act, verify, record the lesson, and then stop or continue based on a named terminal state.

## Autosurvey cycle

Run each dataset cycle as a bounded loop.

1. **Observe**: Read the source workbook, Datamap, prior findings essay, prior escalation packet, prior signal bank, and prior next-pass inventory when available.
2. **Choose**: Pick the highest-value next action from current evidence. This may be field-role repair, topic-map repair, first-pass signal promotion, false-positive guardrail repair, prose rewrite, dashboard repair, or final discard verification.
3. **Act**: Make one bounded change or produce one artifact. Avoid broad rewrites that change the evidence, the recommendation, and the presentation at the same time.
4. **Verify**: Run the relevant acceptance check. Count reconciliation, full-chain presence, discard-set reconciliation, dashboard readability, citation resolution, and prose quality are common checks.
5. **Record**: Write the outcome and lesson into the internal signal bank or workflow improvement log. Use artifact paths, respondent keys, fields, and row counts as evidence pointers.
6. **Repeat or stop**: Continue only when fresh evidence from verification changes the next action. Stop when the run reaches a terminal state.

## Terminal states

Use these states in workflow notes, signal banks, or final response when a cycle ends.

- **Success**: Required artifacts exist, counts reconcile, dashboard and Markdown are readable, final decisions reconcile, and prose is client-ready.
- **Clean no-op**: The cycle found no material change to make, and the evidence supports that result.
- **Blocked**: A required file, Datamap, source workbook, permission, or human decision is missing.
- **Approval required**: The next action would remove data, expose raw respondent text externally, change production-like behavior, send a message, or make a client-facing claim that needs approval.
- **No-progress stop**: Another cycle would repeat the same evidence without improving decisions, artifacts, or learning.

Errors, missing artifacts, and unreadable dashboards are not success.

## Challenge review

Before final delivery, challenge the run as if trying to break it.

Ask:

- Did the run read every row through the independent full-response audit?
- Did the final discard set depend on full-chain meaning rather than isolated flags?
- Did the run protect plausible short, awkward, enthusiastic, or misspelled answers from over-discard?
- Did the run find anything that first-pass scoring missed?
- Did the run over-review anything because a field role, topic map, or answer expectation was wrong?
- Did the final prose explain discoveries, evidence, uncertainty, and next-pass learning in readable language?
- Did the dashboard make the same decisions readable without forcing the reviewer into CSV files?

If the answer is no, repair the smallest material weakness and rerun the relevant check.

## Learning record format

Add compact learning records to `internal_quality_signal_bank.md` or `workflow_improvement_log.md`.

Use this shape:

```md
### Learning record: <short title>

<One to three sentences that state what changed, why it matters, and what the next run should do differently. Cite the artifact, row key, field, or count that proved it.>
```

Write a learning record when:

- a field role was corrected
- a false-positive guardrail protected good data
- a signal was promoted, demoted, or kept review-only
- a missed bad-response pattern was found outside the first-pass queue
- the dashboard or prose failed and the repair changed the workflow

Do not write a learning record for routine script execution or for material already captured as a glossary definition.

## Handoff paragraph

For long or interrupted work, add a short handoff paragraph to the workflow improvement log.

It should state:

- the current terminal state
- the next action
- the artifacts to read first
- the checks that already passed
- the unresolved blocker or decision, if any

Reference artifacts by path. Do not copy large tables, raw responses, or private respondent text into the handoff.
