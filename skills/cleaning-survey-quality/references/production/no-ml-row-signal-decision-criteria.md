# No-ML row signal decision criteria

Use this reference when a production run cannot use the bundled model or a same-dataset training step.

The agent must not only cite broad evidence families. It must mark every production-safe signal for every row, explain the criterion, and state how that signal affected the decision.

## Result assessment from Echo

The no-ML full-dataset run over Echo reviewed 1,566 respondents.

The first no-ML run produced 217 `DISCARD`, 1,095 `REVIEW`, and 254 `KEEP` rows. Strict mode treated only `DISCARD` as a discard. It reached 65.5 percent accuracy, 53.0 percent precision, 20.8 percent recall, and 29.9 percent F1.

The second no-ML run added required `signal_assessments` for all 37 production-safe signals. It produced 58 `DISCARD`, 1,416 `REVIEW`, and 92 `KEEP` rows. Strict mode reached 65.6 percent accuracy, 62.1 percent precision, 6.5 percent recall, and 11.8 percent F1. Soft mode treated `DISCARD` or `REVIEW` as a discard. It reached 39.0 percent accuracy, 36.4 percent precision, 96.9 percent recall, and 52.9 percent F1.

The main shortcomings were:

- The first run emitted evidence-family scores, but it emitted no per-signal assessments.
- The second run fixed signal assessment hygiene, but it overused `REVIEW` even more. It sent 90.4 percent of rows to final review.
- Strict recall was too low in both runs. The second run caught only 36 of 553 client discards.
- Soft precision was too low. The second run placed 938 accepted rows into `DISCARD` or `REVIEW`.
- Several signals were too broad to help row decisions. In this run, `matrix_near_straightline` and `matrix_many_straightlined_grids` were present in every FP, FN, TP, and TN bucket. `brand_low_awareness_count` appeared in about 94 percent to 98 percent of each bucket.
- The agent overcalled `wrong_topic` for outdoor-property answers such as sprinkler systems, decks, ponds, landscaping, mulch, weeds, garden beds, irrigation, patios, fences, and yard cleanup.

These findings mean the next workflow must force row-level signal marking, signal quality checks, stricter decision gates, and a second-read review compression pass. Validator compliance is necessary, but it is not enough.

## Signal preflight

Before Stage 2 row review, build a signal profile from `signal_matrix`.

For every signal, compute:

- row count present;
- row count absent;
- present rate;
- missing rate;
- family;
- allowed decision weight.

If labels are available after the run, also compute present discard rate, absent discard rate, lift, false positives, and false negatives. Do not use label results during blind scoring.

Use these preflight rules during blind scoring:

- If a signal is present in more than 85 percent of rows, mark it as `context_only`. Do not count it toward discard convergence unless the row has a separate row-specific trigger.
- If a signal is present in fewer than 1 percent of rows, mark it as `sparse`. It can support a hard failure when present, but absence does not protect the row.
- If a signal is a family rollup, do not count it as a second independent signal when its child signal is already counted.
- If several signals come from the same source, count them as one family for convergence.
- If a signal is known to be broken or near-universal in the current dataset, keep it in `signal_assessments`, but set `decision_weight` to `context_only`.

## Required row output

Each respondent judgment must include these fields when signal-table mode is active:

```json
{
  "signal_assessments": {
    "platform_qc_auto_fail": {
      "present": false,
      "criterion": "qc is 8 or 9",
      "evidence": "qc=0",
      "decision_weight": "hard_discard",
      "decision_effect": "not_counted",
      "confidence": 1.0
    }
  },
  "signals_present": ["timing_under_p10"],
  "signals_counted_for_discard": [],
  "signals_context_only": ["matrix_near_straightline"],
  "signals_protective": ["grounded_outdoor_property_answer"],
  "disposition_rule_id": "review_mixed_weak_signals"
}
```

`signal_assessments` must contain one key for every production-safe signal in `signal_dictionary`.

For each signal:

