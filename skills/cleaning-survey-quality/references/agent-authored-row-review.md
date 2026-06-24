# Agent-authored row review

Use this reference whenever Autosurvey makes row-level cleaning, authenticity, or validation decisions.

The purpose is to keep the system agentic. Scripts may prepare evidence. They may stitch chains, calculate timing, group duplicate text, find matrix patterns, and reconcile labels. They may not replace the agent's row judgment.

## Required row read

For every respondent, read the full response chain before the final tier is assigned. The chain should include the prompt context when available, structured answers, open ends, timing, routing, source, technical context, and any demographic or qualification context that affects the interpretation.

For each row, the agent must decide:

- what the respondent appears to be saying;
- whether the answer fits the prompt and the qualified respondent universe;
- which discovered signal families apply;
- which accepted-row guardrails protect the row;
- whether a benign explanation is stronger than the concern;
- whether the row should be accepted, reviewed, or escalated as Tier 5.

This judgment can be concise for ordinary accepted rows. It must still be authored. A row has not been reviewed if the output only repeats a score, rule name, or field value.

## Three perspectives

Use three perspectives on each row.

The forensic investigator asks what could be fabricated, automated, copied, off-domain, or inconsistent.

The human advocate asks how a real respondent could reasonably produce the same surface pattern. Protect concise answers, rough language, non-native English, ordinary enthusiasm, plain product phrases, and consistent but simple response chains.

The evidence judge decides the final tier after weighing both sides. The judge must explain why the evidence is enough, not enough, or inconclusive.

## Learned badopen boundary

Client markers such as `badopen` are training clues, not runtime fields. The transferable lesson is semantic.

A bad open end is not merely short. It is an answer that fails as respondent evidence after the full chain is read.

Common high-risk patterns include:

- polished abstract language with no lived detail;
- survey-summary language in place of a personal answer;
- a plausible topical sentence that could fit almost any respondent;
- generic marketing or research language that does not connect to prior answers;
- an answer that stays coherent but belongs to the wrong respondent universe;
- a response chain where open ends, closed answers, timing, and routing do not support one another.

Common protective patterns include:

- short answers that fit a simple prompt;
- plain product phrases that match the question's expected answer type;
- rough wording that still gives a concrete reason, use, role, or experience;
- concise survey-summary answers when the prompt asked what the survey was about;
- accepted controls that show the same surface pattern without authenticity concern.

## Output requirement

Every run must produce a row-level semantic judgment artifact, named `agent_row_semantic_judgments.csv` or `agent_row_semantic_judgments.jsonl`.

Each row should include:

- respondent key and source row;
- final tier and action;
- short chain citation, using field names and values;
- strongest concern;
- strongest protective evidence;
- forensic investigator note;
- human advocate note;
- evidence judge note;
- whether the row changes the next-pass signal bank.

The columns are a container. The writing inside them must come from reading the row. Do not fill them with pasted rule names or repeated template text.

## Calibration rule

For labeled methodology runs, freeze the blind row judgment before opening labels. After labels are revealed, write a separate contrast note for each row that says whether the client decision confirms, challenges, or teaches something different from the blind judgment.

For blank runtime runs, do not mention `status`, client labels, or hidden markers. Apply only the learned semantic questions to the current respondent chain.

## Delivery gate

Before final delivery, inspect the row judgment artifact directly.

Block completion if:

- the row count does not match the source respondent count;
- judgments mostly repeat the same sentence;
- the output only names rules, scores, or criteria;
- accepted rows do not include protective reasoning;
- Tier 5 rows do not explain why the full chain still fails after benign explanations were considered;
- post-unblind validation learning changed the method without being placed in a test-derived hypothesis backlog first.
