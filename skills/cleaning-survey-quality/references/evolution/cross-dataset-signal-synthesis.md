# Cross-Dataset Signal Synthesis (10 Workbooks, 12,384 Respondents)

This document synthesizes signal mining results across 10 annotated TFG workbooks. It is a label-aware evolution reference — use it to improve the pipeline, not as untouched validation data.

## Dataset Inventory

| Dataset | Rows | Discard Rate | Status 3 | Status 5 |
|---|---|---|---|---|
| 251101_THD-CX | 1905 | 6.2% | 1787 | 118 |
| 251205_TFG-Contractor-Index-Q1 | 878 | 11.0% | 781 | 97 |
| 260111_Delta-Water-Filtration | 1353 | 25.7% | 1005 | 348 |
| 260200_SBD | 787 | 44.5% | 437 | 350 |
| 260206_OC-BH | 2164 | 17.3% | 1789 | 375 |
| 260300_ECHO | 1566 | 35.3% | 1013 | 553 |
| 260306_TFG-Contractor-Index-Q2 | 1117 | 36.0% | 715 | 402 |
| 260401_OC-CAN | 743 | 38.4% | 458 | 285 |
| 260403_Masterlock-Conjoint | 916 | 22.5% | 710 | 206 |
| 260404_ADDO | 1356 | 26.4% | 998 | 358 |

Discard rates range from 6.2% (THD-CX) to 44.5% (SBD). The pipeline must calibrate to per-dataset base rates, not assume a fixed threshold.

## Cross-Dataset Field Family Rankings

Total signal scores across all 10 datasets:

1. **demographic_profile**: 5703.8 — strongest in TFG-Contractor-Index-Q2 (q4, q6r1-3, q45f/h, q40, q43)
2. **brand_funnel_ad**: 4058.5 — strongest in ECHO (q17r2/r3, q29, q19_2026othr1, q19_2026r13, q16r1/r2, q18r13)
3. **other** (LangAssess, device, OS): 2729.2 — strongest in TFG-Contractor-Index-Q2, OC-CAN, ADDO
4. **ownership_use_product**: 2722.6 — strongest in ECHO (q11othr1/2/4, q11ar11c4), SBD (q13r1/r2), OC-BH (q121r1)
5. **fielding_technical**: 1446.7 — strongest in TFG-Contractor-Index-Q2 (vlist, list, SUPNAME, bhf, sfh, dcua), OC-CAN
6. **channel_supplier**: 675.8 — strongest in OC-BH (q141r1), Delta (q22 series), ECHO (q21d_2026r17)
7. **switching_loyalty**: 599.1 — strongest in Delta (q32), OC-CAN (q31 series), ECHO (q30_2026, q31_2026)
8. **matrix_attributes**: 592.3 — strongest in TFG-Contractor-Index-Q2 (q37, q34), OC-BH (q36r1-4), Delta (q33)
9. **quota_classification**: 470.9 — strongest in TFG-Contractor-Index-Q2 (CLASSIFY, CLASSIFYGROUP), ECHO (CONAGE, PROAGE, CLASSIFY)
10. **open_end_text**: 16.1 — weak signal overall; strongest in Masterlock, SBD, THD-CX

### Key Insight: Open-End Text Is the Weakest Family

Open-end text has a total signal score of only 16.1 across all datasets — the weakest family by far. This confirms that the v4 pipeline's focus on semantic OE review was misaligned with how clients actually discard. The strongest families are survey-design variables (demographic, brand funnel, ownership, fielding, quota) — not free text.

## Cross-Dataset Marker/Label Observations

| Marker Family | Mentions | Discard Share | Present In |
|---|---|---|---|
| `qualified` | 12785 | 24.2% | All 10 datasets |
| `badopen` | 3092 | **100%** | All 10 datasets |
| `bad:qualified` | 3068 | **100%** | All 10 datasets |
| `RegionQuota` | 3471 | 69.9% | 8 datasets |
| `TotalQuota` | 2406 | 91.6% | 6 datasets |
| `CLASSIFYQuota` | 2273 | 69.9% | 5 datasets |
| `AgeQuota` | 2342 | 65.6% | 5 datasets |
| `ProductBalancingQuota` | 1571 | 87.7% | Masterlock, Delta |
| `GenderQuota` | 1943 | 64.8% | ECHO, Delta, ADDO |
| `BRANDS2RATEQuota` | 1326 | 78.4% | ECHO only |
| `ChannelQuota` | 582 | 95.0% | ECHO only |
| `TradeQuota` | 553 | 89.3% | TFG-Contractor-Index |
| `CONAgeQuota` | 696 | 57.8% | ECHO only |

