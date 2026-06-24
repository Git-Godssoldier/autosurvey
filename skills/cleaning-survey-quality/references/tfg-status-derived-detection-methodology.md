# TFG status-derived detection methodology

Use this reference when the task involves TFG respondent cleaning, fabricated-response detection, bot suspicion, LLM-assisted response suspicion, or status-labeled calibration.

The client-provided training files define observed client outcomes for methodology development:

- `status = 3` means TFG accepted the respondent.
- `status = 5` means TFG rejected the respondent because of quality or authenticity concerns.

The purpose of these labels is not to memorize status or treat rejection as fraud proof. The purpose is to build a detection methodology that transfers to blank Decipher datasets.

Robin's note supersedes the earlier annotation assumption: the original datasets in the current package are annotated through `status = 3` and `status = 5`, subject to inventory verification. The additional HIRI Quarterly test dataset is blinded and must remain blinded.

Always separate client rejection probability from fabrication or authenticity risk. A rejected row may reflect a bot-like respondent, an inattentive human, an unqualified respondent, a routing problem, a client-only exclusion rule, or ordinary quality concern. Do not call a row fraudulent only because `status = 5`.

## Skill design principle

Use high-freedom agent judgment for semantic detection. Scripts can stage ledgers, counts, packet indexes, and candidate evidence. They must not be treated as the author of the fraud or authenticity judgment.

The skill should tell the agent what excellent analysis must do:

- understand the respondent universe
- understand each question set
- compare each answer to the prompt's requested evidence type
- expand every raw signal before weighting it
- read accepted and rejected chains as calibration examples
- write the detection method in plain language with citations
- transfer the learned questions to unannotated datasets without needing status labels

Do not turn the status learning into a rigid fill-in form. Required artifacts are fixed so the work can be audited. The analysis inside them must be written from the evidence in the current dataset.

## Required learning loop

1. Run a blind semantic pass on every labeled row.

Hide `status`, client flags, helper labels, and final-review fields. Assign a five-tier recommendation from the full chain, Question Contract, relation graph, timing, matrix behavior, brand funnel, open ends, duplication, routing, and protective human evidence.

2. Run a label-aware contrastive pass.

Reveal `status`. Compare the blind tier to the client decision. Learn what the blind pass missed, what protected accepted rows, and which client removals are not true authenticity or fabrication signals.

3. Read every `status = 5` row.

Derive the actual authenticity pattern for each rejected respondent. If a row has no script-staged rule, mark it as a semantic-discovery row and read the full response chain closely.

4. Read every `status = 3` row.

Derive accepted-row guardrails. These rows show what real respondents can look like even when they are fast, short, repetitive, polished, rough, or unusual.

5. Compare both sides before promoting a signal.

A signal can move into unannotated scoring only after it has been checked against accepted-row counterexamples.

6. Use labels to learn rules, then remove labels.

The blinded and future unannotated datasets must be scored without `status`. The transferred method is the combination of field-role mapping, first-pass routing signals, full-chain semantic review, and accepted-row guardrails.

## Question-set authenticity map

Before scoring semantic quality, examine all question sets in the workbook. Use the Datamap or codebook when present. If there is no Datamap, infer the question set from source column order, labels, value names, and representative responses.

Write an agent-authored `question_set_authenticity_map.md`. It should cover every major survey section, including screeners, role or qualification questions, brand and product lists, matrices, allocation tasks, use-case prompts, other-specify fields, narrative open ends, final feedback, demographics, timing, supplier fields, and technical identifiers.

For each question set, write:

- the intended respondent universe
- the field role and why it matters
- what kind of answer the prompt requests
- what a real qualified respondent might reasonably say, including short valid answers
- what a fabricated, bot-like, LLM-assisted, inattentive, or unqualified answer might look like
- which accepted-row guardrails prevent over-flagging
- which fields should influence first-pass routing, final discard review, reporting context, or no quality decision

This map is the bridge from TFG labels to new datasets. It forces the agent to ask the right semantic questions before applying any score.

