# Per-Dataset Strongest ML Signals

This reference documents the strongest predictive signals for each of the 11 annotated datasets,
extracted from per-dataset Gradient Boosting models. The agent should use these as a starting
point for independent analysis — they tell the agent WHICH signals matter most for EACH dataset,
not what to conclude. The agent must still verify the signal against the respondent's full chain.

## How to Use

1. When analyzing a new dataset, first check if it resembles one of the 11 training datasets
   (same client, same survey type, similar reject rate).
2. Use the top features for the most similar dataset as priority signals to check.
3. For each flagged respondent, verify the signal by reading the full answer chain.
4. The effect size (Cohen's d) tells you HOW differently rejected vs accepted respondents
   score on that feature. Large positive d = rejected respondents score much higher.
5. Feature importance tells you how much the model RELIED on that feature for classification.

## Signal Interpretation Guide

- `supplier_reject_rate`: Historical reject rate for this supplier. Higher = riskier supplier.
- `rd_RD_Searchr1/r3`: Decipher review metadata. Non-zero = flagged by platform review.
- `qtime_seconds` / `qtime_seconds_zscore`: Completion time. Low z-score = very fast.
- `matrix_unique_ratio`: Diversity of matrix/grid answers. Low = straightlining.
- `oe_*`: Open-end text features. Short/generic/none = low effort.
- `signal_count`: Total client signals. Higher = more quality flags.
- `lang_LangAssess*`: NLP readability scores. Abnormal = suspicious.
- `supplier_x_signals`: Interaction — risky supplier with many signals.
- `coded_dk_ratio`: Proportion of "don't know" answers. High = disengaged.

---

## 251101_THD CX.xlsx

- **Respondents**: 1905
- **Rejected**: 118 (6.2%)
- **In-dataset AUC**: 0.999

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `flag_CLIENTFLAGSr1` | 0.2876 |
| 2 | `rd_RD_Searchr1` | 0.1000 |
| 3 | `lang_LangAssessReadLevel` | 0.0949 |
| 4 | `sig_clientflagsr1_nonzero` | 0.0735 |
| 5 | `demo_qNumEmployees` | 0.0389 |
| 6 | `lang_LangAssessNumWords` | 0.0378 |
| 7 | `signals_x_matrix` | 0.0319 |
| 8 | `coded_unique_ratio` | 0.0292 |
| 9 | `supplier_reject_rate` | 0.0252 |
| 10 | `lang_LangAssessNumSyl` | 0.0197 |
| 11 | `sig_rd_searchr1_2.0` | 0.0177 |
| 12 | `demo_qager1` | 0.0170 |
| 13 | `matrix_unique_ratio` | 0.0149 |
| 14 | `demo_q1` | 0.0135 |
| 15 | `ua_dup_count` | 0.0129 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `sig_clientflagsr1_nonzero` | -2.019 | lower_in_rejected | 0.0000 | 0.6710 |
| 2 | `sig_rd_searchr3_united states` | 1.919 | higher_in_rejected | 0.9831 | 0.3240 |
| 3 | `lang_LangAssessNumSen` | 1.773 | higher_in_rejected | 1.0000 | 0.3346 |
| 4 | `lang_LangAssessReadLevel` | 1.752 | higher_in_rejected | 13.6171 | 3.4397 |
| 5 | `sig_rd_review_nonzero` | 1.634 | higher_in_rejected | 0.9237 | 0.3078 |
| 6 | `flag_CLIENTFLAGSr1` | -1.574 | lower_in_rejected | 0.0000 | 1.9575 |
| 7 | `lang_LangAssessNumSyl` | 1.522 | higher_in_rejected | 24.0424 | 6.4902 |
| 8 | `lang_LangAssessNumWords` | 1.352 | higher_in_rejected | 11.6102 | 3.6463 |
| 9 | `demo_qNumEmployees` | 1.197 | higher_in_rejected | 7.1441 | 3.9183 |
| 10 | `matrix_most_common_freq` | -1.170 | lower_in_rejected | 0.1783 | 0.2790 |
| 11 | `signal_count` | 1.052 | higher_in_rejected | 5.1780 | 4.1248 |
| 12 | `signal_count_zscore` | 1.052 | higher_in_rejected | 0.8449 | -0.0558 |
| 13 | `matrix_count` | 1.035 | higher_in_rejected | 30.4237 | 28.5988 |
| 14 | `t3_count` | 0.980 | higher_in_rejected | 5.0339 | 4.0621 |
| 15 | `demo_CHANNELTRACKING` | 0.965 | higher_in_rejected | 0.9237 | 0.5378 |

### Agent Analysis Notes

- **RD_Search metadata is predictive**: Decipher review flags correlate with rejection. Check rd_RD_Searchr1 and rd_RD_Searchr3 values.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **Low reject rate (6%)**: This dataset has conservative cleaning. Be very precise — false positives are costly.

---

## 251205_TFG Contractor Index Q1.xlsx

- **Respondents**: 878
- **Rejected**: 97 (11.0%)
- **In-dataset AUC**: 1.000

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `supplier_reject_rate` | 0.3770 |
| 2 | `supplier_x_signals` | 0.1752 |
| 3 | `lang_LangAssessReadLevel` | 0.0534 |
| 4 | `coded_unique_ratio` | 0.0491 |
| 5 | `lang_LangAssessNumSyl` | 0.0443 |
| 6 | `sig_duplicate_open_end_text` | 0.0332 |
| 7 | `demo_qager1` | 0.0245 |
| 8 | `ua_dup_count` | 0.0236 |
| 9 | `demo_CLASSIFY` | 0.0163 |
| 10 | `matrix_most_common_freq` | 0.0156 |
| 11 | `qtime_log` | 0.0133 |
| 12 | `signals_x_matrix` | 0.0131 |
| 13 | `demo_qstate` | 0.0102 |
| 14 | `oe_total_chars` | 0.0098 |
| 15 | `coded_count` | 0.0097 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `supplier_reject_rate` | 2.131 | higher_in_rejected | 0.5263 | 0.0529 |
| 2 | `supplier_x_signals` | 2.104 | higher_in_rejected | 3.0463 | 0.3067 |
| 3 | `tech_vmobiledevice` | 1.653 | higher_in_rejected | 1.4742 | 0.2215 |
| 4 | `tech_vmobileos` | 1.508 | higher_in_rejected | 1.6907 | 0.8335 |
| 5 | `matrix_count` | -1.124 | lower_in_rejected | 9.1753 | 10.5992 |
| 6 | `tech_vos` | 0.824 | higher_in_rejected | 2.6289 | 1.5864 |
| 7 | `coded_count` | -0.753 | lower_in_rejected | 58.9381 | 60.1306 |
| 8 | `signals_x_matrix` | -0.678 | lower_in_rejected | 1.7471 | 2.1503 |
| 9 | `matrix_unique_ratio` | 0.646 | higher_in_rejected | 0.6955 | 0.6309 |
| 10 | `rd_RD_Searchr1` | 0.590 | higher_in_rejected | 17.7010 | 11.4891 |
| 11 | `coded_unique_ratio` | 0.574 | higher_in_rejected | 0.4001 | 0.3831 |
| 12 | `tech_vbrowser` | -0.572 | lower_in_rejected | 0.1649 | 0.7260 |
| 13 | `sig_rd_searchr1_24` | 0.516 | higher_in_rejected | 0.2474 | 0.0653 |
| 14 | `sig_rd_searchr1_2` | -0.513 | lower_in_rejected | 0.0825 | 0.2727 |
| 15 | `supplier_missing` | -0.492 | lower_in_rejected | 0.0412 | 0.1959 |

### Agent Analysis Notes

- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.
- **Client signal count is predictive**: Respondents with more client signals are more likely rejected.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **Coded answer diversity matters**: Check for high 'don't know' ratios or low answer diversity.
- **Moderate reject rate (11%)**: Standard cleaning threshold.

---

## 260111_Delta Water Filtration.xlsx

- **Respondents**: 1353
- **Rejected**: 348 (25.7%)
- **In-dataset AUC**: 0.985

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `tech_vos` | 0.0857 |
| 2 | `lang_LangAssessReadLevel` | 0.0822 |
| 3 | `lang_LangAssessNumSyl` | 0.0586 |
| 4 | `rd_RD_Searchr1` | 0.0555 |
| 5 | `matrix_most_common_freq` | 0.0524 |
| 6 | `matrix_unique_ratio` | 0.0464 |
| 7 | `qtime_seconds_zscore` | 0.0362 |
| 8 | `ua_dup_count` | 0.0356 |
| 9 | `tech_vmobileos` | 0.0334 |
| 10 | `oe_mean_chars` | 0.0323 |
| 11 | `signals_x_matrix` | 0.0309 |
| 12 | `demo_qager1` | 0.0292 |
| 13 | `demo_q1` | 0.0282 |
| 14 | `oe_total_chars` | 0.0246 |
| 15 | `demo_qstate` | 0.0244 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `tech_vmobileos` | 0.757 | higher_in_rejected | 1.6954 | 1.1791 |
| 2 | `tech_vmobiledevice` | 0.755 | higher_in_rejected | 1.5144 | 0.8229 |
| 3 | `tech_vos` | 0.737 | higher_in_rejected | 3.2270 | 2.1970 |
| 4 | `lang_LangAssessNumSyl` | 0.664 | higher_in_rejected | 19.7414 | 13.6000 |
| 5 | `t3_count` | -0.645 | lower_in_rejected | 4.1264 | 4.7134 |
| 6 | `oe_max_chars` | 0.644 | higher_in_rejected | 68.6437 | 47.7582 |
| 7 | `oe_mean_chars` | 0.642 | higher_in_rejected | 68.2014 | 47.2824 |
| 8 | `oe_total_chars` | 0.627 | higher_in_rejected | 68.8879 | 48.4935 |
| 9 | `supplier_reject_rate` | 0.618 | higher_in_rejected | 0.3094 | 0.2448 |
| 10 | `supplier_x_t2` | 0.604 | higher_in_rejected | 0.2047 | 0.1056 |
| 11 | `supplier_missing` | 0.597 | higher_in_rejected | 0.5690 | 0.2856 |
| 12 | `supplier_is_none` | 0.597 | higher_in_rejected | 0.5690 | 0.2856 |
| 13 | `oe_max_words` | 0.582 | higher_in_rejected | 10.5776 | 7.6249 |
| 14 | `lang_LangAssessNumWords` | 0.581 | higher_in_rejected | 10.5172 | 7.5990 |
| 15 | `oe_total_words` | 0.567 | higher_in_rejected | 10.6264 | 7.7393 |

### Agent Analysis Notes

- **RD_Search metadata is predictive**: Decipher review flags correlate with rejection. Check rd_RD_Searchr1 and rd_RD_Searchr3 values.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **Moderate reject rate (26%)**: Standard cleaning threshold.

---

## 260200_SBD.xlsx

- **Respondents**: 787
- **Rejected**: 350 (44.5%)
- **In-dataset AUC**: 0.994

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `qtime_log` | 0.0787 |
| 2 | `lang_LangAssessReadLevel` | 0.0725 |
| 3 | `demo_qstate` | 0.0630 |
| 4 | `oe_total_chars` | 0.0500 |
| 5 | `matrix_most_common_freq` | 0.0499 |
| 6 | `oe_lex_div` | 0.0427 |
| 7 | `oe_mean_chars` | 0.0413 |
| 8 | `qtime_seconds` | 0.0375 |
| 9 | `supplier_x_signals` | 0.0351 |
| 10 | `demo_qager1` | 0.0345 |
| 11 | `matrix_unique_ratio` | 0.0336 |
| 12 | `oe_count` | 0.0326 |
| 13 | `demo_qNumEmployees` | 0.0318 |
| 14 | `supplier_reject_rate` | 0.0297 |
| 15 | `signals_x_matrix` | 0.0293 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `sig_qtime_4_to_5_minutes` | 0.431 | higher_in_rejected | 0.1029 | 0.0069 |
| 2 | `supplier_x_signals` | 0.396 | higher_in_rejected | 2.1301 | 1.9811 |
| 3 | `demo_qIndustry` | 0.325 | higher_in_rejected | 0.0914 | 0.0183 |
| 4 | `supplier_reject_rate` | 0.317 | higher_in_rejected | 0.4512 | 0.4360 |
| 5 | `oe_count` | -0.305 | lower_in_rejected | 8.9029 | 9.5195 |
| 6 | `signals_x_matrix` | 0.279 | higher_in_rejected | 3.8034 | 3.6243 |
| 7 | `qtime_log` | -0.271 | lower_in_rejected | 6.3520 | 6.5002 |
| 8 | `signal_count` | 0.254 | higher_in_rejected | 4.7286 | 4.5469 |
| 9 | `signal_count_zscore` | 0.254 | higher_in_rejected | 0.1400 | -0.1121 |
| 10 | `sig_qtime_under_4_minutes` | 0.242 | higher_in_rejected | 0.0286 | 0.0000 |
| 11 | `oe_total_chars` | -0.237 | lower_in_rejected | 88.6257 | 98.0160 |
| 12 | `ip_is_dup` | 0.203 | higher_in_rejected | 0.0314 | 0.0046 |
| 13 | `t3_count` | 0.202 | higher_in_rejected | 4.3771 | 4.2151 |
| 14 | `demo_age` | -0.202 | lower_in_rejected | 0.5371 | 0.6362 |
| 15 | `matrix_straightline` | 0.201 | higher_in_rejected | 0.6229 | 0.5240 |

### Agent Analysis Notes

- **Slow completion is a signal**: Rejected respondents take longer (Cohen's d=0.43). May indicate bot-like or stalling behavior.
- **Open-end text quality is predictive**: Top OE features: oe_total_chars. Check for short, generic, or missing open-ends.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **High reject rate (44%)**: This dataset has aggressive cleaning. Many signals may be needed to match.

---

## 260206_OC BH.xlsx

- **Respondents**: 2164
- **Rejected**: 375 (17.3%)
- **In-dataset AUC**: 0.985

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `supplier_x_signals` | 0.0967 |
| 2 | `matrix_most_common_freq` | 0.0725 |
| 3 | `matrix_unique_ratio` | 0.0710 |
| 4 | `lang_LangAssessReadLevel` | 0.0675 |
| 5 | `supplier_reject_rate` | 0.0472 |
| 6 | `rd_RD_Searchr1` | 0.0425 |
| 7 | `matrix_count` | 0.0419 |
| 8 | `signals_x_matrix` | 0.0417 |
| 9 | `oe_mean_chars` | 0.0385 |
| 10 | `demo_qager1` | 0.0369 |
| 11 | `qtime_seconds` | 0.0331 |
| 12 | `qtime_log` | 0.0316 |
| 13 | `qtime_seconds_zscore` | 0.0315 |
| 14 | `coded_unique_ratio` | 0.0296 |
| 15 | `oe_max_chars` | 0.0245 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `sig_rd_searchr3_united states` | 0.544 | higher_in_rejected | 1.0000 | 0.8709 |
| 2 | `supplier_x_signals` | 0.532 | higher_in_rejected | 0.8746 | 0.7286 |
| 3 | `supplier_reject_rate` | 0.502 | higher_in_rejected | 0.1955 | 0.1695 |
| 4 | `ip_dup_count` | -0.479 | lower_in_rejected | 1.2240 | 8.7563 |
| 5 | `ip_is_dup` | -0.391 | lower_in_rejected | 0.0293 | 0.1347 |
| 6 | `sig_matrix_near_straightline` | -0.344 | lower_in_rejected | 0.5467 | 0.7105 |
| 7 | `sig_qtime_under_4_minutes` | 0.339 | higher_in_rejected | 0.0827 | 0.0117 |
| 8 | `sig_duplicate_open_end_text` | -0.330 | lower_in_rejected | 0.8107 | 0.9217 |
| 9 | `coded_count` | 0.327 | higher_in_rejected | 48.4347 | 44.4612 |
| 10 | `oe_max_chars` | 0.305 | higher_in_rejected | 74.7547 | 55.7647 |
| 11 | `demo_age` | -0.299 | lower_in_rejected | 0.8267 | 1.1023 |
| 12 | `demo_qager1` | -0.296 | lower_in_rejected | 19.1227 | 22.2543 |
| 13 | `oe_total_chars` | 0.287 | higher_in_rejected | 81.9120 | 63.9206 |
| 14 | `coded_unique_ratio` | -0.283 | lower_in_rejected | 0.3132 | 0.3432 |
| 15 | `supplier_missing` | 0.279 | higher_in_rejected | 0.3680 | 0.2409 |

### Agent Analysis Notes

- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.
- **Client signal count is predictive**: Respondents with more client signals are more likely rejected.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **Moderate reject rate (17%)**: Standard cleaning threshold.

---

## 260300_ECHO.xlsx

- **Respondents**: 1566
- **Rejected**: 553 (35.3%)
- **In-dataset AUC**: 0.974

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `coded_count` | 0.1407 |
| 2 | `ua_dup_count` | 0.0694 |
| 3 | `demo_qager1` | 0.0674 |
| 4 | `coded_unique_ratio` | 0.0633 |
| 5 | `matrix_unique_ratio` | 0.0600 |
| 6 | `matrix_most_common_freq` | 0.0522 |
| 7 | `lang_LangAssessReadLevel` | 0.0491 |
| 8 | `demo_q9` | 0.0367 |
| 9 | `signals_x_matrix` | 0.0322 |
| 10 | `qtime_seconds` | 0.0319 |
| 11 | `qtime_seconds_zscore` | 0.0315 |
| 12 | `supplier_x_signals` | 0.0296 |
| 13 | `qtime_log` | 0.0295 |
| 14 | `matrix_count` | 0.0289 |
| 15 | `lang_LangAssessNumWords` | 0.0282 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `demo_CLASSIFY` | -0.463 | lower_in_rejected | 0.7269 | 0.9023 |
| 2 | `demo_q2` | 0.463 | higher_in_rejected | 0.2731 | 0.0977 |
| 3 | `supplier_reject_rate` | 0.451 | higher_in_rejected | 0.3806 | 0.3468 |
| 4 | `supplier_x_signals` | 0.405 | higher_in_rejected | 1.9281 | 1.7637 |
| 5 | `coded_count` | 0.385 | higher_in_rejected | 277.4973 | 273.5074 |
| 6 | `demo_q13` | -0.380 | lower_in_rejected | 0.8861 | 1.1135 |
| 7 | `demo_qager1` | -0.375 | lower_in_rejected | 18.4033 | 22.8638 |
| 8 | `demo_age` | -0.374 | lower_in_rejected | 2.0072 | 2.4136 |
| 9 | `tech_vos` | 0.372 | higher_in_rejected | 3.3852 | 2.6950 |
| 10 | `ua_dup_count` | 0.371 | higher_in_rejected | 90.7396 | 62.4886 |
| 11 | `tech_vmobiledevice` | 0.352 | higher_in_rejected | 1.1863 | 0.8430 |
| 12 | `tech_vmobileos` | 0.324 | higher_in_rejected | 1.4864 | 1.2616 |
| 13 | `supplier_missing` | 0.319 | higher_in_rejected | 0.4485 | 0.2962 |
| 14 | `supplier_is_none` | 0.319 | higher_in_rejected | 0.4485 | 0.2962 |
| 15 | `matrix_count` | 0.280 | higher_in_rejected | 139.8029 | 137.0306 |

### Agent Analysis Notes

- **Coded answer diversity matters**: Check for high 'don't know' ratios or low answer diversity.
- **Cross-respondent duplicates are predictive**: Check for duplicate open-end text, IP addresses, or user agents.
- **High reject rate (35%)**: This dataset has aggressive cleaning. Many signals may be needed to match.

---

## 260306_TFG Contractor Index Q2.xlsx

- **Respondents**: 1117
- **Rejected**: 402 (36.0%)
- **In-dataset AUC**: 0.996

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `supplier_reject_rate` | 0.3273 |
| 2 | `supplier_x_signals` | 0.0957 |
| 3 | `tech_vmobileos` | 0.0528 |
| 4 | `demo_CLASSIFY` | 0.0399 |
| 5 | `lang_LangAssessReadLevel` | 0.0394 |
| 6 | `matrix_count` | 0.0367 |
| 7 | `coded_unique_ratio` | 0.0325 |
| 8 | `demo_qstate` | 0.0309 |
| 9 | `demo_q9` | 0.0283 |
| 10 | `ua_dup_count` | 0.0260 |
| 11 | `demo_qager1` | 0.0250 |
| 12 | `tech_vos` | 0.0248 |
| 13 | `qtime_seconds_zscore` | 0.0215 |
| 14 | `coded_count` | 0.0194 |
| 15 | `oe_max_chars` | 0.0151 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `supplier_reject_rate` | 1.689 | higher_in_rejected | 0.6143 | 0.2386 |
| 2 | `supplier_missing` | 1.665 | higher_in_rejected | 0.7811 | 0.1427 |
| 3 | `supplier_is_none` | 1.665 | higher_in_rejected | 0.7811 | 0.1427 |
| 4 | `supplier_x_signals` | 1.572 | higher_in_rejected | 3.3866 | 1.3899 |
| 5 | `tech_vmobiledevice` | 1.384 | higher_in_rejected | 1.4303 | 0.3091 |
| 6 | `matrix_count` | -1.325 | lower_in_rejected | 4.9055 | 6.6867 |
| 7 | `tech_vos` | 1.200 | higher_in_rejected | 3.7711 | 1.8182 |
| 8 | `tech_vmobileos` | 1.125 | higher_in_rejected | 1.6169 | 0.8993 |
| 9 | `coded_count` | -0.989 | lower_in_rejected | 60.3085 | 62.5427 |
| 10 | `demo_q9` | 0.850 | higher_in_rejected | 5.9428 | 3.7259 |
| 11 | `supplier_x_t2` | 0.811 | higher_in_rejected | 0.3174 | 0.0876 |
| 12 | `demo_CLASSIFY` | 0.786 | higher_in_rejected | 9.0249 | 6.3399 |
| 13 | `signals_x_matrix` | -0.751 | lower_in_rejected | 0.7845 | 1.4723 |
| 14 | `matrix_unique_count` | -0.734 | lower_in_rejected | 4.0746 | 4.9706 |
| 15 | `coded_unique_ratio` | 0.729 | higher_in_rejected | 0.4134 | 0.3915 |

### Agent Analysis Notes

- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.
- **Client signal count is predictive**: Respondents with more client signals are more likely rejected.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **High reject rate (36%)**: This dataset has aggressive cleaning. Many signals may be needed to match.

---

## 260401_ OC CAN.xlsx

- **Respondents**: 743
- **Rejected**: 285 (38.4%)
- **In-dataset AUC**: 1.000

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `supplier_x_signals` | 0.3305 |
| 2 | `matrix_unique_ratio` | 0.0670 |
| 3 | `supplier_x_t2` | 0.0669 |
| 4 | `oe_max_chars` | 0.0545 |
| 5 | `lang_LangAssessReadLevel` | 0.0539 |
| 6 | `qtime_seconds_zscore` | 0.0444 |
| 7 | `qtime_seconds` | 0.0413 |
| 8 | `matrix_most_common_freq` | 0.0412 |
| 9 | `qtime_log` | 0.0368 |
| 10 | `signals_x_matrix` | 0.0297 |
| 11 | `demo_qager1` | 0.0259 |
| 12 | `oe_lex_div` | 0.0209 |
| 13 | `matrix_count` | 0.0181 |
| 14 | `ua_dup_count` | 0.0175 |
| 15 | `demo_qIndustry` | 0.0156 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `supplier_x_signals` | 1.381 | higher_in_rejected | 2.3734 | 1.5136 |
| 2 | `supplier_x_t2` | 1.344 | higher_in_rejected | 0.7606 | 0.3215 |
| 3 | `lang_LangAssessNumSyl` | 1.173 | higher_in_rejected | 20.7263 | 8.9301 |
| 4 | `oe_max_chars` | 1.143 | higher_in_rejected | 74.8807 | 33.8079 |
| 5 | `oe_total_chars` | 1.109 | higher_in_rejected | 87.0246 | 43.8341 |
| 6 | `oe_mean_chars` | 1.082 | higher_in_rejected | 14.3869 | 7.7431 |
| 7 | `oe_total_words` | 1.001 | higher_in_rejected | 16.7965 | 9.7926 |
| 8 | `lang_LangAssessNumWords` | 0.990 | higher_in_rejected | 11.7018 | 5.6769 |
| 9 | `oe_max_words` | 0.964 | higher_in_rejected | 11.7123 | 5.8581 |
| 10 | `lang_LangAssessReadLevel` | 0.917 | higher_in_rejected | 10.2491 | 5.4811 |
| 11 | `sig_rd_searchr3_canada` | 0.829 | higher_in_rejected | 0.9930 | 0.7271 |
| 12 | `supplier_reject_rate` | 0.826 | higher_in_rejected | 0.4614 | 0.3484 |
| 13 | `ip_is_dup` | -0.799 | lower_in_rejected | 0.0140 | 0.2751 |
| 14 | `t2_count` | 0.797 | higher_in_rejected | 1.6105 | 1.0830 |
| 15 | `oe_count` | 0.789 | higher_in_rejected | 6.0526 | 4.6419 |

### Agent Analysis Notes

- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.
- **Open-end text quality is predictive**: Top OE features: oe_max_chars. Check for short, generic, or missing open-ends.
- **Client signal count is predictive**: Respondents with more client signals are more likely rejected.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **High reject rate (38%)**: This dataset has aggressive cleaning. Many signals may be needed to match.

---

## 260403_Masterlock Conjoint.xlsx

- **Respondents**: 916
- **Rejected**: 206 (22.5%)
- **In-dataset AUC**: 0.997

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `matrix_most_common_freq` | 0.1874 |
| 2 | `lang_LangAssessReadLevel` | 0.0871 |
| 3 | `demo_qIndustry` | 0.0568 |
| 4 | `demo_qager1` | 0.0545 |
| 5 | `supplier_reject_rate` | 0.0399 |
| 6 | `oe_total_chars` | 0.0364 |
| 7 | `qtime_seconds_zscore` | 0.0362 |
| 8 | `oe_mean_chars` | 0.0313 |
| 9 | `demo_qstate` | 0.0312 |
| 10 | `rd_RD_Searchr1` | 0.0291 |
| 11 | `ua_dup_count` | 0.0230 |
| 12 | `demo_REGION` | 0.0228 |
| 13 | `qtime_log` | 0.0221 |
| 14 | `oe_total_words` | 0.0215 |
| 15 | `oe_lex_div` | 0.0214 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `matrix_unique_count` | -0.804 | lower_in_rejected | 3.7039 | 3.9775 |
| 2 | `matrix_unique_ratio` | -0.804 | lower_in_rejected | 0.0882 | 0.0947 |
| 3 | `matrix_most_common_freq` | 0.595 | higher_in_rejected | 0.5280 | 0.4544 |
| 4 | `supplier_reject_rate` | 0.242 | higher_in_rejected | 0.2305 | 0.2246 |
| 5 | `demo_qGender` | 0.215 | higher_in_rejected | 0.4369 | 0.3310 |
| 6 | `sig_duplicate_open_end_text` | -0.187 | lower_in_rejected | 0.7816 | 0.8535 |
| 7 | `demo_REGION` | -0.158 | lower_in_rejected | 1.2282 | 1.3775 |
| 8 | `sig_rd_searchr1_22` | -0.149 | lower_in_rejected | 0.0485 | 0.0859 |
| 9 | `demo_q13` | 0.143 | higher_in_rejected | 1.8835 | 1.7056 |
| 10 | `lang_LangAssessReadEase` | 0.130 | higher_in_rejected | 17.4757 | 12.8169 |
| 11 | `oe_count` | 0.125 | higher_in_rejected | 1.1408 | 1.1000 |
| 12 | `sig_rd_searchr1_5` | 0.123 | higher_in_rejected | 0.0485 | 0.0254 |
| 13 | `oe_all_caps` | -0.119 | lower_in_rejected | 0.0000 | 0.0070 |
| 14 | `sig_rd_searchr1_7` | 0.111 | higher_in_rejected | 0.0243 | 0.0099 |
| 15 | `sig_rd_searchr1_1` | -0.106 | lower_in_rejected | 0.0000 | 0.0056 |

### Agent Analysis Notes

- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.
- **Matrix straightlining is predictive**: Rejected respondents have lower matrix diversity (Cohen's d=0.80). Check matrix_unique_ratio < 0.3.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **Moderate reject rate (22%)**: Standard cleaning threshold.

---

## 260404_ADDO.xlsx

- **Respondents**: 1356
- **Rejected**: 358 (26.4%)
- **In-dataset AUC**: 0.994

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `oe_total_chars` | 0.1846 |
| 2 | `lang_LangAssessReadLevel` | 0.0615 |
| 3 | `qtime_seconds_zscore` | 0.0458 |
| 4 | `sig_long_low_specificity_text` | 0.0380 |
| 5 | `qtime_log` | 0.0355 |
| 6 | `oe_max_chars` | 0.0350 |
| 7 | `supplier_x_signals` | 0.0347 |
| 8 | `matrix_most_common_freq` | 0.0337 |
| 9 | `lang_LangAssessNumSyl` | 0.0337 |
| 10 | `signals_x_matrix` | 0.0331 |
| 11 | `qtime_seconds` | 0.0315 |
| 12 | `oe_lex_div` | 0.0310 |
| 13 | `demo_qager1` | 0.0288 |
| 14 | `matrix_unique_ratio` | 0.0286 |
| 15 | `oe_mean_chars` | 0.0263 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `t1_count` | 0.613 | higher_in_rejected | 0.1899 | 0.0090 |
| 2 | `supplier_x_t1` | 0.600 | higher_in_rejected | 0.0513 | 0.0024 |
| 3 | `oe_short` | 0.589 | higher_in_rejected | 0.2039 | 0.0240 |
| 4 | `oe_total_chars` | -0.556 | lower_in_rejected | 117.3324 | 191.4028 |
| 5 | `sig_qtime_under_4_minutes` | 0.550 | higher_in_rejected | 0.1397 | 0.0030 |
| 6 | `oe_mean_chars` | -0.545 | lower_in_rejected | 16.5034 | 26.5718 |
| 7 | `sig_long_low_specificity_text` | 0.537 | higher_in_rejected | 0.1369 | 0.0040 |
| 8 | `oe_total_words` | -0.525 | lower_in_rejected | 24.6983 | 37.5180 |
| 9 | `qtime_log` | -0.504 | lower_in_rejected | 6.1545 | 6.4361 |
| 10 | `oe_max_words` | -0.460 | lower_in_rejected | 14.2793 | 24.3527 |
| 11 | `supplier_x_signals` | 0.459 | higher_in_rejected | 1.6077 | 1.4295 |
| 12 | `lang_LangAssessReadEase` | 0.458 | higher_in_rejected | 14.8045 | 2.3046 |
| 13 | `oe_max_chars` | -0.457 | lower_in_rejected | 75.1508 | 128.0731 |
| 14 | `lang_LangAssessNumSyl` | -0.441 | lower_in_rejected | 11.3240 | 14.6894 |
| 15 | `lang_LangAssessReadLevel` | -0.402 | lower_in_rejected | 5.9913 | 7.5935 |

### Agent Analysis Notes

- **Slow completion is a signal**: Rejected respondents take longer (Cohen's d=0.55). May indicate bot-like or stalling behavior.
- **Open-end text quality is predictive**: Top OE features: oe_total_chars. Check for short, generic, or missing open-ends.
- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.
- **Moderate reject rate (26%)**: Standard cleaning threshold.

---

## 260501_ODL.xlsx

- **Respondents**: 603
- **Rejected**: 32 (5.3%)
- **In-dataset AUC**: 1.000

### Top Features by Model Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `supplier_reject_rate` | 0.1838 |
| 2 | `demo_q12` | 0.1789 |
| 3 | `supplier_x_signals` | 0.1138 |
| 4 | `qtime_seconds_zscore` | 0.0578 |
| 5 | `qtime_seconds` | 0.0403 |
| 6 | `lang_LangAssessReadLevel` | 0.0390 |
| 7 | `signals_x_matrix` | 0.0374 |
| 8 | `coded_unique_ratio` | 0.0366 |
| 9 | `demo_qstate` | 0.0339 |
| 10 | `demo_qager1` | 0.0319 |
| 11 | `sig_matrix_near_straightline` | 0.0251 |
| 12 | `matrix_most_common_freq` | 0.0219 |
| 13 | `t3_count` | 0.0186 |
| 14 | `tech_vos` | 0.0186 |
| 15 | `qtime_log` | 0.0181 |

### Top Features by Discrimination (Cohen's d)

Effect size: how differently rejected vs accepted respondents score.
Positive d = rejected score HIGHER. Negative d = rejected score LOWER.

| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |
|------|---------|-----------|-----------|---------------|---------------|
| 1 | `supplier_reject_rate` | 1.548 | higher_in_rejected | 0.1000 | 0.0451 |
| 2 | `supplier_x_signals` | 1.295 | higher_in_rejected | 0.4514 | 0.2225 |
| 3 | `demo_q12` | 1.240 | higher_in_rejected | 3.5938 | 1.5884 |
| 4 | `sig_matrix_near_straightline` | -0.825 | lower_in_rejected | 0.1250 | 0.4764 |
| 5 | `matrix_count` | -0.780 | lower_in_rejected | 69.3438 | 72.2872 |
| 6 | `demo_CLASSIFY` | 0.777 | higher_in_rejected | 0.8750 | 0.5447 |
| 7 | `sig_duplicate_open_end_text` | -0.733 | lower_in_rejected | 0.7500 | 0.9860 |
| 8 | `demo_qIndustry` | 0.729 | higher_in_rejected | 7.7812 | 4.8581 |
| 9 | `supplier_missing` | -0.710 | lower_in_rejected | 0.0000 | 0.2014 |
| 10 | `supplier_is_none` | -0.710 | lower_in_rejected | 0.0000 | 0.2014 |
| 11 | `demo_q13` | -0.702 | lower_in_rejected | 0.4375 | 1.5289 |
| 12 | `matrix_unique_count` | -0.693 | lower_in_rejected | 6.4688 | 9.3888 |
| 13 | `matrix_unique_ratio` | -0.671 | lower_in_rejected | 0.0918 | 0.1264 |
| 14 | `demo_qNumEmployees` | -0.651 | lower_in_rejected | 0.9062 | 2.9072 |
| 15 | `signal_count` | -0.587 | lower_in_rejected | 4.5625 | 4.9912 |

### Agent Analysis Notes

- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.
- **Client signal count is predictive**: Respondents with more client signals are more likely rejected.
- **Low reject rate (5%)**: This dataset has conservative cleaning. Be very precise — false positives are costly.

---
