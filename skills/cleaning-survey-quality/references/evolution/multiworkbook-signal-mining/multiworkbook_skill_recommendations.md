# Multi-workbook Autosurvey signal mining and skill weakpoints

## Dataset inventory

- **251101_THD-CX**: rows 1905, labeled 1905, discard rate 0.062, status counts {'3': 1787, '5': 118}
- **251205_TFG-Contractor-Index-Q1**: rows 878, labeled 878, discard rate 0.110, status counts {'3': 781, '5': 97}
- **260111_Delta-Water-Filtration**: rows 1353, labeled 1353, discard rate 0.257, status counts {'3': 1005, '5': 348}
- **260200_SBD**: rows 787, labeled 787, discard rate 0.445, status counts {'3': 437, '5': 350}
- **260206_OC-BH**: rows 2164, labeled 2164, discard rate 0.173, status counts {'5': 375, '3': 1789}
- **260300_ECHO**: rows 1566, labeled 1566, discard rate 0.353, status counts {'3': 1013, '5': 553}
- **260306_TFG-Contractor-Index-Q2**: rows 1117, labeled 1117, discard rate 0.360, status counts {'3': 715, '5': 402}
- **260401_-OC-CAN**: rows 743, labeled 743, discard rate 0.384, status counts {'3': 458, '5': 285}
- **260403_Masterlock-Conjoint**: rows 916, labeled 916, discard rate 0.225, status counts {'3': 710, '5': 206}
- **260404_ADDO**: rows 1356, labeled 1356, discard rate 0.264, status counts {'5': 358, '3': 998}

## Cross-dataset strongest families

- **demographic_profile**: total signal score 5703.8; strongest fields: 260306_TFG-Contractor-Index-Q2/q4, 260306_TFG-Contractor-Index-Q2/q6r1, 260306_TFG-Contractor-Index-Q2/q6r3, 260306_TFG-Contractor-Index-Q2/q6r2, 260306_TFG-Contractor-Index-Q2/q45f, 260306_TFG-Contractor-Index-Q2/q40, 260306_TFG-Contractor-Index-Q2/q45h, 260306_TFG-Contractor-Index-Q2/q43
- **brand_funnel_ad**: total signal score 4058.5; strongest fields: 260300_ECHO/q17r2, 260300_ECHO/q29, 260300_ECHO/q19_2026othr1, 260300_ECHO/q17r3, 260300_ECHO/q19_2026r13, 260300_ECHO/q16r1, 260300_ECHO/q16r2, 260300_ECHO/q18r13
- **other**: total signal score 2729.2; strongest fields: 260306_TFG-Contractor-Index-Q2/qc6LangAssessReadLevel, 260306_TFG-Contractor-Index-Q2/vos, 260306_TFG-Contractor-Index-Q2/vmobiledevice, 260306_TFG-Contractor-Index-Q2/vmobileos, 260401_-OC-CAN/qcoe1R1_RD_Reviewr3, 260404_ADDO/qcoe1LangAssessNumSyl, 251205_TFG-Contractor-Index-Q1/qc6LangAssessReadLevel, 260200_SBD/qcoe2r1
- **ownership_use_product**: total signal score 2722.6; strongest fields: 260300_ECHO/q11othr4, 260300_ECHO/q11othr2, 260300_ECHO/q11othr1, 260306_TFG-Contractor-Index-Q2/q13r1, 260300_ECHO/q11ar11c4, 260200_SBD/q13r1, 260206_OC-BH/q121r1, 260200_SBD/q13r2
- **fielding_technical**: total signal score 1446.7; strongest fields: 260306_TFG-Contractor-Index-Q2/vlist, 260306_TFG-Contractor-Index-Q2/list, 260306_TFG-Contractor-Index-Q2/SUPNAME, 260306_TFG-Contractor-Index-Q2/bhf, 260306_TFG-Contractor-Index-Q2/sfh, 260306_TFG-Contractor-Index-Q2/dcua, 260401_-OC-CAN/vlist, 260401_-OC-CAN/list
- **channel_supplier**: total signal score 675.8; strongest fields: 260206_OC-BH/q141r1, 260111_Delta-Water-Filtration/q22r21, 260300_ECHO/q21d_2026r17, 260111_Delta-Water-Filtration/q22r12, 260111_Delta-Water-Filtration/q22r14, 260111_Delta-Water-Filtration/q22r10, 260111_Delta-Water-Filtration/q22r3, 260111_Delta-Water-Filtration/q22r8
- **switching_loyalty**: total signal score 599.1; strongest fields: 260111_Delta-Water-Filtration/q32, 260401_-OC-CAN/q31r2, 260300_ECHO/q31_2026r4, 260401_-OC-CAN/q31r7, 260300_ECHO/q30_2026, 260401_-OC-CAN/q31r9, 260401_-OC-CAN/q31r10, 260300_ECHO/q31_2026r10
- **matrix_attributes**: total signal score 592.3; strongest fields: 260306_TFG-Contractor-Index-Q2/q37, 260206_OC-BH/q36r1, 260306_TFG-Contractor-Index-Q2/q34, 260206_OC-BH/q36r2, 260206_OC-BH/q36r3, 260111_Delta-Water-Filtration/q33, 251205_TFG-Contractor-Index-Q1/q37, 260206_OC-BH/q36r4
- **quota_classification**: total signal score 470.9; strongest fields: 260306_TFG-Contractor-Index-Q2/CLASSIFY, 260306_TFG-Contractor-Index-Q2/CLASSIFYGROUP, 260306_TFG-Contractor-Index-Q2/possibleCLASSIFYr5, 260300_ECHO/CONAGE, 260300_ECHO/PROAGE, 260306_TFG-Contractor-Index-Q2/possibleCLASSIFYr13, 260300_ECHO/CLASSIFY, 251205_TFG-Contractor-Index-Q1/CLASSIFY
- **open_end_text**: total signal score 16.1; strongest fields: 260403_Masterlock-Conjoint/qIndustryr26oe, 260200_SBD/q15r13oe, 260200_SBD/q1r13oe, 251101_THD-CX/q1r26oe, 260111_Delta-Water-Filtration/q26r15oe, 251101_THD-CX/qRoler10oe

