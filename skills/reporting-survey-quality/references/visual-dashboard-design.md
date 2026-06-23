# Visual Dashboard Design

Final survey-quality artifacts should feel like a compact research publication, not a raw script output. The reference direction is open-design-style craft applied to a CBRE-quality figures report: disciplined hierarchy, high information density, confident whitespace, clear figure numbering, strong source notes, and charts that a reviewer can trust without reopening the CSV.

## Design Principles

- Start with a publication header: uppercase metadata line, concise report title, one-sentence deck, run/source note, and a restrained brand accent.
- Use KPI cards for the decision funnel: total responses, review-tagged rows, agent discard rows, and kept review rows.
- Use figure captions in the format `Figure N: Plain-English Chart Name`.
- Add source notes below every chart. State whether the chart comes from scoring artifacts, second-pass disposition, or final agent judgment artifacts.
- Use a restrained palette with a strong dark text color, a deep green or charcoal anchor, one mint/teal accent, and one or two secondary colors. Do not make the page a single-hue gradient theme.
- Keep tables dense but readable: small uppercase headers, clear row rules, top-aligned cells, and only the columns needed for adjudication.
- Use narrative callouts sparingly for the main policy: early scoring finds candidates; full-chain semantic review makes final discard judgments; kept review rows become survey-improvement guidance.
- Treat tables as ledgers, not prose containers. Do not put long semantic judgments, trust rationales, or response-chain text into narrow table cells.
- Add an agent findings essay section from `agent_findings_essay.md`. This section is required for delivery and should read like a senior analyst wrote it after studying the run.
- Add a positive findings section from `agent_positive_insights_report.md`. It should explain strong retained response chains, useful research findings, false-positive guardrails, and what the next pass should learn from good data. Display it as readable prose, not as a cramped table.
- Add a concise terminology note when the dashboard uses client-specific shorthand, PM terms, quality terms, or field names that are not self-explanatory. Use the glossary in `../../cleaning-survey-quality/references/client-terminology-glossary.md`.
- Link `agent_escalation_packet.md` and `internal_quality_signal_bank.md` in the artifact index. Summarize them in prose when they change the final decision. Do not turn internal learning into client-facing accusation language.
- Use row examples only when they help the narrative. They should read as human prose that explains what the full chain means, why the row stayed or was discarded, and what the next pass learns. Do not force them into a fixed annotation schema.
- Never show a raw stitched response chain in the dashboard body. Show a short chain readout and link to the audit artifacts for the full chain.
- Do not put long reasoning into narrow table cells. If a table needs identifiers and decisions, keep it compact. Put the actual explanation in prose blocks, row memos, or linked Markdown artifacts.
- If the run corrected a first-pass assumption, such as a missing field-role map or incomplete topic map, include a clear narrative note about the correction and the next-pass lesson.
- End with an artifact index so reviewers can move from the dashboard to the CSV and Markdown evidence.
- For reruns and workflow-hardening cycles, show the terminal state and next action in a short workflow note. Do not expose internal activity logs. Link the workflow improvement log when it exists.

## Required Visualizations

Use Recharts in HTML dashboards when React is available:

- Action counts: `BarChart` with total row counts.
- Second-pass disposition: `BarChart` showing `discard_candidate`, `keep_with_recommendation`, and `keep_no_issue`.
- Agent review decisions: `PieChart` or donut chart showing final agent discard versus keep-with-review-note decisions.
- Kept review themes: horizontal `BarChart` so long theme names remain readable.
- Supplier/source concentrations: horizontal `BarChart` limited to the highest-count sources, with a note that supplier concentration is directional context and not proof.
- Trend analysis: `ComposedChart` with total response volume and review/discard lines by fielding date.
- Candidate clusters: `ScatterChart` that plots review candidates by completion time and generated score. Color points by final agent decision.
- Supplier decision mix: stacked `BarChart` with kept review rows and agent discard rows by supplier/source.
- Full semantic decision table: one compact ledger row for every candidate the agent investigated. Include identifiers, final decision, theme, counts, score, and next action. Move long semantic judgment, language quality, trust rationale, and response-chain interpretation into row cards or Markdown artifacts.
- Discovery and criteria tables: show new analyses, candidate fields, generated criteria, support, weight, decision role, and citation.
- Dataset observations: include a list of plain-language findings about semantic patterns, trend patterns, supplier/source patterns, and survey improvements.
- Every dense criteria or discovery table must have a short analyst readout before it. The readout should say what the table proves, what changed the review, and which criteria or fields need action.

Wrap charts in `ResponsiveContainer` and include `Tooltip`, axis labels where useful, and `Legend` for donut charts. Avoid chart decorations that do not help the reviewer make a cleaning decision.

## Writing Style

- Dashboard prose must come from agent-authored Markdown artifacts or from a manual rewrite after reading those artifacts. Generated blocks are placeholders until reviewed.
- Use concise research-report language: `Finding`, `Decision Rule`, `Design Implication`, `Source`.
- Lead with the decision, then explain the evidence. Do not make readers infer meaning from scores alone.
- For discard rows, write an expert judgment memo: semantic pattern, language quality, source evidence, benign alternative considered, and final recommended action.
- For kept review rows, explain why the row survived and what question design or fielding parameter should improve.
- For dashboard editorial prose, write in complete analysis paragraphs. Do not stitch together field values or populate a rigid template. State what the agent saw, what it means, why the conclusion is trustworthy, and what should happen next.
- Keep templates in the minority. The dashboard must have stable sections and verified artifacts, but the prose should be written from the run evidence rather than assembled from static fields.
- Do not expose raw parameter strings in prose. Translate model labels, status values, support rates, and source-column lists into readable findings.
- Never let keyword mismatch, AI-likelihood, or supplier/source concentration read as a final semantic decision.
- Use plain writing. Prefer common words. Use complete sentences. Remove filler. Avoid jargon unless you explain it. Do not hide the decision behind phrases such as "may indicate" when the agent has made a final judgment.
- Cite every material claim. Counts should cite local tables. Criteria should cite the generated criteria catalog or criterion evidence table. Agent decisions should cite the agent judgment table. Design and writing choices should cite the design and writing references.

## Quality Gate

Before delivery, verify that the dashboard:

- renders the KPI cards, all required charts, discard table, full semantic decision table, kept synthesis table, and artifact index
- includes discovery, expanded scorer criteria, response analysis criteria, dataset observations, and a citation table
- remains readable at desktop and mobile widths
- contains no overlapping text, one-character column wrapping, or prose squeezed into narrow table cells
- contains no unresolved placeholders, template notes, lorem text, repeated boilerplate, or row cards that only concatenate field values
- contains no raw parameter phrases such as `best_score=`, `risk=`, `narrative=`, `support_rate=`, or unconverted internal status labels in client-facing prose
- includes `agent_findings_essay.md` prose, or clearly blocks delivery until the agent writes it
- includes `agent_positive_insights_report.md` prose, or clearly blocks delivery until the agent writes it
- links the escalation packet and internal signal bank when they exist
- does not require PMs to reopen CSV files to understand the main findings
- clearly marks final discard decisions as agent-generated semantic judgments
- preserves source artifacts rather than mutating evidence files
- states whether the final package is success, clean no-op, blocked, approval required, or no-progress stop when the run is part of an iterative cycle
