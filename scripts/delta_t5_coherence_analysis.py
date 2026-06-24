#!/usr/bin/env python3
"""Delta t=5 self-claim profile coherence analysis.

Reads the first-person proposition profiles and detects contradictions
that are invisible in raw coded data. This is the agent reasoning layer
that uses the self-claim profile as a narrative.

Contradiction families:
1. Concern vs knowledge: high concern + low knowledge, or low concern + high knowledge
2. Contaminants claimed vs concerns: claiming many contaminants but concerned about different/fewer
3. Purchase reason validity: q14 answer that is a brand name, greeting, or non-reason
4. Over-claiming: many contaminants, many brands, many sources beyond plausible
5. Funnel breaks: purchased filtration but don't have any system; or plan to buy everything
6. Outro vs chain: valid chain but nonresponsive outro, or vice versa
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

OUT = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/agent-native-delta-transfer-2026-06-24/.autosurvey-internal/t5_semantic")


def get_prop(profile: dict, field: str) -> str:
    """Get the proposition text for a field."""
    for p in profile.get("self_claim_propositions", []):
        if p["field"] == field:
            return p["proposition"]
    return ""


def get_all_props(profile: dict, field_prefix: str) -> list[str]:
    """Get all propositions for fields starting with prefix."""
    return [p["proposition"] for p in profile.get("self_claim_propositions", []) if p["field"].startswith(field_prefix)]


def analyze_coherence(profile: dict) -> dict:
    """Analyze a self-claim profile for contradictions and incoherence."""
    concerns = []
    hard_invalidities = []

    # Extract key propositions
    q15 = get_prop(profile, "q15")  # concern level
    q16 = get_prop(profile, "q16")  # knowledge level
    q14 = get_prop(profile, "q14")  # purchase reason
    q1 = get_prop(profile, "q1")    # industry
    q6 = get_prop(profile, "q6")    # search stage
    outro = get_prop(profile, "outro")
    q22_props = get_all_props(profile, "q22")  # contaminants in water
    q23_props = get_all_props(profile, "q23")  # concerns about water
    q26_props = get_all_props(profile, "q26")  # brand awareness
    q7_props = get_all_props(profile, "q7")    # research sources
    q3_props = get_all_props(profile, "q3")    # purchased items
    q4_props = get_all_props(profile, "q4")    # interested in purchasing
    q5_props = get_all_props(profile, "q5")    # matrix ownership

    # 1. Concern vs knowledge contradiction
    high_concern = bool(re.search(r"extremely|very concerned", q15, re.I))
    low_concern = bool(re.search(r"not at all|slightly|not concerned", q15, re.I))
    high_knowledge = bool(re.search(r"great deal|a lot|expert", q16, re.I))
    low_knowledge = bool(re.search(r"nothing|very little|not much|don't know", q16, re.I))

    if high_concern and low_knowledge:
        concerns.append("concern_knowledge_break: claims extreme concern but no knowledge of how filters work")
    if low_concern and high_knowledge:
        concerns.append("concern_knowledge_break: claims high knowledge but no concern about water quality")
    if high_concern and not q14:
        concerns.append("concern_reason_break: extremely concerned but no purchase reason given")

    # 2. Contaminants claimed vs concerns mismatch
    # Extract contaminant names from q22 and q23 propositions
    q22_items = extract_list_items(q22_props)
    q23_items = extract_list_items(q23_props)
    if q22_items and q23_items:
        q22_set = set(i.lower() for i in q22_items)
        q23_set = set(i.lower() for i in q23_items)
        # If they claim to have many contaminants but are concerned about completely different ones
        overlap = q22_set & q23_set
        if len(q22_set) >= 5 and len(overlap) == 0:
            concerns.append(f"contaminant_concern_mismatch: claims {len(q22_set)} contaminants in water but concerned about {len(q23_set)} completely different ones")
        elif len(q22_set) >= 7 and len(overlap) <= 1:
            concerns.append(f"contaminant_concern_drift: claims {len(q22_set)} contaminants but only {len(overlap)} overlap with concerns")

    # Over-claiming contaminants
    if len(q22_items) >= 8:
        concerns.append(f"contaminant_overclaim: claims {len(q22_items)} contaminants in water (high count)")

    # 3. Purchase reason validity (q14 is open text)
    if q14:
        reason = q14.lower()
        # Extract the actual answer text from the proposition
        m = re.search(r'is:\s*(.+)', q14)
        reason_text = m.group(1).strip().rstrip(".") if m else reason
        reason_low = reason_text.lower()

        # Brand name only (short, just a brand, no reason words)
        reason_words = re.search(r"taste|smell|health|contamin|chlorine|lead|hard water|safety|quality|family|kid|water|filter|clean|drink|install|concern|pestic|chemical|mineral|rust|iron|bacteria|virus|skin|hair|odor|discolor|because|want|need|decided|improve|reduce|remove|safer|better", reason_low)
        brand_only = re.match(r"^\s*(samsung|delta|moen|kohler|brita|pur|aquasana|culligan|a\.o\. smith|brizo|canopy|apec|waterdrop|ispring|ge|amazon|lg)(\s+(samsung|delta|moen|kohler|brita|pur|aquasana|culligan|a\.o\. smith|brizo|canopy|apec|waterdrop|ispring|ge|amazon|lg))*\s*$", reason_low)
        if brand_only:
            hard_invalidities.append(f"q14_wrong_dimension: purchase reason is just a brand name ('{reason_text[:40]}')")

        # Non-English
        nonenglish = re.search(r"zła woda|badanie|filtrów|dotyczące", reason_low)
        if nonenglish:
            hard_invalidities.append(f"q14_nonenglish: purchase reason is non-English ('{reason_text[:40]}')")

        # Nonresponsive / survey-meta
        if re.search(r"thank you|good survey|nice|amazing|great experience|love this|it's essential|easy to use and unique", reason_low) and not reason_words:
            hard_invalidities.append(f"q14_nonresponsive: purchase reason is nonresponsive ('{reason_text[:40]}')")

        # Templated / generic research-summary style
        templated = re.search(r"primary driver is|the benefits should be|deciding to buy.*is primarily prompted|it's a great technology and a beautiful|regarding the communication i received", reason_low)
        if templated and not re.search(r"my (family|home|house|kid|child)", reason_low):
            concerns.append(f"q14_templated: purchase reason reads as templated/generic ('{reason_text[:50]}')")

        # Placeholder
        if re.search(r"^\s*$|^none$|^n/a$|^idk$|^i don't know$", reason_low):
            concerns.append("q14_placeholder: purchase reason is a placeholder")

    # 4. Over-claiming patterns
    brand_items = extract_list_items(q26_props)
    source_items = extract_list_items(q7_props)
    if len(brand_items) >= 12:
        concerns.append(f"brand_overclaim: aware of {len(brand_items)}/17 brands")
    if len(source_items) >= 6:
        concerns.append(f"source_overclaim: used {len(source_items)} research sources")

    # 5. Funnel breaks
    # Check if they purchased water filtration (q3) but don't have any system (q5)
    q3_text = " ".join(q3_props).lower()
    q5_text = " ".join(q5_props).lower()
    bought_filtration = "water filtration" in q3_text
    has_system = "i currently have" in q5_text
    if bought_filtration and not has_system:
        concerns.append("funnel_break: purchased water filtration but claim no current system")

    # Plan to buy many types
    plan_count = q5_text.count("i plan to get")
    if plan_count >= 5:
        concerns.append(f"funnel_overclaim_plan: plans to buy {plan_count} different water treatment types")

    # 6. Outro vs chain
    if outro:
        outro_text = outro.lower()
        # Valid chain but nonresponsive outro
        if re.search(r"thank you|great experience|love this|amazing|nice survey|very good", outro_text):
            if not hard_invalidities and len(concerns) <= 1:
                concerns.append("outro_chain_mismatch: chain appears coherent but outro is survey-meta praise")

    # 7. Industry mismatch (q1=1 is market research — should be excluded)
    if "market research" in q1.lower():
        hard_invalidities.append("industry_exclusion: works in market research (should be excluded)")

    # Classify
    if hard_invalidities:
        coherence_status = "incoherent_hard"
    elif len(concerns) >= 3:
        coherence_status = "incoherent_soft"
    elif len(concerns) >= 1:
        coherence_status = "minor_concern"
    else:
        coherence_status = "coherent"

    return {
        "respondent_id": profile["respondent_id"],
        "source_excel_row": profile["source_excel_row"],
        "status": profile["status"],
        "qtime_seconds": profile["qtime_seconds"],
        "supplier": profile["supplier"],
        "coherence_status": coherence_status,
        "hard_invalidities": hard_invalidities,
        "soft_concerns": concerns,
        "hard_invalidity_count": len(hard_invalidities),
        "soft_concern_count": len(concerns),
        "self_claim_profile_summary": {
            "q15_concern": q15[:80],
            "q16_knowledge": q16[:80],
            "q14_reason": q14[:80],
            "q1_industry": q1[:60],
            "q6_search": q6[:60],
            "outro": outro[:80],
            "contaminants_claimed": len(q22_items),
            "concerns_listed": len(q23_items),
            "brands_aware": len(brand_items),
            "sources_used": len(source_items),
        },
    }


def extract_list_items(props: list[str]) -> list[str]:
    """Extract item names from multi-select proposition text."""
    items = []
    for p in props:
        # Format: "I [verb]: item1, item2, item3."
        m = re.search(r":\s*(.+?)\.?\s*$", p)
        if m:
            for item in m.group(1).split(","):
                item = item.strip().rstrip(".")
                if item and item not in ("...",):
                    items.append(item)
    return items


def main() -> None:
    t5 = [json.loads(l) for l in (OUT / "t5_self_claim_profiles.ndjson").read_text().splitlines()]
    t3 = [json.loads(l) for l in (OUT / "t3_guardrail_self_claim_profiles.ndjson").read_text().splitlines()]

    t5_results = [analyze_coherence(p) for p in t5]
    t3_results = [analyze_coherence(p) for p in t3]

    t5_status = Counter(r["coherence_status"] for r in t5_results)
    t3_status = Counter(r["coherence_status"] for r in t3_results)

    t5_hard = Counter()
    for r in t5_results:
        for h in r["hard_invalidities"]:
            t5_hard[h.split(":")[0]] += 1
    t3_hard = Counter()
    for r in t3_results:
        for h in r["hard_invalidities"]:
            t3_hard[h.split(":")[0]] += 1

    t5_soft = Counter()
    for r in t5_results:
        for s in r["soft_concerns"]:
            t5_soft[s.split(":")[0]] += 1
    t3_soft = Counter()
    for r in t3_results:
        for s in r["soft_concerns"]:
            t3_soft[s.split(":")[0]] += 1

    (OUT / "t5_coherence_analysis.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in t5_results) + "\n"
    )
    (OUT / "t3_guardrail_coherence_analysis.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in t3_results) + "\n"
    )

    summary = {
        "t5_total": len(t5_results),
        "t3_guardrail_total": len(t3_results),
        "t5_coherence_status": dict(t5_status),
        "t3_coherence_status": dict(t3_status),
        "t5_hard_invalidity_types": dict(t5_hard),
        "t3_hard_invalidity_types": dict(t3_hard),
        "t5_soft_concern_types": dict(t5_soft),
        "t3_soft_concern_types": dict(t3_soft),
        "t5_vs_t3_lift": {
            s: {
                "t5_rate": round(t5_soft.get(s, 0) / len(t5_results), 3),
                "t3_rate": round(t3_soft.get(s, 0) / len(t3_results), 3),
            }
            for s in set(list(t5_soft.keys()) + list(t3_soft.keys()))
        },
    }
    (OUT / "t5_coherence_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
