# Agentic escalation path

Use this reference when the agent needs to move from a raw survey export to final discard choices without waiting for a human to interpret the evidence.

## Working posture

The agent owns the full escalation path. Scripts and scores narrow the work. They do not decide the final meaning of a respondent. The agent must read the materials, form hypotheses, test them, read the response chains, decide what survives, and write the final reasoning.

Use these principles.

- Evidence before narrative. Collect the facts before telling the story.
- Exploration before scripting. Understand the workbook, Datamap, comments, and field roles before writing or running scoring logic.
- Static checks are the case file. The final discard call comes from critic review.
- A benign alternative must be considered before discard. If a plausible benign read survives, keep the row with a note.
- Every important claim needs a citation to a local artifact, workbook field, row key, or generated table.
- A verdict can be `verified`, `not verified`, or `inconclusive`. Inconclusive is not a discard.
- When a lesson repeats, encode it in the workflow or signal bank. Do not leave it as memory.

## Phase 1. Frame the run

Before scoring, state the definition of done in plain words. It should be checkable.

At minimum, done means:

- all source files and sheets were inventoried
- the Datamap or codebook was read when present
- field roles were mapped before scoring
- all internal comments, PM notes, client annotations, and prior criteria available to the run were reviewed
- deterministic evidence artifacts were generated
- the agent read the full response chain before any final discard choice
- a cited findings essay exists
- an escalation packet exists
- the internal signal bank was updated
- the dashboard and Markdown report render without unreadable table or layout failures

If any item is missing, say what is missing and whether it blocks final delivery.

## Phase 2. Explore before scoring

Read enough of the workbook to understand its shape.

Do not start with a scorer. First identify:

- source sheets and row counts
- respondent identifier fields
- Datamap prompt text, value labels, and skip logic when available
- open ends, other-specify fields, matrix grids, brand or preference fields, timing fields, IP fields, source or supplier fields, flags, and helper columns
- demographic fields
- internal comments, client annotations, PM notes, and prior criteria
- fields that may look like evidence but are only context

Write down what each field family can and cannot prove. This is important on unfamiliar datasets because a field name can mislead the scorer.

## Phase 3. Build hypotheses

Turn exploration into hypotheses. A hypothesis is a possible quality signal that can be tested.

Examples:

- Very fast completion may indicate low attention.
- A duplicate IP may indicate a shared household, a panel routing artifact, or duplicate respondent behavior.
- A generic open end may indicate low effort, but it may also be a valid short answer if the prompt asked for a simple reason.
- A repeated character pattern may be spam, or it may be enthusiasm in an otherwise meaningful response.
- A straight grid may indicate inattentiveness, or it may be a real uniform opinion.

For each hypothesis, state what evidence would support it, what evidence would weaken it, and whether it can ever become row-level discard evidence without another signal.

## Phase 4. Run deterministic evidence

Use scripts to produce repeatable evidence. The evidence should be broad enough to catch likely quality issues and narrow enough that the agent can audit it.

Good deterministic evidence includes:

- completion time patterns
- fielding start and date patterns
- duplicate technical signals
- source or supplier concentrations
- matrix straightlining and low-variance grids
- missing or contradictory respondent fields
- open-end length and repetition
- possible topic mismatch
- possible AI or fabricated response helper fields
- brand or preference inconsistency
- criteria support counts

Do not let deterministic evidence become the final story. It is the evidence base.

## Phase 5. Critic review

For every possible discard row, the agent must read the full response chain.

The review should answer:

- What does the respondent appear to be saying?
- Which prompt or field role matters most?
- Does the answer fit the survey topic when read in context?
- Are weak answers isolated, or repeated across important fields?
- Does timing, source, duplicate evidence, or straightlining strengthen the concern?
- What is the strongest benign explanation?
- What would make the row safe to keep?
- What would make the row unsafe to keep?

The agent should be willing to overrule a static check. It should also be willing to escalate a row that a static threshold missed when the full chain shows a strong bad-response pattern.

## Phase 6. Decide

Use these decision meanings.

- `discard_candidate`: The row has converging evidence strong enough that a reviewer is deciding whether to remove it from the dataset.
- `keep_with_review_note`: The row has some concern, but the agent found enough context or counterevidence to keep it.
- `keep_no_issue`: The row has no meaningful quality concern after review.
- `inconclusive`: The row cannot be decided from the available evidence. Treat it as keep with review note unless project rules say otherwise.

A discard candidate should usually have more than one signal. A single signal can support discard only when it is decisive by itself, such as a non-response in a required high-value open end plus no useful context in the chain.

## Phase 7. Produce the escalation packet

The escalation packet is the operational end of the path. It should let a PM or data quality lead act without rebuilding the analysis.

Write `agent_escalation_packet.md` with:

- the final discard set and why each row belongs there
- the strongest kept review cases and why they were kept
- any rows the agent found hard to decide
- the internal comments or criteria that affected the review
- row-level citations to local artifacts
- aggregate patterns that need survey or fielding changes
- what the next pass should do differently

If there are no discards, the packet should still exist and explain why the escalation path ended with no row-level removals.

## Phase 8. Prove the package

Before delivery, verify the real artifacts, not a self-report.

Check:

- all required files exist
- counts reconcile across respondent review, agent judgment, discard set, kept synthesis, and dashboard
- every discard row appears in the escalation packet
- every cited artifact path resolves
- dashboard and Markdown report include the findings essay
- visible tables do not squeeze prose into unreadable cells

If a check is inconclusive, name it. Do not call the run complete.