Also write a Question Contract and question-relation graph. The graph should classify connected fields as parallel, inverse, prerequisite, funnel progression, mutually exclusive, temporal, numerical, routing, or open/closed contradiction. Brand and product funnels must connect awareness, familiarity, use, consideration, preference, recommendation, satisfaction, purchase, and open-ended explanations before consistency scoring.

## Semantic reading questions

Before reading, translate each question-answer pair into a first-person proposition (see `progressive-chain-filtering.md`). Then read the full self-claim profile as a narrative and ask:

Use these as questions to ask while reading, not as keyword rules:

- Does the answer sound like the qualified audience for this survey, or like a homeowner, consumer, student, generic office worker, logistics manager, IT manager, or survey observer from a different universe?
- Does the answer provide the kind of evidence the prompt asked for, such as a personal reason, lived project example, brand list, location, factor, use case, allocation, or feedback?
- Is the answer polished but empty, with abstract business benefits and no role, project, material, customer, supplier, constraint, location, or decision detail?
- Is the answer describing the survey itself instead of answering as the respondent?
- Does the chain use personal-home or consumer examples where the survey expects professional trade or contractor experience?
- Does a coherent answer belong to the wrong domain even though the grammar is fine?
- Does the language drift from a plausible start into unrelated phrase chains?
- Is a bare list acceptable for this question, or did the prompt require an explanation or concrete use case?
- Does timing, straightlining, duplicate technical evidence, or platform review evidence converge with weak semantic authenticity?
- If a grid repeats answers, were the questions semantically similar or genuinely different?
- If the respondent was fast, was the speed implausible for the actual page, section, question mix, and answer chain?
- What accepted rows look similar, and what makes them acceptable?

The best discard decisions answer these questions in prose. They should show why the row is unauthentic in context, not merely why a rule fired.

## Transferable rule families

### Question-time elasticity

A respondent should usually spend more time on complex questions, large matrices, long open ends, conflict-heavy tasks, calculations, and recall-heavy questions than on simple categorical items. Nearly identical latency across simple and difficult question sets can be more suspicious than ordinary speed. Use total qtime only as a fallback when page, section, or question timing is absent.

### Timing

Very fast completion under 4 minutes is a review-routing signal. It is not a final discard reason by itself. Escalate only when the response chain is also weak, contradictory, copied, generic, or otherwise unauthentic.

Fast completion from 4 to 5 minutes is context. It should make the agent read the row more carefully, not discard the row automatically.

When page, section, or question answer time exists, use it. A short total qtime is less informative than knowing which question sets were rushed. A row becomes more concerning when semantically important open ends, role questions, or dissimilar grids were answered too quickly to be credible.

### Platform quality helpers

Fields such as `TERMFLAGS`, `SCRUTINYFLAGS`, and Research Defender review fields can be strong routing evidence. They are not final proof. Confirm the field meaning from the Datamap or export, then inspect the respondent chain.

### Required open ends

Direct placeholders such as "none," "idk," "not sure," and "no comment" can support discard when the prompt required a substantive answer and the full chain does not recover context.

Very short answers are weaker. Short brands, products, locations, roles, and factor lists can be valid when the prompt asks for that type of answer.

### Duplicated text

Copied or repeated open-end text can support discard when it appears in substantive text fields and converges with other weak signals. Do not count supplier names, URLs, panel metadata, or other technical fields as copied respondent text. Common short phrases can repeat naturally.

### Survey feedback in substantive fields

An answer that comments on the survey rather than answering the prompt is review routing. Escalate only when the field required a substantive answer and the full chain shows the respondent repeatedly avoids the topic.

### Matrix behavior

Near-straightlining is review routing. Uniform ratings can be a real opinion, especially in conjoint, brand, or satisfaction batteries. Escalate only when straightlining converges with weak open ends, speed, contradiction, or platform evidence.

Before weighting straightlining, compare the grid items semantically. Repeated answers across very similar statements may be a valid uniform view. Repeated answers across distinct, contrast, or reverse-coded items carry more weight, especially when answer-time evidence suggests the respondent did not read the items.

Use content-aware straightlining: modal proportion, longest run, entropy, response variability, transitions, cyclic patterns, matrix time per cell, reverse-coded contradictions, and differentiation across brands. Aggregate these as one evidence family.

