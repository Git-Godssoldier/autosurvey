# Analyst Prose Standard

Use this reference before writing client-facing findings, positive insights, dashboard prose, or visual findings reports.

## Authorship rule

This is an agent authoring standard, not a script specification.

Scripts may collect counts, examples, citations, charts, and table rows. They may create a rough draft or placeholder when that helps the agent inspect the evidence. They are not the author of the final findings.

The agent must read the run artifacts, decide what the evidence means, and write the final prose. If a helper-generated paragraph sounds like a template, stitched fields, or a parameter dump, the agent must rewrite it or remove it before delivery.

Every delivered artifact must be agent-authored in substance. This applies to the findings essay, positive findings report, escalation packet, internal signal bank, deep findings memo, visual findings report, dashboard prose, final assistant response, and any other file a PM or client might read. A file does not pass because it exists. It passes only when the agent has read the evidence, shaped the narrative, checked the citations, and rewritten any generated draft text that does not explain the run.

The row judgment layer must also be agent-authored. Scripts can assemble the row, chain, score, and candidate evidence. The agent must write the semantic judgment for each respondent. The judgment should say what the row means after the chain was read, not only which rule fired.

Do not solve weak reporting by adding more phrase templates to scripts. Improve the instructions, then have the agent author the analysis from the evidence.

Script output should name itself as draft evidence when it contains generated prose. It should tell the agent what evidence exists and what must be explained. It should not pretend to be the finished client narrative.

The final analysis should answer these questions in prose:

1. What did we discover after mapping the fields and reading the full response chains?
2. Which patterns justify exclusion review, and which patterns only justify review or survey improvement?
3. Which rows are the best evidence for each recommendation?
4. What did the strong retained rows teach us about good participation?
5. What statistics change the interpretation, and what statistics are only routing context?
6. What should change in the next pass?

For annotated fraud-signal training runs, the final analysis must also answer:

1. What did the rejected corpus teach us about likely client-removal and authenticity-risk signals?
2. What did the accepted corpus teach us as antisignals or protective human evidence?
3. Which signals have real lift, and which are too broad because they also appear in many accepted rows?
4. Which blind misses reveal new semantic signals?
5. Which apparent Tier 5 findings are false-exclude risks that need guardrails?
6. What detector upgrade should be used in the naive unannotated rerun?

## What good looks like

The report should combine statistics with clear analyst writing. Counts should answer "how big is the pattern." Prose should answer "what does the pattern mean."

A strong paragraph has this shape:

1. State the finding in plain words.
2. Give the key statistic, count, rate, row key, field, or example.
3. Explain why it affects the quality decision or the next pass.
4. Cite the artifact that supports it.

Example:

> We found a large group of retained rows with weak narrative detail. This covered 1,148 reviewed rows, so it is too broad to use as an exclusion rule by itself. The next pass should add PM examples of acceptable and unacceptable answer depth before scoring this signal more harshly. Source: `agent_kept_review_synthesis_table.csv`.

Annotated training example:

> We learned that answer-time and text coupling is a stronger training signal than speed alone. Rows with severe coupling had a higher status-5 rate than the labeled baseline, while ordinary timing flags also appeared in many accepted rows. The next unannotated pass should route fast polished narratives into agent review, but it should not exclude speed-only rows unless open-end grounding or another independent family also fails. Source: `authenticity_signal_family_lift.csv`.

## What to avoid

Do not expose raw implementation fields in prose.

Avoid:

- `best_score=50`
- `risk=role_calibration_needed`
- `narrative=topic_relevant`
- `keep_no_issue_from_independent_audit`
- `support_rate=0.103`
- raw criterion ids as the sentence subject
- long source column lists
- table headers pasted into body prose
- "This response chain is useful because it was retained as..."
- "status=5 proves fraud"
- "the model found fraud because the row was rejected"

Translate them.

- `best_score=50` becomes "this was one of the strongest retained chains."
- `risk=role_calibration_needed` becomes "the role context still needs PM calibration."
- `topic_relevant` becomes "the answer stayed on the survey topic."
- `keep_no_issue_from_independent_audit` becomes "the independent audit found no quality issue."
- `support_rate=0.103` becomes "the signal appeared in about 10% of responses."

## Statistics

Use statistics as evidence for interpretation, not as a substitute for interpretation.

Good statistics:

- counts and rates that show scale
- comparisons between first pass, final review, and client baseline
- row-count reconciliation
- top themes with clear next action
- supplier, fielding, or demographic context when it changes interpretation

Weak statistics:

- every generated criterion with every source column
- a rate without a denominator
- a raw field name without a plain-language label
- a large table with no paragraph explaining what to do with it

When a report includes a dense table, write a short analyst readout before the table. Say what the table proves, which rows or criteria matter most, and how the reviewer should use it. A table without this readout is unfinished work.

## Row examples

For retained rows, write why the answer is usable. Do not say only that a row was retained.

Good retained-row prose:

> `3ry7w6zbtq2vw60g` is a strong retained example because the respondent described a specific home project, explained the work done, and gave enough surrounding answers to show real engagement. The answer is polished, but it is not generic. It includes concrete work, timing, and outcome details. Source: `full_chain_best_worst_examples.csv`.

For discard rows, write why the full chain still fails after the benign explanation was considered.

Good discard-row prose:

> `n628rrzbjm9ecbya` should remain in the exclusion-review set because the main open end repeats an incoherent phrase and the rest of the chain does not recover a usable project narrative. The concern is not shortness. The concern is that the answer does not become meaningful when read with the full chain. Source: `agent_discard_set.csv`.

For training rows, separate label from interpretation.

Good training prose:

> The client rejected this row, but the training value is more specific than the label. The open-ended answer describes a software rollout in a contractor survey, so the transferable signal is wrong-universe professional language. The next pass should route similar role-domain mismatches into agent review, then compare them with accepted contractor rows that use office language but still give concrete trade context.

For every-row judgment artifacts, write concise but real judgments.

Good row judgment prose:

> The purchase-reason answer is short, but it answers the prompt with a concrete household concern about hard water. The final survey-summary answer is generic, yet accepted controls show that this prompt often receives short topic summaries. The row should be protected unless another independent family fails.

Bad row judgment prose:

> Rule open_generic fired. Score 0.98. Review candidate.

## Required delivery gate

Before final delivery, search the Markdown and dashboard output for signs that parameterized text leaked into prose.

Also inspect `agent_row_semantic_judgments.csv` or `.jsonl` when it exists. Block delivery if it reads like generated boilerplate or if accepted rows do not explain the protective human evidence.

Block delivery when client-facing prose contains:

- `best_score=`
- `risk=`
- `narrative=`
- `support_rate=`
- `keep_no_issue_from_independent_audit`
- `review_or_pm_calibration`
- raw Python, JSON, CSV, or TSV field dumps
- tables without a preceding analyst readout

Fix the prose by rewriting the section, not by hiding the field names in backticks or creating a more elaborate generated template.