- `present` must match the Boolean value in `signal_matrix`.
- `criterion` must state the exact rule that makes the signal present.
- `evidence` must cite the row value or answer text that was checked.
- `decision_weight` must be one of `hard_discard`, `strong_risk`, `review_only`, `context_only`, or `protective`.
- `decision_effect` must be one of `counted_for_discard`, `review_only`, `not_counted`, `protected_keep`, or `conflict_requires_review`.
- `confidence` must be a number from 0.0 to 1.0.

Do not leave a signal implicit. If the signal is absent, include it with `present: false` and evidence that explains why it is absent.

## Required second-read review compression

After the first full-dataset row review, run a second pass over every row marked `REVIEW`.

The goal is not to hide uncertainty. The goal is to separate rows that can safely exit review from rows that need a human decision.

Each `REVIEW` row must be reassigned to one of these routing classes:

- `auto_keep_candidate`: The row has no hard signal, no strong semantic failure, at most one independent review-only risk family, and protective evidence or no row-specific risk.
- `targeted_second_read`: The row has one unresolved question that the agent can answer from workbook evidence, SQLite evidence, duplicate text context, or the raw answer chain.
- `human_review`: The row has a concrete unresolved question that requires human PM judgment. The output must state that question.
- `high_conf_discard_candidate`: The row meets a DISCARD gate after the second read, and the output cites the hard signal or independent counted families.

The final `REVIEW` lane should be budgeted. For no-ML production runs, target a final `REVIEW` rate of 25 percent to 35 percent. Treat 40 percent as the default ceiling unless the workledger explains why the dataset needs more human review.

Do not preserve `REVIEW` only because the row is short, thin, common, or mildly uncertain. If the only present signals are weak or context-only and the row has an outdoor task or no row-specific risk, move it to `KEEP`.

Every row after review compression must include:

- `second_read_action`, one of `keep`, `review`, or `discard`;
- `review_routing_class`, one of the four classes above;
- `review_reason_code`, e.g. `thin_on_topic_only`, `weak_source_timing`, `brand_chain_uncertain`, `possible_wrong_topic`, `possible_nonanswer`, `quota_or_source_context`, `conflicting_evidence`, or `human_pm_judgment`;
- `review_priority`, one of `low`, `medium`, `high`, or `urgent`;
- `review_exit_criteria`, stating what would move the row to KEEP or DISCARD;
- `auto_keep_reason` for KEEP rows;
- `discard_candidate_reason` for DISCARD rows.

Use `human_review` only when the output names the exact human question. A vague statement such as "mixed evidence" is not enough.

## Forbidden row inputs

Do not use these fields during blind scoring:

- `truth`;
- `hard_signal`;
- `risk_score`;
- client `status`;
- raw client `markers`;
- `bad:` marker tokens;
- same-dataset labels;
- same-dataset fitted model scores.

If these fields exist in a matrix or packet, ignore them and state in the workledger that they were excluded.

## Decision weights

### Hard discard

Use `hard_discard` only for evidence that can justify a discard by itself:

- `platform_qc_auto_fail`;
- `platform_termflags_nonzero`;
- `platform_non_us_country`;
- gibberish or repeated-character nonsense;
- complete non-answer such as `n/a`, `none`, `good`, or a one-word answer with no project content;
- clear wrong-domain answer with no outdoor-property bridge;
- high-confidence duplicate or copied text when the duplicate evidence is row-specific.

### Strong risk

Use `strong_risk` for evidence that can support discard only with another independent family:

- `platform_rd_search_high`;
- `agent_badopen_high`;
- `agent_quality_auth_failure`;
- `agent_oe_wrong_topic` after the wrong-topic guardrail below;
- `agent_oe_nonresponsive`;
- `brand_low_rated_count`;
- `family_quota_reconstruction`;
- `family_source_risk`.

### Review only

Use `review_only` for weak or mixed evidence:

- `platform_rd_search_elevated`;
- `timing_under_p10`;
- `timing_under_5_minutes`;
- `lang_readability_high`;
- `answer_entropy_low`;
- `coded_answer_low_diversity`;
- `agent_badopen_medium`;
- `agent_oe_thin_on_topic`;
- `brand_fragmented_rated_count`;
- `structure_classify_pro`;
- `structure_conditions_ariens`.

