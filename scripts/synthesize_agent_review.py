#!/usr/bin/env python3
"""Synthesize agent review judgments into a miss-analysis report.

Reads the false negative, false positive, and true positive agent judgments
produced by subagent review, and synthesizes them into:
1. A pattern analysis report (Markdown)
2. Updated signal recommendations for the pipeline
3. A summary of what the agent found that the rules missed

Usage:
    python3 synthesize_agent_review.py <comparison_dir>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def synthesize(comparison_dir):
    comparison_dir = Path(comparison_dir)
    
    # Load agent judgments
    fn_path = comparison_dir / "fn_agent_judgments.json"
    fp_path = comparison_dir / "fp_agent_judgments.json"
    tp_path = comparison_dir / "tp_agent_judgments.json"
    summary_path = comparison_dir / "comparison_summary.json"
    
    fn = json.load(open(fn_path)) if fn_path.exists() else []
    fp = json.load(open(fp_path)) if fp_path.exists() else []
    tp = json.load(open(tp_path)) if tp_path.exists() else []
    summary = json.load(open(summary_path)) if summary_path.exists() else {}
    
    # Analyze patterns in "signal_we_missed" for false negatives
    missed_signals = Counter()
    client_reasons = Counter()
    for j in fn:
        # Extract key patterns from signal_we_missed
        s = j.get("signal_we_missed", "").lower()
        if "third-person" in s or "meta-description" in s or "restates" in s or "topic-restatement" in s:
            missed_signals["third_person_meta_open_end"] += 1
        if "missing" in s and ("q14" in s or "field" in s):
            missed_signals["missing_critical_fields"] += 1
        if "irrelevant" in s or "incoherent" in s or "non-answer" in s:
            missed_signals["irrelevant_or_incoherent_q14"] += 1
        if "straightlining" in s and ("q15" in s or "q16" in s or "beyond" in s):
            missed_signals["cross_block_straightlining"] += 1
        if "duplicate" in s:
            missed_signals["duplicate_text_underweighted"] += 1
        if "category" in s or "answer option" in s:
            missed_signals["category_label_answer"] += 1
        if "templated" in s or "truncated" in s:
            missed_signals["templated_or_truncated"] += 1
        
        # Extract client reason patterns
        r = j.get("likely_client_reason", "").lower()
        if "straightlining" in r or "straightline" in r:
            client_reasons["matrix_straightlining"] += 1
        if "generic" in r or "non-personal" in r:
            client_reasons["generic_open_end"] += 1
        if "third-person" in r or "topic" in r:
            client_reasons["third_person_open_end"] += 1
        if "duplicate" in r:
            client_reasons["duplicate_text"] += 1
        if "missing" in r:
            client_reasons["missing_fields"] += 1
        if "speeding" in r or "fast" in r:
            client_reasons["speeding"] += 1
        if "incoherent" in r or "inconsistent" in r:
            client_reasons["demographic_incoherence"] += 1
    
    # Analyze false positive patterns
    over_discard_reasons = Counter()
    protective_patterns = Counter()
    for j in fp:
        w = j.get("why_we_over_discarded", "").lower()
        if "matrix" in w and "false" in w:
            over_discard_reasons["matrix_straightline_false_positive"] += 1
        if "duplicate" in w and ("generic" in w or "common" in w or "inevitab" in w):
            over_discard_reasons["dup_oe_over_weighted"] += 1
        if "supplier" in w and "over" in w:
            over_discard_reasons["supplier_risk_over_weighted"] += 1
        if "short" in w and "readability" in w:
            over_discard_reasons["short_oe_readability_compounding"] += 1
        if "speeding" in w or "fast" in w:
            over_discard_reasons["timing_over_weighted"] += 1
        
        p = j.get("protective_evidence", "").lower()
        if "personal" in p or "first-person" in p or "i " in p:
            protective_patterns["personal_open_end"] += 1
        if "matrix" in p and ("variation" in p or "differentiated" in p):
            protective_patterns["matrix_variation_despite_flag"] += 1
        if "misspell" in p or "typo" in p or "human" in p:
            protective_patterns["natural_human_errors"] += 1
        if "specific" in p or "unique" in p:
            protective_patterns["specific_unique_answer"] += 1
        if "outlier" in p:
            protective_patterns["matrix_outlier_value"] += 1
    
    # Analyze true positive patterns
    tp_signals = Counter()
    for j in tp:
        k = j.get("key_discard_signal", "").lower()
        if "generic" in k:
            tp_signals["generic_open_end"] += 1
        if "gibberish" in k or "nonsense" in k:
            tp_signals["gibberish_nonsense"] += 1
        if "duplicate" in k:
            tp_signals["duplicate_text"] += 1
        if "speeding" in k or "fast" in k:
            tp_signals["extreme_speeding"] += 1
        if "off-topic" in k or "irrelevant" in k:
            tp_signals["off_topic_open_end"] += 1
        if "truncated" in k or "templated" in k:
            tp_signals["templated_truncated"] += 1
        if "meta" in k or "fraud" in k:
            tp_signals["meta_fraud_commentary"] += 1
    
    # Build report
    report = f"""# Agent Review Analysis — Miss Assessment

