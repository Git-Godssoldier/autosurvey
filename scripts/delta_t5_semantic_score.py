#!/usr/bin/env python3
"""Delta t=5 semantic-signal expansion + weighted evidence claims.

Agent-derived semantic classification of the status=5 (rejected) population.
Scripts stage evidence; the classification rules below encode the agent's
reading of all 348 outro texts and other-specify responses against the
question-set authenticity map. Weights are assigned per semantic-signal-expansion.md
with plain-language rationale and accepted-row guardrail checks.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

OUT = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/agent-native-delta-transfer-2026-06-24/.autosurvey-internal/t5_semantic")

# ---------------------------------------------------------------------------
# Question-set authenticity map (agent-authored)
# ---------------------------------------------------------------------------
AUTHENTICITY_MAP = {
    "outro": {
        "prompt": "For quality control purposes, please describe what this survey was about in a few words.",
        "expected_evidence_type": "a brief topical summary of the survey subject in the respondent's own words",
        "respondent_universe": "a qualified homeowner / water-filtration intender who just completed the survey",
        "authentic_sound": "concise, rough, names the actual product (water filter, showerhead filter, tub filler, faucet filter) in plain language",
        "fabricated_sound": "polished research-summary enumeration of survey sections; wrong-domain topic; survey-meta praise; gibberish; non-English; copied purchase-reason text",
        "guardrail": "status=3 rows also include some polished summaries ('A study on consumer knowledge...'), so polish alone is weak; weight rises only with wrong-topic, nonresponsive, or copied text",
    },
    "q14": {
        "prompt": "What prompted you to decide to buy a water filtration device?",
        "expected_evidence_type": "a personal purchase reason tied to water quality, taste, safety, contaminants, or household need",
        "respondent_universe": "a buyer/intender who selected a purchase reason",
        "authentic_sound": "concrete personal motivation (bad taste, hard water, kids, health, saw discoloration)",
        "fabricated_sound": "greeting, praise, survey-meta, generic marketing language, nonresponsive",
        "guardrail": "short concrete reasons are valid; nonresponsive q14 is a strong signal because the prompt asks for a personal reason",
    },
    "other_specify": {
        "prompt": "Other (please specify) fields for research sources, faucet types, brands, stores, water source, race",
        "expected_evidence_type": "a specific entity matching the field's category",
        "respondent_universe": "a respondent who chose Other and must name the real thing",
        "authentic_sound": "a real brand, store, source, device type, or demographic group",
        "fabricated_sound": "generic text, wrong-category entity, copied chain, nonresponsive",
        "guardrail": "Other-specify fields are usually short; penalize only wrong-category or nonresponsive text",
    },
}

# Matrix question-similarity note
MATRIX_SIMILARITY = {
    "q5r1": "Kitchen Sink Faucet",
    "q5r2": "Bathroom Sink Faucet",
    "q5r3": "Showerhead",
    "q5r4": "Tub Spout Filler",
    "q5r5": "Whole Home Filtration",
    "q5r6": "Whole Home Softener",
    "q5r7": "Refrigerator/Ice Maker",
}
MATRIX_NOTE = ("The 7 q5 rows are semantically DISTINCT product categories. "
               "Uniform ownership/plan answers across all 7 are more suspicious than within a similar subgroup "
               "(e.g. sink faucets). Question similarity is LOW across the full set, so a flat straightline carries more weight.")

# ---------------------------------------------------------------------------
# Semantic classification of outro text (agent-derived from reading all 348)
# ---------------------------------------------------------------------------
# Wrong-universe / wrong-topic keywords (coherent answer, wrong domain)
WRONG_TOPIC_PATTERNS = [
    (r"finance|banking|investment|money|budget|spending pattern", "finance_banking"),
    (r"whiskey|alcohol|beverage drinking", "alcohol"),
    (r"eyeglass", "eyewear"),
    (r"dishwasher", "dishwasher"),
    (r"home furnish", "home_furnishing"),
    (r"home maintenance", "home_maintenance"),
    (r"home renovation|renovation did", "home_renovation"),
    (r"homebound", "homebound"),
    (r"aquarium", "aquarium"),
    (r"water tank", "water_tank"),
    (r"app on my phone|phone app", "phone_app"),
    (r"water retention", "water_retention"),
    (r"electronic device|technology in daily|modern device|devices people bring", "consumer_electronics"),
    (r"loyalty program|brand partnership|customer reward|retention program", "loyalty_programs"),
    (r"\bIT compan|\bIT industr|role of IT|smart tech", "it_industry"),
    (r"hair product", "hair_products"),
    (r"lowe.s inventory|find for sale at lowe", "store_inventory"),
    (r"kitchen appernce|kitchen appearance", "kitchen_appearance"),
    (r"personalization.*recommendation|pertinent recommendation", "personalization_marketing"),
    (r"innovation within|encouraging innovation", "innovation_marketing"),
    (r"marketing messaging|messaging.*design.*feature.*engagement", "marketing_messaging"),
    (r"willingness to recommend the product to other customer|efficiency of the service.*company", "b2b_services"),
    (r"collecting demographics on our respondent|respondents in order to compare", "researcher_pov"),
    (r"home appliance.*purchased in the past 12 month", "appliance_survey"),
    (r"mobility|transportation", "transportation"),
    (r"dry skin survey", "dry_skin"),
]

# Survey-meta / praise / nonresponsive
PRAISE_PATTERNS = [
    r"thank you so much", r"very good and wonderful", r"so amazing", r"all question is all clear",
    r"supper fast and easy", r"super fast and easy", r"great experience", r"feel great to complete",
    r"this is so good", r"i enjoy", r"enjoyable", r"very enjoy", r"i love it", r"i love this survey",
    r"nice survey", r"very interesting", r"very amazing", r"the survey is a very good",
    r"this survey is awesome", r"good nad nice", r"quiet good enough", r"very easy and fast",
    r"very much for your time", r"i am satisfied with this survey", r"this survey is very enjoy",
    r"it's very important and give me more idea", r"good night my friend", r"this is well survey easy",
    r"quick and effectively", r"the survey was amazing", r"very good and important survey",
    r"clear and easy survey", r"the survey was very clear", r"offers allot great deal",
]

NONRESPONSIVE_PATTERNS = [
    r"survey was about stuff", r"about stuff", r"none nothing", r"i cant fhjnk",
    r"everything is good", r"interesting survey and topics", r"it was about the best way",
    r"about getting money", r"it is about sink in the home", r"this survey home water",
    r"this survey is a good of kitchen", r"about the difference option",
    r"format requires participant", r"businesses provide both physical",
    r"customers show satisfaction through their purchasing",
    r"people show their spending pattern", r"to marketing in home water equipment",
    r"market research about different brand", r"about water brand",
]

# Gibberish / non-English
GIBBERISH_PATTERNS = [
    r"bvnhgjut|vcgtr|bvhfyt",
    r"Badanie dotyczące|filtrów do wody",
]
NONENGLISH_HINTS = ["Badanie", "dotyczące", "filtrów"]

# Templated / generic-filler research-summary indicators
TEMPLATED_INDICATORS = [
    r"the survey examined", r"the poll examined", r"the poll identified", r"this poll",
    r"the study aimed", r"the purpose of this study", r"the research examined",
    r"the questionnaire was about", r"in my opinion,? the purpose",
    r"crucially,? the poll", r"notably,? the poll", r"interestingly",
    r"in order to determine", r"throughout the questionnaire",
    r"the survey clear goal was to comprehend",
    r"consumer (opinions|attitudes|behavior|preference|motivation|research)",
    r"examining (customer|consumer)", r"recognizing (consumer|brand) (attitudes|preferences)",
    r"analyzing consumer", r"assessing consumer", r"determining consumer",
    r"exploring consumer", r"understanding consumer",
    r"a study on consumer", r"consumer research on",
    r"study (the reasons|focused|studied|gathered)",
    r"preferences for (convenient|the appearance)", r"general views on home water",
    r"lifestyle habits related to water", r"reasons for using water filter",
    r"awareness of water contaminant", r"daily use of filtered water",
    r"frequency of replacing", r"test of the filter.s applicability",
    r"motivation and experience of purchasing",
    r"water purification equipment for improving the quality of life",
    r"the ideas and situations of different types",
    r"whole-house water purification covers",
    r"heavy metal contamination in tap water",
    r"the greatest concern regarding water quality chemicals",
    r"customer motivations and experiences",
    r"showerhead water filter benefits and water quality concerns",
    r"consumer opinions on faucet filtration",
    r"attitudes toward tap water improvement",
    r"buying behavior for residential filtration",
    r"opinions about reducing contaminants",
    r"reducing contaminants in household tap",
    r"views on enhancing the taste and safety",
    r"an overview of how consumers view",
    r"considering factors which impact the adoption",
    r"improving satisfaction by providing better assistance",
    r"assisting in the decision-making process for progressing",
    r"researching the habits of consumers in general",
    r"understanding consumer preference behavior",
    r"research evaluated consumer trust in their local",
    r"the research examined how people establish their daily routines",
    r"list of known and unknown brands",
    r"participants were asked to provide their opinions",
    r"customers were asked to provide their opinions",
    r"conducting market research on overall",
    r"summarizing overall perceptions",
    r"recognizing consumer attitudes,? preferences",
    r"making tap water healthier and better tasting",
    r"exploring consumer behavior and decision",
]

# Wrong-dimension: answers a purchase-reason / personal-experience question instead of survey summary
WRONG_DIMENSION_PATTERNS = [
    r"i bought one because i wanted a convenient solution",
    r"i obviously decided to get a filtration equipment",
    r"i wanted a more cost effective solution",
    r"after detecting discoloration in the tap water",
]


def classify_outro(text: str) -> tuple[str, str]:
    """Return (category, reason). Agent-derived classification."""
    t = text.strip()
    low = t.lower()
    if not t:
        return "blank", "no outro text"
    # gibberish / non-English first
    for pat in GIBBERISH_PATTERNS:
        if re.search(pat, low):
            return "gibberish_nonenglish", "keyboard mash or non-English text"
    if any(h in t for h in NONENGLISH_HINTS):
        return "gibberish_nonenglish", "non-English text"
    # wrong dimension (personal purchase reason instead of survey summary)
    for pat in WRONG_DIMENSION_PATTERNS:
        if re.search(pat, low):
            return "wrong_dimension", "answers a purchase-reason question, not the survey-summary prompt"
    # wrong topic / wrong universe
    for pat, label in WRONG_TOPIC_PATTERNS:
        if re.search(pat, low):
            return "wrong_universe", f"wrong domain ({label})"
    # nonresponsive
    for pat in NONRESPONSIVE_PATTERNS:
        if re.search(pat, low):
            return "survey_meta_nonresponsive", "nonresponsive or vague meta-answer"
    # praise / survey-meta
    for pat in PRAISE_PATTERNS:
        if re.search(pat, low):
            return "survey_meta_praise", "survey-meta praise instead of a topical answer"
    # templated / generic filler research-summary
    templated_hits = sum(1 for pat in TEMPLATED_INDICATORS if re.search(pat, low))
    if templated_hits >= 1:
        # distinguish pure templated (research-title style, no personal grounding) from polished-but-on-topic
        # if it also names the actual product personally, downgrade to adjacent
        has_personal = re.search(r"\bmy\b.*(home|house|kitchen|bathroom|shower|tap|water|filter|family|kid|health)", low)
        if has_personal and templated_hits == 1:
            return "adjacent_fit", "polished but contains personal grounding; review-only"
        return "generic_filler_templated", f"research-summary style, ungrounded ({templated_hits} templated indicators)"
    # otherwise direct fit
    return "direct_fit", "on-topic summary naming the survey subject"


def weight_for_category(cat: str) -> tuple[str, str]:
    """Provisional weight (low/moderate/high) + plain-language rationale."""
    W = {
        "direct_fit": ("low", "On-topic summary. Outro does not support discard; rejection driven by other evidence."),
        "adjacent_fit": ("low", "Polished but grounded. Review-only; not a discard driver from outro alone."),
        "wrong_universe": ("high", "Coherent answer in the wrong domain. Strong prompt-fit failure independent of other signals."),
        "survey_meta_praise": ("moderate", "Describes the survey experience instead of the topic. Nonresponsive; weight rises with recurrence."),
        "survey_meta_nonresponsive": ("moderate", "Vague or nonresponsive. Weight rises when paired with other concerns."),
        "generic_filler_templated": ("moderate", "Research-summary style without personal grounding. Supports synthetic/template hypothesis; weight rises with duplicates or missing supplier."),
        "gibberish_nonenglish": ("high", "Keyboard mash or non-English. Strong usability failure independent of other signals."),
        "wrong_dimension": ("high", "Answers a different question. Strong prompt-fit failure."),
        "blank": ("moderate", "Missing outro. Weight depends on whether the field was required vs routed."),
    }
    return W.get(cat, ("low", "uncategorized"))


def main() -> None:
    t5 = [json.loads(l) for l in (OUT / "t5_population_semantic_packets.ndjson").read_text().splitlines()]
    g3 = [json.loads(l) for l in (OUT / "t3_guardrail_sample.ndjson").read_text().splitlines()]

    # ---- classify t5 outro + other-specify ----
    judgments = []
    cat_counts = Counter()
    for r in t5:
        outro = next((o for o in r["open_ends_verbatim"] if o["field"] == "outro"), None)
        outro_text = str(outro["raw_value"]).strip() if outro else ""
        cat, reason = classify_outro(outro_text)
        w, wrationale = weight_for_category(cat)
        cat_counts[cat] += 1
        # other-specify classification
        other_concerns = []
        for o in r["open_ends_verbatim"]:
            if o["field"] in ("outro", "qUSHHI", "q12", "q31", "qEmploy"):
                continue
            txt = str(o["raw_value"]).strip()
            if not txt:
                continue
            oc, _ = classify_outro(txt)
            if oc not in ("direct_fit", "adjacent_fit", "blank"):
                other_concerns.append({"field": o["field"], "text": txt[:120], "category": oc})
        # matrix straightline: uniform across all 7 distinct product areas
        ms = r.get("matrix_statistics", {})
        flat_matrices = [b for b, v in ms.items() if v.get("unique", 99) == 1 and v.get("answered", 0) >= 3]
        all_seven_flat = len(flat_matrices) >= 7
        # combine evidence families
        rej_dups = r["population_context"]["rejected_only_duplicate_opens"]
        supplier = r["technical"].get("supplier")
        qtime = r["timing"].get("qtime_seconds")
        evidence_families = []
        if cat in ("wrong_universe", "gibberish_nonenglish", "wrong_dimension"):
            evidence_families.append("outro_hard_invalidity")
        elif cat in ("survey_meta_praise", "survey_meta_nonresponsive", "generic_filler_templated"):
            evidence_families.append("outro_soft_concern")
        if rej_dups:
            evidence_families.append("rejected_only_duplicate_open")
        if all_seven_flat:
            evidence_families.append("matrix_flat_across_distinct_products")
        if other_concerns:
            evidence_families.append("other_specify_concern")
        # final weight adjustment: combine
        hard = cat in ("wrong_universe", "gibberish_nonenglish", "wrong_dimension")
        final_weight = w
        if hard and (rej_dups or all_seven_flat):
            final_weight = "severe"
        elif hard:
            final_weight = "high"
        elif cat in ("generic_filler_templated",) and rej_dups:
            final_weight = "high"
        elif w == "moderate" and (rej_dups or all_seven_flat):
            final_weight = "high"
        judgments.append({
            "respondent_id": r["respondent_id"],
            "source_excel_row": r["source_excel_row"],
            "status": r["status"],
            "outro_text": outro_text[:200],
            "outro_category": cat,
            "outro_classification_reason": reason,
            "outro_provisional_weight": w,
            "final_weight": final_weight,
            "weight_rationale": wrationale,
            "supplier": supplier,
            "qtime_seconds": qtime,
            "rejected_only_duplicate_count": len(rej_dups),
            "matrix_flat_across_distinct_products": all_seven_flat,
            "other_specify_concerns": other_concerns,
            "evidence_families": evidence_families,
            "evidence_family_count": len(evidence_families),
        })

    # ---- guardrail cross-check: classify t3 sample ----
    g3_cats = Counter()
    g3_judgments = []
    for r in g3:
        outro = next((o for o in r["open_ends_verbatim"] if o["field"] == "outro"), None)
        outro_text = str(outro["raw_value"]).strip() if outro else ""
        cat, reason = classify_outro(outro_text)
        g3_cats[cat] += 1
        g3_judgments.append({"respondent_id": r["respondent_id"], "outro_text": outro_text[:200], "category": cat})

    combo_counts = Counter(tuple(sorted(j["evidence_families"])) for j in judgments)
    combo_str = {" + ".join(k): v for k, v in combo_counts.items() if k}

    # ---- write artifacts ----
    (OUT / "t5_agent_row_semantic_judgments.jsonl").write_text(
        "\n".join(json.dumps(j, ensure_ascii=False, separators=(",", ":")) for j in judgments) + "\n"
    )
    summary = {
        "t5_total": len(t5),
        "t5_outro_categories": dict(cat_counts),
        "t5_final_weights": dict(Counter(j["final_weight"] for j in judgments)),
        "t5_evidence_family_combinations": combo_str,
        "guardrail_t3_total": len(g3),
        "guardrail_t3_outro_categories": dict(g3_cats),
        "guardrail_false_positive_risk": {
            c: g3_cats.get(c, 0) for c in ("wrong_universe", "gibberish_nonenglish", "wrong_dimension", "survey_meta_praise", "survey_meta_nonresponsive", "generic_filler_templated") if g3_cats.get(c, 0) > 0
        },
    }
    (OUT / "t5_semantic_summary.json").write_text(json.dumps(summary, indent=2))
    (OUT / "t3_guardrail_semantic_judgments.json").write_text(json.dumps(g3_judgments, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