### Critical Finding: `badopen` and `bad:qualified` Are Universal Discard Markers

Across ALL 10 datasets, `badopen` has a 100% discard share — every row with this marker was discarded by the client. `bad:qualified` is similarly universal (100% discard share, 3068 mentions). This means:

1. The client's primary discard mechanism is open-end quality judgment (`badopen`), not fraud detection
2. `badopen` is applied across all survey programs, not just ECHO
3. The pipeline's Stage 2 (PM Quality Assessment) must be the primary discard driver, not Stage 1 (Fraud Detection)

### Quota Markers Are Dataset-Specific

Quota marker families vary by dataset:
- ECHO has `BRANDS2RATEQuota`, `ChannelQuota`, `CONAgeQuota` — brand and channel quota management
- Masterlock has `ProductBalancingQuota` — conjoint product balancing
- TFG-Contractor-Index has `TradeQuota`, `TradeGroupQuota` — trade classification quotas
- Delta has `GenderQuota`, `RegionQuota` — demographic quotas

This confirms that quota reconstruction must be per-dataset, not generic.

## Cross-Dataset Derived Signals

Key derived signals with positive lift across datasets:

| Signal | Dataset | Hits | Discard Rate | Lift |
|---|---|---|---|---|
| `missing_supplier` | TFG-CI-Q2 | 416 | 75.5% | +39.5% |
| `classify_1` (pro) | ECHO | 250 | 60.4% | +25.1% |
| `very_fast_under_5min` | SBD | 49 | 93.9% | +49.4% |
| `very_fast_under_5min` | ADDO | 128 | 56.3% | +29.8% |
| `conditions_ariens` | ECHO | 289 | 59.2% | +23.9% |
| `brand_share_fragmented` | ECHO | 348 | 52.0% | +16.7% |

Fast completion (<5 min) generalizes across datasets (SBD, ADDO, ECHO). Pro-branch classification generalizes (ECHO, TFG-CI). Missing supplier is a strong signal in TFG-CI-Q2.

## Skill Weakpoints Identified

1. **Survey-design variables are not admin noise.** Across workbooks, high-signal fields often live in quota/classification, fielding, brand/product funnel, condition, list/source, and branch variables. The skill should require a survey-design contract before semantic row review.

2. **Brand/product funnel reconstruction is central.** The most label-correlated family across Echo and other workbooks is not free text alone; it is the connected pattern of awareness/top/possible/rating/share/ad/consideration/product variables.

3. **Open-end review needs field-specific standards.** Generic placeholder/meta/junk checks are insufficient; each open field needs prompt-fit examples and accepted guardrails, because short noun answers are valid in some fields and invalid in others.

4. **Client discard is broader than authenticity.** The skill should produce separate `authenticity_risk`, `quality_discard_risk`, and `client_reject_probability` so quota or fielding removals do not get mislabeled as fraud.

5. **Residual learning must be mandatory.** After every annotated comparison, all FNs/FPs should be packetized with label marker family, raw branch fields, our rationale, and proposed missed signal; promote only signals that survive accepted-row counterexamples.

6. **Matrix and allocation tasks need typed validators.** Share allocations, conjoint/rating grids, rank/NPS batteries, and repeated brand matrices should be checked for sum constraints, overbreadth, excessive high ratings, impossible missingness, and branch-incoherent answers.

## Recommended Skill Additions

### 1. Survey-Design Contract (pre-review phase)

Before semantic row review, build a survey-design contract from:
- Quota/branch fields: CLASSIFY, CLASSIFYGROUP, CONAGE, PROAGE, REGION, TradeQuota
- Condition flags: conditionsAriens, conditionsHD_or_OPE_dealers, conditionsOther_channel
- List/source: list, vlist, SUPNAME, sfh, bhf, dcua
- Brand-to-rate fields: BRANDS2RATE, q17, q18, q19 series
- Fielding context: vlist, list, supplier cohort