### Answer-time and text coupling

Long, detailed, highly polished, or pasted-looking text produced in implausibly little time is stronger than speed or polish alone. Abrupt style changes across open ends can be a routing signal, especially when timing suggests paste-like production. A short answer produced quickly is not equivalent evidence.

### Cross-respondent synthetic clustering

Compare respondents across the sample for near-duplicate open ends, repeated rhetorical templates, shared rare phrases, matching response vectors, matching timing vectors, identical matrix patterns, and burst submissions. Open-ended responses are often more revealing across the sample than in isolation.

### Full-chain nonresponse and route integrity

Resolve skip logic before treating blanks as suspicious. Detect missing prerequisites, populated downstream answers after "never," unexplained section omission, default-value chains, and export defects separately.

### Numeric allocation patterns

Repeated round allocations across unrelated fields can be context for low attention. Treat this carefully because some survey tasks naturally ask for round allocations that sum to a total.

### AI-like or over-polished prose

Generic polished prose can be a fabricated-response signal when it lacks lived detail, ignores the prompt, or converges with timing, duplication, contradiction, or weak chain evidence. Fluent writing alone is not a discard reason.

Semantic fit matters more than topic keywords. Adjacent domain language can be valid when it answers the prompt. For example, construction language may fit a home-renovation question when it describes renovation work, contractors, materials, permits, costs, or homeowner decision-making. It becomes suspicious when the response shifts into unrelated commercial construction, generic project management, or abstract business language without lived respondent detail.

AI-assistance concern must remain weak supporting evidence unless it converges with independent authenticity problems. Em dashes, polished prose, formality, low typo rates, or generic fluency do not independently justify exclusion.

### Hostile or nonsense text

Hostile, nonsense, or keyboard-mash text in a substantive field can support discard when the answer cannot be read as meaningful in context.

### Pasted text

Pasted-text helper flags route rows for review. They need semantic confirmation. Pasting can be benign if a respondent drafted elsewhere or copied a real business answer.

## Semantic-only rules from rejected rows with no parser signal

The rejected-row backlog showed several status-5 rows that had no obvious timing, platform, duplicate, placeholder, or straightline signal. These rows are the reason autosurvey must do full semantic reading.

### Abstract business solution without lived detail

Several rejected rows answered with plausible business language, e.g. centralized platforms, reduced delays, coordination, milestones, or procurement efficiency, but did not sound like a specific respondent describing their own work. On unannotated datasets, this should route to semantic review when an open end asks for a lived experience, operational pain point, or concrete example and the answer stays at the level of generic business optimization.

Guardrail: Some real respondents speak in business terms. Keep the row when the full chain has concrete role, project, tool, supplier, location, or decision detail.

### Survey meta-analysis instead of respondent answer

Some rejected rows answered by describing what the poll or survey measured, rather than giving the respondent's own view. These include phrases about the poll identifying gaps, examining feature inputs, or explaining the study topic. On unannotated datasets, classify this separately from ordinary off-topic text. It is a strong fabricated-response or low-engagement signal when the prompt asked for a personal reason, experience, or preference.

Guardrail: Some outro questions may ask for survey feedback. Confirm the prompt role before escalating.

### Role or qualification mismatch

Some rejected rows sounded like a homeowner, consumer, student, generic office worker, logistics manager, or IT manager answering a contractor or trade-professional survey. The words can be fluent, but the claimed experience does not fit the qualified audience. On unannotated datasets, compare open ends against the role, industry, trade, purchase authority, and project-involvement fields before deciding authenticity.

Guardrail: A qualified contractor can also discuss personal projects. Keep the row when the full chain proves professional role fit.

### Personal-home project substituted for professional project

In contractor and building-material datasets, rejected rows often described personal kitchens, living rooms, garden beds, decor, home office upgrades, appliances, or household accents when the survey expected trade, contractor, dealer, or professional building context. This should become a semantic review rule, not a keyword rule.

Guardrail: If the survey explicitly allows homeowner or DIY respondents, this is not a discard signal.

### Fluent but generic project claim

