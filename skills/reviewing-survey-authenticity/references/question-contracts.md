# Question Contracts

A question contract explains what each field means and how fields relate before any respondent is judged.

## Minimum Contract

Write a compact but complete contract that covers:

- Respondent identity fields and stable join fields.
- Status or label fields, if present, marked as post-seal only.
- Survey sections in order.
- Screeners and route gates.
- Brand, product, supplier, or concept entities.
- Awareness, familiarity, use, consideration, preference, recommendation, satisfaction, purchase, and refusal funnels.
- Open-ended questions and the closed-end answers they are supposed to explain.
- Other-specify fields and the prompt they answer.
- Matrices, scale direction, reverse-coded or opposed items, and whether uniform answers can be legitimate.
- Timing fields and whether they are total, page-level, question-level, or derived.
- Demographics and any demographic facts that could make an answer more or less plausible.
- Technical fields such as IP, device, browser, supplier, source, duplicate identifiers, and session metadata.

## Relationship Graph

For each important relationship, write the relationship type and the obligation it creates:

- Prerequisite: later answer requires an earlier selected experience.
- Funnel progression: awareness leads to use, use leads to satisfaction, satisfaction can support recommendation.
- Mutual exclusion: two answers cannot both be true without a special explanation.
- Parallel consistency: similar questions should generally align but can differ in nuance.
- Inverse consistency: an agree item and a disagree item point in opposite directions.
- Temporal consistency: later claims must fit stated time periods.
- Numerical consistency: counts, ranks, shares, ages, and years should not contradict.
- Route integrity: skipped and shown fields must fit the survey logic.
- Open/closed explanation: narrative text should explain or qualify the closed selection, not merely repeat generic language.

## Authoring Standard

The contract should be understandable to a client. It should not be a pasted field dictionary. It should explain the survey’s logic, the evidence each section can produce, and the risks of misreading fields before scoring.
