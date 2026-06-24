# Semantic signal expansion

Use this reference whenever a run evaluates respondent authenticity, fraud risk, bot-like behavior, LLM-assisted answers, straightlining, speeding, open-end quality, duplicate technical evidence, or any other candidate quality signal.

## Core standard

Every discovery must become a weighted evidence claim, not a raw flag.

A script may surface candidate evidence such as a fast qtime, repeated grid pattern, duplicate IP, short open end, text similarity, or timing outlier. The agent must decide what the evidence means after reading the question set, answer options, response chain, accepted counterexamples, and any available timing or fielding context.

Do not ask, "Did this rule fire?" Ask:

- What exact behavior was observed?
- What question set produced it?
- How similar were the questions being compared?
- What answer type did the prompt ask for?
- How much time was available for that question, page, section, or survey?
- What does the open-ended response chain reveal about the respondent's authenticity?
- Does the pattern repeat across unrelated questions, suppliers, devices, sessions, or respondents?
- What accepted examples look similar?
- What weight should this evidence carry, and why?

## Research rationale

Open ends and complete response chains are central because common quality checks can miss insincere respondents. Open-ended answers often reveal whether a respondent is personally grounded, copied, synthetic, off-domain, or simply rough but valid.

Treat timing probabilistically. Do not rely on arbitrary fixed cutoffs. Time should be read against uncertainty, cognitive burden, page or screen context, matrix size, answer length, and response-chain evidence.

Use pairwise semantic comparisons when possible. Comparing two answers, two respondents, or one row against a similar accepted control can be more stable than asking for an absolute quality score.

Treat cross-respondent homogeneity as a population-level signal. Repeated rare phrasing, response vectors, timing vectors, and matrix patterns can reveal synthetic response families that are invisible inside one row.

Keep human-easy and agent-hard probes separate from the current runtime method. Future instrumentation can add probes designed for agent detection, but this skill should not assume those probes exist in current Decipher exports.

## Weighting dimensions

Assign each discovery a provisional weight in natural language. Numeric weights can exist in evidence tables, but the controlling artifact is the agent's explanation.

Use these dimensions:

- **Prompt fit**: whether the answer gives the kind of evidence the prompt requested.
- **Question similarity**: whether repeated answers occurred across questions that were semantically similar, adjacent but different, or clearly unrelated.
- **Time plausibility**: whether completion time, page time, section time, or per-question answer time supports or weakens the concern.
- **Semantic authenticity**: whether open-ended answers sound personally grounded, qualified, and responsive to the question set.
- **Cross-chain coherence**: whether the full response chain is internally consistent across role, product, brand, use case, geography, demographics, and narrative fields.
- **Signal independence**: whether multiple concerns are independent or are really the same evidence repeated under different names.
- **Pattern recurrence**: whether the behavior repeats across rows, suppliers, IPs, devices, fielding bursts, or copied answer chains.
- **Accepted-row guardrails**: whether status-3 or otherwise accepted respondents show the same surface pattern without being unauthentic.
- **Survey-design ambiguity**: whether the prompt, grid, or answer format invited the weak-looking behavior.

Weights should increase when evidence is specific, independent, repeated, prompt-inconsistent, and hard to explain benignly. Weights should decrease when questions are semantically similar, timing is plausible, the open ends are authentic, accepted counterexamples are common, or the survey design made the response pattern likely.

## Straightlining expansion

Never treat straightlining as only "same answer repeated."

For every matrix or grid straightline concern, evaluate:

- the semantic similarity of the grid items
- whether identical answers are plausible because the items ask nearly the same thing
- whether the repeated answers span unrelated constructs
- whether reverse-coded or contrast items were present
- whether the answer pattern changed when the question topic changed
- page, section, or question answer time when available
- whether the respondent gave authentic open-ended explanations elsewhere
- whether the same pattern appears across many respondents from the same supplier or technical cluster

