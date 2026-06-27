# Cross-Corpus ML Signal Correlation Analysis

**Corpus:** 13388 respondents across 11 datasets

## Evidence Family Correlations with Client Discard

| Family | Mean Correlation | N Datasets | Direction |
|--------|-----------------|------------|----------|
| platform_risk | 0.086 | 11 | positive |
| timing_engagement | 0.073 | 11 | positive |
| duplicate_semantics | 0.042 | 11 | positive |
| overall_signal_strength | -0.038 | 11 | negative |
| other | 0.032 | 11 | positive |
| core_oe_quality | -0.030 | 11 | negative |
| survey_structure | 0.023 | 11 | positive |

## Universal Signals (3+ datasets)

| Signal | Family | N Datasets | Mean Importance |
|--------|--------|------------|----------------|
| low_total_duration | timing_engagement | 10 | 0.1580 |
| text_time_mismatch | timing_engagement | 9 | 0.0161 |
| no_strong_staged_signal | overall_signal_strength | 9 | 0.0750 |
| low_total_duration; text_time_mismatch | timing_engagement | 8 | 0.0131 |
| survey_meta_substitution | survey_structure | 7 | 0.1444 |
| thin_open_end; low_total_duration | core_oe_quality | 6 | 0.0111 |
| thin_open_end | core_oe_quality | 6 | 0.0179 |
| qtime | timing_engagement | 6 | 0.3177 |
| RD_Searchr1 | platform_risk | 6 | 0.1587 |
| age | other | 6 | 0.0587 |
| CLASSIFY | survey_structure | 6 | 0.1405 |
| weak_persona_context | core_oe_quality | 5 | 0.1246 |
| REGION | other | 5 | 0.0239 |
| duplicate_open_chain | duplicate_semantics | 5 | 0.0525 |
| survey_meta_substitution; low_total_duration | survey_structure | 4 | 0.0155 |
| thin_open_end; duplicate_open_chain | core_oe_quality | 4 | 0.0099 |
| low_total_duration; weak_persona_context | timing_engagement | 4 | 0.1144 |
| text_time_mismatch; weak_persona_context | timing_engagement | 3 | 0.0087 |
| low_total_duration; text_time_mismatch; weak_persona_context | timing_engagement | 3 | 0.0372 |
| high_matrix_uniformity; low_total_duration | timing_engagement | 3 | 0.0231 |

## Per-Dataset Top Signals

### addo-racetrac-us-gp (AUC=0.599, 358 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| low_total_duration | 0.7792 | timing_engagement |
| survey_meta_substitution | 0.1365 | survey_structure |
| survey_meta_substitution; low_total_duration | 0.0416 | survey_structure |
| text_time_mismatch | 0.0153 | timing_engagement |
| low_total_duration; text_time_mismatch | 0.0081 | timing_engagement |
| survey_meta_substitution; text_time_mismatch | 0.0079 | survey_structure |
| survey_meta_substitution; low_total_duration; text_time_mismatch | 0.0067 | survey_structure |
| no_strong_staged_signal | 0.0047 | overall_signal_strength |

### delta-water-filtration (AUC=0.573, 348 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| survey_meta_substitution | 0.7327 | survey_structure |
| thin_open_end; low_total_duration | 0.0536 | core_oe_quality |
| survey_meta_substitution; low_total_duration; text_time_mismatch | 0.0536 | survey_structure |
| low_total_duration | 0.0401 | timing_engagement |
| thin_open_end; duplicate_open_chain | 0.0319 | core_oe_quality |
| thin_open_end | 0.0279 | core_oe_quality |
| low_total_duration; text_time_mismatch | 0.0181 | timing_engagement |
| survey_meta_substitution; thin_open_end | 0.0172 | survey_structure |
| survey_meta_substitution; text_time_mismatch | 0.0074 | survey_structure |
| survey_meta_substitution; polished_ungrounded_open_end | 0.0051 | survey_structure |

### echo-bh (AUC=0.556, 553 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| duplicate_open_chain; weak_persona_context | 0.7174 | duplicate_semantics |
| survey_meta_substitution; low_total_duration; text_time_mismatch; weak_persona_context | 0.1089 | survey_structure |
| weak_persona_context | 0.1035 | core_oe_quality |
| low_total_duration; weak_persona_context | 0.0684 | timing_engagement |
| text_time_mismatch; weak_persona_context | 0.0009 | timing_engagement |
| low_total_duration; text_time_mismatch; weak_persona_context | 0.0009 | timing_engagement |

### masterlock-conjoint (AUC=0.528, 206 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| qtime | 0.5330 | timing_engagement |
| RD_Searchr1 | 0.1324 | platform_risk |
| REGION | 0.0861 | other |
| age | 0.0562 | other |
| low_total_duration | 0.0357 | timing_engagement |
| low_total_duration; weak_persona_context | 0.0292 | timing_engagement |
| thin_open_end; low_total_duration; weak_persona_context | 0.0212 | core_oe_quality |
| survey_meta_substitution; weak_persona_context | 0.0192 | survey_structure |
| weak_persona_context | 0.0186 | core_oe_quality |
| CLASSIFY | 0.0157 | survey_structure |

### odl-switchable-glass (AUC=0.616, 32 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| no_strong_staged_signal | 0.4120 | overall_signal_strength |
| weak_persona_context | 0.3195 | core_oe_quality |
| low_total_duration; text_time_mismatch; weak_persona_context | 0.1073 | timing_engagement |
| low_total_duration; weak_persona_context | 0.0542 | timing_engagement |
| survey_meta_substitution | 0.0380 | survey_structure |
| text_time_mismatch | 0.0266 | timing_engagement |
| low_total_duration; text_time_mismatch | 0.0251 | timing_engagement |
| text_time_mismatch; weak_persona_context | 0.0118 | timing_engagement |
| low_total_duration | 0.0056 | timing_engagement |

