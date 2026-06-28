# V7 calibration and guardrails

Use this reference during blind runs and during skill evolution. It captures the latest successful ECHO calibration pattern and the rules that should transfer to future Decipher datasets.

## Benchmark result to preserve

The V7 ECHO pass reviewed all 1,566 respondents and beat both V6 and the Captain semantic baseline.

| Metric | Captain | V6 | V7 | Change |
|---|---:|---:|---:|---|
| Precision | 0.581 | 0.451 | 0.664 | +47% vs V6 |
| Recall | 0.508 | 0.401 | 0.524 | +31% vs V6 |
| F1 | 0.542 | 0.425 | 0.586 | +38% vs V6 |
| Balanced accuracy | 0.654 | 0.567 | 0.690 | +22% vs V6 |
| False positives | 203 | 270 | 147 | 46% fewer than V6 |

V7 caught 290 true client rejects and reduced false positives to 147. It also kept a REVIEW bucket for human judgment. This is the current pattern to preserve until a newer sealed benchmark beats it on F1, precision, recall, and false-positive exposure.

## Why V7 worked

V7 improved because it stopped treating every weak-looking answer as an exclusion signal. It used ML as a calibrated disposition gate, required stronger independent evidence for discard, and protected accepted rows with concise but coherent responses.

The most important changes were:

1. Use ML as a controlled disposition gate.
2. Require 4 or more converging evidence families when ML is not strong.
3. Do not fire `core_oe_quality` for `thin_on_topic`.
4. Treat Stage 2 quality failure as REVIEW unless ML or family convergence supports discard.
5. Treat badopen severity as a modifier, not a primary driver.
6. Tighten platform risk so moderate RD_Search values do not fire alone.
7. Make client rejection probability the largest score component.
8. Use direct-discard combinations only when model risk combines with brand funnel, survey structure, or quota reconstruction.

## Runtime decision rules

Use these rules after the row has been semantically read. Do not let a script apply them without authored reasoning.

### DISCARD

Use DISCARD when one of these conditions is met:

- ML score is at least 0.8.
- ML score is at least 0.6 and at least one independent evidence family also fires.
- ML score is at least 0.5 and model risk combines with brand funnel, survey structure, quota reconstruction, wrong brand universe, off-topic core open end, non-answer, or gibberish.
- At least 4 independent evidence families fire.
- Platform fraud is certain, such as qc 8, qc 9, non-English in a US survey, or TERMFLAGS with no strong human counterevidence.

### REVIEW

Use REVIEW when one of these conditions is met:

- 2 or 3 evidence families fire.
- The answer is thin but on topic and no stronger independent family supports discard.
- The Stage 2 quality bar appears to fail but fewer than 4 families fire and ML is below 0.6.
- Badopen severity is high but model risk and family convergence are not strong.
- ML is 0.5 to 0.6 with no other family.
- Signals conflict and a benign explanation remains plausible.

### KEEP

Use KEEP when one of these conditions is met:

- ML is below 0.2, platform flags are absent, and the response chain has no hard invalidity.
- The row has at most 1 weak family and has coherent prompt-fit evidence.
- The only concern is shortness, rough wording, ordinary enthusiasm, or a valid simple answer.

## Evidence family health

V7 family gaps were positive or neutral. This is the health check to maintain:

| Family | Discard minus keep gap |
|---|---:|
| model_risk | +0.35 |
| survey_structure | +0.22 |
| brand_funnel | +0.19 |
| source_risk | +0.14 |
| quota_reconstruction | +0.11 |
| core_oe_quality | +0.10 |
| platform_risk | +0.09 |
| timing_engagement | +0.08 |
| duplicate_semantics | +0.00 |

If any family fires more often for accepted rows than rejected rows in a new labeled evaluation, downgrade that family before the next blind run.

## Guardrails that prevent regression

### Thin-on-topic is not a discard signal

Do not fire `core_oe_quality` for an answer that is thin but answers the prompt in the right domain. This was the single most important false-positive guardrail.

Examples:

- "Mowing the lawn" can be valid for a simple task prompt.
- "Basic yard maintenance" can be valid when no narrative detail is required.
- "Water filtration systems" can be valid when the prompt asks what the survey was about.

These answers become DISCARD candidates only when another independent family explains why they are not credible in this row.

### Substantive open ends are not automatically protective

A detailed open end can still be client-rejected. Treat substantive text as evidence to read, not as a keep rule. If ML, platform, branch, or brand-funnel signals are strong, the row can still be REVIEW or DISCARD.

### Stage 2 failure defaults to REVIEW

A quality-stage failure over-discarded in V6. Do not turn a project-quality concern into DISCARD unless ML is at least 0.6 or at least 4 independent families fire.

### Badopen severity is a modifier

High badopen severity should raise concern, but it should not drive DISCARD alone. It becomes strong when paired with model risk, platform risk, brand-funnel incoherence, survey-structure mismatch, or cross-row template evidence.

### Moderate platform risk needs convergence

RD_Search threat 20 to 25 is context. It does not fire platform risk alone. RD_Search at least 25 can fire. qc 8, qc 9, non-English in a US survey, and strong TERMFLAGS remain high-severity evidence.

## Evolution requirements

After each labeled evaluation:

1. Read every false positive and identify the accepted-row guardrail that should have protected it.
2. Read every false negative and identify whether the miss was due to weak ML, missing field role, missing brand funnel logic, quota reconstruction, badopen boundary, or cross-row behavior.
3. Promote only the smallest rule change that would have improved the sealed run.
4. Record rollback conditions for every promoted rule.
5. Test the new rule on the next unconsumed dataset. Do not present a revised score on the same dataset as validation.

## Current improvement target

The next performance gain should come from false-negative analysis without sacrificing the V7 precision gain.

Focus on:

- thin-on-topic rows with low ML and no convergence that the client still rejected;
- accepted Stage 2 fail rows that need stronger protection;
- field-specific badopen boundaries;
- brand-funnel and survey-structure combinations that are independent of text quality;
- review-bucket rows whose ML score is between 0.5 and 0.6.
