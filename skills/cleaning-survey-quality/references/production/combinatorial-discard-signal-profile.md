# Combinatorial Discard Signal Profile

## Overview

Analysis of 13,388 respondents across 11 annotated Excel datasets. Ground truth is `status == 5` as client reject/discard; all other statuses are treated as accepts. Overall reject rate is 23.3% (3,124/13,388).

## Current status

Use this file as signal discovery background, not as the final disposition rule. The V7 calibration in `v7-calibration-and-guardrails.md` supersedes the older auto-discard language below whenever there is a conflict.

The key correction is that raw signal tiers must pass accepted-row guardrails and evidence-family convergence. A high-lift signal can route a row to REVIEW, but DISCARD still requires the V7 threshold pattern: strong ML, certain platform fraud, or independent family convergence.

## Key Conclusions

1. **Combinations are more informative than raw signal count, but still not sufficient as a global discard rule.** The derived signal count distributions overlap heavily between accepts and rejects. High-volume signals usually lift reject odds only modestly above the 23.3% baseline.

2. **The best-supported high-lift combinations cluster around explicit review/termination flags plus geography/search and timing/text-quality signals.** These combinations can identify concentrated risk pockets, but the high-precision pockets are relatively small.

3. **Dataset context matters.** Client reject rates range from 5.3% to 44.5%. A single global combination threshold will over-discard cleaner datasets and under-discard high-reject datasets. Per-dataset calibration is mandatory.

## Dataset Baseline

| Dataset | Rows | Rejects | Reject Rate |
|---------|------|---------|-------------|
| ODL Switchable Glass | 603 | 32 | 5.3% |
| THD Digital CX | 1,905 | 118 | 6.2% |
| TFG Contractor Index Q1 | 878 | 97 | 11.0% |
| Oldcastle Brand Health | 2,164 | 375 | 17.3% |
| Masterlock Conjoint | 916 | 206 | 22.5% |
| Delta Water Filtration | 1,353 | 348 | 25.7% |
| ADDO RaceTrac | 1,356 | 358 | 26.4% |
| Echo Brand Health | 1,566 | 553 | 35.3% |
| TFG Contractor Index Q2 | 1,117 | 402 | 36.0% |
| Oldcastle Canada | 743 | 285 | 38.4% |
| SBD Brand Association | 787 | 350 | 44.5% |

## Signal Tier System

Based on empirical lift analysis against client ground truth, signals fall into three tiers with very different predictive values. **Do NOT treat all signals equally. Do NOT use signal count as a risk accumulator** — nearly every respondent has 4-6 signals.

### TIER 1 — High Precision (strong disposition candidates, 50-90% precision)

| Signal | Support | Rejects | Reject Rate | Lift | Recall |
|--------|---------|---------|-------------|------|--------|
| `generic_placeholder_open_end` | 23 | 20 | 87.0% | 3.73x | 0.6% |
| `termflags_nonzero` | 68 | 47 | 69.1% | 2.96x | 1.5% |
| `ai_or_overpolished_text_marker` | 98 | 50 | 51.0% | 2.19x | 1.6% |
| `long_low_specificity_text` | 55 | 50 | 90.9% | 3.90x | 1.6% |
| `pasted_text_flag` / `pasted_open_end` | 33 | 9 | 27.3% | 1.17x | 0.3% |

**Usage**: Treat TIER 1 signals as strong review evidence. Auto-discard only when the V7 threshold is met, such as ML >= 0.8, certain platform fraud, or independent family convergence. `pasted_text_flag` alone routes to REVIEW.

### TIER 2 — Moderate (use with supplier risk or semantic weakness)

| Signal | Support | Rejects | Reject Rate | Lift | Recall |
|--------|---------|---------|-------------|------|--------|
| `rd_searchr3_canada` | 617 | 283 | 45.9% | 1.97x | 9.1% |
| `rd_searchr1_22` | 562 | 170 | 30.2% | 1.30x | 5.4% |
| `rd_searchr1_23` | 1,345 | 444 | 33.0% | 1.42x | 14.2% |
| `rd_searchr1_20` | 1,611 | 434 | 26.9% | 1.15x | 13.9% |
| `qtime_under_dataset_p10` | 1,344 | 420 | 31.2% | 1.34x | 13.4% |

**Usage**: Use as discard evidence only when combined with high-risk supplier OR semantic incoherence. Do not discard on TIER 2 signals alone.

### TIER 3 — Low/Anti-Predictive (do NOT use as discard triggers)