## Marker/label observations

- **qualified**: mentions 12785, discard share 0.242, datasets {'260206_OC-BH': 2164, '251101_THD-CX': 1905, '260300_ECHO': 1566, '260404_ADDO': 1356, '260111_Delta-Water-Filtration': 1353}
- **badopen**: mentions 3092, discard share 1.000, datasets {'260300_ECHO': 553, '260306_TFG-Contractor-Index-Q2': 402, '260206_OC-BH': 375, '260404_ADDO': 358, '260200_SBD': 350}
- **bad:qualified**: mentions 3068, discard share 1.000, datasets {'260300_ECHO': 553, '260306_TFG-Contractor-Index-Q2': 392, '260206_OC-BH': 375, '260404_ADDO': 358, '260111_Delta-Water-Filtration': 347}
- **RegionQuota**: mentions 3471, discard share 0.699, datasets {'260206_OC-BH': 790, '251101_THD-CX': 627, '260300_ECHO': 553, '260306_TFG-Contractor-Index-Q2': 407, '260111_Delta-Water-Filtration': 347}
- **TotalQuota**: mentions 2406, discard share 0.916, datasets {'260300_ECHO': 553, '260401_-OC-CAN': 436, '260200_SBD': 388, '260404_ADDO': 358, '260111_Delta-Water-Filtration': 347}
- **CLASSIFYQuota**: mentions 2273, discard share 0.699, datasets {'251101_THD-CX': 592, '260300_ECHO': 582, '260206_OC-BH': 556, '260200_SBD': 337, '260403_Masterlock-Conjoint': 206}
- **AgeQuota**: mentions 2342, discard share 0.656, datasets {'260206_OC-BH': 863, '260404_ADDO': 484, '260200_SBD': 459, '260111_Delta-Water-Filtration': 415, '251101_THD-CX': 121}
- **ProductBalancingQuota**: mentions 1571, discard share 0.877, datasets {'260403_Masterlock-Conjoint': 1138, '260111_Delta-Water-Filtration': 433}
- **GenderQuota**: mentions 1943, discard share 0.648, datasets {'260300_ECHO': 928, '260111_Delta-Water-Filtration': 657, '260404_ADDO': 358}
- **q13q31BalancingQuota**: mentions 1580, discard share 0.680, datasets {'260404_ADDO': 1580}
- **BRANDS2RATEQuota**: mentions 1326, discard share 0.784, datasets {'260300_ECHO': 1326}
- **ChannelQuota**: mentions 582, discard share 0.950, datasets {'260300_ECHO': 582}
- **TradeQuota**: mentions 553, discard share 0.893, datasets {'260306_TFG-Contractor-Index-Q2': 404, '251205_TFG-Contractor-Index-Q1': 149}
- **TradeGroupQuota**: mentions 1214, discard share 0.403, datasets {'251205_TFG-Contractor-Index-Q1': 675, '260306_TFG-Contractor-Index-Q2': 539}
- **CONAgeQuota**: mentions 696, discard share 0.578, datasets {'260300_ECHO': 696}

## Top reusable skill weakpoints

1. **Survey-design variables are not admin noise.** Across workbooks, high-signal fields often live in quota/classification, fielding, brand/product funnel, condition, list/source, and branch variables. The skill should require a survey-design contract before semantic row review.
2. **Brand/product funnel reconstruction is central.** The most label-correlated family across Echo and other workbooks is not free text alone; it is the connected pattern of awareness/top/possible/rating/share/ad/consideration/product variables.
3. **Open-end review needs field-specific standards.** Generic placeholder/meta/junk checks are insufficient; each open field needs prompt-fit examples and accepted guardrails, because short noun answers are valid in some fields and invalid in others.
4. **Client discard is broader than authenticity.** The skill should produce separate `authenticity_risk`, `quality_discard_risk`, and `client_reject_probability` so quota or fielding removals do not get mislabeled as fraud.
5. **Residual learning must be mandatory.** After every annotated comparison, all FNs/FPs should be packetized with label marker family, raw branch fields, our rationale, and proposed missed signal; promote only signals that survive accepted-row counterexamples.
6. **Matrix and allocation tasks need typed validators.** Share allocations, conjoint/rating grids, rank/NPS batteries, and repeated brand matrices should be checked for sum constraints, overbreadth, excessive high ratings, impossible missingness, and branch-incoherent answers.

## Recommended next skill additions

- Add `question_set_authenticity_map` sections for quota/branch contract, brand/product relation graph, open-end field contracts, and fielding/source context.
- Add `client_discard_reconstruction_map.md`: label-aware, not used during untouched validation, that describes how each client marker family maps to raw workbook evidence.
- Add `accepted_guardrail_ledger.csv`: for every proposed rule, include accepted rows that look similar and why they must be kept.
- Add model features for family-level row summaries: quota branch, condition flags, list/source, supplier, timing percentile, open-end prompt-fit, brand-funnel coherence, allocation anomalies, matrix entropy/straightlining, duplicate text, and contradiction families.
