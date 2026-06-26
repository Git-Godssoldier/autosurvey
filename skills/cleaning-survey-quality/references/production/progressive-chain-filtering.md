# Progressive chain filtering

Use this reference when running the full-chain review layer of the autosurvey workflow. It defines the four-layer progressive filtering order and the agent reasoning that each layer requires.

## Core principle

The review follows a strict ordering: Datamap mapping → per-field chain validity → observational signals → cross-population signals. Each layer filters the population progressively. Do not jump to observational or cross-population signals before the chain layer is complete, because chain validity changes the meaning of every downstream signal.

A fast respondent with a coherent, on-topic chain is a keep. A fast respondent with a weak chain is a discard candidate. Speed means nothing until you know what the respondent said.

### Production mode: agent semantic interpretation is mandatory

In production there are no annotations, no status labels, and no answer bank. The agent must semantically interpret each and every row using its own intelligence. The workflow is a four-stage multi-agent pipeline:

**Stage 1 — Script: Data staging (no semantic work)**
Scripts parse the Datamap, map response fields to question text and value labels, and compute population-level statistics. Scripts output structured JSON packets containing: the question text for each field, the value label for each coded answer, the raw open-end text, the timing, the supplier, and the duplicate group membership. Scripts do NOT score, do NOT classify open-ends, do NOT judge coherence. They stage raw materials only.

**Stage 2 — Agent: Respondent identity construction (natural language, not scripts)**
A subagent reads each staged packet and writes a natural-language respondent identity profile. The agent reads the full answer chain and writes who this respondent claims to be, in plain English, including ALL signals translated to natural language. The agent decides how to phrase each claim based on the question context. No script template generates these profiles.

**Stage 3 — Agent: Cross-respondent similarity comparison (natural language, not scripts)**
A subagent reads all respondent identity profiles and compares them to find synthetic response families, shared patterns, incoherent profiles, and supplier-based clusters. The agent writes a similarity report.

**Stage 4 — Agent: Final determination per row (natural language, not scripts)**
For each row, a subagent reads the identity profile, the similarity findings, and the static signals, and makes a final discard/review/keep determination with a natural-language justification.

Regex and scripted rules have a role, but it is strictly limited to Stage 1 data staging. Regex must NOT make the final discard decision. A regex that says "if text contains 'thank you' then discard" is wrong — the agent must read the full profile and decide whether "thank you" in the outro is the only signal or part of a broader incoherence pattern. The same regex match might be a discard in one row (where the chain is also weak) and a keep in another (where the chain is strong and the respondent just gave a short outro).

This is the only way to achieve high precision without annotations. Scripted rules produce false positives because they cannot read context. The agent can.

### Blind run validation results

The four-stage multi-agent pipeline was validated on the Delta Water Filtration unannotated set (1353 rows) and compared against the annotated answer bank (348 rejects, 1005 accepts):

| Metric | Scripted approach | Agent semantic approach |
|---|---:|---:|
| Discard precision | 33.9% | 42.0% |
| Discard recall | 10.9% | 18.1% |
| Discard F1 | 16.5% | 25.3% |
| Flagged F1 (discard+review) | 40.9% | 40.9% |

The agent semantic approach improves discard precision by +8.1pp and recall by +7.2pp over scripted scoring. The agent correctly identified 63 of 348 annotated rejects as discards, and flagged 200 of 348 (57.5%) as discard or review. The agent is more conservative than human annotators (11.1% discard rate vs 25.7% human rejection rate), prioritizing precision over recall — the right behavior for a first-pass filter.

Key patterns the agent caught that human annotators also caught:
- Kitchen-faucet-for-bathroom synthetic family (71 respondents, physically impossible)
- Finance/banking attention-check cluster (7 respondents with attention-check text as purchase reason)
- Garbled/nonsensical open-end text
- Brand name as purchase reason
- Concern contradictions ("not at all concerned" but actively shopping)
- Impossible demographics (5,000+ sq ft home valued under $250K)
- Off-topic survey descriptions (outro about "electronic devices", "whiskey")
- Templated/LLM-generated text
- Non-English responses
- Supplier-based fraud clusters (RevenueUniverse 60% severe issue rate)

