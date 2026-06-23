# Analyst Prose Standard

Use this reference before writing client-facing findings, positive insights, dashboard prose, or visual findings reports.

## Authorship rule

This is an agent authoring standard, not a script specification.

Scripts may collect counts, examples, citations, charts, and table rows. They may create a rough draft or placeholder when that helps the agent inspect the evidence. They are not the author of the final findings.

The agent must read the run artifacts, decide what the evidence means, and write the final prose. If a helper-generated paragraph sounds like a template, stitched fields, or a parameter dump, the agent must rewrite it or remove it before delivery.

Do not solve weak reporting by adding more phrase templates to scripts. Improve the instructions, then have the agent author the analysis from the evidence.

Script output should name itself as draft evidence when it contains generated prose. It should tell the agent what evidence exists and what must be explained. It should not pretend to be the finished client narrative.

The final analysis should answer these questions in prose:

1. What did we discover after mapping the fields and reading the full response chains?
2. Which patterns justify exclusion review, and which patterns only justify review or survey improvement?
3. Which rows are the best evidence for each recommendation?
4. What did the strong retained rows teach us about good participation?
5. What statistics change the interpretation, and what statistics are only routing context?
6. What should change in the next pass?

## What good looks like

The report should combine statistics with clear analyst writing. Counts should answer "how big is the pattern." Prose should answer "what does the pattern mean."

A strong paragraph has this shape:

1. State the finding in plain words.
2. Give the key statistic, count, rate, row key, field, or example.
3. Explain why it affects the quality decision or the next pass.
4. Cite the artifact that supports it.

Example:

> We found a large group of retained rows with weak narrative detail. This covered 1,148 reviewed rows, so it is too broad to use as an exclusion rule by itself. The next pass should add PM examples of acceptable and unacceptable answer depth before scoring this signal more harshly. Source: `agent_kept_review_synthesis_table.csv`.

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

## Required delivery gate

Before final delivery, search the Markdown and dashboard output for signs that parameterized text leaked into prose.

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
