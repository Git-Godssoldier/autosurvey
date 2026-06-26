#!/usr/bin/env python3
"""Compare v4 vs v5 holistic agent review results against client ground truth for ECHO."""
import json
import sys
from pathlib import Path
from collections import defaultdict

import openpyxl

def load_client_ground_truth(annotated_path):
    """Load status labels from the client-annotated workbook."""
    wb = openpyxl.load_workbook(annotated_path, read_only=True)
    ws = wb.active
    headers = [c.value for c in ws[1]]
    status_idx = headers.index('status')
    uuid_idx = headers.index('uuid')
    record_idx = headers.index('record')

    gt = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        uuid = row[uuid_idx]
        record = row[record_idx]
        status = row[status_idx]
        # status=3 = accepted (keep), status=5 = discarded
        gt[uuid] = 'DISCARD' if status == 5 else 'KEEP'
    return gt

def load_judgments(path):
    """Load agent judgments from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    judgments = {}
    for item in data:
        rid = item.get('respondent_id') or item.get('uuid')
        judgments[rid] = {
            'judgment': item.get('agent_judgment', item.get('judgment', '')),
            'score': item.get('agent_score', item.get('score', 0)),
            'justification': item.get('agent_justification', item.get('justification', ''))
        }
    return judgments

def compute_metrics(gt, judgments):
    """Compute precision, recall, F1 for discard detection."""
    tp = fp = tn = fn = 0
    matched = 0
    for rid, gt_label in gt.items():
        if rid not in judgments:
            continue
        matched += 1
        pred = judgments[rid]['judgment']
        # Treat DISCARD as positive (predicting discard), KEEP/REVIEW as non-discard for strict comparison
        # But also compute with REVIEW as a separate category

        if gt_label == 'DISCARD':
            if pred == 'DISCARD':
                tp += 1
            elif pred == 'REVIEW':
                fn += 1  # missed discard, sent to review
            else:  # KEEP
                fn += 1
        else:  # gt_label == 'KEEP'
            if pred == 'DISCARD':
                fp += 1
            elif pred == 'REVIEW':
                tn += 1  # not discarded, sent to review (correct non-discard)
            else:  # KEEP
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Also compute "soft recall" — DISCARD or REVIEW counts as catching a discard
    soft_tp = tp + sum(1 for rid, gt_label in gt.items()
                       if rid in judgments and gt_label == 'DISCARD'
                       and judgments[rid]['judgment'] == 'REVIEW')
    soft_recall = soft_tp / (soft_tp + sum(1 for rid, gt_label in gt.items()
                                           if rid in judgments and gt_label == 'DISCARD'
                                           and judgments[rid]['judgment'] == 'KEEP')) if True else 0

    return {
        'matched': matched,
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'soft_recall': soft_recall,
        'discard_predicted': tp + fp,
        'review_predicted': sum(1 for r in judgments.values() if r['judgment'] == 'REVIEW'),
        'keep_predicted': sum(1 for r in judgments.values() if r['judgment'] == 'KEEP'),
    }

def main():
    annotated_path = '/Users/jeremyalston/Perfect/AutoQuality Pair Copy - Echo/260300_ECHO - client annotated.xlsx'
    v4_path = '/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run/all_judgments.json'
    v5_dir = Path('/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v5')

    print('=' * 80)
    print('ECHO v4 vs v5 Comparison Against Client Ground Truth')
    print('=' * 80)

    # Load ground truth
    gt = load_client_ground_truth(annotated_path)
    gt_discards = sum(1 for v in gt.values() if v == 'DISCARD')
    gt_keeps = sum(1 for v in gt.values() if v == 'KEEP')
    print(f'\nClient ground truth: {len(gt)} respondents')
    print(f'  Discards (status=5): {gt_discards} ({gt_discards/len(gt)*100:.1f}%)')
    print(f'  Keeps (status=3):    {gt_keeps} ({gt_keeps/len(gt)*100:.1f}%)')

    # Load v4
    v4_judgments = load_judgments(v4_path)
    v4_metrics = compute_metrics(gt, v4_judgments)

    print(f'\n--- V4 Results ---')
    print(f'  Matched: {v4_metrics["matched"]}/{len(gt)}')
    print(f'  Predicted: DISCARD={v4_metrics["discard_predicted"]}, REVIEW={v4_metrics["review_predicted"]}, KEEP={v4_metrics["keep_predicted"]}')
    print(f'  TP={v4_metrics["tp"]}, FP={v4_metrics["fp"]}, TN={v4_metrics["tn"]}, FN={v4_metrics["fn"]}')
    print(f'  Precision: {v4_metrics["precision"]:.3f}')
    print(f'  Recall:    {v4_metrics["recall"]:.3f}')
    print(f'  F1:        {v4_metrics["f1"]:.3f}')
    print(f'  Soft recall (DISCARD+REVIEW catches): {v4_metrics["soft_recall"]:.3f}')

    # Load v5 (merge all chunk judgment files)
    v5_judgments = {}
    chunk_files = sorted(v5_dir.glob('agent_judgments_chunk_*.json'))
    for cf in chunk_files:
        with open(cf) as f:
            chunk_data = json.load(f)
        for item in chunk_data:
            rid = item.get('respondent_id')
            v5_judgments[rid] = {
                'judgment': item.get('agent_judgment', ''),
                'score': item.get('agent_score', 0),
                'justification': item.get('agent_justification', '')
            }

    if not v5_judgments:
        print(f'\n--- V5 Results ---')
        print(f'  No judgment files found yet. Subagents may still be running.')
        print(f'  Expected files in: {v5_dir}')
        return

    v5_metrics = compute_metrics(gt, v5_judgments)

    print(f'\n--- V5 Results ---')
    print(f'  Matched: {v5_metrics["matched"]}/{len(gt)}')
    print(f'  Predicted: DISCARD={v5_metrics["discard_predicted"]}, REVIEW={v5_metrics["review_predicted"]}, KEEP={v5_metrics["keep_predicted"]}')
    print(f'  TP={v5_metrics["tp"]}, FP={v5_metrics["fp"]}, TN={v5_metrics["tn"]}, FN={v5_metrics["fn"]}')
    print(f'  Precision: {v5_metrics["precision"]:.3f}')
    print(f'  Recall:    {v5_metrics["recall"]:.3f}')
    print(f'  F1:        {v5_metrics["f1"]:.3f}')
    print(f'  Soft recall (DISCARD+REVIEW catches): {v5_metrics["soft_recall"]:.3f}')

    # Delta
    print(f'\n--- Delta (V5 - V4) ---')
    print(f'  Precision: {v5_metrics["precision"] - v4_metrics["precision"]:+.3f}')
    print(f'  Recall:    {v5_metrics["recall"] - v4_metrics["recall"]:+.3f}')
    print(f'  F1:        {v5_metrics["f1"] - v4_metrics["f1"]:+.3f}')
    print(f'  Soft recall: {v5_metrics["soft_recall"] - v4_metrics["soft_recall"]:+.3f}')
    print(f'  Discards predicted: {v5_metrics["discard_predicted"]} vs {v4_metrics["discard_predicted"]}')

    # Analyze v5 false negatives (missed discards)
    print(f'\n--- V5 False Negatives (missed client discards) ---')
    fn_samples = []
    for rid, gt_label in gt.items():
        if gt_label == 'DISCARD' and rid in v5_judgments:
            pred = v5_judgments[rid]['judgment']
            if pred == 'KEEP':
                fn_samples.append({
                    'rid': rid,
                    'score': v5_judgments[rid]['score'],
                    'justification': v5_judgments[rid]['justification'][:200]
                })
    print(f'  Total FN (predicted KEEP for client discard): {len(fn_samples)}')
    for s in fn_samples[:10]:
        print(f'    {s["rid"]} (score={s["score"]}): {s["justification"]}')

    # Analyze v5 false positives (discarded a client keep)
    print(f'\n--- V5 False Positives (discarded client keeps) ---')
    fp_samples = []
    for rid, gt_label in gt.items():
        if gt_label == 'KEEP' and rid in v5_judgments:
            pred = v5_judgments[rid]['judgment']
            if pred == 'DISCARD':
                fp_samples.append({
                    'rid': rid,
                    'score': v5_judgments[rid]['score'],
                    'justification': v5_judgments[rid]['justification'][:200]
                })
    print(f'  Total FP (predicted DISCARD for client keep): {len(fp_samples)}')
    for s in fp_samples[:10]:
        print(f'    {s["rid"]} (score={s["score"]}): {s["justification"]}')

    # Save full comparison
    output = {
        'ground_truth': {'total': len(gt), 'discards': gt_discards, 'keeps': gt_keeps},
        'v4': v4_metrics,
        'v5': v5_metrics,
        'delta': {
            'precision': v5_metrics['precision'] - v4_metrics['precision'],
            'recall': v5_metrics['recall'] - v4_metrics['recall'],
            'f1': v5_metrics['f1'] - v4_metrics['f1'],
            'soft_recall': v5_metrics['soft_recall'] - v4_metrics['soft_recall'],
        }
    }
    output_path = v5_dir / 'v4_v5_comparison.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f'\nFull comparison saved to: {output_path}')

if __name__ == '__main__':
    main()