The main gap is false negatives (148 annotated rejects kept by the agent). These are cases requiring cross-dataset context, supplier-level rejection patterns, or domain expertise not available in a single-dataset blind run.

## Layer 1: Datamap to response-question mapping

The first step is always mapping the Datamap to the actual response fields.

For each field, extract:
- the question text from the Datamap or codebook
- the expected evidence type: reason, brand, location, rating, use case, allocation, demographic, feedback, factor, or entity name
- the response type: coded, open text, open numeric, matrix cell, or raw
- the field role: screener, funnel, matrix, open end, demographic, technical, helper, or other-specify
- the value labels for coded fields
- the routing rules that determine when the field is answered vs skipped

Build the Question Contract and question-relation graph before any scoring. The graph connects awareness→consideration→use→preference→recommendation→satisfaction→purchase→open-ended explanation. Classify each relationship as parallel, inverse, prerequisite, funnel progression, mutually exclusive, temporal, numerical, routing, or open/closed contradiction.

Do not score any field until its role and prompt text are known. A field scored without its Datamap context is a guess, not evidence.

## Layer 2: Per-field chain validity

After the Datamap is mapped, review each respondent's full response chain field by field. For every answered field, the agent judges whether the answer is on-topic and credible for that specific prompt.

### Per-field judgment questions

Before judging each field, translate the question-answer pair into a natural-language proposition. This turns the chain review from "checking coded values against labels" into "reading a set of first-person self-claims and checking whether they form a coherent respondent identity."

#### Natural-language proposition mapping

For every question-answer pair, generate a first-person proposition that states what the respondent is claiming about themselves. The proposition is written from the respondent's perspective using the answer value and the question context.

Examples:
- Q: "How concerned are you about the quality of water in your home?" A: "Very concerned" → "I am very concerned about the quality of water in my home."
- Q: "Which brands are you aware of?" A: checked Delta, Brita, PUR → "I am aware of Delta, Brita, and PUR water filter brands."
- Q: "What does your water filtration system do?" A: "None / I don't know" → "I do not know what my water filtration system does."
- Q: "What prompted you to decide to buy a water filtration device?" A: "Bad taste" → "I decided to buy a water filtration device because of bad taste."
- Q: "What is the main source of water for your home?" A: "City/municipal" → "My home's water comes from the city or local municipality."

The proposition mapping rules:
- **Coded single-select**: state the selected value label as a first-person claim using the question's subject. "I [claim] [value label]."
- **Multi-select (checked items)**: list the checked items as a claim of awareness, ownership, concern, or use. "I am aware of / have / am concerned about [checked items]."
- **Multi-select (unchecked items)**: note what the respondent did NOT claim when relevant. "I did not claim awareness of [major unchecked brands]."
- **Open text**: state what the respondent said as a self-claim. "I said: '[verbatim text]' about [question subject]."
- **Matrix cells**: translate each cell into a claim about that specific product/attribute. "I currently have [product]. I plan to get [product]. I do not have or plan to get [product]."
- **Numeric**: state the value as a self-claim. "My home is approximately [value] square feet."
- **Blank/routed**: note the routing state. "I was not asked this question" or "I left this blank."

The full set of propositions for a respondent forms their **self-claim profile**. The agent reads this profile as a narrative and checks:
- Do the propositions form a coherent person?
- Do any propositions contradict each other?
- Does a proposition claim expertise or concern that another proposition undermines?
- Does the respondent claim to have, know, or care about things that an authentic qualified respondent would not?
- Is the self-claim profile internally consistent across role, product, brand, purchase, concern, and demographic propositions?

This is more powerful than checking coded values because it exposes contradictions that are invisible in raw data. For example:
- "I am very concerned about water quality" + "I do not know what my water filtration system does" + "I am aware of 12 brands including obscure ones" = a respondent who claims high concern and broad awareness but no product knowledge — an incoherent identity.
- "I bought a water filtration system in the past 12 months" + "I do not have any water treatment systems" + "I plan to buy 6 different types" = a funnel break visible only when propositions are read together.

