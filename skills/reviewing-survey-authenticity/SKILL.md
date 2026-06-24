---
name: reviewing-survey-authenticity
description: Use when reviewing survey respondent authenticity, fraud risk, bot-like records, possible LLM-assisted survey answers, fabricated open ends, Decipher data cleaning, client rejection risk, or market research respondent quality. This skill conducts an agent-native, label-blind semantic review before any evaluator or script is allowed to inspect respondent content.
---

# Reviewing Survey Authenticity

Use this skill for respondent-level authenticity review on unannotated survey data or for the pre-seal phase of annotated-corpus development.

## Non-Negotiable Boundary

Before a blind semantic decision ledger is sealed, the agent is the inference system.

Scripts are allowed as deterministic infrastructure when they preserve or expose evidence without making a semantic decision. They may read XLSX files, reconstruct question and answer labels, normalize nulls and data types, preserve raw row packets, compute blind descriptive evidence, estimate token size, build compact packets, schedule batches, run retries, validate schemas, reconcile row coverage, and seal hashes.

Scripts must not silently assign the five-tier decision, rewrite an agent-authored decision, interpret respondent authenticity, or use client labels before the seal.

Allowed before the seal:

- Programmatic workbook extraction that preserves every respondent and keeps a lossless raw-row audit pointer.
- Question-contract, relation-graph, timing, missingness, matrix, routing, duplicate, similarity, and open-end evidence tables derived only from the blind workbook.
- Agent-authored reasoning, citations, notes, rubrics, first decisions, second reviews, adjudications, and sealed final decisions.
- Deterministic validation of row coverage, required fields, schema integrity, and file hashes.

Client labels, status columns, client flags, review notes, annotated formatting, and discard decisions remain forbidden until the blind ledger is sealed.

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

## Echo Calibration Lesson

The Echo benchmark showed that a generally plausible consumer story can hide field-level semantic invalidity. Do not let one coherent brand chain or normal timing rescue unrelated invalid fields. Evaluate each key field family on its own terms, then recombine the evidence.

Raise client-rejection probability when invalid field semantics converge with any independent mechanical cue:

- Open ends contain numeric codes, placeholders, platform names, off-category brands, wrong-dimension answers, survey-meta text, or generic adjectives that do not answer the specific prompt.
- A respondent names plausible brands but gives invalid other-specify answers in equipment, store, ad recall, switching, or loyalty fields.
- No open ends or invalid open ends leave fast timing, all-brand selection, matrix uniformity, or overbroad share allocation without human grounding.
- Broad “possible,” “aware,” “seen,” or “consider” patterns pair with weak recall, flat small-share allocation, or top-box concentration.
- Long timing appears with off-category text, fully uniform ad grids, all-brand selection, or incoherent funnels. Long duration can be interruption, not proof of careful review.

Protect accepted-looking rows only when the protective evidence answers the exact field at issue. A real brand name, a misspelling, or a coherent one-brand story is protective for that chain, but it does not automatically validate unrelated matrices or open ends.

## Seal Discipline

The blind ledger is sealed only after every respondent has a decision, rationale, signals, protective evidence, citations, and reviewer confidence. Client labels, status columns, external annotations, and evaluator scripts remain out of scope until after sealing.