| Signal | Support | Rejects | Reject Rate | Lift | Recall |
|--------|---------|---------|-------------|------|--------|
| `rd_searchr3_united_states` | 11,209 | 2,839 | 25.3% | 1.09x | 90.9% |
| `rd_review_any_nonzero` | 10,762 | 2,783 | 25.9% | 1.11x | 89.1% |
| `rd_review_r4_positive` | 10,091 | 2,574 | 25.5% | 1.09x | 82.4% |
| `matrix_near_straightline` | 8,450 | 2,197 | 26.0% | 1.11x | 70.3% |
| `duplicate_open_end_text` | 865 | 230 | 26.6% | 1.14x | 7.4% |
| `qtime_5_to_10_minutes` | 5,495 | 1,084 | 19.7% | **0.85x** | 34.7% |
| `qtime_under_4_minutes` | — | — | 17% | **0.73x** | — |
| `qtime_4_to_5_minutes` | — | — | 0% TP | **ANTI** | — |
| `very_short_required_open_end` | — | — | 11% | **0.46x** | — |

**Usage**: These signals are present in the vast majority of BOTH accepts and rejects. They are NOT discriminative. Do NOT use them as discard triggers. On Delta, `matrix_near_straightline` was actually MORE common in false positives than true positives. Fast timing (`qtime_5_to_10_minutes`, `qtime_under_4_minutes`) is ANTI-predictive — fast respondents with signals are often ACCEPTED by the client.

**Critical anti-pattern**: `clientflags_ge_3 + qtime_5_to_10_minutes` has a 0.0% reject rate. This combination is a strong ACCEPT signal.

## Best-Supported Pair Combinations (minimum 75 respondents)

| Combo | Support | Rejects | Reject Rate | Lift |
|-------|---------|---------|-------------|------|
| `rd_review_r4_positive + rd_searchr3_canada` | 495 | 236 | 47.7% | 2.04x |
| `qtime_under_5_minutes + duplicate_open_end_text` | 112 | 51 | 45.5% | 1.95x |
| `rd_review_any_nonzero + rd_searchr3_canada` | 561 | 246 | 43.9% | 1.88x |
| `rd_searchr3_canada + matrix_near_straightline` | 436 | 188 | 43.1% | 1.85x |
| `rd_searchr3_canada + qtime_under_5_minutes` | 88 | 36 | 40.9% | 1.75x |
| `qtime_under_dataset_p10 + duplicate_open_end_text` | 135 | 52 | 38.5% | 1.65x |
| `qtime_under_dataset_p10 + matrix_near_straightline` | 779 | 298 | 38.3% | 1.64x |
| `rd_review_problem_code + qtime_under_dataset_p10` | 890 | 312 | 35.1% | 1.50x |
| `qtime_under_5_minutes + matrix_near_straightline` | 784 | 259 | 33.0% | 1.42x |
| `rd_searchr3_united_states + qtime_under_dataset_p10` | 1,160 | 383 | 33.0% | 1.41x |
| `rd_review_any_nonzero + qtime_under_dataset_p10` | 1,145 | 376 | 32.8% | 1.41x |
| `qtime_under_dataset_p10 + very_short_required_open_end` | 201 | 66 | 32.8% | 1.41x |

## Best-Supported Triple Combinations (minimum 50 respondents)

| Combo | Support | Rejects | Reject Rate | Lift |
|-------|---------|---------|-------------|------|
| `termflags_nonzero + rd_searchr3_united_states + matrix_near_straightline` | 66 | 46 | 69.7% | 2.99x |
| `termflags_nonzero + rd_review_any_nonzero + matrix_near_straightline` | 56 | 37 | 66.1% | 2.83x |
| `termflags_nonzero + rd_review_r4_positive + matrix_near_straightline` | 56 | 37 | 66.1% | 2.83x |
| `rd_review_any_nonzero + rd_review_r4_positive + ai_or_overpolished_text_marker` | 64 | 40 | 62.5% | 2.68x |
| `rd_review_r4_positive + rd_searchr3_united_states + ai_or_overpolished_text_marker` | 60 | 36 | 60.0% | 2.57x |
| `qtime_under_5_minutes + qtime_under_dataset_p10 + duplicate_open_end_text` | 91 | 45 | 49.5% | 2.12x |
| `rd_review_r4_positive + rd_searchr3_canada + qtime_under_dataset_p10` | 65 | 32 | 49.2% | 2.11x |

## Most Common Exact Signal Archetypes

