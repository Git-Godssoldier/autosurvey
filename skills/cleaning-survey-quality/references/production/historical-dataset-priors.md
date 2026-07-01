# Historical dataset priors for no-ML calibration

Use this reference when a run cannot use model scores and needs historical memory from prior assessed workbooks.

These priors are label-aware evolution evidence. They are not row labels for a new workbook. They are not targets to force. Use them to ask better questions, to spot outlier outputs, and to choose which workbook-derived signals need closer row review.

## How to use these priors

1. Match the current workbook to the closest historical dataset by client, survey topic, field roles, supplier fields, brand funnel, quota structure, and open-end prompts.
2. Record the closest historical base rate in `workledger.md`.
3. Use the risky examples as questions to check in the current workbook, not as automatic discard rules.
4. Use the keep-leaning counterexamples as false-positive guardrails.
5. Before auto-KEEP, use unresolved closest-prior families as holdouts. A holdout keeps the row in REVIEW with a named question. It does not create DISCARD.
6. After blind scoring, compare the output distribution to the closest historical base rate. A large gap is an audit trigger. It is not a reason to force the output to match the historical rate.
7. Promote a signal only when it survives accepted-row counterexamples from the same or a similar survey family.

Do not use client `status`, raw client `markers`, `bad:` marker tokens, or label-derived same-dataset fields during blind scoring.

## Base rates across assessed workbooks

The 10 assessed workbooks contain 12,785 labeled respondents. The weighted average discard rate is 24.2 percent. The unweighted average discard rate is 26.3 percent. The range is 6.2 percent to 44.5 percent.

| Dataset | Rows | Kept | Discarded | Discard rate | Calibration note |
|---|---:|---:|---:|---:|---|
| 251101_THD-CX | 1,905 | 1,787 | 118 | 6.2% | Low-discard dataset. Accuracy can be reward-hacked by keeping nearly everyone. |
| 251205_TFG-Contractor-Index-Q1 | 878 | 781 | 97 | 11.0% | Supplier and fielding signals matter. Conservative discard is needed. |
| 260111_Delta-Water-Filtration | 1,353 | 1,005 | 348 | 25.7% | Fielding, channel, and timing signals matter. Timing is not always intuitive. |
| 260200_SBD | 787 | 437 | 350 | 44.5% | High-discard dataset. Ownership and product-use signals matter. |
| 260206_OC-BH | 2,164 | 1,789 | 375 | 17.3% | Fielding source and matrix patterns matter. |
| 260300_ECHO | 1,566 | 1,013 | 553 | 35.3% | Brand funnel, equipment ownership, classification, and timing matter. |
| 260306_TFG-Contractor-Index-Q2 | 1,117 | 715 | 402 | 36.0% | Supplier, fielding source, device, classification, and readability matter. |
| 260401_-OC-CAN | 743 | 458 | 285 | 38.4% | Fielding source and review metadata have strong lift. |
| 260403_Masterlock-Conjoint | 916 | 710 | 206 | 22.5% | Matrix and demographic patterns matter more than open-end text alone. |
| 260404_ADDO | 1,356 | 998 | 358 | 26.4% | Readability and very short open-end evidence matter. |

## Cross-dataset signal priors

These signal families showed recurring lift across assessed workbooks:

- Fielding and supplier source. Strong in TFG Q1, TFG Q2, OC-CAN, OC-BH, Delta, and SBD.
- Brand, product, ownership, or funnel reconstruction. Strong in ECHO, SBD, OC-BH, and Delta.
- Quota and classification structure. Strong in ECHO, TFG Q2, SBD, OC-CAN, and THD-CX.
- Readability and language metadata. Strong in THD-CX, TFG Q1, TFG Q2, and ADDO.
- Timing extremes. Useful in some datasets, but counterexamples exist. Fast completion is not a universal discard rule.
- Open-end text quality. It is weak as a global signal. It becomes useful only when the field contract is clear.

## V3 residual lesson from Echo

This is label-aware evolution evidence from the Echo no-ML V3 run. Use it after reading the current workbook. Do not use it as a same-dataset label shortcut.

V3 moved many weak REVIEW rows to KEEP and improved the human-review queue. The remaining weakness was auto-KEEP false negatives. Among V3 KEEP rows, 172 were client discards and 649 were client keeps.

The strongest differences between auto-KEEP false negatives and true keeps were family-level signals:

| Signal family | Auto-KEEP false negatives | True keeps | Difference |
|---|---:|---:|---:|
| `family_brand_funnel` | 56 of 172, 32.6% | 100 of 649, 15.4% | +17.1 points |
| `family_source_risk` | 43 of 172, 25.0% | 100 of 649, 15.4% | +9.6 points |
| `family_survey_structure` | 34 of 172, 19.8% | 70 of 649, 10.8% | +9.0 points |

A simulated V4 holdout rule showed the direction:

| Holdout rule for V3 KEEP rows | Rows moved back to REVIEW | Discarded rows recovered | Kept rows moved to review | Soft F1 |
|---|---:|---:|---:|---:|
| `family_brand_funnel` present | 156 | 56 | 100 | 60.1% |
| any of brand, source, or structure family present | 274 | 81 | 193 | 58.8% |
| at least two of brand, source, or structure present | 104 | 38 | 66 | 59.8% |

This does not justify more auto-DISCARD. It justifies a prior-family holdout before auto-KEEP. If a closest-prior family is present and unresolved, keep the row in REVIEW with `review_reason_code: prior_family_holdout`.

## V5 residual holdout lesson from Echo

This is label-aware evolution evidence from the Echo no-ML V5 run. Use it to guide the shape of future loops, not as a same-dataset shortcut during blind scoring.

V4's broad brand-family holdout moved 100 KEEP rows back to REVIEW and recovered 43 client discards. V5 then mined the remaining V4 KEEP false negatives against true keeps across raw field/value pairs and selected only holdouts with enough support and accepted-row counterexamples.

V5 moved 74 additional KEEP rows to REVIEW, recovering 46 client discards and moving 28 client keeps. Soft F1 improved from 60.7 percent to 63.9 percent. Soft recall improved from 76.7 percent to 85.0 percent. Strict precision and strict recall were unchanged because V5 added REVIEW holdouts, not DISCARD rules.

The best surviving holdouts were specific, not broad:

- misspelled brand or brand-funnel anomalies, such as `q17r1 = John deer`;
- low-awareness brand recommendation patterns, such as the RedMax recommendation field;
- extreme or inconsistent brand rating positions;
- classification and ownership anomalies;
- readability extremes.

The lesson is procedural: after a broad prior-family holdout works, mine the residual KEEP false negatives for specific field/value or cross-field holdouts and require accepted-row counterexamples. Once soft false negatives are reduced and the remaining gap is strict recall, stop widening REVIEW and switch to REVIEW true-positive versus REVIEW false-positive mining for hard discard candidates.

## V10 signal-split lesson from Echo

This is label-aware evolution evidence from the Echo no-ML V10 run. Use it to guide future signal-split loops. Do not use it as a same-dataset shortcut during blind scoring.

V10 started from V9 and promoted semantically reconstructed REVIEW rows to DISCARD. Strict F1 improved from 49.3 percent to 57.2 percent. From V2 to V10, strict F1 improved from 11.8 percent to 57.2 percent. Soft F1 stayed at 63.9 percent because V10 moved rows from REVIEW to DISCARD, not from KEEP.

Accepted signal-split families:

- Brand rating straightlining across multiple attributes of the same brand. Echo examples include RedMax, ECHO, and Brand 4.
- Cross-question matrix row matching. Echo example: the same value on row 17 across q21 and q19.
- Adjacent-row straightlining in ad recall. Echo example: the same value on adjacent q28 rows.

Rejected signal-split families:

- q5 or q16 percentage allocations without survey meaning.
- q19_2026 coded values without survey meaning.
- qager1 age correlations.
- Any field pair whose only support is same-dataset lift.

The next useful step after V10 is cross-dataset validation. If another assessed workbook has brand ratings, matrix rows, or ad recall fields, translate the V10 families into that workbook's field names and test them as evaluation-only probes. If no validation dataset is ready, mine the remaining KEEP-lane false negatives only as REVIEW holdouts.

2026-07-01 cross-dataset transfer check: a direct SBD brand-rating structural probe fired on 647 of 787 respondents, with 1,040 row-brand-battery hits. That is too broad for standalone routing. It can be stored as a context-only signal column, but it should not move rows to REVIEW or DISCARD until a sharper child criterion is validated against true labels and accepted-row counterexamples.

## Dataset signal examples

Each row below lists examples from prior assessed data. "Risky example" means that value had a higher discard rate than the dataset base rate. "Keep-leaning counterexample" means that a similar signal area had a lower discard rate than the dataset base rate.