### oldcastle-brand-health (AUC=0.528, 375 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| low_total_duration; weak_persona_context | 0.3058 | timing_engagement |
| low_total_duration | 0.2081 | timing_engagement |
| weak_persona_context | 0.1730 | core_oe_quality |
| high_matrix_uniformity; low_total_duration; weak_persona_context | 0.0744 | timing_engagement |
| no_strong_staged_signal | 0.0491 | overall_signal_strength |
| high_matrix_uniformity; weak_persona_context | 0.0469 | timing_engagement |
| survey_meta_substitution | 0.0446 | survey_structure |
| high_matrix_uniformity; low_total_duration | 0.0401 | timing_engagement |
| text_time_mismatch | 0.0309 | timing_engagement |
| high_matrix_uniformity | 0.0123 | timing_engagement |

### oldcastle-canada (AUC=0.579, 285 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| RD_Searchr1 | 0.4083 | platform_risk |
| qtime | 0.2797 | timing_engagement |
| CLASSIFY | 0.1084 | survey_structure |
| age | 0.0861 | other |
| thin_open_end | 0.0323 | core_oe_quality |
| survey_meta_substitution | 0.0273 | survey_structure |
| survey_meta_substitution; low_total_duration | 0.0149 | survey_structure |
| low_total_duration; text_time_mismatch | 0.0145 | timing_engagement |
| no_strong_staged_signal | 0.0105 | overall_signal_strength |
| weak_persona_context | 0.0082 | core_oe_quality |

### sbd-brand-association (AUC=0.558, 350 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| low_total_duration | 0.4945 | timing_engagement |
| no_strong_staged_signal | 0.1451 | overall_signal_strength |
| high_matrix_uniformity | 0.1213 | timing_engagement |
| text_time_mismatch | 0.0618 | timing_engagement |
| duplicate_open_chain | 0.0514 | duplicate_semantics |
| low_total_duration; text_time_mismatch | 0.0333 | timing_engagement |
| high_matrix_uniformity; low_total_duration | 0.0290 | timing_engagement |
| survey_meta_substitution | 0.0277 | survey_structure |
| q16 | 0.0113 | other |
| duplicate_open_chain; low_total_duration | 0.0112 | duplicate_semantics |

### tfg-contractor-index-q1 (AUC=0.648, 97 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| CLASSIFY | 0.2812 | survey_structure |
| qtime | 0.2166 | timing_engagement |
| age | 0.1683 | other |
| RD_Searchr1 | 0.1280 | platform_risk |
| duplicate_open_chain | 0.1043 | duplicate_semantics |
| duplicate_open_chain; low_total_duration | 0.0731 | duplicate_semantics |
| thin_open_end | 0.0124 | core_oe_quality |
| REGION | 0.0097 | other |
| low_total_duration | 0.0043 | timing_engagement |
| thin_open_end; duplicate_open_chain | 0.0014 | core_oe_quality |

### tfg-contractor-index-q2 (AUC=0.822, 402 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| qtime | 0.4898 | timing_engagement |
| CLASSIFY | 0.4075 | survey_structure |
| RD_Searchr1 | 0.0447 | platform_risk |
| age | 0.0348 | other |
| REGION | 0.0075 | other |
| low_total_duration | 0.0053 | timing_engagement |
| thin_open_end; duplicate_open_chain | 0.0038 | core_oe_quality |
| thin_open_end | 0.0031 | core_oe_quality |
| text_time_mismatch | 0.0011 | timing_engagement |
| thin_open_end; low_total_duration | 0.0011 | core_oe_quality |

### thd-digital-cx (AUC=0.681, 118 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| qtime | 0.3822 | timing_engagement |
| RD_Searchr1 | 0.2381 | platform_risk |
| q1 | 0.1051 | other |
| duplicate_open_chain | 0.0982 | duplicate_semantics |
| no_strong_staged_signal | 0.0458 | overall_signal_strength |
| duplicate_open_chain; low_total_duration; text_time_mismatch | 0.0410 | duplicate_semantics |
| CLASSIFY | 0.0279 | survey_structure |
| thin_open_end | 0.0242 | core_oe_quality |
| REGION | 0.0161 | other |
| low_total_duration | 0.0065 | timing_engagement |

## Global Model

- AUC: 0.499
- Total: 13388 respondents (3124 discards)

| Signal | Importance | Family |
|--------|------------|--------|
| CLASSIFY | 0.3553 | survey_structure |
| qtime | 0.1486 | timing_engagement |
| RD_Searchr1 | 0.1368 | platform_risk |
| thin_open_end | 0.0812 | core_oe_quality |
| no_strong_staged_signal | 0.0548 | overall_signal_strength |
| q1 | 0.0504 | other |
| REGION | 0.0398 | other |
| age | 0.0214 | other |
| low_total_duration | 0.0171 | timing_engagement |
| duplicate_open_chain | 0.0157 | duplicate_semantics |
| thin_open_end; low_total_duration | 0.0127 | core_oe_quality |
| duplicate_open_chain; low_total_duration; weak_persona_context | 0.0108 | duplicate_semantics |
| duplicate_open_chain; low_total_duration | 0.0058 | duplicate_semantics |
| thin_open_end; duplicate_open_chain | 0.0053 | core_oe_quality |
| weak_persona_context | 0.0053 | core_oe_quality |