The proposition mapping is agent-authored natural language, not a script template. Scripts stage the question text, value labels, and raw values. The agent writes the proposition for each field using the question context and the answer.

### Coherence analysis using self-claim profiles

Once the self-claim profile is built, the agent reads it as a narrative and checks for contradictions across proposition families. The Delta t=5 analysis identified these coherence break types:

- **contaminant_concern_drift**: respondent claims many contaminants in their water (q22) but is concerned about (q23) completely different or minimally overlapping ones. This is a 3.9x lift signal — rejected rows drift between what they claim to have and what they claim to worry about.
- **contaminant_overclaim**: claiming 8+ contaminants in water. 1.8x lift. Some accepted rows also do this (25%), so it is soft concern unless combined with drift.
- **q14_wrong_dimension**: purchase reason (q14) is a brand name, survey-meta, or non-reason instead of a personal motivation. 5.9x lift. This is hard invalidity because the prompt asks for a reason and the answer gives a different evidence type.
- **source_overclaim**: using 6+ research sources. 2.7x lift. Soft concern unless combined with other signals.
- **concern_knowledge_break**: claims extreme concern but no knowledge of how filters work, or claims high knowledge but no concern. Rare but strong when present.
- **funnel_break**: purchased filtration but claims no current system. NOT a separator in Delta (64.7% t5 vs 58.8% t3) — common in both populations. Do not use as a primary signal.

The agent must check each coherence break against the accepted-row guardrail. A break that appears in 25%+ of accepted rows is weak. A break that appears in <5% of accepted rows is strong. The lift calculation is the guardrail test.

### Cross-dataset generalization of coherence signals

The proposition mapping and coherence analysis methodology was validated across all 11 TFG annotated datasets (3,124 rejected rows, 10,344 accepted rows, 880-row accepted guardrail). The generalization results classify each signal as universal, moderate, or dataset-specific:

**Universal signals (use in all datasets without per-dataset validation):**
- **meta_praise in open-ends**: Survey-meta praise ("thank you", "good survey", "amazing") instead of substantive content. Appears in 10/11 datasets, >2x lift in 6, zero false positives in 5. This is the strongest generalizing open-end signal across the TFG portfolio.
- **placeholder in open-ends**: "None", "N/A", "Nothing", "IDK". Appears in 6/11 datasets, >2x lift in 5. One inverse case (ECHO). Check guardrail per dataset.

**Universal non-signals (down-weight in all datasets):**
- **very_few_words (≤3 words)**: Appears in 11/11 datasets with 0.74x avg lift. Accepted rows are equally likely to give short answers. This is a false positive that must always be down-weighted.

**Dataset-dependent signals (check guardrail before using):**
- **timing direction**: Rejected rows are faster in 5/11 datasets, slower in 6/11. The direction reverses across datasets. Extreme fast rates (<200s) show >2x lift in 6/11 datasets.
- **missing supplier**: >1.5x lift in only 2/11 datasets. Inverse in 4/11. Check per dataset.
- **long text (40+ words)**: Bot signature in some datasets (OC BH 22x), human signature in others (THD CX 0x, ADDO 0.4x). Check per dataset.

