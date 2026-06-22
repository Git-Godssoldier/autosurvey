# Visual Dashboard Design

Final survey-quality artifacts should feel like a compact research publication, not a raw script output. The reference direction is open-design-style craft applied to a CBRE-quality figures report: disciplined hierarchy, high information density, confident whitespace, clear figure numbering, strong source notes, and charts that a reviewer can trust without reopening the CSV.

## Design Principles

- Start with a publication header: uppercase metadata line, concise report title, one-sentence deck, run/source note, and a restrained brand accent.
- Use KPI cards for the decision funnel: total responses, review-tagged rows, agent discard rows, and kept review rows.
- Use figure captions in the format `Figure N: Plain-English Chart Name`.
- Add source notes below every chart. State whether the chart comes from scoring artifacts, second-pass disposition, or final agent judgment artifacts.
- Use a restrained palette with a strong dark text color, a deep green or charcoal anchor, one mint/teal accent, and one or two secondary colors. Do not make the page a single-hue gradient theme.
- Keep tables dense but readable: small uppercase headers, clear row rules, top-aligned cells, and only the columns needed for adjudication.
- Use narrative callouts sparingly for the main policy: programmatic scoring finds candidates; the agent makes final semantic discard judgments; kept review rows become survey-improvement guidance.
- Treat tables as ledgers, not prose containers. Do not put long semantic judgments, trust rationales, or response-chain text into narrow table cells.
- Add an agent findings essay section from `agent_findings_essay.md`. This section is required for delivery and should read like a senior analyst wrote it after studying the run.
- Link `agent_escalation_packet.md` and `internal_quality_signal_bank.md` in the artifact index. Summarize them in prose when they change the final decision. Do not turn internal learning into client-facing accusation language.
- Use row examples only when they help the narrative. They should read as human prose that explains what the full chain means, why the row stayed or was discarded, and what the next pass learns. Do not force them into a fixed annotation schema.
- Never show a raw stitched response chain in the dashboard body. Show a short chain readout and link to the audit artifacts for the full chain.
- End with an artifact index so reviewers can move from the dashboard to the CSV and Markdown evidence.

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

Wrap charts in `ResponsiveContainer` and include `Tooltip`, axis labels where useful, and `Legend` for donut charts. Avoid chart decorations that do not help the reviewer make a cleaning decision.

## Writing Style

- Use concise research-report language: `Finding`, `Decision Rule`, `Design Implication`, `Source`.
- Lead with the decision, then explain the evidence. Do not make readers infer meaning from scores alone.
- For discard rows, write an expert judgment memo: semantic pattern, language quality, source evidence, benign alternative considered, and final recommended action.
- For kept review rows, explain why the row survived and what question design or fielding parameter should improve.
- For dashboard editorial prose, write in complete analysis paragraphs. Do not stitch together field values or populate a rigid template. State what the agent saw, what it means, why the conclusion is trustworthy, and what should happen next.
- Never let keyword mismatch, AI-likelihood, or supplier/source concentration read as a final semantic decision.
- Use plain writing. Prefer common words. Use complete sentences. Remove filler. Avoid jargon unless you explain it. Do not hide the decision behind phrases such as "may indicate" when the agent has made a final judgment.
- Cite every material claim. Counts should cite local tables. Criteria should cite the generated criteria catalog or criterion evidence table. Agent decisions should cite the agent judgment table. Design and writing choices should cite the design and writing references.

## Quality Gate

Before delivery, verify that the dashboard:

- renders the KPI cards, all required charts, discard table, full semantic decision table, kept synthesis table, and artifact index
- includes discovery, expanded scorer criteria, response analysis criteria, dataset observations, and a citation table
- remains readable at desktop and mobile widths
- contains no overlapping text, one-character column wrapping, or prose squeezed into narrow table cells
- includes `agent_findings_essay.md` prose, or clearly blocks delivery until the agent writes it
- links the escalation packet and internal signal bank when they exist
- does not require PMs to reopen CSV files to understand the main findings
- clearly marks final discard decisions as agent-generated semantic judgments
- preserves source artifacts rather than mutating evidence files