## Dataset: {summary.get('dataset', 'Unknown')}
## Comparison Summary

| Metric | Value |
|--------|-------|
| Total respondents | {summary.get('total_respondents', 'N/A')} |
| Annotated respondents | {summary.get('annotated_respondents', 'N/A')} |
| Client discards | {summary.get('client_discards', 'N/A')} |
| Our discards | {summary.get('our_discards', 'N/A')} |
| True positives (correct catches) | {summary.get('true_positives', 'N/A')} |
| False negatives (missed discards) | {summary.get('false_negatives', 'N/A')} |
| False positives (wrong discards) | {summary.get('false_positives', 'N/A')} |
| Precision | {summary.get('precision', 'N/A')} |
| Recall | {summary.get('recall', 'N/A')} |
| F1 | {summary.get('f1', 'N/A')} |

### False Negative Breakdown
- In REVIEW band (we flagged but didn't discard): {summary.get('fn_in_review', 'N/A')}
- In KEEP band (we completely missed): {summary.get('fn_in_keep', 'N/A')}

---

## Agent Review of {len(fn)} False Negatives (Missed Discards)

The agent reviewed {len(fn)} sampled false negatives and judged **{sum(1 for j in fn if j['agent_judgment'] == 'DISCARD')} as DISCARD**, **{sum(1 for j in fn if j['agent_judgment'] == 'REVIEW')} as REVIEW**, and **{sum(1 for j in fn if j['agent_judgment'] == 'KEEP')} as KEEP**.

### Signals We Missed (from agent analysis)

| Pattern | Count | Description |
|---------|-------|-------------|
"""
    for signal, count in missed_signals.most_common():
        desc = {
            "third_person_meta_open_end": "Open-end describes what the survey was about in third person instead of sharing personal experience",
            "missing_critical_fields": "Critical fields like q14 are entirely missing",
            "irrelevant_or_incoherent_q14": "q14 answers are off-topic, non-answers, or incoherent",
            "cross_block_straightlining": "Same answer across semantically different single-choice questions (q15=q16)",
            "duplicate_text_underweighted": "Duplicate open-end text was detected but not weighted enough",
            "category_label_answer": "Open-end reads like a copied answer option, not personal narrative",
            "templated_or_truncated": "Open-end is truncated mid-sentence or follows a template",
        }.get(signal, signal)
        report += f"| {signal} | {count} | {desc} |\n"
    
    report += f"""
### Likely Client Reasons for Discard

| Reason | Count |
|--------|-------|
"""
    for reason, count in client_reasons.most_common():
        report += f"| {reason} | {count} |\n"
    
    report += f"""
### Agent Justifications (Sample)

"""
    for j in fn[:5]:
        report += f"**{j['respondent_id']}** (agent score: {j['agent_score']}, judgment: {j['agent_judgment']})\n"
        report += f"- Justification: {j['agent_justification']}\n"
        report += f"- Likely client reason: {j['likely_client_reason']}\n"
        report += f"- Signal we missed: {j['signal_we_missed']}\n\n"

    report += f"""---

## Agent Review of {len(fp)} False Positives (Wrong Discards)

The agent reviewed {len(fp)} sampled false positives and judged **{sum(1 for j in fp if j['agent_judgment'] == 'KEEP')} as KEEP**, **{sum(1 for j in fp if j['agent_judgment'] == 'REVIEW')} as REVIEW**, and **{sum(1 for j in fp if j['agent_judgment'] == 'DISCARD')} as DISCARD**.

### Why We Over-Discarded

| Pattern | Count | Description |
|---------|-------|-------------|
"""
    for reason, count in over_discard_reasons.most_common():
        desc = {
            "matrix_straightline_false_positive": "Matrix straightlining flag triggered but actual matrix answers show variation",
            "dup_oe_over_weighted": "Duplicate open-end text is generic/topical inevitability, not fraud signal",
            "supplier_risk_over_weighted": "Supplier-level reject rate applied to individual with no personal signals",
            "short_oe_readability_compounding": "Short open-end + low readability compounded, but q14 was substantive",
            "timing_over_weighted": "Fast timing flagged but other evidence shows genuine engagement",
        }.get(reason, reason)
        report += f"| {reason} | {count} | {desc} |\n"
    
    report += f"""
### Protective Evidence Patterns

| Pattern | Count | Description |
|---------|-------|-------------|
"""
    for pattern, count in protective_patterns.most_common():
        desc = {
            "personal_open_end": "Open-end uses first-person language with personal experience",
            "matrix_variation_despite_flag": "Matrix answers show genuine variation despite straightlining flag",
            "natural_human_errors": "Misspellings/typos indicate human respondent (bots produce correct text)",
            "specific_unique_answer": "Answer is specific and unique to this respondent",
            "matrix_outlier_value": "Matrix contains an unusual outlier value showing genuine engagement",
        }.get(pattern, pattern)
        report += f"| {pattern} | {count} | {desc} |\n"
    
    report += f"""
### Agent Justifications (Sample)

"""
    for j in fp[:5]:
        report += f"**{j['respondent_id']}** (agent score: {j['agent_score']}, judgment: {j['agent_judgment']})\n"
        report += f"- Justification: {j['agent_justification']}\n"
        report += f"- Why we over-discarded: {j['why_we_over_discarded']}\n"
        report += f"- Protective evidence: {j['protective_evidence']}\n\n"

    report += f"""---

## Agent Review of {len(tp)} True Positives (Correct Discards)

### Key Discard Signals (from agent analysis)

| Signal | Count |
|--------|-------|
"""
    for signal, count in tp_signals.most_common():
        report += f"| {signal} | {count} |\n"
    
    report += f"""
### Agent Justifications (Sample)

"""
    for j in tp[:5]:
        report += f"**{j['respondent_id']}** (agent score: {j['agent_score']})\n"
        report += f"- Justification: {j['agent_justification']}\n"
        report += f"- Key signal: {j['key_discard_signal']}\n"
        report += f"- Converging evidence: {j.get('converging_evidence', 'N/A')}\n\n"

    report += f"""---

## Key Insights

### What the agent catches that the rules miss:

1. **Third-person meta-description open-ends**: The biggest missed pattern. Respondents write "this survey was about..." or "questions were asked about..." instead of sharing personal experience. This is a semantic judgment — regex cannot detect it. The agent reads the open-end and recognizes it's a survey description, not a personal answer.

2. **Irrelevant or incoherent q14 answers**: Answers like "Good night my friend" or "i need it" or conspiracy theories. These require semantic understanding to flag.

3. **Missing critical fields**: q14 entirely absent. The pipeline doesn't check for the PRESENCE of expected fields, only the quality of present fields.

4. **Cross-block straightlining**: Same answer to q15 and q16 (semantically different questions). The pipeline only checks matrix blocks, not cross-question patterns.

5. **Category-label answers**: Open-ends that read like copied answer options ("Concerns about water quality or taste") rather than personal narrative.

### What causes false positives (over-discarding):

1. **Matrix straightlining false positive**: When 90%+ of respondents have matrix straightlining, it's not discriminative. The pipeline should disable matrix straightlining as a discard signal when the population prevalence is too high.

2. **Generic duplicate open-end over-weighting**: "Water filtration systems" is a topical inevitability, not fraud. The pipeline should check whether duplicate text is generic/topical vs. unusual.

3. **Supplier risk over-weighting**: Supplier-level reject rates should not be applied to individuals with no personal signals.

4. **Short open-end + readability compounding**: Short outro text with low readability should not compound when the substantive q14 field is present and personal.

### Recommended Pipeline Updates:

1. **Add open-end semantic classification**: Check if open-end text is:
   - First-person personal experience (KEEP signal)
   - Third-person survey description (DISCARD signal)
   - Generic topic restatement (DISCARD signal)
   - Off-topic or incoherent (DISCARD signal)
   - Templated or truncated mid-sentence (DISCARD signal)

2. **Check for missing critical fields**: If expected high-value open-end fields (q14, qcoe1) are empty, this should be a strong discard signal.

3. **Cross-block straightlining detection**: Check if semantically different single-choice questions (q15, q16) have identical answers.

4. **Matrix prevalence gating**: If >80% of respondents have matrix straightlining, disable it as a discard signal (it's not discriminative).

5. **Duplicate text classification**: Classify duplicate open-end text as "generic/topical" (not fraud) vs. "unusual" (fraud signal).

6. **Protective factor weighting**: First-person open-ends, matrix outlier values, and natural human errors (misspellings) should be strong protective factors.
"""
    
    # Write report
    report_path = comparison_dir / "agent_review_analysis.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report written to: {report_path}")
    
    # Write structured findings for pipeline integration
    findings = {
        "dataset": summary.get("dataset", ""),
        "missed_signals": dict(missed_signals.most_common()),
        "client_reasons": dict(client_reasons.most_common()),
        "over_discard_reasons": dict(over_discard_reasons.most_common()),
        "protective_patterns": dict(protective_patterns.most_common()),
        "tp_signals": dict(tp_signals.most_common()),
        "fn_agent_judgments": fn,
        "fp_agent_judgments": fp,
        "tp_agent_judgments": tp,
    }
    findings_path = comparison_dir / "agent_review_findings.json"
    with open(findings_path, "w") as f:
        json.dump(findings, f, indent=2)
    print(f"Findings written to: {findings_path}")
    
    return report


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 synthesize_agent_review.py <comparison_dir>")
        return
    synthesize(sys.argv[1])


if __name__ == "__main__":
    main()
