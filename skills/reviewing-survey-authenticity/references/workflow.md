# Agent-Native Authenticity Workflow

Use this workflow when the task is to decide whether survey respondents look authentic, fabricated, automated, bot-like, inattentive, or client-rejectable.

## 1. Freeze Inputs

Identify every input file and note its role before reading respondent content:

- Unannotated survey export.
- Datamap, questionnaire, codebook, or survey programming export.
- Any client comments, known reject criteria, or past annotations.
- Any blinded or annotated benchmark labels.

Client labels and annotations stay closed until after the blind ledger is sealed.

## 2. Build the Question Contract

Before reviewing respondents, reconstruct the survey itself:

- Field roles and respondent identifiers.
- All screeners, routes, survey sections, brands, products, entities, matrices, grids, scales, open ends, other-specify fields, timing fields, supplier fields, device fields, and technical identifiers.
- Which answers create obligations later in the survey.
- Which questions are parallel, inverse, prerequisite, mutually exclusive, temporal, numerical, routing-dependent, or open/closed linked.

This contract is written in natural language and should make the survey intelligible to another analyst.

## 3. Read Every Respondent Blind

For every respondent, read the full response chain in context. Do not score isolated cells first. The unit of review is the respondent’s full survey behavior:

- Closed answers.
- Open ends.
- Matrix patterns.
- Timing where natively visible.
- Routing coherence.
- Brand or product funnels.
- Demographics when relevant to claimed behavior.
- Technical identifiers as context, not standalone proof.

Write notes with citations to row, field, and cell values wherever possible.

## 4. Use Three Perspectives

For each respondent, write the blind assessment from three angles:

- Forensic investigator: what looks fabricated, synthetic, pasted, automated, or strategically evasive.
- Human advocate: what could make the same evidence legitimate human behavior.
- Evidence judge: whether independent evidence families converge strongly enough to justify exclusion.

Do not treat many variants of one family as many independent reasons.

## 5. Decide a Five-Tier Outcome

Use the decision rubric to assign one of five tiers. Only the highest tier is an exclusion recommendation. Every other tier remains a keep, review, or learning case.

## 6. Seal the Ledger

The sealed ledger must contain one row per respondent, stable row identity, decision tier, binary recommendation, rationale, suspicious evidence, protective evidence, cited fields, confidence, and notes for future learning.

After the ledger is complete, hash the exact files that contain decisions and record the seal manifest. Only then may a post-seal evaluator compare to client labels.

## 7. Reveal Labels and Learn

After sealing, compare the blind decisions to the labels:

- Rejected rows caught.
- Rejected rows missed.
- Accepted rows protected.
- Accepted rows falsely escalated.
- Similar accepted controls for rejected rows.
- Similar rejected controls for accepted rows.

Turn recurring distinctions into transferable signal specifications only after attacking them with counterexamples.

## 8. Update the System

Promote a signal only when it is:

- Transferable across surveys.
- Expressed as a natural-language judgment task.
- Protected by accepted-row guardrails.
- Documented with evidence and counterevidence.
- Regression-tested in the post-seal evaluator boundary.

If no native workbook reader is available for direct agent row review, stop before respondent review with `BLOCKED_NATIVE_WORKBOOK_READER_REQUIRED`.
