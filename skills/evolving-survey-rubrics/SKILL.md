---
name: evolving-survey-rubrics
description: Evolves survey quality rubrics from adjudicated respondent review examples. Use when improving scoring criteria, comparing Opulent candidate annotations to PM final review, tuning thresholds, creating self-improving loops, or justifying survey quality rubric changes with evidence.
---

# Evolving Survey Rubrics

Use this skill after at least one workbook has PM-adjudicated final review labels, internal comments, client annotations, findings essays, escalation packets, signal banks, or next-pass signal inventories. Normal scoring should run on unannotated exports first; graded workbooks are calibration and evaluation surfaces. Never promote a stable discard rule from unreviewed model output alone.

This skill should evolve analysis methodology, generated criteria, discovery coverage, generated provisional weights, and evaluation quality. A flat scoring tweak is the last resort, not the default.

When the task covers the 11 existing TFG original/graded pairs, treat them as development data and use dataset-level out-of-fold validation. Do not call those results external validation or a release claim.

## Workflow

1. Load the candidate and adjudicated workbooks.
2. Load available learning artifacts from prior runs:
   - `agent_findings_essay.md`
   - `agent_escalation_packet.md`
   - `internal_quality_signal_bank.md`
   - `next_pass_signal_inventory.csv`
   - `question_set_authenticity_map.md`
   - `question_contract.md`
   - `question_relation_graph.csv`
   - `semantic_signal_expansion_notes.md`
   - `progressive_chain_filtering_notes.md` (from the full-chain review layer)
   - `blind_authenticity_review_table.csv`
   - `label_aware_contrast_table.csv`
   - `authenticity_signal_family_lift.csv`
   - `protective_human_evidence.md`
   - `agent_review_judgment_table.csv`
   - `agent_discard_set.csv`
   - client or PM annotation workbooks
3. Join respondents by `uuid`, then `record`, then `RID` when adjudicated row labels exist.
4. Compare candidate action, final action, score, and flag families.
5. Identify systematic misses:
   - false keep: candidate says `Keep`, PM says review
   - overflag: candidate says review, PM says `Keep`
   - severity mismatch: both review, but PM assigns a stricter action
   - escalation mismatch: Opulent escalated a survivor row, failed to escalate a true discard candidate, or lacked enough second-pass evidence for the discard decision
   - signal-bank mismatch: a prior internal signal would have helped, but was not used
   - false-positive regression: a prior false-positive guardrail was ignored
   - analysis-quality miss: the final essay or escalation packet was too shallow for a PM to act on
   - row-authorship miss: rows were scored or templated, but not judged by an agent reading the full response chain
   - semantic-expansion miss: a raw check was treated as decisive before reviewing question similarity, answer timing, open-end authenticity, chain coherence, or accepted-row guardrails
   - weighting miss: a generated weight was too high or too low because the agent did not explain prompt fit, signal independence, recurrence, or false-positive risk
   - label-leakage miss: the analysis explained a row as bad only after seeing `status = 5`, without a blind semantic basis
   - tier-collapse miss: review tiers were mixed with Tier 5 exclusion candidates
   - family-double-count miss: many correlated metrics from one evidence family were treated as independent convergence
6. Propose the smallest methodology, generated-criteria, generated-weight, semantic-expansion, field-role mapping, or agent-review instruction change that improves the next run.
7. Write a proposed evolution record with:
   - old generated criterion or discovery behavior
   - proposed generated criterion, tag, or weighting rationale
   - semantic expansion that should happen before weighting, such as question-similarity review for straightlining or prompt-fit review for open ends
   - whether the change improves client rejection probability, authenticity-risk detection, or both
   - blind-pass effect and label-aware contrast effect
   - whether the change affects first-pass scoring, review routing, final escalation, reporting, or the internal signal bank
   - evidence rows
   - metric delta
   - annotation-quality delta when PM feedback shows the explanation was too shallow, too rigid, or linguistically unconvincing
   - row-level semantic delta when a change improves the agent's ability to separate rejected rows from accepted controls
   - risk notes
   - rollback condition

Run:

```bash
python3 ../cleaning-survey-quality/scripts/run_quality_loop.py \
  --candidate-file /path/to/candidate_review_export.xlsx \
  --adjudicated-file /path/to/final_pm_review.xlsx \
  --output-dir /path/to/outputs/rubric-evolution
```

## Evolution Rules

- Require adjudicated examples before promoting a generated criterion or generated weight into a stable project policy.
- Separate status prediction from authenticity-risk detection. A change can improve client-label recall without proving fraud; label that honestly.
- Require blind-pass evidence before promoting a row-level exclusion rule. Label-aware contrast can teach signals, but it cannot be the only basis for a rule.
- Require PM approval or repeated cross-run evidence before promoting an internal signal into a discard criterion.
- Treat the provided graded workbook as a sneak peek used to seed and test the loop, not as the expected future input shape.
- Prefer new generated candidate criteria, tags, dimension-level open-end evidence, and evaluation tests over static point changes.
- Prefer semantic-expansion improvements over point changes. If a straightline, speed, duplicate technical, or open-end rule failed, first ask whether the next run needs better question-set mapping, question similarity assessment, answer-time interpretation, open-end authenticity review, or accepted-row guardrails.
- Prefer agent row-review improvements over static rule changes. If a labeled validation fails because accepted controls share the same surface pattern as rejected rows, update the semantic questions and guardrails before changing numeric thresholds.
- Prefer high-support criteria over one-off examples.
- If candidate and final labels already match, report rubric stability.
- Track provenance: source file, sheet, respondent key, columns used, old value, new decision.
- Track escalation impact: whether the change escalates only decisive discard candidates and keeps survivor rows with stronger rationale or survey-question recommendations.
- Separate open-end interpretation from numeric scoring.
- Require every evolved weight to have an agent-authored rationale. The rationale should state why the signal is stronger or weaker after prompt fit, question similarity, time plausibility, semantic authenticity, chain coherence, signal independence, recurrence, and false-positive guardrails are considered.
- Preserve the five-tier model. Only Tier 5 is an exclusion candidate; Tiers 2-4 can increase review volume but should not be counted as discards.
- Aggregate within evidence families before claiming convergence.
- Evolve agent annotation guidance when reviewers had to redo the reasoning because the semantic analysis, fluency assessment, or trust rationale lacked depth.
- Evolve the mandatory row judgment artifact when validation shows that rows were not being read deeply enough. The artifact must show what the agent understood from each row, not only what a script measured.
- Evolve the findings essay and escalation packet guidance when a PM could not act from the prose alone.
- Keep false-positive guardrails as important as discard signals. A signal that prevents over-discarding is a successful evolution.
- Update `internal_quality_signal_bank.md` when a run confirms, weakens, retires, or reframes an internal criterion.
- Promote survivor findings into question-design improvements when clearer answer frameworks would reduce fuzzy or gameable responses.
- Report chance-adjusted and ordinal disagreement metrics when labels exist.

## When To Read References

- Read `references/evolution-protocol.md` before proposing changes.
- Read `references/research-grounding.md` for AutoResearch-level validation requirements.
- Read `../cleaning-survey-quality/references/authenticity-first-calibration.md` before changing status calibration, blind review, five-tier routing, Question Contracts, or protective accepted-row learning.
- Read `../cleaning-survey-quality/references/semantic-signal-expansion.md` before changing weights, straightlining interpretation, open-end authenticity, semantic similarity, duration criteria, or convergence rules.
