# Decipher blind authenticity review

Use this reference for normal Autosurvey runs on blank Decipher survey exports. A blank run means the respondent file has no client cleaning outcome label. It may still contain Decipher system fields, routing fields, quotas, timestamps, and helper fields. Do not treat any field as a client accept or reject label unless the user has explicitly provided an annotated training workbook.

The review operates in two stages: **fraud detection** (is the respondent authentic?) and **PM quality assessment** (does the respondent meet the quality bar for this survey?). Both stages use the learned signal questions below. A respondent can pass fraud detection but fail quality assessment — both result in DISCARD or REVIEW.

Annotated TFG workbooks are a development lab. They are used to discover signals, test false positives, and improve these instructions. They are not runtime inputs. A normal Autosurvey run should apply the learned signal questions below to the new dataset without using `status = 3`, `status = 5`, client flags, or hidden review outcomes.

## Runtime boundary

Keep these paths separate:

- **Methodology development**: use annotated TFG workbooks to learn what rejected rows have in common and what accepted rows protect. Write training artifacts in a calibration output folder.
- **Autosurvey runtime**: use only the blank Decipher export, Datamap, codebook, internal comments, prior signal bank, and prior natural-language signal instructions. Do not use client outcome labels.

If a blank export has a column named `status`, inspect the Datamap before using it. In Decipher exports, a status-like field may describe survey routing or completion state. It is not a TFG accept or reject label unless the source file is a cleaning-answer workbook.

Before scoring a blinded dataset, confirm that the methodology is frozen. The calibration folder should contain the frozen input manifest, blind-vs-label contrast, transferable signal specifications, control-match notes, and a statement that no stable new signal remains unresolved. If those artifacts are missing, continue methodology development and do not score the blinded file.

The learned methodology separates two ideas. Client rejection probability means a row resembles the client's labeled removals. Authenticity risk means the response chain suggests the respondent may not have answered faithfully as a qualified human. In a blank runtime pass, use both ideas as review questions, but do not claim that a client-like row is fraudulent unless the current full response chain provides independent evidence.

## What to build before scoring

Before any scoring or scripting, read the workbook and Datamap. Then author these materials in plain language:

- `question_set_authenticity_map.md`: every major question family, intended respondent universe, expected evidence type, valid short answers, fabricated-response risks, and accepted-row guardrails.
- `question_contract.md`: the survey's audience, role assumptions, routing prerequisites, timing burden, brand or product funnel, matrix logic, open-ended burden, and protective human evidence.
- `question_relation_graph.csv`: field relationships such as prerequisite, funnel progression, parallel, inverse, mutually exclusive, temporal, numerical, routing, and open or closed contradiction.
- `semantic_signal_expansion_notes.md`: how each raw signal was weighted after reading prompt context, timing context, response-chain context, and accepted-row guardrails.
- `agent_row_semantic_judgments.csv` or `.jsonl`: one agent-authored judgment per respondent after full-chain review.

These are authored review artifacts. Scripts may stage candidate fields and counts, but the agent must decide what the question set asks and what authentic response evidence should look like.

The row judgment artifact is not optional. It is where Autosurvey uses agent intelligence on every respondent rather than relying on a rigid checklist. A large dataset can use concise row judgments, but every judgment must reflect the row's chain, not only a rule name.

## Learned signal questions for any Decipher survey

Ask these questions on every blank dataset. Adapt them to the Datamap and the respondent universe. Do not use them as fixed keyword rules.

1. **Respondent universe fit**
   Does the respondent's role, trade, product experience, location, or eligibility claim match the survey audience? A coherent answer can still be suspicious if it belongs to the wrong universe.

2. **Role and qualification chain**
   Do role screeners, qualification fields, brand or product experience, and open-ended explanations agree? Watch for vague executive roles, generic procurement language, personal-home examples in a professional survey, or professional-sounding answers that never prove the claimed role.

3. **Question-time elasticity**
   Does time increase when the question burden increases? Matrix grids, long recall questions, ranking tasks, allocation tasks, and narrative open ends should usually take more time than simple single-choice questions. Uniform speed across simple and complex work is more suspicious than ordinary fast completion.

4. **Answer-time and text coupling**
   Does the amount and polish of text fit the time available? Long, detailed, highly polished, or pasted-looking answers produced in very little time should route to review. Short answers produced quickly are not enough by themselves.

5. **Open-end grounding**
   Does each open end refer to the respondent's own selections, role, brand use, product experience, location, time period, or prior answers? Generic praise, generic business language, or answers that could fit any survey are weak evidence of authentic responding.

   Learned guardrail: short, plain, or generic-looking answers can be acceptable when the prompt asks for a simple topic, product, or survey summary. Learned risk: polished topical prose can be weak when it does not show personal grounding or chain support.

6. **Prompt-fit and answer burden**
   Did the respondent answer the type of evidence requested? A prompt asking for a place, brand, simple object, or short factor can accept a short answer. A prompt asking for an experience, use case, trade role, explanation, or reason needs more grounded detail.

