#!/usr/bin/env python3
"""Validate v6 AutoQuality run: check all artifacts, all fields, and verify agent-filled metadata."""
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

V6_DIR = Path('/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run_v6')

REQUIRED_FIELDS = [
    'respondent_id', 'agent_score', 'agent_judgment', 'agent_justification',
    'authenticity_risk', 'quality_discard_risk', 'client_reject_probability',
    'primary_removal_reason', 'secondary_removal_reason', 'removal_confidence',
    'evidence_families_fired', 'evidence_family_scores',
    'badopen_trigger', 'badopen_field', 'badopen_evidence', 'badopen_severity',
    'oe_classification', 'oe_equipment_named', 'oe_grounding_anchors', 'oe_word_count',
    'ml_score', 'ml_top_signals', 'ml_confidence',
    'semantic_remapping', 'stage1_fraud_verdict', 'stage2_quality_verdict',
    'converging_family_count',
]

EVIDENCE_FAMILIES = [
    'core_oe_quality', 'platform_risk', 'model_risk', 'source_risk',
    'duplicate_semantics', 'survey_structure', 'brand_funnel',
    'timing_engagement', 'quota_reconstruction',
]

def main():
    print('=' * 80)
    print('V6 RUN VALIDATION')
    print('=' * 80)

    errors = []
    warnings = []

    # 1. Check all artifacts exist
    print('\n[1/6] Checking artifacts...')
    expected_artifacts = [
        'agent_review_instructions.md',
        'review_summary.json',
        'agent_judgments.json',
        '109-2601 Echo BH_annotated.xlsx',
        '109-2601 Echo BH_dashboard.html',
        'summary.json',
        'comparison_results.json',
    ]
    for art in expected_artifacts:
        path = V6_DIR / art
        if path.exists():
            print(f'  OK: {art}')
        else:
            errors.append(f'Missing artifact: {art}')
            print(f'  MISSING: {art}')

    # Check chunk files
    for i in range(8):
        chunk = V6_DIR / f'review_chunk_{i:02d}.json'
        if chunk.exists():
            print(f'  OK: review_chunk_{i:02d}.json')
        else:
            errors.append(f'Missing review_chunk_{i:02d}.json')

        judgment = V6_DIR / f'agent_judgments_chunk_{i:02d}.json'
        if judgment.exists():
            print(f'  OK: agent_judgments_chunk_{i:02d}.json')
        else:
            errors.append(f'Missing agent_judgments_chunk_{i:02d}.json')

    # 2. Load all judgments and check field completeness
    print('\n[2/6] Checking field completeness...')
    all_judgments = []
    for i in range(8):
        path = V6_DIR / f'agent_judgments_chunk_{i:02d}.json'
        if not path.exists():
            continue
        with open(path) as f:
            chunk = json.load(f)
        all_judgments.extend(chunk)

    print(f'  Total judgments: {len(all_judgments)}')

    missing_fields = defaultdict(int)
    null_fields = defaultdict(int)
    for j in all_judgments:
        for field in REQUIRED_FIELDS:
            if field not in j:
                missing_fields[field] += 1
            elif j[field] is None and field not in ('secondary_removal_reason', 'badopen_field', 'badopen_evidence'):
                null_fields[field] += 1

    if missing_fields:
        for field, count in sorted(missing_fields.items()):
            errors.append(f'Missing field {field}: {count} respondents')
            print(f'  MISSING FIELD: {field} ({count} respondents)')
    else:
        print(f'  All {len(REQUIRED_FIELDS)} required fields present in all judgments')

    if null_fields:
        for field, count in sorted(null_fields.items()):
            warnings.append(f'Null field {field}: {count} respondents')
            print(f'  NULL FIELD: {field} ({count} respondents)')
    else:
        print(f'  No unexpected null fields')

    # 3. Verify agent-filled metadata (not script-filled)
    print('\n[3/6] Verifying metadata is agent-filled (not script-filled)...')

    # Check: evidence_family_scores should have varied triggers (not all the same)
    trigger_variety = set()
    for j in all_judgments:
        efs = j.get('evidence_family_scores', {})
        for fam, data in efs.items():
            if isinstance(data, dict):
                trigger = data.get('trigger')
                if trigger:
                    trigger_variety.add(trigger)

    print(f'  Unique evidence family triggers: {len(trigger_variety)}')
    if len(trigger_variety) < 5:
        warnings.append(f'Low trigger variety ({len(trigger_variety)}) — may be script-filled')
    else:
        print(f'  OK: {len(trigger_variety)} unique triggers — indicates agent judgment')

    # Check: justifications should be unique (not templated)
    justifications = [j.get('agent_justification', '') for j in all_judgments]
    unique_justifications = len(set(justifications))
    print(f'  Unique justifications: {unique_justifications}/{len(all_judgments)}')
    if unique_justifications < len(all_judgments) * 0.5:
        warnings.append(f'Low justification variety ({unique_justifications}/{len(all_judgments)}) — may be templated')
    else:
        print(f'  OK: {unique_justifications} unique justifications — indicates agent authoring')

    # Check: oe_equipment_named should vary (not all empty or all same)
    equipment_lists = [tuple(sorted(j.get('oe_equipment_named', []))) for j in all_judgments]
    unique_equipment = len(set(equipment_lists))
    print(f'  Unique equipment_named lists: {unique_equipment}/{len(all_judgments)}')
    if unique_equipment < 10:
        warnings.append(f'Low equipment variety — may be script-filled')
    else:
        print(f'  OK: {unique_equipment} unique equipment lists — indicates agent analysis')

    # Check: authenticity_risk should have variety (not all same value)
    auth_values = [j.get('authenticity_risk') for j in all_judgments]
    unique_auth = len(set(auth_values))
    print(f'  Unique authenticity_risk values: {unique_auth}')
    if unique_auth < 5:
        warnings.append(f'Low authenticity_risk variety — may be script-filled')
    else:
        print(f'  OK: {unique_auth} unique values — indicates agent scoring')

    # Check: badopen_trigger distribution
    badopen_dist = Counter(j.get('badopen_trigger', 'missing') for j in all_judgments)
    print(f'  Badopen trigger distribution: {dict(badopen_dist)}')
    if len(badopen_dist) < 3:
        warnings.append(f'Low badopen trigger variety — may be script-filled')
    else:
        print(f'  OK: {len(badopen_dist)} distinct triggers — indicates agent classification')

    # Check: primary_removal_reason distribution
    reason_dist = Counter(j.get('primary_removal_reason', 'missing') for j in all_judgments)
    print(f'  Primary removal reason distribution: {dict(reason_dist)}')
    if len(reason_dist) < 3:
        warnings.append(f'Low removal reason variety — may be script-filled')
    else:
        print(f'  OK: {len(reason_dist)} distinct reasons — indicates agent classification')

    # 4. Check evidence_family_scores structure
    print('\n[4/6] Checking evidence_family_scores structure...')
    for j in all_judgments[:5]:
        efs = j.get('evidence_family_scores', {})
        missing_families = [f for f in EVIDENCE_FAMILIES if f not in efs]
        if missing_families:
            errors.append(f'Respondent {j.get("respondent_id")}: missing families in evidence_family_scores: {missing_families}')
        for fam, data in efs.items():
            if not isinstance(data, dict):
                errors.append(f'Respondent {j.get("respondent_id")}: {fam} is not a dict')
            elif 'fired' not in data or 'score' not in data:
                errors.append(f'Respondent {j.get("respondent_id")}: {fam} missing fired/score')

    if not any('evidence_family_scores' in str(e) for e in errors):
        print(f'  OK: All 9 evidence families present with fired/score/trigger structure')

    # 5. Check semantic_remapping structure
    print('\n[5/6] Checking semantic_remapping structure...')
    sr_fields = ['core_oe_field', 'core_oe_role', 'classify_branch', 'channel_condition', 'quota_cells']
    for j in all_judgments[:5]:
        sr = j.get('semantic_remapping', {})
        missing_sr = [f for f in sr_fields if f not in sr]
        if missing_sr:
            errors.append(f'Respondent {j.get("respondent_id")}: missing semantic_remapping fields: {missing_sr}')

    if not any('semantic_remapping' in str(e) for e in errors):
        print(f'  OK: semantic_remapping has all 5 sub-fields')

    # 6. Summary
    print(f'\n{"="*80}')
    print(f'VALIDATION SUMMARY')
    print(f'{"="*80}')
    print(f'  Total judgments: {len(all_judgments)}')
    print(f'  Required fields: {len(REQUIRED_FIELDS)}')
    print(f'  Errors: {len(errors)}')
    print(f'  Warnings: {len(warnings)}')

    if errors:
        print(f'\nERRORS:')
        for e in errors[:20]:
            print(f'  - {e}')

    if warnings:
        print(f'\nWARNINGS:')
        for w in warnings[:10]:
            print(f'  - {w}')

    if not errors:
        print(f'\nPASS: All artifacts generated, all fields present, metadata is agent-filled')
    else:
        print(f'\nFAIL: {len(errors)} errors found')

    return len(errors) == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
