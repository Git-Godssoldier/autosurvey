# Internal signal learning

Use this reference when a run has internal comments, PM feedback, client annotations, prior discard criteria, or repeated findings that should improve later runs.

## Purpose

Internal comments and criteria are learning material. They should help the agent notice bad or fabricated responses over time. They should not become rigid discard rules unless enough evidence supports them.

The goal is to build a signal bank that improves review quality across datasets while keeping the final agent judgment open-ended.

## What to collect

Before scoring, look for:

- client annotated workbooks
- PM final review columns
- comments in cells or workbook notes
- prior quality briefs
- previous `agent_findings_essay.md` files
- previous `agent_escalation_packet.md` files
- previous `next_pass_signal_inventory.csv` files
- known bad response examples
- known false positives
- fielding or supplier notes
- project-specific qualification rules

Treat all collected comments as evidence with a source, not as truth by default.

## How to read internal comments

For each useful comment or criterion, ask:

- What behavior is it describing?
- Is it row-level evidence, wave-level context, or a survey design problem?
- Does it apply to this dataset, this audience, and this field role?
- What would a benign version look like?
- What evidence would confirm it?
- What evidence would make it a false positive?
- Should it change first-pass scoring, review routing, final escalation, or only the final essay?

Do not copy client wording into the final client-facing output unless it is approved for sharing.

## Signal status

Use these statuses when updating `internal_quality_signal_bank.md`.

- `observed`: The agent saw the pattern, but it needs more evidence.
- `review_routing`: The pattern is useful for shortening the review list.
- `candidate_discard_signal`: The pattern can support discard when it converges with other evidence.
- `pm_approved_discard_signal`: The PM or client has approved the pattern as enough for escalation in the stated context.
- `false_positive_guardrail`: The pattern caused over-review or over-discard risk and should limit future static checks.
- `survey_design_signal`: The pattern points to unclear prompts, weak answer formats, or fielding controls rather than bad respondents.

## What the signal bank should contain

Write `internal_quality_signal_bank.md` as a plain internal research note. Keep it useful to the next agent.

Each signal should explain:

- the pattern in plain words
- where it came from
- whether it is row-level evidence or aggregate context
- the current status
- examples that support it
- examples that weaken it
- how to use it on the next dataset
- when not to use it
- whether it needs PM approval before it can affect discard

This file can be free-form. Do not make the agent fill a rigid table when a paragraph explains the lesson better.

## Fabricated or bad response patterns to keep watching

Watch for these families, then interpret them in context:

- repeated generic praise with no survey-specific detail
- contradictory answers across linked fields
- implausible brand, product, or role combinations
- a required open end that is non-responsive across multiple important fields
- straightlined grids paired with weak open ends
- very fast completion paired with weak, evasive, or generic answers
- duplicate technical signals paired with similar answer chains
- survey-feedback wording submitted where a substantive answer was required
- AI helper fields that agree with other evidence
- open ends that sound polished but do not answer the prompt
- copied or near-duplicate narratives across supposedly independent respondents
- hostile or nonsense text that cannot be read as a meaningful answer
- direct non-response or repeated placeholder text in a required high-value open end, especially when the full chain does not recover usable context
- duplicate IP, device, or session clusters where supposedly independent respondents also share weak answer chains or the same non-response pattern
- first-pass topic mismatches caused by a missing project-specific topic map

These are not automatic discard rules. The agent must still read the full response chain and consider benign alternatives.

## False positive guardrails

Record false positives with the same care as true bad responses.

Common false positives:

- short but valid factor-list answers
- enthusiastic repeated characters in an otherwise meaningful answer
- rough spelling or grammar from a respondent who is still on topic
- speed-only rows with coherent chains
- uniform matrix ratings that match a plausible opinion
- shared IPs that look like household, workplace, or panel routing context
- keyword misses caused by a weak project topic map
- direct speed flags when the chain is coherent and the substantive answer is plausible
- weak narrative answers that remain PM calibration examples until another strong signal appears

False positive guardrails should be fed into the next first pass before harsher criteria are added.

## Closing the loop

At the end of every run:

1. Read the findings essay, escalation packet, kept synthesis, discard set, and next-pass inventory.
2. Decide what belongs in the internal signal bank.
3. Add new lessons with source citations.
4. Promote, demote, or retire old signals if the run produced better evidence.
5. State which signals should affect the next first-pass scoring and which should stay agent-only.

Do not let the signal bank become append-only clutter. If a signal has become misleading, say so and retire it.

The next cycle must start with this read. The agent should carry promoted
signals into the first-pass context, keep false-positive guardrails active,
and then test whether the signals still work on a new dataset. If the new run
shows that a signal is too broad, demote it. If it catches a pattern that the
scorer missed and the full-chain read confirms it, promote it.
