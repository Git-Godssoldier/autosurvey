---
name: reviewing-survey-authenticity
description: Use when reviewing survey respondent authenticity, fraud risk, bot-like records, possible LLM-assisted survey answers, fabricated open ends, Decipher data cleaning, client rejection risk, or market research respondent quality. This skill conducts an agent-native, label-blind semantic review before any evaluator or script is allowed to inspect respondent content.
---

# Reviewing Survey Authenticity

Use this skill for respondent-level authenticity review on unannotated survey data or for the pre-seal phase of annotated-corpus development.

## Non-Negotiable Boundary

Before a blind semantic decision ledger is sealed, the agent is the inference system.

Do not run, write, import, or reuse code that examines respondent content before the seal. This includes dataframe reads, workbook parsing scripts, regex scoring, word counts, timing features, formulas, similarity models, packet builders, existing Autosurvey predictors, or any script that turns respondent answers into evidence.

Allowed before the seal:

- Native workbook or spreadsheet viewing that exposes cells directly to the agent.
- Direct reading of Datamaps, questionnaires, survey text, field labels, row cells, and response chains.
- Agent-authored reasoning, citations, notes, rubrics, and sealed decisions.
- Editing this skill, its references, or post-seal evaluator boundaries.

If the environment cannot expose workbook cell values for direct agent reading without scripts, stop with:

`BLOCKED_NATIVE_WORKBOOK_READER_REQUIRED`

## Required References

Read only the references needed for the active phase:

- [workflow.md](references/workflow.md) for the end-to-end blind review process.
- [question-contracts.md](references/question-contracts.md) for field-role mapping and relationship graphs.
- [semantic-signal-bank.md](references/semantic-signal-bank.md) for authenticity signal families.
- [accepted-respondent-guardrails.md](references/accepted-respondent-guardrails.md) for human protective evidence.
- [decision-rubric.md](references/decision-rubric.md) for the five-tier decision frame.
- [relationship-patterns.md](references/relationship-patterns.md) for cross-question semantic logic.
- [validated-case-patterns.md](references/validated-case-patterns.md) for portable lessons from prior development.
- [provisional-hypotheses.md](references/provisional-hypotheses.md) for ideas still under attack.
- [failed-hypotheses.md](references/failed-hypotheses.md) for weak signals that must not drive exclusion alone.
- [output-schema.md](references/output-schema.md) for the sealed ledger and narrative artifacts.

## Operating Standard

Every run must first understand the survey, then read every respondent, then write the blind ledger. The review must combine three perspectives:

- Forensic investigator: searches for fabricated, automated, pasted, synthetic, or routed-incoherent behavior.
- Human advocate: protects plausible humans with messy, concise, fast, emotional, non-native, or unusual but coherent responses.
- Evidence judge: separates independent evidence families from repeated versions of the same signal and decides whether exclusion is warranted.

The public reporting should read like research-grade analysis written for a client. It should explain what was discovered, why it matters, which records best illustrate it, what protective guardrails were learned, and what should change in the next pass. It must not sound like a stitched export of feature names.

## Seal Discipline

The blind ledger is sealed only after every respondent has a decision, rationale, signals, protective evidence, citations, and reviewer confidence. Client labels, status columns, external annotations, and evaluator scripts remain out of scope until after sealing.