7. **Wrong-domain coherence**
   Is the answer coherent but off-domain? Examples include IT or office-management claims inside contractor studies, personal shopping examples inside professional purchase studies, or general construction prose that never ties to the respondent's own trade.

8. **Brand or product funnel plausibility**
   Do awareness, familiarity, use, consideration, preference, recommendation, purchase, satisfaction, and open-ended rationale form a plausible chain? Treat impossible or unexplained jumps as review evidence. Check brand name quality in OE fields. Compare real brands against garbled or wrong-universe brands. Check share allocation plausibility. Equal share to all brands or many zero allocations are quality concerns. Brand funnel fields were the strongest raw predictors in ECHO and should be read before final disposition.

9. **Content-aware straightlining**
   Are repeated answers occurring across similar items or across questions that should differ? Straightlining across substantively similar questions may be a real opinion. Straightlining across opposed, unrelated, reverse-coded, or high-burden items is stronger evidence, especially when timing and open ends are weak.

10. **Survey-structure coherence**
    Does the respondent's classification match their answer pattern? Professional respondents should show professional purchasing patterns, such as dealer channels, commercial equipment, or professional volume. A pro who answers like a consumer is a quality concern. Check channel conditions. A respondent in a channel condition should usually show some matching brand or dealer logic. Check pro and consumer branch fields before judging the answer.

11. **Substantive engagement**
    Does the core open-end demonstrate substantive engagement with the survey's specific topic? An answer like "Mowing and blowing" is on-topic for an outdoor power equipment survey but thin. V7 learned that thin-on-topic should not fire the core open-end quality family by itself. Treat it as REVIEW only when another concern exists. Promote it to DISCARD only when ML is strong or independent evidence families converge.

12. **Cross-respondent synthetic clustering**
   Do multiple supposedly independent respondents share rare phrases, open-end templates, response vectors, timing vectors, matrix patterns, or burst timing? Similar technical context alone is not enough. Similar response chains make the signal stronger.

13. **Duplicate technical context**
   Shared IP, device, supplier, session, or fielding burst is context, not proof. It becomes stronger when the same group also shares weak open ends, rare phrasing, identical matrices, impossible routing, or timing patterns.

14. **Full-chain nonresponse and route integrity**
   Resolve skip logic before treating blanks as bad. Look for missing prerequisites, downstream answers after a "never" response, unexplained section omission, default-value chains, populated fields that should have been skipped, and export defects.

15. **Survey-meta substitution**
   Did the respondent answer the survey process instead of the prompt? Feedback about the survey, idea, or questionnaire should be classified separately from substantive answers.

16. **AI-assistance concern**
   Polished prose, formal wording, low typo rate, or em dashes are weak cues only. They matter when paired with genericity, wrong universe, implausible answer-time coupling, copied templates, or chain contradiction.

17. **Human protective evidence**
   Give credit for grounded details, ordinary self-corrections, rough but coherent wording, non-native English, valid short answers, legitimate extreme opinions, plausible "don't know" behavior, and consistent role or brand chains.

## Weighting standard

Do not count correlated checks as independent proof. Aggregate evidence into families first:

- timing and time elasticity
- answer-time and text coupling
- open-end grounding and prompt fit
- respondent-universe and qualification fit
- brand or product funnel consistency
- matrix behavior
- cross-respondent clustering
- duplicate technical context
- route integrity and nonresponse
- AI-assistance concern
- protective human evidence

Move a row toward exclusion review only when independent families converge and the full response chain does not provide a benign explanation. Keep single-family concerns as review routing unless the evidence is severe and directly tied to a required high-value response.

## V7 disposition standard

Use the calibrated V7 rules unless a newer sealed benchmark has replaced them.

- DISCARD when ML is at least 0.8.
- DISCARD when ML is at least 0.6 and at least one independent evidence family also fires.
- DISCARD when at least 4 independent evidence families fire.
- DISCARD when certain platform fraud appears, such as qc 8, qc 9, non-English in a US survey, or TERMFLAGS without strong human counterevidence.
- REVIEW when 2 or 3 families fire.
- REVIEW when Stage 2 quality fails but ML is below 0.6 and fewer than 4 families fire.
- REVIEW when badopen severity is high but convergence is weak.
- KEEP or REVIEW thin-on-topic answers based on the rest of the chain. Do not discard them for shortness alone.

The successful V7 pattern improved ECHO precision to 0.664, recall to 0.524, F1 to 0.586, and balanced accuracy to 0.690. Preserve those guardrails before adding broader recall rules.

## Output expectation

For a blank Decipher run, the final report should not discuss `status = 3` or `status = 5`. It should say which learned signal questions were applied, which evidence families surfaced rows, which rows remain Tier 5 after full-chain review, which suspicious rows were protected, and what the next first-pass context should learn.

When a blank run uses a lesson discovered from annotated data, state it as a general detection question. Do not cite the annotated workbook as if it were part of the new run's evidence. The annotated data explains why the method exists. The current blank workbook provides the evidence for current row decisions.
