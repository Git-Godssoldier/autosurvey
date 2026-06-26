# Echo residual signal mining for Autosurvey skill improvement

Rows: 1566. Discard base rate: 0.353. Inputs mined after benchmark evaluation; use findings for methodology evolution, not as untouched validation.

## Strongest raw field families

- **brand_funnel**: total score 2345.5; top fields: q19_2026othr1, q17r3, q19_2026r13, q16r1, q16r2, q18r13, q19_2026r5, q19_2026r17
- **equipment_ownership_use**: total score 896.3; top fields: q11othr2, q11othr1, q11ar11c4, q11othr6, q11ar3c4, q11othr3, q11ar4c4, q13b
- **other**: total score 572.9; top fields: q15r1, q19r13, qager1, q19r17, q1r10, FIRMREV, q2, q5
- **ad_recall**: total score 361.4; top fields: q25_2026r4, q25_2026r3, q25_2026r5, q25_2026r8, q25_2026r6, q25_2026r7, q25_2026r11, q25_2026r12
- **demographic_profile**: total score 353.8; top fields: q3r1, q3r2, q39_2026, q41, q4, q43, q9, q3r3
- **channel_supplier**: total score 171.3; top fields: q21d_2026r17, q21r13, q21c_2026, q21d_2026r1, q14r13, q21r17, q21d_2026r4, q14r10
- **fielding_technical**: total score 118.1; top fields: bhf, SUPNAME, conditionsAriens, dcua, sfh, vlist, list, conditionsOther_channel
- **switching_loyalty**: total score 105.8; top fields: q31_2026r4, q30_2026, q31_2026r10, q30_2026r6oe, q31_2026r5, q31_2026r12, q31_2026r6, q32_2026r3
- **quota_classification**: total score 64.7; top fields: CONAGE, PROAGE, CLASSIFY, REGION

## Top raw fields by status lift

- **q11othr2** (equipment_ownership_use, score 77.5): q11othr2='2' n=19 discard=1.00; q11othr2='4' n=16 discard=1.00; q11othr2='__MISSING__' n=1249 discard=0.32
- **q19_2026othr1** (brand_funnel, score 65.3): q19_2026othr1='Ryobi' n=13 discard=0.62; q19_2026othr1='John Deere' n=20 discard=0.20; q19_2026othr1='Craftsman' n=11 discard=0.27
- **q17r3** (brand_funnel, score 61.0): q17r3='__MISSING__' n=970 discard=0.41; q17r3='John Deere' n=27 discard=0.04; q17r3='Milwaukee' n=23 discard=0.04
- **q11othr1** (equipment_ownership_use, score 57.2): q11othr1='2' n=13 discard=1.00; q11othr1='1' n=9 discard=1.00; q11othr1='None' n=12 discard=0.25
- **q19_2026r13** (brand_funnel, score 55.5): q19_2026r13='__MISSING__' n=1031 discard=0.23; q19_2026r13='0' n=244 discard=0.56; q19_2026r13='10' n=69 discard=0.68
- **q16r1** (brand_funnel, score 48.3): q16r1='55' n=40 discard=0.68; q16r1='45' n=43 discard=0.63; q16r1='0' n=178 discard=0.22
- **q16r2** (brand_funnel, score 48.3): q16r2='45' n=40 discard=0.68; q16r2='55' n=43 discard=0.63; q16r2='100' n=178 discard=0.22
- **q18r13** (brand_funnel, score 48.2): q18r13='1' n=738 discard=0.22; q18r13='6' n=110 discard=0.68; q18r13='5' n=198 discard=0.58
- **q19_2026r5** (brand_funnel, score 46.9): q19_2026r5='0' n=248 discard=0.59; q19_2026r5='__MISSING__' n=906 discard=0.24; q19_2026r5='4' n=9 discard=1.00
- **q19_2026r17** (brand_funnel, score 43.7): q19_2026r17='__MISSING__' n=1023 discard=0.24; q19_2026r17='0' n=254 discard=0.54; q19_2026r17='10' n=80 discard=0.62
- **q11ar11c4** (equipment_ownership_use, score 42.7): q11ar11c4='0' n=614 discard=0.56; q11ar11c4='1' n=952 discard=0.22
- **q15r1** (other, score 42.5): q15r1='45' n=27 discard=0.81; q15r1='55' n=36 discard=0.69; q15r1='25' n=120 discard=0.21
- **q18r14** (brand_funnel, score 40.7): q18r14='5' n=175 discard=0.62; q18r14='1' n=810 discard=0.23; q18r14='6' n=87 discard=0.70
- **q19_2026r4** (brand_funnel, score 40.4): q19_2026r4='__MISSING__' n=902 discard=0.25; q19_2026r4='5' n=87 discard=0.57; q19_2026r4='0' n=230 discard=0.47
- **q18r17** (brand_funnel, score 39.6): q18r17='6' n=103 discard=0.67; q18r17='5' n=182 discard=0.57; q18r17='1' n=675 discard=0.24
- **q19_2026r14** (brand_funnel, score 38.9): q19_2026r14='0' n=236 discard=0.58; q19_2026r14='__MISSING__' n=1072 discard=0.25; q19_2026r14='10' n=77 discard=0.58
- **q11othr6** (equipment_ownership_use, score 37.9): q11othr6='1' n=10 discard=1.00; q11othr6='Any' n=9 discard=0.44; q11othr6='__MISSING__' n=1368 discard=0.35
- **q11ar3c4** (equipment_ownership_use, score 35.5): q11ar3c4='0' n=729 discard=0.51; q11ar3c4='1' n=837 discard=0.21
- **q11othr3** (equipment_ownership_use, score 34.1): q11othr3='2' n=8 discard=1.00; q11othr3='__MISSING__' n=1417 discard=0.34
- **q11ar4c4** (equipment_ownership_use, score 34.0): q11ar4c4='0' n=772 discard=0.50; q11ar4c4='1' n=794 discard=0.21