These signals can move a row from `KEEP` to `REVIEW`. They cannot create `DISCARD` unless at least one hard or strong signal also fires.

### Context only

Use `context_only` for signals that are too broad in the current dataset.

In the Echo no-ML run, these must not count toward discard:

- `matrix_near_straightline`;
- `matrix_many_straightlined_grids`;
- `brand_low_awareness_count`, unless the agent also finds row-specific brand-chain inconsistency.

### Protective

Use `protective` for evidence that prevents over-discard:

- first-person outdoor property experience;
- named outdoor power equipment;
- a specific task, place, or condition;
- coherent pro or consumer branch fit;
- longer answer with grounded detail;
- no hard failure and no strong signal.

## Wrong-topic guardrail

Do not mark an answer as hard wrong-topic only because it is not a named outdoor power equipment product.

Outdoor-property answers are not hard wrong-topic by themselves. Examples include sprinkler systems, decks, ponds, landscaping, mulch, weeds, flower beds, garden beds, irrigation, patios, fences, snow removal, yard cleanup, lawn work, trimming, blowing leaves, pruning, and garden work.

For these answers:

- mark `agent_oe_wrong_topic` as false unless the answer clearly has no connection to outdoor property work;
- use `outdoor_adjacent_review` in `disposition_rule_id` when the answer is thin or uncertain;
- do not assign `DISCARD` without another hard or strong signal.

Hard wrong-topic should be reserved for clearly unrelated domains, e.g. indoor appliances, vehicles, phones, unrelated shopping, medical care, finance, entertainment, or pure product praise with no project.

## Thin-on-topic guardrail

Thin on-topic answers are common and ambiguous.

Do not discard a row only because the core open end is short. If the answer names an outdoor task such as mowing, trimming, blowing leaves, raking, clearing weeds, edging, pruning, or yard cleanup, classify it as `thin_on_topic`.

Use these rules:

- If there are no hard or strong signals, `thin_on_topic` should be `KEEP` or `REVIEW`, not `DISCARD`.
- If `thin_on_topic` combines with two or more independent review-only signals, use `REVIEW`.
- If `thin_on_topic` combines with one strong signal and at least two independent review-only signals, use `DISCARD` only when protective evidence is weak.
- If the answer has first-person wording, a task, and a location, add protective evidence.

## Final disposition gates

Use these gates after marking every signal.

### DISCARD

Use `DISCARD` when one of these is true:

- one hard-discard signal is present and no protective evidence explains it away;
- one strong semantic failure is present with at least two other independent counted families;
- at least four independent counted families are present, at least one is `strong_risk`, and no protective evidence is strong;
- complete non-answer, gibberish, or clear unrelated answer is present.

### REVIEW

Use `REVIEW` when one of these is true:

- there is mixed evidence after the second-read pass;
- the row has a named unresolved question that a human reviewer can answer;
- the row has outdoor-adjacent text that may or may not fit the survey, and no workbook evidence resolves the fit;
- the row has weak source, timing, language, or brand evidence plus another row-specific concern;
- the row has conflicting protective and risk signals that cannot be resolved from the answer chain.

Do not use `REVIEW` when weak review-only signals are the only concerns and protective evidence is present.

### KEEP

Use `KEEP` when all of these are true:

- no hard-discard signal is present;
- no strong semantic failure is present;
- at most one independent counted risk family is present, or only weak review-only signals are present;
- the answer is substantive or thin but on topic;
- protective evidence is present or the signal table shows no meaningful row-specific risk.

## Validation rule

Do not accept an agent output if:

- `signal_assessments` is missing;
- any production-safe signal is missing from `signal_assessments`;
- a signal has no criterion or no evidence;
- `present` does not match `signal_matrix`;
- near-universal signals are counted toward discard;
- the row has a final judgment but no `disposition_rule_id`;
- the justification does not cite the signals that drove the final judgment.
- review compression is active and `review_reason_code`, `review_priority`, or `review_exit_criteria` is missing;
- review compression is active and the final `REVIEW` rate exceeds the configured review budget without a workledger exception.
