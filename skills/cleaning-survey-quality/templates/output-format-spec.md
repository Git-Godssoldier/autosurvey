# Output Templates

This directory documents the format of the output artifacts produced by the pipeline. These are not loaded into context during runs — they are reference specifications for the output format.

## Annotated Excel Format

The annotated Excel file is the original workbook with review columns added. It must include the legacy 9 columns and the V7 decision fields when available.

| Column | Type | Description |
|---|---|---|
| `ML_Triage_Score` | float (0-1) | ML model risk probability |
| `Agent_Score` | float (-1 to +1) | Initial agent score on discard-keep continuum |
| `Final_Score` | float (-1 to +1) | Score after reassessment |
| `Final_Judgment` | string | DISCARD (red), REVIEW (yellow), or KEEP (green) |
| `Agent_Justification` | string | 2-4 sentence natural-language justification citing specific evidence |
| `Key_Signals` | string | Semicolon-separated list of signals that drove the score |
| `Reassessment_Notes` | string | Notes from second-pass reassessment (if applicable) |
| `Defender_Summary` | string | Human-readable consolidation of platform signals |
| `AI_Text_Suspicion` | float (0-1) | Cross-respondent AI text similarity score |
| `Authenticity_Risk` | float (0-1) | Fraud, bot, platform, duplicate, or synthetic-response risk |
| `Quality_Discard_Risk` | float (0-1) | Project quality bar risk after full-chain review |
| `Client_Reject_Probability` | float (0-1) | Likelihood the client process would reject the row |
| `Primary_Removal_Reason` | string | quality_auth_failure, quota_balancing, eligibility_screenout, partial_incomplete, vendor_source, manual_admin, unknown_mixed, or none |
| `Evidence_Families_Fired` | string | Independent evidence families that fired, not correlated subchecks |
| `Converging_Family_Count` | int | Number of independent families after aggregation |
| `Badopen_Trigger` | string | duplicate_text, too_short, pasted_text, wrong_topic, profanity, ai_like_similarity, nonresponsive, human_reviewer, or none |
| `OE_Classification` | string | substantive, thin_on_topic, off_topic, non_answer, gibberish, product_review, benefit_stack, or other |
| `Protective_Evidence` | string | Accepted-row guardrail or benign explanation considered before final action |

## Dashboard HTML Format

Self-contained HTML file with:

1. **Summary cards** — Total, discard, review, keep counts and percentages
2. **Agent score distribution chart** — -1 to +1 buckets
3. **Timing distribution chart** — Completion time distribution
4. **Top population signals list** — Most common signals across all respondents
5. **Supplier analysis table** — Top 15 suppliers by count, mean score, discards, reviews
6. **LangAssess readability distribution** — Open-end text readability levels
7. **ML triage score distribution** — Risk probability distribution
8. **Discard set table** — Top 50 discards with scores, signals, and agent justifications
9. **Evidence-family health** — firing rate by family, guardrail notes, and whether each family shows positive, neutral, or negative discrimination when labels exist
10. **Error-learning section** — after labeled evaluation, narrative analysis of false positives and false negatives with recommended skill changes

## Summary JSON Format

```json
{
  "source_files": [{"file": "path", "sheet": "A1", "rows": 1566, "columns": 790}],
  "metrics": {
    "dataset_name": {
      "rows": 1566,
      "computed_action_counts": {"Keep": 1520, "Review": 46, "Discard": 0},
      "severity_counts": {"No action": 1505, "Survived second pass": 61},
      "second_pass_decision_counts": {"keep_no_issue": 1505, "keep_with_recommendation": 61}
    }
  },
  "rubric_version": "v7-calibrated-convergence"
}
```

## Review Packet Format (Stage 1 output)

Each `review_chunk_XX.json` contains an array of respondent packets:

```json
[{
  "respondent_id": "uuid",
  "record": 15,
  "answer_chain": [{"field": "q9", "question": "...", "answer": "...", "label": "..."}],
  "open_ends": [{"field": "qcoe1", "question": "...", "text": "..."}],
  "timing_minutes": 9.2,
  "timing_percentile": 0.45,
  "supplier": "Qmee",
  "supplier_reject_rate": 0.12,
  "ml_triage_score": 0.23,
  "defender_summary": "TERMFLAGS=0, qc=0, RD_Search=low",
  "ai_text_suspicion": 0.15,
  "duplicate_text_counts": {"qcoe1": 0, "outro": 3},
  "answer_entropy": 2.8,
  "grid_straightline_analysis": {"q44": false, "q45": false}
}]
```

## Agent Judgment Format (Stage 2 output)

Each `agent_judgments_chunk_XX.json` contains one object per respondent. The minimum runtime fields are below. A run should not be accepted if it only contains respondent ID, score, judgment, and a generic justification.

```json
[{
  "respondent_id": "uuid",
  "agent_score": -0.7,
  "agent_judgment": "DISCARD",
  "agent_justification": "The core OE answer 'water filtration systems' fails the motivation question role. It names the topic but gives no lived experience. Converges with ML triage 0.82 and generic outro matching 12 other respondents.",
  "authenticity_risk": 0.72,
  "quality_discard_risk": 0.61,
  "client_reject_probability": 0.84,
  "stage1_fraud_verdict": "review",
  "stage2_quality_verdict": "fail",
  "primary_removal_reason": "quality_auth_failure",
  "secondary_removal_reason": "model_risk",
  "removal_confidence": 0.78,
  "evidence_families_fired": ["model_risk", "brand_funnel"],
  "evidence_family_scores": {
    "model_risk": {"fired": true, "score": 0.82, "trigger": "ml_ge_0_8"},
    "core_oe_quality": {"fired": false, "score": 0.2, "trigger": "thin_on_topic_protected"}
  },
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
  "signals_present": ["model_risk"],
  "signals_counted_for_discard": ["model_risk"],
  "signals_context_only": [],
  "signals_protective": ["thin_on_topic_protected"],
  "disposition_rule_id": "discard_model_brand_convergence",
  "badopen_trigger": "none",
  "oe_classification": "thin_on_topic",
  "converging_family_count": 2,
  "protective_evidence": "The answer is short but on topic; the discard comes from model and brand-funnel convergence, not shortness alone.",
  "second_read_action": "discard",
  "review_routing_class": "high_conf_discard_candidate",
  "review_reason_code": "model_brand_convergence",
  "review_priority": "high",
  "review_exit_criteria": "Keep only if the brand-funnel contradiction is resolved by source workbook evidence.",
  "auto_keep_reason": "",
  "discard_candidate_reason": "The discard is supported by model risk and brand-funnel convergence."
}]
```

In no-ML signal-table mode, `signal_assessments` is required. It must include one key for every production-safe signal in `signal_dictionary`. Each signal entry must include `present`, `criterion`, `evidence`, `decision_weight`, `decision_effect`, and `confidence`.

When no-ML review compression is active, each final output row must also include `second_read_action`, `review_routing_class`, `review_reason_code`, `review_priority`, and `review_exit_criteria`. KEEP rows must include `auto_keep_reason`. DISCARD rows must include `discard_candidate_reason` or a specific `disposition_rule_id`.

Validate each chunk with:

```bash
python3 skills/cleaning-survey-quality/scripts/validate_agent_judgments.py \
  /path/to/review_chunk_XX.json /path/to/agent_judgments_chunk_XX.json \
  --signal-dictionary /path/to/signal_dictionary.csv \
  --signal-matrix /path/to/signal_matrix.csv
```

For compressed no-ML outputs, add:

```bash
python3 skills/cleaning-survey-quality/scripts/validate_agent_judgments.py \
  /path/to/review_chunk_XX.json /path/to/agent_judgments_chunk_XX.json \
  --signal-dictionary /path/to/signal_dictionary.csv \
  --signal-matrix /path/to/signal_matrix.csv \
  --require-review-routing \
  --max-review-rate 0.40
```