## Derived candidate signals

- **conditions_ariens**: hits 289, discard rate 0.592, lift +0.239. Ariens condition flag
- **pro_branch**: hits 250, discard rate 0.604, lift +0.251. CLASSIFY=1 professional branch
- **brand_share_fragmented**: hits 348, discard rate 0.520, lift +0.167. Nonzero share assigned to 8+ brands
- **fast_under_5min**: hits 15, discard rate 1.000, lift +0.647. Total qtime under 5 minutes
- **brand_share_many_zero_allocations**: hits 426, discard rate 0.472, lift +0.119. Many zero values in brand share allocation among answered brands
- **consumer_branch**: hits 1316, discard rate 0.305, lift -0.048. CLASSIFY=2 consumer branch
- **low_topic_open_text**: hits 543, discard rate 0.425, lift +0.072. Open text exists but no OPE/store/brand topical term
- **few_open_texts**: hits 405, discard rate 0.284, lift -0.069. 0-1 open text fields present
- **termflags_nonzero**: hits 15, discard rate 0.667, lift +0.314. TERMFLAGS nonzero
- **many_high_brand_ratings**: hits 1362, discard rate 0.362, lift +0.009. 12+ high 8-10 brand ratings
- **open_placeholders**: hits 100, discard rate 0.330, lift -0.023. At least one placeholder open end
- **list25**: hits 0, discard rate 0.000, lift +0.000. sample/list 25
- **brand_share_sum_not_100**: hits 0, discard rate 0.000, lift +0.000. Brand share allocation does not sum near 100
- **pro_missing_proage**: hits 0, discard rate 0.000, lift +0.000. Professional classification but PROAGE missing
- **consumer_has_proage_missing_conage**: hits 0, discard rate 0.000, lift +0.000. Consumer classification but CONAGE missing

## Recommended skill/process changes

1. Add a label-aware evolution phase that builds a quota/classification contract from `CLASSIFY`, `CONAGE`, `PROAGE`, `REGION`, condition flags, list/source, and brand-to-rate fields before future blind runs. The current semantic review underweights these survey-design fields.
2. Add brand-funnel relation graphs: awareness/top/possible/rated/brand-share/ad/NPS fields must be checked as a connected system, including impossible or suspicious allocation patterns, fragmented shares, excessive high ratings, and brand quota eligibility.
3. Split “authenticity risk” from “client discard reconstruction.” Rows can be human-looking but client-discardable because of quota, classification, or bad-open standards.
4. Tighten bad-open field contracts by field family. `qc5`, q11 other-specifies, q17 brands, q19 other, q29 ad recall, q30-q32 switching/loyalty, and channel other-specifies need separate valid/invalid examples and accepted-row guardrails.
5. Add residual review packets for every FN/FP after evaluation: each packet should include raw branch/condition/brand-funnel values, marker family, our rationale, and candidate missed signal; promote only rules that survive accepted-row counterexamples.