Strong straightlining evidence usually requires repeated answers across semantically distinct items, implausibly low exposure or answer time, and weak chain evidence. Weak straightlining evidence often occurs when the questions are similar, the respondent has a plausible uniform opinion, or the open-ended chain shows real engagement.

The final note should say whether the grid behavior is:

- a valid uniform opinion
- review routing
- a survey-design weakness
- a contributor to discard only when paired with other evidence
- a strong authenticity concern because it converges with time, semantic, or technical evidence

## Speed and duration expansion

Completion time is a routing signal until interpreted.

For each time concern, inspect the best available timing level:

- total qtime or duration
- page or section duration
- question answer time
- start and completion timestamps
- fielding burst or odd-hour context
- supplier or source concentration

Fast time carries more weight when the respondent also straightlines semantically distinct grids, gives generic or non-responsive open ends, contradicts role or qualification fields, or appears in a copied chain cluster. Fast time carries less weight when the respondent answers simple short prompts, gives coherent open ends, or the survey has many closed-ended items that can reasonably be completed quickly.

Slow time is not automatically good. It may indicate distraction, breakoffs, copied text, or pasted content. Read the chain before treating slow time as reassurance.

## Open-ended authenticity expansion

Open ends are the main semantic review surface. Evaluate them against the question-set authenticity map.

For each important text answer, decide whether it:

- answers the exact prompt
- gives the requested evidence type, such as reason, use case, concrete example, role claim, location, product factor, brand, or feedback
- fits the qualified respondent universe
- contains lived detail when the prompt asks for experience
- stays coherent through the full sentence or answer chain
- connects to role, brand, product, timing, demographic, or prior-answer context
- sounds generic, survey-meta, off-domain, copied, overly polished without detail, evasive, hostile, nonsensical, or fabricated

Do not penalize rough grammar, short valid noun phrases, enthusiasm, or imperfect phrasing when the answer fits the prompt. Do not reward polished language when it fails to provide the requested evidence.

Example reasoning standard: if the survey asks about home renovation, a response about construction may be acceptable when it clearly describes renovation work, materials, contractors, permits, costs, or homeowner decision-making. It becomes suspicious when it drifts into generic construction management, unrelated commercial projects, or polished business language that never answers the home-renovation prompt.

## Semantic similarity and topic fit

Semantic similarity should be agent-adjudicated. Scripts may stage likely similar text, copied chains, token overlap, or embedding-style candidates, but they do not decide topic fit.

For each topic-fit concern, classify the relationship:

- **direct fit**: answers the prompt in the expected domain
- **adjacent fit**: related domain that may be valid after reading role and prompt context
- **wrong universe**: coherent answer, wrong survey audience or decision context
- **survey meta-answer**: describes the survey instead of answering it
- **generic filler**: plausible words with no usable respondent evidence
- **semantic drift**: starts on topic, then becomes incoherent or unrelated

Only wrong-universe, survey-meta, generic-filler, or semantic-drift findings should materially increase discard weight. Adjacent-fit findings should usually stay review-only unless the full chain contradicts qualification or role.

## Converging evidence

A strong discard recommendation usually blends multiple evidence families:

- semantically distinct straightlining plus implausible answer time
- fast completion plus weak or generic open ends
- duplicate technical evidence plus copied or similarly weak response chains
- role or qualification mismatch plus off-domain narratives
- survey-meta answers plus low-effort or inconsistent chains
- platform review flags plus agent-confirmed semantic weakness

Do not double-count the same fact. For example, one IP address appearing in many columns is not many independent signals. It becomes stronger only when multiple supposedly independent respondents share technical evidence and similar weak chains.

## Required agent output

For each important discovery, write:

- the candidate signal
- the semantic expansion performed
- the provisional weight and why
- the accepted-row guardrail
- the evidence that would raise or lower the weight in the next pass
- whether it should affect first-pass routing, final discard review, reporting only, or no future behavior

If the agent cannot explain the weight in plain language, keep the signal as review routing or reporting context.
