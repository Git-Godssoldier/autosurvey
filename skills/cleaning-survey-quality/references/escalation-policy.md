# Escalation Policy

Use escalation only for bad candidate responses that survive an extra analysis pass as decisive discard candidates. Ordinary review uncertainty should not be escalated.

## Row Severity Bands

Generate severity bands from the run's generated criteria, generated weights, and evidence patterns. Do not hard-code score cutoffs before discovery.

| Severity | Owner | Use when |
|---|---|---|
| `No action` | No escalation | No material quality signal or only negligible evidence. |
| `Survived second pass` | No escalation | Evidence exists, but the extra pass did not find enough convergence to justify discard. Keep with rationale and aggregate recommendations. |
| `Data quality escalation` | Data Quality Lead | Extra pass found converging evidence strong enough that the row should be reviewed for removal from the final dataset. |

## Second-Pass Rule

Run every possible escalation through an extra pass that asks only whether the row should be thrown out. The output must be one of:

- `discard_candidate`: escalate to Data Quality Lead with discard rationale, triggering criteria, observed values, score, respondent metadata, agent semantic analysis, linguistic fluency assessment, trust rationale, and recommended next step.
- `keep_with_recommendation`: do not escalate; keep the row, explain why it survived, and aggregate the survey-question recommendation.
- `keep_no_issue`: do not escalate; no material evidence was detected.

The extra pass should look for converging evidence, such as duplicate technical evidence plus another strong signal, straightlining plus low-quality open ends, speed plus inattentiveness, or poor open-end authenticity plus low relevance/effort. A single fuzzy or ambiguous signal should survive unless project-specific adjudication says otherwise.

When the extra pass depends on semantic relevance, the Opulent agent must adjudicate the text directly. Treat script-produced topic mismatch as a candidate signal only. The agent should downgrade responses whose wording is awkward but contextually relevant, and should escalate only when the text is substantively off-topic, evasive, generic, or non-responsive in a way that strengthens other quality evidence.

## Override Rules

Mark a row `discard_candidate` even below the generated data-quality threshold only when the extra pass confirms:

- duplicate technical evidence combines with another strong signal
- straightlining combines with another strong signal
- the same severe pattern appears repeatedly by supplier/source
- review queue volume suggests a wave-level quality issue

Rows that survive should feed aggregate recommendations rather than individual escalation. Use those recommendations to strengthen survey questions, for example by adding structured reason codes, requiring concrete examples, shortening matrix grids, adding reverse-coded items, or asking follow-up prompts when answers are vague.

## Communication Rules

- Say "discard candidate" or "recommended for exclusion review" rather than "fraud" unless the client has confirmed that standard.
- Include source column, observed value, score, and justification for each severe row.
- Include agent-generated semantic analysis for each discard candidate so the reader sees the judgment, not just the score.
- Include linguistic fluency assessment when text evidence contributes to the decision.
- Include trust rationale that explains why the row should be adjudicated for discard without forcing the reviewer to redo the analysis.
- Separate row-level discard escalation from wave-level supplier/source or survey-design recommendations.
- For survivor rows, include why they were kept and what survey-question framing would make the answer harder to game.
- Do not expose raw open ends externally without approval.