### 2. Brand/Product Relation Graph

Check the brand funnel as a connected system:
- Awareness → Top-of-mind → Possible → Rating → Share allocation → Ad recall → Consideration → NPS
- Impossible jumps (aware of but cannot rate; recommend but never heard of)
- Share allocation anomalies (equal share, fragmented share, many zeros)
- Brand name quality in OE (real brands vs garbled/wrong-universe)
- Rating consistency with stated preference

### 3. Open-End Field Contracts

Each open-end field needs:
- Prompt text and expected answer role
- Valid examples (accepted rows with this field)
- Invalid examples (discarded rows with this field)
- Accepted-row guardrails (rows that look similar but were kept)
- Short-answer validity rules (when is a short answer valid vs invalid for this field?)

### 4. Three-Component Risk Score

Replace the single `agent_score` with three components:
- `authenticity_risk` (0-1): Is this respondent a bot/fraud/AI?
- `quality_discard_risk` (0-1): Does this respondent fail the PM quality bar?
- `client_reject_probability` (0-1): Would the client discard this respondent?

The final `agent_judgment` is derived from the combination:
- High authenticity_risk → DISCARD (fraud)
- Low authenticity_risk + high quality_discard_risk → DISCARD or REVIEW (quality)
- Low both + high client_reject_probability (quota/fielding) → REVIEW (calibration needed)

### 5. Accepted Guardrail Ledger

For every proposed rule, maintain a ledger of accepted rows that look similar and why they must be kept. This prevents over-firing rules from creating false positives.

### 6. Matrix/Allocation Validators

Typed validators for structured answer patterns:
- **Share allocation**: sum constraint (should sum to 100), overbreadth (8+ brands), zero-count
- **Conjoint/rating grids**: excessive high ratings (12+ at 8-10), straightlining across distinct constructs
- **Rank/NPS batteries**: impossible missingness, branch-incoherent answers
- **Repeated brand matrices**: entropy, pattern clustering

## Per-Dataset Calibration Notes

### ECHO (35.3% discard rate)
- Primary driver: `badopen` (100% of discards)
- Strong signals: brand funnel (q17, q19, q16, q18), equipment ownership (q11), CLASSIFY=1, conditionsAriens
- Quota markers: BRANDS2RATEQuota, ChannelQuota, CONAgeQuota, GenderQuota

### SBD (44.5% discard rate)
- High base rate — calibrate threshold downward
- Strong signals: ownership_use_product (q13r1/r2), very_fast_under_5min
- Quota markers: TotalQuota, CLASSIFYQuota, AgeQuota, GenderQuota

### Delta Water Filtration (25.7% discard rate)
- Strong signals: channel_supplier (q22 series), switching_loyalty (q32), matrix_attributes (q33)
- Quota markers: ProductBalancingQuota, GenderQuota, RegionQuota, TotalQuota

### TFG-Contractor-Index-Q2 (36.0% discard rate)
- Strong signals: demographic_profile (q4, q6, q45, q40, q43), fielding_technical (vlist, list, SUPNAME), quota_classification (CLASSIFY, CLASSIFYGROUP)
- Quota markers: TradeQuota, TradeGroupQuota, RegionQuota
- `missing_supplier` has 75.5% discard rate (lift +39.5%)

### THD-CX (6.2% discard rate)
- Very low base rate — calibrate threshold upward
- Most respondents are kept; be conservative with discards
- Quota markers: RegionQuota, CLASSIFYQuota, AgeQuota

## Source Data

Full signal mining artifacts are in `references/evolution/multiworkbook-signal-mining/`:
- `dataset_inventory.csv` — per-dataset row counts, discard rates, column counts
- `cross_dataset_family_summary.csv` — field family scores across datasets
- `cross_dataset_raw_field_signals.csv` — per-field lift scores (1.1MB)
- `cross_dataset_derived_signals.csv` — derived signal lift across datasets
- `cross_dataset_marker_summary.csv` — marker family distribution and discard share
- `open_end_signal_examples.csv` — per-respondent OE text with marker context
- `multiworkbook_skill_recommendations.md` — original recommendations