**Dataset-specific signals (don't expect to generalize):**
- **templated language**: Delta-only LLM-template signatures (47x lift). Not found in other datasets.
- **repetition_loop**: ODL-only bot/fatigue pattern (62x lift). Not found elsewhere.
- **contaminant_concern_drift**: Delta-specific (requires water quality fields).
- **q14_wrong_dimension**: Delta-specific (requires purchase reason field).

The key learning: **the proposition mapping methodology generalizes, but individual coherence break signals do not.** The agent must build the accepted-row guardrail first, compute lift per dataset, and only apply signals with >1.5x lift in that specific dataset. The meta_praise and placeholder signals are the exceptions — they generalize broadly enough to apply with high confidence.

For each answered field, ask:
- Does the answer give the evidence type the prompt requested?
- Does the answer fit the qualified respondent universe?
- Is the answer responsive to the exact question, or does it answer a different question?
- Is the answer a valid short noun phrase (acceptable for brand/location/factor prompts) or a nonresponsive placeholder?
- Does the answer contradict the respondent's own answers to adjacent or related fields?
- Does an open-end contain lived detail when the prompt asks for experience, or does it stay generic?
- Does an other-specify field name a real entity in the correct category?

### Per-field classification

Classify each field answer as one of:
- **responsive**: answers the exact prompt with the requested evidence type
- **partially responsive**: addresses the prompt but misses part of the requested evidence
- **nonresponsive**: does not address the prompt (greeting, praise, meta, vague)
- **wrong semantic dimension**: answers a different question than the one asked
- **off-topic / wrong universe**: coherent answer in the wrong domain
- **invalid type**: wrong data type or impossible value
- **route-inconsistent**: answer present where routing should have skipped, or missing where routing should have presented
- **unsupported other-specify**: Other field text that does not name a real entity in the correct category
- **mechanically repeated**: identical or near-identical text copied from another field or respondent
- **locally protected**: short or rough but valid for the prompt type

### Hard invalidity vs soft concern

Separate hard invalidity from soft concern:

**Hard invalidity** includes:
- wrong-question answers
- wrong semantic dimension
- unsupported other-specifies
- off-category entities
- impossible allocations
- route violations
- copied text from another prompt
- invalid matrix structure

**Soft concern** includes:
- speed
- shortness
- generic text
- broad selection
- straightlining
- repetition
- high positivity
- weak detail

Hard invalidity in one field is a strong signal. Soft concern in one field is routing evidence. Multiple soft concerns across independent fields can combine to support a discard.

### Funnel consistency

After per-field classification, check funnel consistency across related fields:
- Does awareness match consideration? A respondent who claims awareness of many brands but cannot name a reason for purchase may be over-selecting.
- Does use match preference? A respondent who claims to use a product but gives a wrong-universe purchase reason has a funnel break.
- Does purchase intent match the purchase reason? A respondent who says they will buy but gives a nonresponsive reason has a funnel break.
- Does the role screener match the open-end expertise? A respondent who passes the role screener but answers open ends like an unqualified observer has a qualification mismatch.

Funnel breaks are hard invalidity when they show the respondent does not understand the product category. They are soft concern when they show carelessness but not fabrication.

### What this layer finds

This layer is the primary authenticity surface. Most rejection drivers should be findable here. The Delta t=5 analysis showed that 55.7% of rejected rows had a valid outro but were rejected for reasons found in the full chain: funnel inconsistency, brand awareness anomalies, supplier concentration, or technical evidence.

If a row has no chain-validity concern at this layer, its rejection driver is observational, cross-population, or PM-quality (Layer 2b), not semantic. Move to Layer 2b or Layer 3.

## Layer 2b: Survey-structure and brand-funnel coherence (v5)

After per-field chain validity, check whether the respondent's classification, channel, and brand funnel form a coherent system. This layer addresses PM-quality discards that pass authenticity review but fail the client's quality bar.

### Survey-structure coherence

- **CLASSIFY branch**: CLASSIFY=1 (professional) respondents should show professional purchasing patterns (dealer channels, commercial equipment, volume purchases). A pro who answers like a consumer is a quality failure. ECHO data: pro-branch rejects at 60.4% vs 30.5% for consumer.
- **PROAGE/CONAGE**: Pro-branch respondents should show professional experience depth. Consumer-branch should show consumer experience. Mismatch is a quality concern.
- **Channel conditions**: `conditionsAriens=1` → brand answers should include Ariens. `conditionsHD_or_OPE_dealers=1` → Home Depot / OPE dealer channel. Channel-brand mismatch is a quality concern. ECHO data: Ariens channel rejects at 59.2%.
- **list/source**: Different suppliers have different reject rates. Context, not proof.

### Brand funnel as a connected system

Brand funnel fields are the strongest raw predictors of client discards (signal score 2345.5 on ECHO, far exceeding semantic content fields). Check the funnel as a connected graph:

- **Awareness → Rating → Consideration → Recommendation → NPS chain**: Does the respondent claim awareness of brands they later cannot rate? Do they recommend brands they did not claim awareness of?
- **Brand name quality in OE fields**: Real OPE brands (Stihl, Husqvarna, Echo, Honda, Ryobi, Toro, Craftsman) vs garbled/wrong-universe brands ("Harmmer", "china", "Mercedes" for OPE).
- **Share allocation plausibility**: Equal share to all brands = potential straightlining. Many zero allocations = disengaged (47.2% reject rate on ECHO). Fragmented share (8+ brands with nonzero share) = 52.0% reject rate.
- **Rating consistency**: Do ratings align with stated preference and recommendation? A respondent who rates a brand 10/10 but never mentions it in open-ends has a funnel break.
- **NPS verbatim quality**: Should be brand-specific, not generic praise. "Effective work and power" = generic. "They put their name in VERY LARGE letters" = brand-specific.

### Substantive engagement threshold

The core open-end must demonstrate substantive engagement with the survey's specific topic:
- "Mowing and blowing" is on-topic for an OPE survey but thin — it names generic tasks without equipment, project narrative, or personal detail.
- For strict clients, thin-but-on-topic is a quality failure even though the respondent is authentic.
- The threshold varies by dataset. Without calibration data, treat thin-but-on-topic as REVIEW, not KEEP.

### How Layer 2b combines with other layers

- Hard chain invalidity (Layer 2) + survey-structure mismatch (Layer 2b) → strong discard candidate
- Valid chain (Layer 2) + survey-structure mismatch (Layer 2b) → review candidate (authentic but quality-failing)
- Valid chain (Layer 2) + brand funnel incoherence (Layer 2b) → review candidate, escalate with any observational signal
- Valid chain (Layer 2) + thin substantive engagement (Layer 2b) → REVIEW (not KEEP) without calibration data

## Layer 3: Observational signals

Only after chain validity is established, filter in observational signals that contextualize the chain.

### Timing

Read timing probabilistically:
- Total qtime is the fallback. Page, section, or question answer time is better when available.
- Fast time carries more weight when the chain is also weak, contradictory, copied, generic, or nonresponsive.
- Fast time carries less weight when the respondent answers simple short prompts, gives coherent open ends, or the survey has many closed-ended items.
- Slow time is not automatically good. It may indicate distraction, breakoffs, copied text, or pasted content.
- Question-time elasticity: a respondent should usually spend more time on complex questions, large matrices, long open ends, and recall-heavy questions than on simple categorical items. Nearly identical latency across simple and difficult question sets can be more suspicious than ordinary speed.

### Supplier/source cohort

- Missing supplier is context, not proof.
- Supplier concentration becomes evidence when multiple respondents from the same supplier share weak chains.
- Compare supplier cohorts against each other. If one supplier's rejected rate is materially higher than others, that is a wave-level finding, not a row-level discard reason by itself.

### Technical

- IP address, device, user agent, session. Treat as independent context unless multiple supposedly independent respondents share the same technical evidence and weak chains.
- One IP appearing in many columns is not many independent signals. It becomes stronger only when multiple respondents share technical evidence and similar weak chains.

### Platform helpers

- TERMFLAGS, SCRUTINYFLAGS, Research Defender fields. Confirm meaning from the Datamap, then inspect the chain.
- These are routing evidence, not final proof.

### How observational signals combine with chain

Observational signals refine the chain layer. They do not replace it. The combination rules are:
- Hard chain invalidity + any observational concern → strong discard candidate
- Soft chain concern + timing implausibility → review candidate, escalate only with convergence
- Soft chain concern + supplier concentration → review candidate, escalate only if the supplier cohort shows a pattern
- Valid chain + fast time → keep (fast but coherent is human)
- Valid chain + missing supplier → keep (context only)

## Layer 4: Cross-population signals

Only after observational signals are layered in, filter in cross-population signals that reveal synthetic response families.

### Duplicate open text

- Text that appears in multiple respondents, especially rejected-only duplicates (text that appears more than once overall and only in rejected rows, never in accepted rows).
- Common short phrases can repeat naturally. Only count duplicates of substantive text (open ends, purchase reasons, survey summaries) as evidence.
- Do not count supplier names, URLs, panel metadata, or other technical fields as copied respondent text.

### Response vector clustering

- Respondents with identical or near-identical coded-answer vectors across many fields.
- A response vector is the concatenation of all coded answers. Two respondents with the same vector across 50+ fields are likely copied or synthetic.

### Timing vector clustering

- Respondents with matching timing profiles or burst submissions (many completes in a short window from the same supplier).

### Matrix pattern clustering

- Respondents with identical matrix patterns across semantically distinct items.
- Compare across the full set of matrix rows, not within a similar subgroup. Identical patterns across distinct constructs are more suspicious than within similar constructs.

### Shared rare phrases

- Repeated rhetorical templates or unusual phrasing across respondents.
- The Delta t=5 analysis found shared templated phrases like "the poll examined", "the study aimed", "crucially, the poll", "in order to determine" across multiple rejected rows — these are LLM-template signatures.

### Copied chains

- Full response chains that are near-duplicates of other respondents. These are the strongest cross-population signal.

### How cross-population signals combine

Cross-population signals are the strongest convergence evidence:
- Single row with weak chain → review candidate
- Single row with weak chain + part of a duplicate cluster → strong discard candidate
- Single row with hard chain invalidity + rejected-only duplicate → severe discard candidate
- Multiple rows from the same supplier with shared weak chains + shared timing → synthetic response family

## Delta t=5 validation

The Delta Water Filtration t=5 analysis validated this ordering:

- **Layer 1 (Datamap)**: 15 open-end fields mapped, 7 matrix bases identified as semantically distinct product categories, question-relation graph built.
- **Layer 2 (chain validity)**: 194/348 (55.7%) had valid outtros. Their rejection drivers were in the full chain, not the open end. 36 wrong-universe, 4 wrong-dimension, 2 gibberish, 65 generic-filler-templated, 45 survey-meta/nonresponsive outtros were found at this layer. Self-claim proposition mapping then exposed coherence breaks invisible in raw data: contaminant_concern_drift (4.0x lift), q14_templated (14x lift), source_overclaim (2.7x lift). The incoherent_soft rate was 3.4x higher in rejected rows (17.0% vs 5.0%).
- **Layer 3 (observational)**: 0 rows flat-lined all 7 matrix categories — straightlining was correctly down-weighted to zero. Timing showed rejected rows were actually SLOWER on average (1028s vs 899s), confirming speed is not the primary driver. Missing supplier was 56.9% rejected vs 28.6% accepted (2.0x lift, context not proof). Zero duplicate IPs.
- **Layer 4 (cross-population)**: Only 13 rows carried true rejected-only duplicate text after correcting the definition to require actual duplication. The 4 severe-weight rows all combined hard chain invalidity with rejected-only duplicate convergence. 65 generic_filler_templated outtros shared LLM-template signatures ("the poll examined", "the study aimed", "crucially, the poll").

The ordering correctly identified that chain validity is the primary surface, observational signals refine but do not replace it, and cross-population signals provide the strongest convergence for the hardest cases.

### Signals correctly down-weighted by the guardrail

The accepted-row guardrail (80-row sample) was essential for down-weighting false positives:
- **funnel_break** (purchased filtration but no current system): 64.7% t5 vs 58.8% t3 — NOT a separator, common in both populations
- **matrix_oversel_have** (5+ products): 27.3% t5 vs 33.5% t3 — INVERSE, accepted rows claim more products
- **brand_overclaim** (12+ brands): 1.1% t5 vs 2.5% t3 — INVERSE, accepted rows over-claim brands
- **concern_knowledge_break**: 1.1% t5 vs 1.3% t3 — NOT a separator
- **matrix straightlining**: 0% in both populations — zero signal

Without the guardrail, these would have been false-positive discard signals. The lift calculation is the guardrail test: a signal with <1.5x lift is weak, >3x is strong, and inverse lift means the signal is more common in accepted rows.
