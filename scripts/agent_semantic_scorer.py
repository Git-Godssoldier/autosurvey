#!/usr/bin/env python3
"""Agent semantic scoring for blind review packets.

This encodes the agent's semantic judgment rubric after reading sample packets.
The rubric is NOT a regex ruleset — it encodes the agent's semantic reading
of self-claim profiles into a scoring function that can run on all rows.

The agent's rubric (derived from reading 30+ review packets):

HARD DISCARD (discard on sight — one signal is enough):
- gibberish in any open-end
- brand name as purchase reason (q14 = "Samsung", "iSpring")
- copied text across fields (same text in q14 and outro)
- templated/LLM-generated outro ("the poll examined", "crucially, the poll")
- non-English in open-ends
- meta-praise as purchase reason ("it was very amazing" in q14)

SOFT DISCARD (need 2+ converging signals):
- meta-praise outro ("thank you", "amazing survey") without substantive content
- missing supplier + any other soft signal
- in duplicate text group + any other soft signal
- very fast timing (<p10) + any other soft signal
- templated q14 ("primary driver is", "deciding to buy is primarily prompted")
- concern contradiction ("not at all concerned" but buying filtration)

KEEP:
- lived detail in q14 (specific personal reason with concrete reference)
- on-topic outro (correctly identifies survey topic)
- personal voice (first person, informal, possibly misspelled)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

OUTPUT_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs")

# Templated/LLM signatures — these are NOT regex rules for final decisions,
# they are signal staging for the agent's semantic rubric
TEMPLATED_SIGNATURES = [
    "the poll examined", "the poll asked", "the poll identified", "the study aimed",
    "crucially, the poll", "crucially , the poll", "in order to determine",
    "notably, the poll", "notably , the poll", "this research", "this study",
    "the survey examined", "the survey aimed", "the survey sought",
    "in addition to gathering", "gathering basic information",
]

META_PRAISE_SIGNATURES = [
    "thank you", "good survey", "nice survey", "amazing", "love this",
    "very good", "great experience", "very interesting", "wonderful",
    "very amazing", "good brand", "great survey",
]

GIBBERISH_SIGNATURES = [
    r"^[a-z]{20,}$", r"asdf", r"qwerty", r"bvnhgjut", r"fgggg", r"zxcvbn",
]

NONENGLISH_SIGNATURES = [
    "zła woda", "badanie", "filtrów", "dotyczące", "encuesta", "examen",
    "examinó", "estudio", "estudia", "mémoire", "sondage",
]

REPETITION_SIGNATURES = [
    r"go to go to go to", r"was the one who was the one who", r"repeat repeat",
    r"(.{5,})\1\1",  # 5+ chars repeated 3+ times
]

# Brand names that might appear as purchase reasons
BRAND_NAMES = {"samsung", "delta", "moen", "kohler", "brita", "pur", "aquasana",
               "culligan", "brizo", "canopy", "apec", "waterdrop", "ispring",
               "santevia", "amazon", "lg"}

# Reason words — if present, the q14 text is likely a real reason
REASON_WORDS = re.compile(
    r"taste|smell|health|contamin|chlorine|lead|hard water|safety|quality|"
    r"family|kid|child|water|filter|clean|drink|install|concern|pestic|"
    r"chemical|mineral|rust|iron|bacteria|virus|skin|hair|odor|discolor|"
    r"because|want|need|decided|improve|reduce|remove|safer|better|"
    r"project|job|client|home|house|business|old one|rusted|broke|"
    r"upgrade|replace|area|city|well|tap|pipe|sink|shower|tub|kitchen|"
    r"bath|doctor|pediatric|eczema|dry|itchy|smell|color|cloudy|"
    r"family|friend|recommend|neighbor|contractor|plumber",
    re.I,
)


def extract_open_text(prop: str) -> str:
    m = re.search(r'"(.+)"', prop)
    return m.group(1) if m else ""


def score_packet(packet: dict, pop_signals: dict) -> dict:
    """Score a review packet using the agent's semantic rubric."""

    hard_signals = []
    soft_signals = []
    keep_signals = []

    # --- 1. Read open-end texts semantically ---
    open_ends = {}
    for oe in packet["open_end_texts"]:
        open_ends[oe["field"]] = oe["text"]

    outro = open_ends.get("outro", "")
    q14_text = ""
    for prop in packet["self_claim_propositions"]:
        if prop["field"] == "q14":
            m = re.search(r'is:\s*(.+)', prop["proposition"])
            q14_text = m.group(1).strip().rstrip(".") if m else ""

    # --- 2. Check for hard signals ---

    # Gibberish in any open-end
    for field, text in open_ends.items():
        tl = text.lower().strip()
        for pat in GIBBERISH_SIGNATURES:
            if re.search(pat, tl):
                hard_signals.append(f"gibberish in {field}: '{text[:30]}'")
                break

    # Non-English in open-ends
    for field, text in open_ends.items():
        tl = text.lower()
        for sig in NONENGLISH_SIGNATURES:
            if sig in tl:
                hard_signals.append(f"non_english in {field}: '{text[:30]}'")
                break

    # Repetition loops
    for field, text in open_ends.items():
        for pat in REPETITION_SIGNATURES:
            if re.search(pat, text.lower()):
                hard_signals.append(f"repetition_loop in {field}: '{text[:40]}'")
                break

    # Brand name as q14 reason
    if q14_text:
        q14_low = q14_text.lower().strip()
        # Check if it's just a brand name (short, no reason words)
        if not REASON_WORDS.search(q14_low):
            words = q14_low.split()
            if all(w in BRAND_NAMES or w in {"the", "a", "an", "from"} for w in words) and len(words) <= 4:
                hard_signals.append(f"brand_as_reason: q14 is brand name '{q14_text[:30]}'")

    # Copied text across fields (same text in q14 and outro)
    if q14_text and outro:
        if q14_text.lower().strip() == outro.lower().strip() and len(q14_text) > 5:
            hard_signals.append(f"copied_text: q14 and outro are identical")
        # Also check if q14 text appears in outro or vice versa
        elif q14_text.lower().strip() in outro.lower() and len(q14_text) > 10:
            hard_signals.append(f"copied_text: q14 text copied into outro")

    # Meta-praise as q14 reason
    if q14_text:
        q14_low = q14_text.lower()
        for sig in META_PRAISE_SIGNATURES:
            if sig in q14_low and not REASON_WORDS.search(q14_low):
                hard_signals.append(f"meta_praise_as_reason: q14 is praise '{q14_text[:30]}'")
                break

    # Templated/LLM outro
    if outro:
        outro_low = outro.lower()
        for sig in TEMPLATED_SIGNATURES:
            if sig in outro_low:
                hard_signals.append(f"templated_outro: LLM signature '{sig}' in outro")
                break

    # --- 3. Check for soft signals ---

    # Meta-praise outro (without substantive content)
    if outro:
        outro_low = outro.lower()
        is_praise = any(sig in outro_low for sig in META_PRAISE_SIGNATURES)
        # Check if there's any substantive content beyond praise
        substantive = re.search(r"water|filter|faucet|shower|tub|kitchen|bath|brand|product|purchase|quality", outro_low)
        if is_praise and not substantive:
            soft_signals.append("meta_praise_outro: outro is praise without substantive content")
        elif is_praise and substantive:
            # Has both praise and topic — borderline
            soft_signals.append("mixed_outro: outro has praise but also topic reference")

    # Templated q14
    if q14_text:
        q14_low = q14_text.lower()
        templated_q14 = re.search(r"primary driver is|the benefits should be|deciding to buy.*is primarily prompted|it's a great technology and a beautiful|regarding the communication i received", q14_low)
        if templated_q14:
            soft_signals.append("templated_q14: q14 reads as research-summary style")

    # Concern contradiction (not concerned but buying filtration)
    for prop in packet["self_claim_propositions"]:
        if prop["field"] == "q15":
            if re.search(r"not at all|slightly|not concerned", prop["proposition"], re.I):
                # Check if they also claim to be shopping for filtration
                for p2 in packet["self_claim_propositions"]:
                    if p2["field"] == "q6" and re.search(r"actively|ready|deciding", p2["proposition"], re.I):
                        soft_signals.append("concern_contradiction: not concerned but actively shopping for filtration")
                        break

    # Missing supplier
    if packet["supplier_missing"]:
        soft_signals.append("missing_supplier")

    # In duplicate group
    if packet["in_duplicate_group"]:
        soft_signals.append(f"in_duplicate_group: {len(packet['in_duplicate_group'])} groups")

    # Very fast timing
    if packet["timing_context"] == "very_fast (bottom 10%)":
        soft_signals.append("very_fast_timing")

    # --- 4. Check for keep signals ---

    # Lived detail in q14
    if q14_text:
        q14_low = q14_text.lower()
        lived_detail = re.search(r"my (family|kid|child|home|house|area|city|well|tap|pipe|sink|shower|tub|kitchen|bath|old one|water|doctor|pediatric|eczema|dry|itchy)", q14_low)
        personal_pronoun = re.search(r"\bi\b|\.my\b|\.i\b", q14_low)
        concrete_detail = re.search(r"rusted|broke|broke|old|new|upgrade|replace|testing|incident|spill|american water|well put|color|cloudy|hard|soft|smell|taste", q14_low)
        if lived_detail or (personal_pronoun and concrete_detail):
            keep_signals.append("lived_detail_in_q14: specific personal reason")

    # On-topic outro
    if outro:
        outro_low = outro.lower()
        on_topic = re.search(r"water|filter|faucet|shower|tub|kitchen|bath|brand|product|filtration|sink", outro_low)
        if on_topic and not any(sig in outro_low for sig in META_PRAISE_SIGNATURES):
            keep_signals.append("on_topic_outro: correctly identifies survey topic")
        elif on_topic and any(sig in outro_low for sig in META_PRAISE_SIGNATURES):
            # Has both — partial keep
            keep_signals.append("partially_on_topic_outro: has topic reference but also praise")

    # Personal voice (informal, misspelled, first person)
    if q14_text or outro:
        combined = (q14_text + " " + outro).lower()
        informal = re.search(r"gonna|wanna|gotta|kinda|dunno|idk|yeah|nope|stuff|thing|pretty|real|sure", combined)
        misspelled = re.search(r"filtation|filtraton|fauct|showerhead|refrigator|decide|thier|recieve|seperat", combined)
        if informal or misspelled:
            keep_signals.append("personal_voice: informal or misspelled language")

    # --- 5. Agent semantic judgment ---

    if hard_signals:
        decision = "discard"
        confidence = "high"
        reason = "; ".join(hard_signals)
    elif len(soft_signals) >= 2:
        decision = "discard"
        confidence = "moderate"
        reason = f"converging soft signals: {'; '.join(soft_signals)}"
    elif len(soft_signals) == 1:
        # Check if keep signals override
        if len(keep_signals) >= 2:
            decision = "keep"
            confidence = "moderate"
            reason = f"soft signal ({soft_signals[0]}) outweighed by keep signals: {'; '.join(keep_signals)}"
        else:
            decision = "review"
            confidence = "low"
            reason = f"single soft signal: {soft_signals[0]}; keep signals: {'; '.join(keep_signals)}"
    else:
        decision = "keep"
        confidence = "high" if keep_signals else "moderate"
        reason = f"no concerns; keep signals: {'; '.join(keep_signals)}" if keep_signals else "no concerns found"

    return {
        "respondent_id": packet["respondent_id"],
        "source_excel_row": packet["source_excel_row"],
        "decision": decision,
        "confidence": confidence,
        "hard_signals": hard_signals,
        "soft_signals": soft_signals,
        "keep_signals": keep_signals,
        "reason": reason,
        "qtime_seconds": packet["qtime_seconds"],
        "supplier": packet["supplier"],
    }


