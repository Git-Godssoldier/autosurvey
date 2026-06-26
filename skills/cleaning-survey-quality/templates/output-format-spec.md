# Output Templates

This directory documents the format of the output artifacts produced by the pipeline. These are not loaded into context during runs — they are reference specifications for the output format.

## Annotated Excel Format

The annotated Excel file is the original workbook with 9 added columns:

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
  "rubric_version": "v4-evidence-family"
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

Each `agent_judgments_chunk_XX.json` contains:

```json
[{
  "respondent_id": "uuid",
  "agent_score": -0.7,
  "agent_judgment": "DISCARD",
  "agent_justification": "The core OE answer 'water filtration systems' fails the motivation question role. It names the topic but gives no lived experience. Converges with ML triage 0.82 and generic outro matching 12 other respondents."
}]
```