| Dataset | Base rate | Candidate signal | Risky example | Keep-leaning counterexample |
|---|---:|---|---|---|
| 251101_THD-CX | 6.2% | Fielding source `vlist` | `13`, n=328, discard 27% | `27`, n=1,208, discard 0% |
| 251101_THD-CX | 6.2% | State verification `qStateVer` | `19`, n=21, discard 62% | Missing, n=1,210, discard 0% |
| 251101_THD-CX | 6.2% | Income or profile value `q8r1` | `210000`, n=9, discard 33% | `50000`, n=81, discard 0% |
| 251205_TFG-Contractor-Index-Q1 | 11.0% | Supplier `SUPNAME` | `MIRATSINSIGHTSPRIVATELIMITED-FEED`, n=77, discard 88% | `PrimeInsightsGroupLLC-API`, n=406, discard 3% |
| 251205_TFG-Contractor-Index-Q1 | 11.0% | Product or ownership `q13r1` | `68`, n=8, discard 62% | `50`, n=101, discard 0% |
| 251205_TFG-Contractor-Index-Q1 | 11.0% | Demographic profile `q5r1` | `63`, n=5, discard 100% | `90`, n=74, discard 1% |
| 260111_Delta-Water-Filtration | 25.7% | Device or OS `vos` | `4`, n=588, discard 41% | `12`, n=251, discard 9% |
| 260111_Delta-Water-Filtration | 25.7% | Fielding technical `dcua` | `..`, n=666, discard 39% | `si`, n=247, discard 9% |
| 260111_Delta-Water-Filtration | 25.7% | Supplier missingness | missing supplier, n=485, discard 41% | supplier value present with low-risk fielding codes |
| 260200_SBD | 44.5% | Product-use text `qcoe2r1` | `Bosch`, n=17, discard 82% | `Milwaukee`, n=145, discard 31% |
| 260200_SBD | 44.5% | Ownership `q13r1` | `Bosch`, n=20, discard 80% | `Craftsman`, n=129, discard 34% |
| 260200_SBD | 44.5% | Timing | under 5 minutes, n=49, discard 94% | Do not apply to other datasets without checking local timing distribution |
| 260206_OC-BH | 17.3% | Fielding source `vlist` | `25`, n=113, discard 48% | `3`, n=231, discard 0% |
| 260206_OC-BH | 17.3% | Product or ownership `q139r9` | `5`, n=350, discard 35% | `99`, n=383, discard 4% |
| 260206_OC-BH | 17.3% | Term flags | `termflags_nonzero`, n=12, discard 58% | no open text, n=37, discard 0% |
| 260300_ECHO | 35.3% | Brand funnel `q17r2` | `ECHO`, n=8, discard 75% | `John Deere`, n=40, discard 15% |
| 260300_ECHO | 35.3% | Equipment ownership `q11othr2` | coded `2`, n=19, discard 100% | `Leaf blower`, n=9, discard 22% |
| 260300_ECHO | 35.3% | Other brand `q19_2026othr1` | `Ryobi`, n=13, discard 62% | `John Deere`, n=20, discard 20% |
| 260306_TFG-Contractor-Index-Q2 | 36.0% | Readability `qc6LangAssessReadLevel` | `9.74`, n=14, discard 93% | `9.57`, n=16, discard 6% |
| 260306_TFG-Contractor-Index-Q2 | 36.0% | Fielding source `vlist` | `23`, n=96, discard 94% | `1`, n=701, discard 13% |
| 260306_TFG-Contractor-Index-Q2 | 36.0% | Supplier `SUPNAME` | missing, n=416, discard 75% | `MakeOpinionGmbH-API`, n=29, discard 0% |
| 260401_-OC-CAN | 38.4% | Fielding source `vlist` | `15`, n=190, discard 84% | `3`, n=121, discard 0% |
| 260401_-OC-CAN | 38.4% | Review metadata `qcoe1R1_RD_Reviewr3` | `0`, n=301, discard 67% | missing, n=121, discard 0% |
| 260401_-OC-CAN | 38.4% | Demographic profile `q43` | `5`, n=42, discard 88% | `1`, n=31, discard 0% |
| 260403_Masterlock-Conjoint | 22.5% | Open-end industry text | `Security`, n=5, discard 60% | no broad open-end rule. Check matrix and profile signals first |
| 260403_Masterlock-Conjoint | 22.5% | Age `qager1` | `62`, n=7, discard 71% | `56`, n=14, discard 7% |
| 260403_Masterlock-Conjoint | 22.5% | State `qstate` | `22`, n=14, discard 50% | `48`, n=15, discard 0% |
| 260404_ADDO | 26.4% | Readability syllables `qcoe1LangAssessNumSyl` | `2`, n=17, discard 88% | `33`, n=16, discard 0% |
| 260404_ADDO | 26.4% | Readability words `qcoe1LangAssessNumWords` | `1`, n=121, discard 52% | `18`, n=26, discard 4% |
| 260404_ADDO | 26.4% | Review metadata `outroR1_RD_Reviewr3` | `16`, n=37, discard 76% | `0`, n=500, discard 19% |

## Rules for avoiding reward hacking

- Do not set a target discard rate or target REVIEW rate before row review.
- Do not move rows between KEEP, REVIEW, and DISCARD to match a historical average.
- Do not treat high historical base rate as proof that a new row is bad.
- Do not treat low historical base rate as proof that a new row is good.
- When an output distribution is far from the closest historical base rate, audit the evidence. Then record the reason for the gap in `workledger.md`.
- Use historical positives and negatives together. A candidate signal without its accepted-row counterexamples is incomplete.
- Before promoting a transferred signal, record its coverage on the target workbook. A high-coverage structural hit is context, not a routing rule, unless it still separates labeled discards from labeled keeps after counterexample review.
