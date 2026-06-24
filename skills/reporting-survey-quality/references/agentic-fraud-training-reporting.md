# Agentic fraud training reporting

Use this reference when reporting from annotated `status = 3/5` data, fraud-signal discovery, authenticity-risk training, or calibration against accepted and rejected respondents.

## Reporting frame

The report is not a generic data-quality summary. It is a training report for an agentic fraud-detection framework.

Explain the work as:

- labeled rejected rows are the observed client-removal corpus
- labeled kept rows are the antisignal and protective-evidence corpus
- the system is learning evidence families, interactions, and guardrails
- `status = 5` predicts client rejection, not proof of fraud by itself
- the goal is to transfer learned signals to unannotated datasets and find additional likely fraudulent responses the client process may not have found

Avoid language that implies every rejected respondent is fraudulent, a bot, or LLM-generated. Use precise terms: client rejection, authenticity risk, fabrication risk, unqualified respondent signal, inattentive-response signal, routing defect, or survey-design ambiguity.

## Required narrative

Every training report must answer:

- What hidden signals were uncovered in the rejected rows?
- Which accepted rows show the same surface anomalies and therefore protect against false positives?
- Which signal families separate rejected rows from accepted rows?
- Which signal families are broad but weak and should not drive exclusion?
- Which interactions are stronger than their component signals?
- Which blind-pass misses reveal new semantic criteria?
- Which false-exclude risks show that the detector is too broad?
- What should change before the naive unannotated rerun?

## Required sections

1. **Training Objective**
   State that Autosurvey is learning an agentic fraud/authenticity detector from annotated examples.

2. **Ground Truth and Limits**
   Define `status = 3` and `status = 5`. State that status is a client decision and not direct proof of fraud.

3. **Blind Review First**
   Show the blind tier distribution before status is revealed. Explain why this prevents label leakage.

4. **Label-Aware Contrast**
   Show where the blind detector matched status, missed status-5 rows, and over-flagged status-3 rows.

5. **Signal Families**
   Report family-level lift and false-positive exposure, not only raw metrics. Aggregate correlated checks inside families.

6. **Signal Interactions**
   Highlight combinations that are stronger than single signals, such as answer-time/text coupling plus open-end weakness, or matrix behavior plus weak open ends.

7. **Antisignals and Protective Evidence**
   Treat accepted anomalous rows as training data. Explain which human evidence protects them.

8. **Blind Misses**
   Read status-5 rows that the blind pass did not catch. These are the highest-value source of new semantic rules.

9. **Detector Upgrade Plan**
   State which signals should become first-pass routing, which should stay agent-only, which should require more evidence, and which should be retired.

10. **Naive Rerun Readiness**
   State whether the learned detector is ready to run on original unannotated datasets. If not, name the missing signal or guardrail.

## Required visualizations

Dashboards and decks should focus on model training and signal discovery:

- labeled corpus overview: total labeled rows, status-3 rows, status-5 rows, rejected rate
- blind tier by status: stacked bar showing Tier 1-5 distribution for accepted and rejected rows
- contrast outcome funnel: blind match, review match, blind miss, false-exclude risk, protective review
- family lift map: signal family by threshold, with reject rate and accepted-row exposure
- precision-recall style view by tier: Tier 5 precision, Tier 3-5 coverage, false-positive exposure
- signal interaction heatmap or table: pair/family interactions with lift and support
- antisignal gallery: accepted rows with surface anomalies and protective evidence
- blind-miss gallery: rejected rows missed by the blind pass, with hypothesized new semantic signals
- detector upgrade roadmap: promote, hold, demote, retire

Do not center the dashboard on generic "quality count" charts when the task is annotated fraud-signal training.

## Prose standard

Write like a senior analyst explaining a model-training loop:

- "We learned..."
- "The accepted rows protect against..."
- "This signal is too broad because..."
- "This interaction is more useful than either signal alone because..."
- "The next unannotated pass should..."

Do not write:

- "The script found..."
- "The agent final pass..."
- "Rows with status 5 are fraudulent..."
- "This score proves..."
- raw quota chains, redirect URLs, pipe dumps, or respondent-chain exports as prose
- long examples that make the reader parse source-system tokens before the finding

When examples are needed, write an authored chain readout. Name the workbook, row, field or question family, and the reason the example matters. Then paraphrase the relevant answers in one or two readable sentences. If raw source text is necessary for auditability, quote only the short answer fragment that carries the signal and cite the table or packet where the full chain can be opened.

For accepted-row antisignals, say what protected the row: grounded personal detail, coherent role context, valid short answer, plausible brand funnel, understandable non-native wording, or a real tradeoff. For rejected-row blind misses, say what the next detector should learn: wrong respondent universe, brand-funnel contradiction, generic professional wording, implausible timing/text coupling, copied template, or chain-level incoherence. Do not paste the full chain into the report body.

## Output gate

A training report is incomplete if it lacks:

- a blind-vs-label contrast
- accepted-row antisignals
- family-level aggregation
- a false-positive discussion
- a blind-miss discussion
- a transfer plan for unannotated reruns