Some rejected rows used polished project language, such as a custom home, renovation delivered under deadlines, or a high-quality result, but gave no credible process detail. The issue is not polish. The issue is missing lived specificity after a prompt that invites a concrete example.

Guardrail: Polished writing is acceptable when it includes specific materials, decisions, constraints, trade role, timeline, tools, suppliers, or customer context.

### Sentence drift and incoherent phrase chaining

Some rejected rows contained phrase chains that begin plausibly and then drift into incoherence, e.g. fragments about phones, doors, wind, vaccines, cats, or unrelated customer service. On unannotated datasets, these should route directly to discard review when the full chain cannot recover meaning.

Guardrail: Rough grammar or a typo is not enough. The issue is that the response cannot be interpreted as a meaningful answer.

### List answer where the prompt required a use case

Some rejected rows answered with bare lists of places or objects when the prompt asked for a use case, experience, or explanation. This is most visible in product-use prompts such as padlock locations. On unannotated datasets, inspect the prompt role before escalating.

Guardrail: Lists are valid when the prompt asks for locations, brands, products, or factors.

### Off-domain professional claim

Some rejected rows described logistics programs, global IT overhauls, generic productivity tools, or other professional claims that did not fit the survey's qualified domain. This is stronger than topic mismatch because the answer may be coherent but belongs to the wrong respondent universe.

Guardrail: Do not use this signal until field-role mapping has identified the intended respondent universe.

## Ten-times-better-than-Farnsworth standard

The client annotation work is the baseline, not the destination. Autosurvey should exceed it by doing work a spreadsheet flag cannot do:

- reconstruct the question chain and full response chain before judgment
- explain the intended respondent universe for each question set
- compare rejected rows with accepted counterexamples before promoting a signal
- find semantic-only failures where no scripted rule fired
- protect valid short, rough, enthusiastic, or unusual answers when the prompt allows them
- distinguish poor writing from fabricated, bot-like, LLM-assisted, unqualified, or inattentive responding
- produce prose that a PM can read without reverse-engineering flags, parameters, or scoring fields
- carry every durable learning into the next unannotated pass as a detection question, guardrail, or routing signal

If the output only reproduces counts, flags, and field values, it has not met this standard.

## Required artifacts

For status-labeled calibration, produce:

- `blind_authenticity_review_table.csv`: every labeled respondent reviewed with status and client flags hidden.
- `label_aware_contrast_table.csv`: blind tier, status, disagreement type, learned signal, and protective evidence.
- `question_contract.md`: respondent universe, expected answer types, timing burden, relation graph summary, and protective evidence.
- `question_relation_graph.csv`: field relationships and contradiction/guardrail logic.
- `question_set_authenticity_map.md`: agent-authored map of question sets, expected evidence types, authenticity risks, and accepted-row guardrails.
- `authenticity_signal_family_lift.csv`: family-level lift against status labels and accepted-row false-positive exposure.
- `protective_human_evidence.md`: accepted-row guardrails with cited examples.
- `tfg_rejected_row_rule_ledger.csv`: every `status = 5` row, every staged rule that fired, evidence snippets, and open-end excerpts.
- `tfg_rejected_semantic_discovery_backlog.csv`: every `status = 5` row where no staged rule fired. These rows require semantic reading because they reveal what the parser still cannot see.
- `tfg_accepted_guardrail_ledger.csv`: every `status = 3` row that fired a staged rule, so false-positive guardrails are visible.
- `tfg_discard_rule_evidence.csv`: rule performance by dataset, including accepted counterexamples.
- `tfg_discard_signal_rulebook.md`: the transferable rulebook.
- `semantic_review_packets/`: chunked full-chain packets for literal row reading.
- `semantic_packet_notes/`: agent-authored notes after reading packets.

## Promotion standard

Before a rule changes unannotated scoring, the agent must answer:

- Which rejected rows does this rule explain?
- Which accepted rows look similar?
- What makes the rejected rows different from the accepted counterexamples?
- What semantic expansion changed the weight of the raw signal?
- Is this row-level evidence or wave-level context?
- Should this affect first-pass routing, final discard escalation, reporting only, or no future behavior?

If the answer is not clear, keep the signal as review routing or semantic-discovery backlog.
