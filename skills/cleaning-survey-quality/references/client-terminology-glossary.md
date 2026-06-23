# Client Terminology Glossary

Use this glossary before writing PM-facing or client-facing survey-quality artifacts. It explains recurring terms in plain language so future runs do not assume that a new reviewer already knows Opulent, TFG, PM, or Decipher shorthand.

Adapt these definitions to the actual workbook, Datamap, and client annotations in the run. Do not invent study-specific meaning. If a term is ambiguous, define it from the local evidence or say that it needs PM confirmation.

## Core roles

- **Client-facing**: Safe to share outside the internal review team. It should avoid raw respondent text unless approved and should explain decisions in plain language.
- **PM**: The project manager or project review owner who makes or approves final operational calls.
- **Data Quality Lead**: The person accountable for respondent-quality decisions and escalation standards.
- **Reviewer**: The person reading the final artifacts to decide whether to accept, keep, or remove rows.

## Source materials

- **Source workbook**: The raw survey export or client-provided workbook being reviewed.
- **Datamap**: The sheet or file that maps field names to question text, answer codes, value labels, and field groups. This is the first source for field-role mapping when present.
- **Codebook**: A Datamap-like reference that explains survey variables and answer options.
- **Client annotations**: Notes, helper columns, comments, or marked examples from the client or prior reviewer. They are calibration evidence, not automatic proof.
- **Internal comments**: Opulent, PM, or team notes about what to watch for. They become hypotheses until the response chain proves or weakens them.

## Respondent and field terms

- **Respondent row**: One completed survey response in the source workbook.
- **Respondent key**: The stable identifier used to cite a respondent, such as `uuid`, `record`, `RID`, or another ID field.
- **Field role**: The purpose of a column. Common roles include narrative open end, brand list, matrix grid, demographic field, supplier/source field, timing field, respondent identifier, IP/device field, review helper, and qualification field.
- **Question chain**: The ordered set of prompts from the Datamap or source columns.
- **Full response chain**: All nonempty answers from one respondent, stitched with prompt context where available.
- **Focused semantic chain**: The subset of the full response chain around fields most relevant to quality review. In one study this may include `qcoe1`, `q9`, `q10`, `q32`, `q43`, or `outro`; in another study it may be a different set discovered from the Datamap.
- **Narrative open end**: A free-text field where the respondent explains an experience, reason, priority, or opinion.
- **Other-specify field**: A free-text answer attached to an "Other" choice. It may be valid even when short.
- **Survey-feedback field**: Text that comments on the survey, idea, or experience of taking the survey rather than answering the project topic.
- **Demographic field**: A respondent profile field such as `qGender`, `qager1`, `age`, `qEthnic*`, `qEd`, `qStateVer`, `qEmploy`, `qUSHHI`, `q44`, `q45`, or `qPolitics`. Demographics are interpretation context, not row-level quality evidence by themselves.

## Evidence and signal terms

- **First-pass scoring**: The early deterministic or generated pass that routes rows for review. It is the case file, not the final decision.
- **Criterion**: A generated quality rule or observation, such as speeding, straightlining, weak open end, duplicate technical signal, or possible topic mismatch.
- **Review-only signal**: Evidence that should route a row for human or agent review but cannot justify discard by itself.
- **False-positive guardrail**: A rule or lesson that protects valid rows from over-review or over-discard, such as short valid brand answers or enthusiastic repeated characters.
- **Counterevidence**: Context in the full response chain that weakens a discard concern.
- **Converging evidence**: Two or more independent signals that support the same quality concern.
- **Duplicate technical signal**: Shared IP, device, session, or similar technical evidence. It is context by itself and becomes stronger only when paired with shared weak response patterns or other quality concerns.
- **qtime**: Completion time or survey duration. Fast completion is usually review routing unless the response chain also has weak, contradictory, or nonresponsive answers.
- **Straightlining**: Repeated or nearly repeated answers across a grid or matrix. It may be real opinion or low attention depending on the prompt and chain.
- **Topic mismatch**: A possible gap between answer text and the project topic. Keyword mismatch is only review routing until semantic relevance is confirmed from the Datamap and response chain.
- **AI-likelihood**: A helper or model signal that text may be AI-assisted. It must not be treated as fraud proof by itself.

## Decision terms

- **Discard candidate**: A row recommended for exclusion review because full-chain review found enough evidence to consider removing it.
- **Keep with review note**: A row with some concern, but enough context or counterevidence to keep it while preserving the lesson.
- **Keep no issue**: A row with no meaningful quality concern after review.
- **Inconclusive**: A row that cannot be decided from available evidence. Treat it as keep with review note unless approved project rules say otherwise.
- **PM calibration**: Examples that should be discussed with the PM before becoming automated or first-pass rules.
- **Semantic discard basis**: The plain-language reason a row remains a discard candidate after the full response chain and counterevidence were reviewed.
- **Trust rationale**: The explanation of why the recommendation is defensible from the source evidence.

## Learning terms

- **Signal bank**: Internal learning that preserves useful criteria, comments, guardrails, bad-response patterns, and next-run lessons.
- **Next-pass signal inventory**: The list of signals to promote, demote, keep review-only, or test in the next first-pass scoring run.
- **Kept-review synthesis**: The analysis of suspicious rows that were retained, including what the survey or quality parameters should learn from them.
- **Positive insights report**: The companion report that explains strong retained responses, useful research findings, and what good data looks like in the run.
- **Decision trail**: A short audit log of non-obvious choices, with evidence pointers rather than long prose.