| Active Signal Combo | Support | Rejects | Reject Rate | Lift |
|---------------------|---------|---------|-------------|------|
| `rd_review_any_nonzero + rd_review_r4_positive + rd_searchr3_united_states + matrix_near_straightline` | 1,690 | 448 | 26.5% | 1.14x |
| `rd_review_any_nonzero + rd_review_problem_code + rd_review_r4_positive + rd_searchr3_united_states + matrix_near_straightline` | 1,213 | 305 | 25.1% | 1.08x |
| `rd_review_any_nonzero + rd_review_r4_positive + rd_searchr3_united_states + qtime_5_to_10_minutes` | 927 | 186 | 20.1% | **0.86x** |
| `rd_review_any_nonzero + rd_review_r4_positive + rd_searchr3_united_states` | 530 | 183 | 34.5% | 1.48x |
| `rd_searchr3_united_states + matrix_near_straightline` | 469 | 145 | 30.9% | 1.32x |
| `clientflags_ge_3 + qtime_5_to_10_minutes` | 246 | 0 | **0.0%** | **0.00x** |

**Key insight**: The most common archetype (1,690 respondents) has only 1.14x lift — barely above baseline. The `qtime_5_to_10_minutes` archetypes have BELOW-baseline reject rates. The `clientflags_ge_3 + qtime_5_to_10_minutes` archetype has ZERO rejects.

## Supplier Risk Calibration

Supplier reject rates vary enormously. Use supplier risk level as a major factor in discard decisions:

- **High-risk** (reject_rate >= 40%): Lower threshold for discard. These suppliers produce more bad data.
- **Moderate-risk** (reject_rate 20-39%): Standard threshold.
- **Low-risk** (reject_rate < 20%): Higher threshold. Be conservative — false positives are costly here.

On Delta, high-risk supplier discards achieved 58% precision vs 28% for moderate-risk. The "None" supplier (missing SUPNAME) had a 57% precision rate.

## Timing Is Counterintuitive

- **Fast timing is NOT a discard signal.** `qtime_5_to_10_minutes` has 0.85x lift — BELOW baseline. Fast respondents with signals are often ACCEPTED by the client.
- **Above-median timing is MORE predictive of rejection.** On Delta, above-median timing discards had 59% precision vs 33% for bottom-25% timing.
- **`qtime_under_dataset_p10`** (bottom 10% of timing for the dataset) has 1.34x lift, making it the only timing signal with meaningful discriminative power. Use it as a TIER 2 signal, not a standalone discard trigger.

## Historical refined discard decision rules

These rules came before V7 and should be interpreted through the V7 guardrails.

1. **Strong review or discard candidate**: Any TIER 1 signal present (`termflags_nonzero`, `long_low_specificity_text`, `ai_or_overpolished_text_marker`, `generic_placeholder_open_end`)
2. **DISCARD**: Supplier is high-risk AND profile shows ANY semantic weakness
3. **DISCARD**: Supplier is high-risk AND 2+ TIER 2 signals present
4. **DISCARD**: Profile is clearly incoherent (demographic contradictions, off-topic open-end, AI-generated text, third-person text)
5. **REVIEW**: Supplier is moderate-risk with TIER 2 signals but coherent profile
6. **REVIEW**: `pasted_text_flag` only with otherwise coherent profile
7. **REVIEW**: Supplier is high-risk with coherent profile and no TIER 2 signals
8. **KEEP**: No TIER 1 or TIER 2 signals AND profile is coherent (regardless of TIER 3 signals)
9. **KEEP**: Low-risk supplier with coherent profile (even with TIER 3 signals)

**Calibrate per-dataset**: Match the target discard rate from `population_stats.json` `dataset_reject_rate`. If natural rule application gives a different rate, adjust strictness on Rule 4 (semantic coherence).

## Signal Definitions

Signals are derived from fields present in the workbooks: `TERMFLAGS`, `redem_*`, `CLIENTFLAGSr1`, `*_RD_Reviewr*`, `RD_Searchr*`, `_Pasted`, `qtime`, primary open-end text fields, and matrix-style numeric question grids. Exact duplicate text is computed within each dataset and text column after lowercasing and punctuation normalization. `matrix_near_straightline` flags rows where at least 5 answered cells in an inferred matrix group have >=80% identical non-zero values. Near-ubiquitous RD fields (`rd_searchr0_low`, `rd_searchr3_nonempty`) are intentionally excluded from combination tables because they create tautological combinations without improving discrimination.

## Validated Performance (Delta Water Filtration)

| Metric | V1 (no signals) | V2 (refined) | Improvement |
|--------|----------------|--------------|-------------|
| Discard rate | 11.1% | 26.0% | +14.9pp |
| Precision | 42.0% | 43.2% | +1.2pp |
| Recall | 18.1% | 43.7% | +25.6pp |
| F1 | 25.3% | 43.4% | +18.1pp |
| True positives | 63 | 152 | +89 |
| False positives | 87 | 200 | +113 |

The refined pipeline maintained precision while more than doubling recall, proving that signal tiering + supplier risk + semantic coherence can improve discard identification without proportionally increasing false positives.