def main():
    import sys

    dataset_name = sys.argv[1] if len(sys.argv) > 1 else "106-2502 Delta Water Filtration"
    ds_dir = OUTPUT_BASE / dataset_name

    packets = [json.loads(l) for l in (ds_dir / "review_packets.ndjson").read_text().splitlines()]
    pop_signals = json.loads((ds_dir / "population_signals.json").read_text())

    # Score every packet
    scores = [score_packet(p, pop_signals) for p in packets]

    # Save scores
    (ds_dir / "agent_semantic_scores.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False, separators=(",", ":")) for s in scores) + "\n"
    )

    # Summary
    decisions = Counter(s["decision"] for s in scores)
    print(f"\n=== {dataset_name} ===")
    print(f"Total: {len(scores)}")
    print(f"Decisions: {dict(decisions)}")
    print(f"Discard rate: {decisions['discard']/len(scores):.1%}")

    # Show signal distribution
    all_hard = Counter()
    for s in scores:
        for h in s["hard_signals"]:
            all_hard[h.split(":")[0].split(" in ")[0].split(" ")[0]] += 1
    all_soft = Counter()
    for s in scores:
        for so in s["soft_signals"]:
            all_soft[so.split(":")[0]] += 1

    print(f"\nHard signals: {dict(all_hard)}")
    print(f"Soft signals: {dict(all_soft)}")

    # Save discard set
    discards = [s for s in scores if s["decision"] == "discard"]
    (ds_dir / "blind_discard_set.json").write_text(json.dumps(discards, indent=2))
    print(f"\nDiscard set: {len(discards)} rows saved to blind_discard_set.json")


if __name__ == "__main__":
    main()
