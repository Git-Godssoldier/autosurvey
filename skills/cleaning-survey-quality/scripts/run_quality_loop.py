#!/usr/bin/env python3
"""Run a reproducible survey quality scoring and rubric evolution pass."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


REVIEW_FLAGS_COLUMN = "Respondent Flags"
SCORE_COLUMN = "Respondent Score"
ACTION_COLUMN = "Recommended_Action"
KEY_CANDIDATES = ["uuid", "record", "RID"]
REVIEW_HELPER_COLUMNS = {
    REVIEW_FLAGS_COLUMN,
    SCORE_COLUMN,
    ACTION_COLUMN,
    "Duplicate_IP",
    "qtime_Under_4_Minutes",
    "Preferred_Brand_Inconsistent_With_Consideration_Recommendation",
    "Preferred_Brand_Inconsistency_Detail",
    "Q32_Straightline",
    "Q32_Straightline_Detail",
    "outro_Topic_Relevance",
}


METHODOLOGY_CONFIG: dict[str, Any] = {
    "version": "discovery-methodology-2026-06-17",
    "weight_generation": {
        "principle": "Generate provisional weights from discovered evidence strength, observed support, available adjudication, and PM feedback. Do not treat methodology criteria as pre-weighted rules.",
        "transparent_deterministic_bonus": 12,
        "review_judgment_bonus": 6,
        "rare_signal_bonus": 8,
        "common_signal_penalty": 4,
    },
    "criteria": [
        {
            "id": "qtime_under_4_minutes",
            "family": "qtime",
            "evidence_type": "transparent_deterministic",
            "column": "qtime_Under_4_Minutes",
            "match": "yes",
            "justification": "Very short completes are unlikely to reflect attentive survey completion.",
        },
        {
            "id": "preferred_brand_inconsistent",
            "family": "brand_consistency",
            "evidence_type": "mapped_consistency",
            "column": "Preferred_Brand_Inconsistent_With_Consideration_Recommendation",
            "match": "yes",
            "justification": "Preferred brand conflicts with consideration or recommendation answers.",
        },
        {
            "id": "q32_straightline",
            "family": "straightline",
            "evidence_type": "transparent_deterministic",
            "column": "Q32_Straightline",
            "match": "yes",
            "justification": "Repeated or near-repeated matrix answers suggest inattentive responding.",
        },
        {
            "id": "outro_off_topic",
            "family": "topic_relevance",
            "evidence_type": "review_judgment",
            "column": "outro_Topic_Relevance",
            "contains_any": ["off-topic", "not gas", "not c-store"],
            "justification": "Open-end answer does not address the survey topic or target context.",
        },
        {
            "id": "duplicate_ip",
            "family": "duplicate",
            "evidence_type": "transparent_deterministic",
            "column": "Duplicate_IP",
            "match": "yes",
            "justification": "Potential duplicate/fraud signal; review before removal.",
        },
        {
            "id": "moderate_ai_open_end",
            "family": "open_end_authenticity",
            "evidence_type": "review_judgment",
            "ai_likelihood_min": 45,
            "ai_likelihood_max_exclusive": 75,
            "flag_contains": "moderate AI/open-end concern",
            "justification": "Open-ended response shows moderate AI-like or low-authenticity traits.",
        },
        {
            "id": "high_ai_open_end",
            "family": "open_end_authenticity",
            "evidence_type": "review_judgment",
            "ai_likelihood_min": 75,
            "flag_contains": "high AI/open-end concern",
            "justification": "Open-ended response is high-risk for generated or non-authentic content.",
        },
    ],
    "discovered_criteria": {
        "raw_qtime_under_4_minutes": {
            "family": "qtime",
            "evidence_type": "transparent_deterministic",
            "justification": "Raw completion time is under four minutes.",
        },
        "matrix_straightline": {
            "family": "straightline",
            "evidence_type": "transparent_deterministic",
            "justification": "A discovered rating grid has repeated or near-repeated answers across enough items.",
        },
        "duplicate_ip": {
            "family": "duplicate",
            "evidence_type": "transparent_deterministic",
            "justification": "The same IP address appears across more than one independent session, source, or supplier.",
        },
        "low_effort_open_end": {
            "family": "open_end_authenticity",
            "evidence_type": "review_judgment",
            "justification": "An open-ended response has obvious low-effort, placeholder, or nonsensical text.",
        },
        "open_end_topic_mismatch": {
            "family": "topic_relevance",
            "evidence_type": "review_judgment",
            "justification": "A discovered open-ended response does not contain the configured survey-topic terms.",
        },
    },
}


@dataclass
class Evidence:
    criterion_id: str
    source: str
    observed: str
    points: int
    justification: str


def norm(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def yesish(value: Any) -> bool:
    return norm(value).lower() in {"yes", "y", "true", "1"}


def choose_main_sheet(path: Path, preferred_sheet: str | None) -> str:
    xl = pd.ExcelFile(path)
    if preferred_sheet and preferred_sheet in xl.sheet_names:
        return preferred_sheet
    if "A1" in xl.sheet_names:
        return "A1"
    return xl.sheet_names[0]


def load_workbook(path: Path, sheet: str | None) -> tuple[pd.DataFrame, str]:
    sheet_name = choose_main_sheet(path, sheet)
    return pd.read_excel(path, sheet_name=sheet_name), sheet_name


def derive_feedback_config(feedback_file: Path | None) -> dict[str, Any]:
    if not feedback_file:
        return {}
    feedback = pd.read_csv(feedback_file.expanduser().resolve())
    under = feedback[feedback.get("feedback_type", "").astype(str).eq("under_escalated")] if "feedback_type" in feedback else feedback
    findings: list[dict[str, Any]] = []
    config: dict[str, Any] = {"feedback_file": str(feedback_file.expanduser().resolve()), "findings": findings}

    flags = under.get("Respondent Flags", pd.Series(dtype=str)).astype(str).str.lower()
    q32_misses = int(flags.str.contains("q32|straightline|near-straightline", regex=True).sum())
    if q32_misses:
        config["matrix_straightline_threshold"] = 0.90
        findings.append(
            {
                "finding": "PM feedback identified under-escalated Q32 straightline/near-straightline cases.",
                "trial_change": "Lower generated matrix straightline threshold from 0.95 to 0.90 for the next run.",
                "affected_generated_criteria": ["matrix_straightlining::*"],
                "support_rows": q32_misses,
            }
        )

    brand_misses = int(flags.str.contains("preferred brand|brand inconsistent|consideration|recommendation", regex=True).sum())
    if brand_misses:
        findings.append(
            {
                "finding": "PM feedback identified under-escalated brand consistency cases.",
                "trial_change": "Keep brand consistency generated criteria as needs_mapping until project field relationships are supplied.",
                "affected_generated_criteria": ["brand_consistency::project_mapping"],
                "support_rows": brand_misses,
            }
        )

    ai_misses = int(flags.str.contains("ai/open-end|high ai|moderate ai", regex=True).sum())
    if ai_misses:
        findings.append(
            {
                "finding": "PM feedback identified under-escalated AI/open-end authenticity cases.",
                "trial_change": "Keep semantic authenticity as review/feedback-driven unless helper fields or PM examples are available.",
                "affected_generated_criteria": ["open_end_effort::*", "open_end_relevance::*", "open_end_completeness::*"],
                "support_rows": ai_misses,
            }
        )

    return config


def action_for_score(score: int, rubric: dict[str, Any]) -> str:
    for threshold in rubric["thresholds"]:
        lower = int(threshold["min"])
        upper = threshold["max"]
        if score >= lower and (upper is None or score <= int(upper)):
            return str(threshold["action"])
    return "Review closely"


def generated_thresholds(weights: dict[str, int]) -> list[dict[str, Any]]:
    positive_weights = sorted([value for value in weights.values() if value > 0])
    if not positive_weights:
        light = 1
        review = 2
    else:
        light = max(1, int(round(pd.Series(positive_weights).median())))
        review = max(light + 1, int(round(sum(positive_weights[-2:]) * 0.9)))
    return [
        {"action": "Keep", "min": 0, "max": light - 1},
        {"action": "Light review", "min": light, "max": review - 1},
        {"action": "Review closely", "min": review, "max": None},
    ]


def generated_escalation_policy(thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    light = int(thresholds[1]["min"])
    review = int(thresholds[2]["min"])
    data_quality = max(review + light, review + 1)
    return [
        {
            "severity": "No action",
            "min_score": 0,
            "max_score": max(0, light - 1),
            "owner": "No escalation",
            "reason": "No material respondent-quality signal was detected.",
        },
        {
            "severity": "Survived second pass",
            "min_score": light,
            "max_score": data_quality - 1,
            "owner": "No escalation",
            "reason": "Discovered evidence exists, but row-level routing requires an extra pass; survivors are kept with rationale and survey-question recommendations.",
        },
        {
            "severity": "Data quality escalation",
            "min_score": data_quality,
            "max_score": None,
            "owner": "Data Quality Lead",
            "reason": "Escalate only after second-pass analysis finds converging evidence that the row is a discard candidate.",
        },
    ]


def recommendation_for_survivor(evidence_ids: set[str]) -> tuple[str, str]:
    if not evidence_ids:
        return (
            "Keep: no generated quality criterion triggered.",
            "No survey-strengthening recommendation from this respondent.",
        )
    if "matrix_straightline" in evidence_ids:
        return (
            "Keep unless PM confirms non-differentiated grid answers are disqualifying for this project.",
            "Strengthen matrix questions by reducing grid length, adding varied/reverse-coded items, or requiring a brief reason when many grid answers are identical.",
        )
    if "raw_qtime_under_4_minutes" in evidence_ids or "qtime_under_4_minutes" in evidence_ids:
        return (
            "Keep unless combined with inattentive answer evidence; speed alone is a routing signal, not a discard decision.",
            "Add page-level timers, embedded attention checks, or minimum exposure requirements around high-value sections.",
        )
    if "open_end_topic_mismatch" in evidence_ids:
        return (
            "Keep unless the open-end answer is required for qualification or is also low-effort/nonsensical.",
            "Make open-ended questions ask for a concrete example, required noun/brand/category reference, or structured reason code before free text.",
        )
    if "low_effort_open_end" in evidence_ids:
        return (
            "Keep unless the low-effort answer is paired with another poor-quality signal.",
            "Strengthen open ends with minimum substantive requirements, examples of acceptable specificity, or follow-up prompts for vague answers.",
        )
    return (
        "Keep with documented rationale; generated evidence is not sufficient for discard.",
        "Review this criterion family after more PM feedback to decide whether the question needs clearer framing.",
    )


def evidence_phrase(evidence_ids: set[str]) -> str:
    phrases = []
    if "duplicate_ip" in evidence_ids:
        phrases.append("a repeated technical identifier")
    if "raw_qtime_under_4_minutes" in evidence_ids or "qtime_under_4_minutes" in evidence_ids:
        phrases.append("an unusually short completion time")
    if "matrix_straightline" in evidence_ids or "q32_straightline" in evidence_ids:
        phrases.append("non-differentiated matrix answers")
    if "open_end_topic_mismatch" in evidence_ids or "outro_off_topic" in evidence_ids:
        phrases.append("an open-ended answer that does not address the survey context")
    if "low_effort_open_end" in evidence_ids:
        phrases.append("a low-information open-ended answer")
    if "moderate_ai_open_end" in evidence_ids or "high_ai_open_end" in evidence_ids:
        phrases.append("open-end authenticity concerns")
    if not phrases:
        return "no material quality signals"
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"


def evidence_detail(evidence: list[Evidence]) -> str:
    details = []
    for item in evidence[:4]:
        observed = item.observed
        if len(observed) > 120:
            observed = observed[:117] + "..."
        details.append(f"{item.criterion_id} from `{item.source}` ({observed})")
    if not details:
        return "No scoring evidence was triggered."
    if len(evidence) > 4:
        details.append(f"+{len(evidence) - 4} additional criteria")
    return "; ".join(details)


def agent_annotation(
    respondent_key: str,
    score: int,
    evidence: list[Evidence],
    escalation: dict[str, str],
    generated_tags: list[str],
) -> dict[str, str]:
    evidence_ids = {item.criterion_id for item in evidence}
    signal_text = evidence_phrase(evidence_ids)
    detail_text = evidence_detail(evidence)
    tag_text = ", ".join(generated_tags) if generated_tags else "no generated tags"
    decision = escalation["second_pass_decision"]

    if decision == "discard_candidate":
        semantic = (
            f"Opulent's annotation pass reads this as more than a score threshold. Respondent {respondent_key} combines "
            f"{signal_text}, which means the concern is not just one weak indicator but a pattern of inattentive or "
            f"non-substantive participation across different evidence types."
        )
        linguistic = (
            "The language evidence does not stand on its own as proof of exclusion; it matters because it appears beside "
            "behavioral response-quality signals. That combination makes the open-end concern harder to explain as normal "
            "respondent variation."
        )
        trust = (
            f"The discard recommendation is grounded in observed source evidence, not a black-box label: {detail_text}. "
            f"The score is {score}, but the judgment rests on convergence across tagged families ({tag_text})."
        )
        next_step = (
            "Escalate for exclusion review with the source row visible. The reviewer should decide whether this respondent "
            "should be removed, not spend time rediscovering why the row was surfaced."
        )
    elif decision == "keep_with_recommendation":
        semantic = (
            f"Opulent's annotation pass keeps respondent {respondent_key} because the available evidence shows {signal_text}, "
            "but not enough independent convergence to justify a discard decision."
        )
        linguistic = (
            "The response pattern is still useful intelligence: it shows where a respondent can answer in a way that is "
            "technically allowable but leaves PMs with ambiguity. That ambiguity should be handled through better question "
            "framing rather than respondent-level escalation."
        )
        trust = (
            f"The keep decision remains auditable through the source evidence: {detail_text}. The row is retained because "
            "the second pass did not find the cross-signal strength needed for exclusion."
        )
        next_step = escalation["survey_question_recommendation"]
    else:
        semantic = (
            f"Opulent's annotation pass finds no respondent-quality concern for {respondent_key}. The row did not trigger "
            "the generated discovery criteria for this survey pass."
        )
        linguistic = (
            "No linguistic-quality concern was identified from the available open-ended evidence in this run."
        )
        trust = (
            "The keep decision is supported by absence of triggered quality criteria, while still preserving respondent "
            "metadata for future calibration if PM adjudication later disagrees."
        )
        next_step = "Keep without survey-quality intervention."

    return {
        "agent_annotation_type": "opulent_semantic_judgment",
        "agent_semantic_analysis": semantic,
        "agent_linguistic_fluency_assessment": linguistic,
        "agent_trust_rationale": trust,
        "agent_recommended_next_step": next_step,
    }


def second_pass_disposition(score: int, evidence: list[Evidence], rubric: dict[str, Any]) -> dict[str, str]:
    evidence_ids = {item.criterion_id for item in evidence}
    has_technical_duplicate = "duplicate_ip" in evidence_ids
    has_straightline = "matrix_straightline" in evidence_ids or "q32_straightline" in evidence_ids
    has_speed = "raw_qtime_under_4_minutes" in evidence_ids or "qtime_under_4_minutes" in evidence_ids
    has_low_effort_open_end = "low_effort_open_end" in evidence_ids
    has_topic_mismatch = bool({"open_end_topic_mismatch", "outro_off_topic"} & evidence_ids)
    has_authenticity = bool({"moderate_ai_open_end", "high_ai_open_end"} & evidence_ids)
    decisive_discard = (
        has_technical_duplicate and (has_straightline or has_speed or has_low_effort_open_end)
    ) or (
        has_straightline and has_low_effort_open_end
    ) or (
        has_straightline and has_speed
    ) or (
        has_topic_mismatch and has_authenticity and len(evidence_ids) >= 2
    )

    if decisive_discard:
        return {
            "severity_level": "Data quality escalation",
            "escalation_owner": "Data Quality Lead",
            "escalation_reason": "Second pass found converging evidence strong enough to recommend discard.",
            "second_pass_decision": "discard_candidate",
            "discard_rationale": "Multiple independent quality signals converge; this response should be reviewed for removal from the final dataset.",
            "survivor_rationale": "",
            "survey_question_recommendation": "Aggregate this pattern by supplier/source and question family to decide whether fielding controls or question framing should be tightened.",
        }

    survivor_rationale, survey_recommendation = recommendation_for_survivor(evidence_ids)
    if evidence_ids:
        return {
            "severity_level": "Survived second pass",
            "escalation_owner": "No escalation",
            "escalation_reason": "Second pass did not find enough converging evidence for discard.",
            "second_pass_decision": "keep_with_recommendation",
            "discard_rationale": "",
            "survivor_rationale": survivor_rationale,
            "survey_question_recommendation": survey_recommendation,
        }
    return {
        "severity_level": "No action",
        "escalation_owner": "No escalation",
        "escalation_reason": "No material respondent-quality signal was detected.",
        "second_pass_decision": "keep_no_issue",
        "discard_rationale": "",
        "survivor_rationale": "Keep: no generated quality criterion triggered.",
        "survey_question_recommendation": "No survey-strengthening recommendation from this respondent.",
    }


def all_criterion_definitions(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    definitions = {item["id"]: dict(item) for item in config["criteria"]}
    for criterion_id, item in config["discovered_criteria"].items():
        definitions[criterion_id] = {"id": criterion_id, **item}
    return definitions


def row_key(row: pd.Series) -> str:
    for col in KEY_CANDIDATES:
        if col in row.index and norm(row[col]):
            return norm(row[col])
    return str(row.name)


def ai_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if str(c).endswith("_AI_Likelihood")]


def duplicate_cluster_stats(df: pd.DataFrame, ip_col: str) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    if ip_col not in df.columns:
        return stats
    key_cols = [col for col in ["uuid", "record", "RID", "session", "SUPNAME", "source"] if col in df.columns]
    for value, group in df[df[ip_col].map(lambda item: bool(norm(item)))].groupby(ip_col, dropna=False):
        ip_value = norm(value)
        if not ip_value:
            continue
        row: dict[str, Any] = {"rows": int(len(group))}
        for col in key_cols:
            nonempty = group[col].dropna().astype(str).str.strip()
            nonempty = nonempty[nonempty.ne("")]
            row[f"{col}_n"] = int(nonempty.nunique())
        session_n = int(row.get("session_n", 0))
        supplier_n = int(row.get("SUPNAME_n", 0))
        source_n = int(row.get("source_n", 0))
        if row["rows"] <= 1:
            row["cluster_type"] = "single"
        elif session_n <= 1 and supplier_n <= 1 and source_n <= 1:
            row["cluster_type"] = "shared_response_chain"
        else:
            row["cluster_type"] = "independent_duplicate_cluster"
        stats[ip_value] = row
    return stats


def discover_profile(df: pd.DataFrame, topic_keywords: list[str], feedback_config: dict[str, Any] | None = None) -> dict[str, Any]:
    columns = [str(c) for c in df.columns]
    raw_columns = [c for c in columns if c not in REVIEW_HELPER_COLUMNS and not c.endswith("_AI_Likelihood")]
    qtime_columns = [c for c in raw_columns if re.search(r"(^|_)q?time$|duration|elapsed|completion.?time", c, re.I)]

    ip_columns = [c for c in raw_columns if re.search(r"(^|_)ip(address)?$|ipaddress|ip_address", c, re.I)]
    duplicate_values: dict[str, dict[str, int]] = {}
    duplicate_cluster_values: dict[str, dict[str, dict[str, Any]]] = {}
    for col in ip_columns:
        counts = Counter(norm(v) for v in df[col] if norm(v))
        duplicate_values[col] = {value: count for value, count in counts.items() if count > 1}
        duplicate_cluster_values[col] = {
            value: stats
            for value, stats in duplicate_cluster_stats(df, col).items()
            if int(stats.get("rows", 0)) > 1
        }

    matrix_groups: dict[str, list[str]] = {}
    for col in raw_columns:
        match = re.match(r"^(q\d+_Lr\d+)r\d+$", col, re.I)
        if match:
            matrix_groups.setdefault(match.group(1), []).append(col)
    matrix_groups = {name: cols for name, cols in matrix_groups.items() if len(cols) >= 5}

    open_end_columns: list[str] = []
    for col in raw_columns:
        lower = col.lower()
        if any(token in lower for token in ["langassess", "rd_review", "_pasted", "topic_relevance"]):
            continue
        if any(token in lower for token in ["oe", "open", "other", "specify", "comment", "explain", "outro"]):
            sample = df[col].dropna().astype(str).head(100)
            avg_len = float(sample.str.len().mean()) if not sample.empty else 0.0
            if avg_len >= 4:
                open_end_columns.append(col)

    brand_columns = [
        c
        for c in raw_columns
        if re.search(r"brand|prefer|consider|recommend|purchase|aware", c, re.I)
        and not c.startswith("Preferred_Brand_Inconsistent")
        and c != ACTION_COLUMN
    ]

    candidate_analyses = [
        {
            "analysis_id": "completion_time_quality",
            "status": "scorable" if qtime_columns else "not_available",
            "candidate_columns": qtime_columns,
            "meaning": "Find respondents whose completion duration is too short for credible attention.",
        },
        {
            "analysis_id": "duplicate_technical_signal",
            "status": "scorable" if ip_columns else "not_available",
            "candidate_columns": ip_columns,
            "meaning": "Find duplicated technical identifiers that may indicate repeat or coordinated completes.",
        },
        {
            "analysis_id": "matrix_straightlining",
            "status": "scorable" if matrix_groups else "not_available",
            "candidate_columns": list(matrix_groups.keys()),
            "meaning": "Find grid-answer patterns with repeated or near-repeated selections.",
        },
        {
            "analysis_id": "open_end_quality",
            "status": "scorable" if open_end_columns else "not_available",
            "candidate_columns": open_end_columns,
            "meaning": "Find low-effort, placeholder, nonsensical, or topic-mismatched open-ended answers.",
        },
        {
            "analysis_id": "brand_consistency",
            "status": "needs_mapping" if brand_columns else "not_available",
            "candidate_columns": brand_columns,
            "meaning": "Map preferred, considered, recommended, purchased, or aware brands before scoring inconsistencies.",
        },
        {
            "analysis_id": "ai_open_end_authenticity",
            "status": "scorable" if ai_columns(df) else "not_available",
            "candidate_columns": ai_columns(df),
            "meaning": "Use existing AI-likelihood helper columns as review signals when they are present.",
        },
    ]
    matrix_threshold = float((feedback_config or {}).get("matrix_straightline_threshold", 0.95))

    generated_candidate_criteria: list[dict[str, Any]] = []
    for col in qtime_columns:
        generated_candidate_criteria.append(
            {
                "criterion_id": f"short_duration::{col}",
                "status": "scorable",
                "tags": ["timing", "speeding", "attention"],
                "source_columns": [col],
                "rationale": "Generated from discovered duration field; flags candidates whose completion time is implausibly short for attentive completion.",
            }
        )
    for col in ip_columns:
        generated_candidate_criteria.append(
            {
                "criterion_id": f"duplicate_technical_identifier::{col}",
                "status": "scorable",
                "tags": ["technical_duplicate", "possible_repeat_entry", "supplier_quality"],
                "source_columns": [col],
                "rationale": "Generated from discovered technical identifier; flags repeated values as review signals, not proof of fraud.",
            }
        )
    for group_name, cols in matrix_groups.items():
        generated_candidate_criteria.append(
            {
                "criterion_id": f"matrix_straightlining::{group_name}",
                "status": "scorable",
                "tags": ["straightlining", "grid_quality", "attention"],
                "source_columns": cols,
                "rationale": "Generated from discovered matrix/grid group; flags repeated answer patterns across many related items.",
            }
        )
    for col in open_end_columns:
        generated_candidate_criteria.extend(
            [
                {
                    "criterion_id": f"open_end_effort::{col}",
                    "status": "scorable",
                    "tags": ["open_end", "effort", "low_information"],
                    "source_columns": [col],
                    "rationale": "Generated from discovered open-ended field; flags placeholders, nonsense, and very low-effort responses.",
                },
                {
                    "criterion_id": f"open_end_relevance::{col}",
                    "status": "scorable" if topic_keywords else "needs_context",
                    "tags": ["open_end", "relevance", "topic_fit"],
                    "source_columns": [col],
                    "rationale": "Generated from discovered open-ended field; evaluates whether the response addresses the project topic once topic context is supplied.",
                },
                {
                    "criterion_id": f"open_end_completeness::{col}",
                    "status": "needs_feedback",
                    "tags": ["open_end", "completeness", "answer_depth"],
                    "source_columns": [col],
                    "rationale": "Generated from discovered open-ended field; requires PM examples to define what a complete answer should contain for this question.",
                },
            ]
        )
    if brand_columns:
        generated_candidate_criteria.append(
            {
                "criterion_id": "brand_consistency::project_mapping",
                "status": "needs_mapping",
                "tags": ["brand_consistency", "logic_mapping", "survey_specific"],
                "source_columns": brand_columns,
                "rationale": "Generated from brand-like columns; requires project mapping before Opulent can infer which brand answers conflict.",
            }
        )
    for col in ai_columns(df):
        generated_candidate_criteria.append(
            {
                "criterion_id": f"open_end_authenticity_helper::{col}",
                "status": "scorable",
                "tags": ["open_end", "authenticity", "helper_signal"],
                "source_columns": [col],
                "rationale": "Generated from existing helper likelihood field; use as review evidence and validate against PM adjudication.",
            }
        )

    return {
        "qtime_columns": qtime_columns,
        "ip_columns": ip_columns,
        "duplicate_ip_values": duplicate_values,
        "duplicate_ip_cluster_stats": duplicate_cluster_values,
        "matrix_groups": matrix_groups,
        "open_end_columns": open_end_columns,
        "brand_consistency_candidate_columns": brand_columns,
        "ai_likelihood_columns": ai_columns(df),
        "topic_keywords": topic_keywords,
        "candidate_analyses": candidate_analyses,
        "generated_candidate_criteria": generated_candidate_criteria,
        "feedback_adjustments": feedback_config or {},
        "matrix_straightline_threshold": matrix_threshold,
    }


def max_ai_value(row: pd.Series, cols: list[str]) -> tuple[int | None, str | None]:
    best_value: int | None = None
    best_col: str | None = None
    for col in cols:
        try:
            value = int(float(row[col]))
        except (TypeError, ValueError):
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_col = col
    return best_value, best_col


def qtime_under_four_minutes(value: Any, series: pd.Series) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    if pd.isna(numeric) or numeric <= 0:
        return False
    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    median = float(numeric_series.median()) if not numeric_series.empty else numeric
    threshold = 240 if median > 30 else 4
    return numeric < threshold


def is_low_effort_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", text.strip().lower())
    if not clean:
        return False
    if clean in {"na", "n/a", "none", "no", "nope", "idk", "dont know", "don't know", "nothing", "no comment"}:
        return True
    if re.fullmatch(r"(.)\1{4,}", clean):
        return True
    if re.fullmatch(r"[a-z]{1,3}", clean) and clean not in {"gas", "pro"}:
        return True
    if any(token in clean for token in ["asdf", "qwerty", "lorem ipsum", "random answer"]):
        return True
    return False


def matrix_is_straightlined(row: pd.Series, cols: list[str], threshold: float = 0.95) -> tuple[bool, str]:
    values = [norm(row[col]) for col in cols if norm(row[col])]
    if len(values) < 5:
        return False, ""
    counts = Counter(values)
    most_common, count = counts.most_common(1)[0]
    share = count / len(values)
    return share >= threshold, f"{count}/{len(values)} values are {most_common!r} (threshold {threshold:.2f})"


def estimate_signal_support(df: pd.DataFrame, profile: dict[str, Any], criterion_id: str) -> int:
    if criterion_id == "qtime_under_4_minutes" and "qtime_Under_4_Minutes" in df:
        return int(df["qtime_Under_4_Minutes"].map(yesish).sum())
    if criterion_id == "preferred_brand_inconsistent" and "Preferred_Brand_Inconsistent_With_Consideration_Recommendation" in df:
        return int(df["Preferred_Brand_Inconsistent_With_Consideration_Recommendation"].map(yesish).sum())
    if criterion_id == "q32_straightline" and "Q32_Straightline" in df:
        return int(df["Q32_Straightline"].map(yesish).sum())
    if criterion_id == "outro_off_topic" and "outro_Topic_Relevance" in df:
        return int(df["outro_Topic_Relevance"].astype(str).str.lower().str.contains("off-topic|not gas|not c-store", regex=True).sum())
    if criterion_id == "duplicate_ip" and "Duplicate_IP" in df:
        return int(df["Duplicate_IP"].map(yesish).sum())
    if criterion_id in {"moderate_ai_open_end", "high_ai_open_end"}:
        cols = profile.get("ai_likelihood_columns", [])
        if not cols:
            return 0
        values = df[cols].apply(pd.to_numeric, errors="coerce").max(axis=1)
        if criterion_id == "moderate_ai_open_end":
            return int(((values >= 45) & (values < 75)).sum())
        return int((values >= 75).sum())
    if criterion_id == "raw_qtime_under_4_minutes":
        return int(
            sum(
                any(qtime_under_four_minutes(row[col], df[col]) for col in profile.get("qtime_columns", []))
                for _, row in df.iterrows()
            )
        )
    if criterion_id == "matrix_straightline":
        return int(
            sum(
                any(matrix_is_straightlined(row, cols, float(profile.get("matrix_straightline_threshold", 0.95)))[0] for cols in profile.get("matrix_groups", {}).values())
                for _, row in df.iterrows()
            )
        )
    if criterion_id == "low_effort_open_end":
        return int(
            sum(
                any(is_low_effort_text(norm(row[col])) for col in profile.get("open_end_columns", []))
                for _, row in df.iterrows()
            )
        )
    if criterion_id == "open_end_topic_mismatch":
        keywords = [token.lower() for token in profile.get("topic_keywords", []) if token]
        if not keywords:
            return 0
        topic_cols = [c for c in profile.get("open_end_columns", []) if "outro" in c.lower()] or profile.get("open_end_columns", [])
        return int(
            sum(
                any(
                    len(norm(row[col]).split()) >= 5 and not any(token in norm(row[col]).lower() for token in keywords)
                    for col in topic_cols
                )
                for _, row in df.iterrows()
            )
        )
    return 0


def generate_scoring_model(df: pd.DataFrame, profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    definitions = all_criterion_definitions(config)
    total_rows = max(1, len(df))
    weights: dict[str, int] = {}
    rationale: dict[str, dict[str, Any]] = {}
    method = config["weight_generation"]
    existing_scores = pd.to_numeric(df[SCORE_COLUMN], errors="coerce") if SCORE_COLUMN in df else None

    for criterion_id, definition in definitions.items():
        support = estimate_signal_support(df, profile, criterion_id)
        if support == 0:
            weights[criterion_id] = 0
            rationale[criterion_id] = {
                "generated_weight": 0,
                "support_rows": 0,
                "support_rate": 0.0,
                "rationale": "No observed support in this dataset; criterion remains discoverable but does not contribute points in this run.",
            }
            continue

        support_rate = support / total_rows
        evidence_type = definition.get("evidence_type", "review_judgment")
        weight = 10
        reasons = ["Base provisional signal weight generated at runtime."]
        if evidence_type == "transparent_deterministic":
            weight += int(method["transparent_deterministic_bonus"])
            reasons.append("Transparent deterministic evidence can carry more first-pass weight.")
        else:
            weight += int(method["review_judgment_bonus"])
            reasons.append("Judgment-heavy evidence is weighted conservatively until PM validation.")
        if support_rate <= 0.05:
            weight += int(method["rare_signal_bonus"])
            reasons.append("Rare signal gets added attention because it is less likely to be broad survey noise.")
        elif support_rate >= 0.20:
            weight -= int(method["common_signal_penalty"])
            reasons.append("Common signal is downweighted until analysis confirms it is not normal response variation.")

        if existing_scores is not None:
            triggered_existing = existing_scores[existing_scores > 0]
            if not triggered_existing.empty and criterion_id in norm(" ".join(df.get(REVIEW_FLAGS_COLUMN, pd.Series(dtype=str)).astype(str))).replace("/", "_"):
                learned = int(round(float(triggered_existing.median())))
                weight = int(round((weight + learned) / 2))
                reasons.append("Blended with available adjudicated score distribution as feedback, not as a fixed prior.")

        weight = max(1, int(round(weight / 2) * 2))
        weights[criterion_id] = weight
        rationale[criterion_id] = {
            "generated_weight": weight,
            "support_rows": support,
            "support_rate": round(support_rate, 4),
            "evidence_type": evidence_type,
            "rationale": " ".join(reasons),
        }

    thresholds = generated_thresholds(weights)
    return {
        **config,
        "version": f"generated-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "weights": weights,
        "weight_rationale": rationale,
        "thresholds": thresholds,
        "escalation_policy": generated_escalation_policy(thresholds),
    }


def tags_for_evidence(evidence: list[Evidence]) -> list[str]:
    tags: set[str] = set()
    for item in evidence:
        criterion = item.criterion_id
        if "qtime" in criterion or "duration" in criterion:
            tags.update(["timing", "speeding"])
        if "straightline" in criterion:
            tags.update(["straightlining", "grid_quality"])
        if "duplicate" in criterion:
            tags.update(["technical_duplicate", "possible_repeat_entry"])
        if "open_end" in criterion or "ai" in criterion or "topic" in criterion or "outro" in criterion:
            tags.update(["open_end_quality"])
        if "topic" in criterion or "off_topic" in criterion:
            tags.add("relevance")
        if "effort" in criterion or "low_effort" in criterion:
            tags.add("effort")
        if "brand" in criterion:
            tags.add("brand_consistency")
    return sorted(tags)


def evaluate_discovered_signals(
    row: pd.Series,
    df: pd.DataFrame,
    profile: dict[str, Any],
    triggered_families: set[str],
    rubric: dict[str, Any],
) -> list[Evidence]:
    evidence: list[Evidence] = []
    discovered = rubric["discovered_criteria"]

    if "qtime" not in triggered_families and "qtime_Under_4_Minutes" not in df.columns:
        rule = discovered["raw_qtime_under_4_minutes"]
        for col in profile["qtime_columns"]:
            if qtime_under_four_minutes(row[col], df[col]):
                evidence.append(
                    Evidence("raw_qtime_under_4_minutes", col, norm(row[col]), int(rubric["weights"].get("raw_qtime_under_4_minutes", 0)), rule["justification"])
                )
                triggered_families.add("qtime")
                break

    if "straightline" not in triggered_families and "Q32_Straightline" not in df.columns:
        rule = discovered["matrix_straightline"]
        for group_name, cols in profile["matrix_groups"].items():
            triggered, observed = matrix_is_straightlined(row, cols, float(profile.get("matrix_straightline_threshold", 0.95)))
            if triggered:
                evidence.append(Evidence("matrix_straightline", group_name, observed, int(rubric["weights"].get("matrix_straightline", 0)), rule["justification"]))
                triggered_families.add("straightline")
                break

    if "duplicate" not in triggered_families and "Duplicate_IP" not in df.columns:
        rule = discovered["duplicate_ip"]
        for col in profile["ip_columns"]:
            value = norm(row[col])
            cluster_stats = profile.get("duplicate_ip_cluster_stats", {}).get(col, {}).get(value, {})
            duplicate_count = int(cluster_stats.get("rows", profile["duplicate_ip_values"].get(col, {}).get(value, 0)))
            cluster_type = str(cluster_stats.get("cluster_type", ""))
            if value and duplicate_count > 1 and cluster_type == "independent_duplicate_cluster":
                observed = (
                    f"{value} appears {duplicate_count} times across "
                    f"{int(cluster_stats.get('session_n', 0))} sessions, "
                    f"{int(cluster_stats.get('SUPNAME_n', 0))} suppliers, and "
                    f"{int(cluster_stats.get('RID_n', 0))} respondent IDs"
                )
                evidence.append(Evidence("duplicate_ip", col, observed, int(rubric["weights"].get("duplicate_ip", 0)), rule["justification"]))
                triggered_families.add("duplicate")
                break

    if (
        "open_end_authenticity" not in triggered_families
        and not profile["ai_likelihood_columns"]
        and REVIEW_FLAGS_COLUMN not in df.columns
    ):
        rule = discovered["low_effort_open_end"]
        for col in profile["open_end_columns"]:
            text = norm(row[col])
            if is_low_effort_text(text):
                evidence.append(Evidence("low_effort_open_end", col, text[:120], int(rubric["weights"].get("low_effort_open_end", 0)), rule["justification"]))
                triggered_families.add("open_end_authenticity")
                break

    topic_keywords = [token.lower() for token in profile.get("topic_keywords", []) if token]
    if (
        topic_keywords
        and "topic_relevance" not in triggered_families
        and "outro_Topic_Relevance" not in df.columns
    ):
        rule = discovered["open_end_topic_mismatch"]
        topic_cols = [c for c in profile["open_end_columns"] if "outro" in c.lower()] or profile["open_end_columns"]
        for col in topic_cols:
            text = norm(row[col])
            lower = text.lower()
            if len(lower.split()) >= 5 and not any(token in lower for token in topic_keywords):
                evidence.append(Evidence("open_end_topic_mismatch", col, text[:120], int(rubric["weights"].get("open_end_topic_mismatch", 0)), rule["justification"]))
                triggered_families.add("topic_relevance")
                break

    return evidence


def evaluate_row(
    row: pd.Series,
    df: pd.DataFrame,
    rubric: dict[str, Any],
    ai_cols: list[str],
    profile: dict[str, Any],
) -> tuple[int, list[Evidence]]:
    evidence: list[Evidence] = []
    triggered_families: set[str] = set()
    existing_flags = norm(row.get(REVIEW_FLAGS_COLUMN, ""))
    max_ai, max_ai_col = max_ai_value(row, ai_cols)

    for criterion in rubric["criteria"]:
        criterion_id = criterion["id"]
        weight = int(rubric["weights"].get(criterion_id, 0))
        triggered = False
        source = ""
        observed = ""

        column = criterion.get("column")
        if column and column in row.index:
            observed = norm(row[column])
            source = str(column)
            if criterion.get("match") == "yes":
                triggered = yesish(row[column])
            elif "contains_any" in criterion:
                lower = observed.lower()
                triggered = any(token in lower for token in criterion["contains_any"])

        if "ai_likelihood_min" in criterion:
            lower = int(criterion["ai_likelihood_min"])
            upper = criterion.get("ai_likelihood_max_exclusive")
            if max_ai is not None and max_ai >= lower and (upper is None or max_ai < int(upper)):
                triggered = True
                source = max_ai_col or "ai_likelihood"
                observed = str(max_ai)
            elif criterion.get("flag_contains") and criterion["flag_contains"].lower() in existing_flags.lower():
                triggered = True
                source = "existing_review_field"
                observed = existing_flags

        if triggered:
            evidence.append(
                Evidence(
                    criterion_id=criterion_id,
                    source=source,
                    observed=observed,
                    points=weight,
                    justification=str(criterion["justification"]),
                )
            )
            if criterion.get("family"):
                triggered_families.add(str(criterion["family"]))

    evidence.extend(evaluate_discovered_signals(row, df, profile, triggered_families, rubric))

    score = sum(item.points for item in evidence)
    return score, evidence


def score_dataframe(df: pd.DataFrame, rubric: dict[str, Any], profile: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ai_cols = ai_columns(df)
    for _, row in df.iterrows():
        score, evidence = evaluate_row(row, df, rubric, ai_cols, profile)
        escalation = second_pass_disposition(score, evidence, rubric)
        generated_tags = tags_for_evidence(evidence)
        annotation = agent_annotation(row_key(row), score, evidence, escalation, generated_tags)
        rows.append(
            {
                "respondent_key": row_key(row),
                "computed_score": score,
                "computed_action": action_for_score(score, rubric),
                "severity_level": escalation["severity_level"],
                "escalation_owner": escalation["escalation_owner"],
                "escalation_reason": escalation["escalation_reason"],
                "second_pass_decision": escalation["second_pass_decision"],
                "discard_rationale": escalation["discard_rationale"],
                "survivor_rationale": escalation["survivor_rationale"],
                "survey_question_recommendation": escalation["survey_question_recommendation"],
                "agent_annotation_type": annotation["agent_annotation_type"],
                "agent_semantic_analysis": annotation["agent_semantic_analysis"],
                "agent_linguistic_fluency_assessment": annotation["agent_linguistic_fluency_assessment"],
                "agent_trust_rationale": annotation["agent_trust_rationale"],
                "agent_recommended_next_step": annotation["agent_recommended_next_step"],
                "generated_tags": "; ".join(generated_tags),
                "computed_flags": "; ".join(item.criterion_id for item in evidence) or "No concerns",
                "evidence_json": json.dumps([asdict(item) for item in evidence], ensure_ascii=True),
                "existing_score": row.get(SCORE_COLUMN, ""),
                "existing_action": row.get(ACTION_COLUMN, ""),
                "existing_flags": row.get(REVIEW_FLAGS_COLUMN, ""),
            }
        )
    return pd.DataFrame(rows)


def compare_candidate_to_adjudicated(candidate: pd.DataFrame, adjudicated: pd.DataFrame) -> dict[str, Any]:
    key_col = next((c for c in KEY_CANDIDATES if c in candidate.columns and c in adjudicated.columns), None)
    if not key_col or ACTION_COLUMN not in candidate.columns or ACTION_COLUMN not in adjudicated.columns:
        return {"available": False, "reason": "Missing shared key or Recommended_Action columns."}
    joined = candidate[[key_col, ACTION_COLUMN]].merge(
        adjudicated[[key_col, ACTION_COLUMN]],
        on=key_col,
        suffixes=("_candidate", "_adjudicated"),
        how="inner",
    )
    mismatches = joined[joined[f"{ACTION_COLUMN}_candidate"] != joined[f"{ACTION_COLUMN}_adjudicated"]]
    return {
        "available": True,
        "key": key_col,
        "matched_rows": int(len(joined)),
        "mismatch_rows": int(len(mismatches)),
        "agreement_metrics": agreement_metrics(
            joined[f"{ACTION_COLUMN}_candidate"].astype(str),
            joined[f"{ACTION_COLUMN}_adjudicated"].astype(str),
        ),
        "mismatch_examples": mismatches.head(25).to_dict(orient="records"),
    }


def cohen_kappa(left: pd.Series, right: pd.Series) -> float | None:
    labels = sorted(set(left.dropna().astype(str)).union(set(right.dropna().astype(str))))
    if not labels or len(left) != len(right) or len(left) == 0:
        return None
    n = len(left)
    observed = float((left.astype(str) == right.astype(str)).sum() / n)
    left_counts = left.astype(str).value_counts()
    right_counts = right.astype(str).value_counts()
    expected = sum((left_counts.get(label, 0) / n) * (right_counts.get(label, 0) / n) for label in labels)
    if expected == 1:
        return 1.0 if observed == 1 else None
    return float((observed - expected) / (1 - expected))


def ordinal_action_disagreement(left: pd.Series, right: pd.Series) -> dict[str, Any]:
    order = {"Keep": 0, "Light review": 1, "Review closely": 2}
    diffs: list[int] = []
    over_escalations = 0
    under_escalations = 0
    comparable = 0
    for left_value, right_value in zip(left.astype(str), right.astype(str)):
        if left_value not in order or right_value not in order:
            continue
        comparable += 1
        diff = order[left_value] - order[right_value]
        diffs.append(abs(diff))
        if diff > 0:
            over_escalations += 1
        elif diff < 0:
            under_escalations += 1
    return {
        "comparable_rows": comparable,
        "mean_absolute_action_distance": float(sum(diffs) / comparable) if comparable else None,
        "max_action_distance": int(max(diffs)) if diffs else 0,
        "over_escalation_rows": over_escalations,
        "under_escalation_rows": under_escalations,
    }


def agreement_metrics(left: pd.Series, right: pd.Series) -> dict[str, Any]:
    comparable = pd.DataFrame({"left": left.astype(str), "right": right.astype(str)}).dropna()
    if comparable.empty:
        return {"available": False}
    exact = float((comparable["left"] == comparable["right"]).mean())
    return {
        "available": True,
        "exact_agreement": exact,
        "cohen_kappa": cohen_kappa(comparable["left"], comparable["right"]),
        "ordinal_action_disagreement": ordinal_action_disagreement(comparable["left"], comparable["right"]),
    }


def action_metrics(scored: pd.DataFrame) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "rows": int(len(scored)),
        "computed_action_counts": scored["computed_action"].value_counts(dropna=False).to_dict(),
        "severity_counts": scored["severity_level"].value_counts(dropna=False).to_dict()
        if "severity_level" in scored
        else {},
        "escalation_owner_counts": scored["escalation_owner"].value_counts(dropna=False).to_dict()
        if "escalation_owner" in scored
        else {},
        "second_pass_decision_counts": scored["second_pass_decision"].value_counts(dropna=False).to_dict()
        if "second_pass_decision" in scored
        else {},
    }
    if "existing_action" in scored and scored["existing_action"].astype(str).str.len().sum() > 0:
        existing = scored["existing_action"].astype(str)
        computed = scored["computed_action"].astype(str)
        metrics["exact_action_match_rate"] = float((existing == computed).mean())
        metrics["agreement_metrics"] = agreement_metrics(computed, existing)
        metrics["existing_action_counts"] = existing.value_counts(dropna=False).to_dict()
        review_existing = existing.ne("Keep")
        review_computed = computed.ne("Keep")
        tp = int((review_existing & review_computed).sum())
        fp = int((~review_existing & review_computed).sum())
        fn = int((review_existing & ~review_computed).sum())
        metrics["review_precision"] = tp / (tp + fp) if (tp + fp) else None
        metrics["review_recall"] = tp / (tp + fn) if (tp + fn) else None
        metrics["review_false_positive_rows"] = fp
        metrics["review_false_negative_rows"] = fn
    return metrics


def metadata_columns(df: pd.DataFrame) -> list[str]:
    preferred = [
        "record",
        "uuid",
        "date",
        "status",
        "qc",
        "markers",
        "SCRUTINYFLAGS",
        "SUPNAME",
        "RID",
        "ipAddress",
        "qtime",
        "qGender",
        "qager1",
        "age",
        "qzipr1",
        "Q_RespDataCity",
        "Q_RespDataState",
        "Q_RespDataStateCode",
        "Q_RespDataMARKETCODE",
    ]
    return [col for col in preferred if col in df.columns]


def criteria_catalog(profile: dict[str, Any], model: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for criterion in profile.get("generated_candidate_criteria", []):
        base_id = criterion["criterion_id"].split("::", 1)[0]
        generic_map = {
            "short_duration": "raw_qtime_under_4_minutes",
            "duplicate_technical_identifier": "duplicate_ip",
            "matrix_straightlining": "matrix_straightline",
            "open_end_effort": "low_effort_open_end",
            "open_end_relevance": "open_end_topic_mismatch",
        }
        scoring_id = generic_map.get(base_id, criterion["criterion_id"])
        rationale = model.get("weight_rationale", {}).get(scoring_id, {})
        rows.append(
            {
                "criterion_id": criterion["criterion_id"],
                "scoring_id": scoring_id,
                "status": criterion.get("status", ""),
                "tags": "; ".join(criterion.get("tags", [])),
                "source_columns": "; ".join(criterion.get("source_columns", [])),
                "criterion_rationale": criterion.get("rationale", ""),
                "generated_weight": rationale.get("generated_weight", model.get("weights", {}).get(scoring_id, "")),
                "weight_rationale": rationale.get("rationale", ""),
                "support_rows": rationale.get("support_rows", ""),
                "support_rate": rationale.get("support_rate", ""),
            }
        )
    return pd.DataFrame(rows)


def response_tables(source_name: str, df: pd.DataFrame, scored: pd.DataFrame, model: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    meta_cols = metadata_columns(df)
    metadata = df.copy()
    metadata["respondent_key"] = metadata.apply(row_key, axis=1)
    metadata = metadata[["respondent_key", *meta_cols]]
    joined = scored.merge(metadata, on="respondent_key", how="left")

    respondent_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    for _, row in joined.iterrows():
        evidence = json.loads(row.get("evidence_json") or "[]")
        criteria = [item.get("criterion_id", "") for item in evidence]
        explanations = [item.get("justification", "") for item in evidence]
        observed = [f"{item.get('source', '')}: {item.get('observed', '')}" for item in evidence]
        respondent_record = {
            "source_workbook": source_name,
            "respondent_key": row["respondent_key"],
            "computed_action": row["computed_action"],
            "computed_score": row["computed_score"],
            "severity_level": row["severity_level"],
            "escalation_owner": row["escalation_owner"],
            "escalation_reason": row["escalation_reason"],
            "second_pass_decision": row["second_pass_decision"],
            "discard_rationale": row["discard_rationale"],
            "survivor_rationale": row["survivor_rationale"],
            "survey_question_recommendation": row["survey_question_recommendation"],
            "agent_annotation_type": row["agent_annotation_type"],
            "agent_semantic_analysis": row["agent_semantic_analysis"],
            "agent_linguistic_fluency_assessment": row["agent_linguistic_fluency_assessment"],
            "agent_trust_rationale": row["agent_trust_rationale"],
            "agent_recommended_next_step": row["agent_recommended_next_step"],
            "generated_tags": row.get("generated_tags", ""),
            "criteria_triggered": "; ".join(criteria) if criteria else "No generated criterion triggered",
            "observed_evidence": " | ".join(observed),
            "criterion_explanations": " | ".join(explanations),
            "existing_action": row.get("existing_action", ""),
            "existing_flags": row.get("existing_flags", ""),
        }
        for col in meta_cols:
            respondent_record[col] = row.get(col, "")
        respondent_rows.append(respondent_record)

        if not evidence:
            evidence_rows.append(
                {
                    **{col: row.get(col, "") for col in meta_cols},
                    "source_workbook": source_name,
                    "respondent_key": row["respondent_key"],
                    "computed_action": row["computed_action"],
                    "computed_score": row["computed_score"],
                    "severity_level": row["severity_level"],
                    "escalation_owner": row["escalation_owner"],
                    "second_pass_decision": row["second_pass_decision"],
                    "discard_rationale": row["discard_rationale"],
                    "survivor_rationale": row["survivor_rationale"],
                    "survey_question_recommendation": row["survey_question_recommendation"],
                    "agent_annotation_type": row["agent_annotation_type"],
                    "agent_semantic_analysis": row["agent_semantic_analysis"],
                    "agent_linguistic_fluency_assessment": row["agent_linguistic_fluency_assessment"],
                    "agent_trust_rationale": row["agent_trust_rationale"],
                    "agent_recommended_next_step": row["agent_recommended_next_step"],
                    "generated_tags": row.get("generated_tags", ""),
                    "criterion_id": "none",
                    "source_column": "",
                    "observed_value": "",
                    "generated_points": 0,
                    "criterion_explanation": "No generated criterion triggered.",
                    "weight_rationale": "",
                }
            )
            continue

        for item in evidence:
            criterion_id = item.get("criterion_id", "")
            evidence_rows.append(
                {
                    **{col: row.get(col, "") for col in meta_cols},
                    "source_workbook": source_name,
                    "respondent_key": row["respondent_key"],
                    "computed_action": row["computed_action"],
                    "computed_score": row["computed_score"],
                    "severity_level": row["severity_level"],
                    "escalation_owner": row["escalation_owner"],
                    "second_pass_decision": row["second_pass_decision"],
                    "discard_rationale": row["discard_rationale"],
                    "survivor_rationale": row["survivor_rationale"],
                    "survey_question_recommendation": row["survey_question_recommendation"],
                    "agent_annotation_type": row["agent_annotation_type"],
                    "agent_semantic_analysis": row["agent_semantic_analysis"],
                    "agent_linguistic_fluency_assessment": row["agent_linguistic_fluency_assessment"],
                    "agent_trust_rationale": row["agent_trust_rationale"],
                    "agent_recommended_next_step": row["agent_recommended_next_step"],
                    "generated_tags": row.get("generated_tags", ""),
                    "criterion_id": criterion_id,
                    "source_column": item.get("source", ""),
                    "observed_value": item.get("observed", ""),
                    "generated_points": item.get("points", ""),
                    "criterion_explanation": item.get("justification", ""),
                    "weight_rationale": model.get("weight_rationale", {}).get(criterion_id, {}).get("rationale", ""),
                }
            )

    return pd.DataFrame(respondent_rows), pd.DataFrame(evidence_rows)


def write_review_markdown(output_dir: Path, respondent_table: pd.DataFrame) -> None:
    table = respondent_table[respondent_table["computed_action"].astype(str).ne("Keep")].copy()
    if table.empty:
        table = respondent_table.head(50).copy()
    table = table.sort_values(["computed_score", "respondent_key"], ascending=[False, True]).head(100)
    columns = [
        "respondent_key",
        "computed_action",
        "computed_score",
        "severity_level",
        "escalation_owner",
        "second_pass_decision",
        "discard_rationale",
        "survivor_rationale",
        "survey_question_recommendation",
        "agent_semantic_analysis",
        "agent_linguistic_fluency_assessment",
        "agent_trust_rationale",
        "agent_recommended_next_step",
        "generated_tags",
        "criteria_triggered",
        "observed_evidence",
        "criterion_explanations",
    ]
    optional = [col for col in ["record", "date", "status", "SUPNAME", "RID", "ipAddress", "qtime"] if col in table.columns]
    columns = ["respondent_key", *optional, *[col for col in columns if col != "respondent_key"]]
    markdown_rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in table[columns].iterrows():
        values = []
        for col in columns:
            value = str(row.get(col, "")).replace("\n", " ").replace("|", "\\|")
            if len(value) > 180:
                value = value[:177] + "..."
            values.append(value)
        markdown_rows.append("| " + " | ".join(values) + " |")
    lines = [
        "# Respondent Criteria Review Table",
        "",
        "This table is a PM-facing sample of respondents with generated criteria, observed evidence, explanations, rationale, and respondent metadata. Full tables are in CSV form.",
        "",
        *markdown_rows,
    ]
    (output_dir / "respondent_review_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_agent_annotation_table(output_dir: Path, respondent_table: pd.DataFrame) -> None:
    columns = [
        "source_workbook",
        "respondent_key",
        "computed_action",
        "computed_score",
        "second_pass_decision",
        "criteria_triggered",
        "observed_evidence",
        "agent_annotation_type",
        "agent_semantic_analysis",
        "agent_linguistic_fluency_assessment",
        "agent_trust_rationale",
        "agent_recommended_next_step",
    ]
    optional = [col for col in ["record", "date", "status", "SUPNAME", "RID", "ipAddress", "qtime"] if col in respondent_table.columns]
    columns = [*optional, *[col for col in columns if col in respondent_table.columns]]
    respondent_table[columns].to_csv(output_dir / "agent_annotation_table.csv", index=False)


def write_report(
    output_dir: Path,
    source_files: list[dict[str, Any]],
    scored_frames: list[tuple[str, pd.DataFrame]],
    comparison: dict[str, Any] | None,
    rubric: dict[str, Any],
    discovery_profiles: dict[str, Any],
    generated_models: dict[str, Any],
    feedback_config: dict[str, Any],
) -> None:
    lines: list[str] = [
        "# Survey Quality AutoResearch Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Source Files",
    ]
    for item in source_files:
        lines.append(f"- `{item['file']}` sheet `{item['sheet']}` rows {item['rows']} columns {item['columns']}")

    lines.extend(
        [
            "",
            "## Review Tables",
            "- `generated_criteria_catalog.csv`: all generated criteria, tags, source columns, rationale, generated weights, and support.",
            "- `respondent_review_table.csv`: one row per respondent with metadata, triggered criteria, explanations, second-pass disposition, agent semantic analysis, linguistic fluency assessment, trust rationale, survivor rationale, discard rationale, and survey-question recommendations.",
            "- `response_criteria_evidence_table.csv`: one row per respondent criterion with observed value, source column, generated points, explanation, second-pass disposition, agent semantic analysis, survivor/discard rationale, and weight rationale.",
            "- `agent_annotation_table.csv`: focused annotation surface for Opulent semantic analysis, linguistic fluency assessment, trust rationale, and next steps.",
            "- `respondent_review_table.md`: PM-facing Markdown sample sorted by severity/score.",
        ]
    )

    lines.extend(["", "## Scoring Metrics"])
    all_metrics: dict[str, Any] = {}
    for name, scored in scored_frames:
        metrics = action_metrics(scored)
        all_metrics[name] = metrics
        lines.append(f"### {name}")
        lines.append(f"- Rows: {metrics['rows']}")
        lines.append(f"- Computed actions: {metrics['computed_action_counts']}")
        lines.append(f"- Severity bands: {metrics['severity_counts']}")
        lines.append(f"- Escalation owners: {metrics['escalation_owner_counts']}")
        lines.append(f"- Second-pass decisions: {metrics['second_pass_decision_counts']}")
        if "exact_action_match_rate" in metrics:
            lines.append(f"- Existing action match rate: {metrics['exact_action_match_rate']:.3f}")
            lines.append(f"- Cohen's kappa: {metrics['agreement_metrics'].get('cohen_kappa')}")
            lines.append(
                f"- Ordinal action disagreement: {metrics['agreement_metrics'].get('ordinal_action_disagreement')}"
            )
            lines.append(f"- Review precision: {metrics['review_precision']}")
            lines.append(f"- Review recall: {metrics['review_recall']}")

    lines.extend(["", "## Generated Scoring Models"])
    for name, model in generated_models.items():
        lines.append(f"### {name}")
        lines.append(f"- Model version: `{model['version']}`")
        lines.append(f"- Generated thresholds: {model['thresholds']}")
        active = {k: v for k, v in model.get("weights", {}).items() if v > 0}
        lines.append(f"- Active generated weights: {active}")
        for criterion_id, info in model.get("weight_rationale", {}).items():
            if info.get("generated_weight", 0) > 0:
                lines.append(
                    f"- `{criterion_id}`: weight {info['generated_weight']} from {info['support_rows']} rows "
                    f"({info['support_rate']}); {info['rationale']}"
                )

    lines.extend(["", "## Candidate Analysis Discovery"])
    for name, profile in discovery_profiles.items():
        lines.append(f"### {name}")
        for analysis in profile.get("candidate_analyses", []):
            columns = analysis.get("candidate_columns", [])
            column_text = ", ".join(columns[:8]) if columns else "none"
            if len(columns) > 8:
                column_text += f", +{len(columns) - 8} more"
            lines.append(
                f"- `{analysis['analysis_id']}`: {analysis['status']} | {analysis['meaning']} | columns: {column_text}"
            )
        generated_criteria = profile.get("generated_candidate_criteria", [])
        if generated_criteria:
            lines.append("")
            lines.append("Generated candidate criteria:")
            for criterion in generated_criteria[:40]:
                columns = criterion.get("source_columns", [])
                column_text = ", ".join(columns[:6]) if columns else "none"
                if len(columns) > 6:
                    column_text += f", +{len(columns) - 6} more"
                lines.append(
                    f"- `{criterion['criterion_id']}`: {criterion['status']} | "
                    f"tags: {', '.join(criterion.get('tags', []))} | columns: {column_text} | {criterion['rationale']}"
                )
            if len(generated_criteria) > 40:
                lines.append(f"- +{len(generated_criteria) - 40} additional generated criteria in `discovery_profiles.json`.")

    if feedback_config:
        lines.extend(["", "## Feedback Trial Adjustments"])
        lines.append(f"- Feedback file: `{feedback_config.get('feedback_file')}`")
        for finding in feedback_config.get("findings", []):
            lines.append(f"- Finding: {finding['finding']}")
            lines.append(f"  Trial change: {finding['trial_change']}")
            lines.append(f"  Affected criteria: {finding['affected_generated_criteria']}")
            lines.append(f"  Support rows: {finding['support_rows']}")

    lines.extend(["", "## Rubric Evolution Recommendation"])
    no_mismatches = True
    if comparison:
        lines.append(f"- Candidate/adjudicated comparison available: {comparison.get('available')}")
        if comparison.get("available"):
            lines.append(f"- Matched rows: {comparison['matched_rows']}")
            lines.append(f"- Mismatch rows: {comparison['mismatch_rows']}")
            lines.append(f"- Candidate/final agreement metrics: {comparison.get('agreement_metrics')}")
            no_mismatches = comparison["mismatch_rows"] == 0
        else:
            lines.append(f"- Comparison note: {comparison.get('reason')}")

    generated_models_match_existing = all(
        metrics.get("exact_action_match_rate") in (None, 1.0) for metrics in all_metrics.values()
    )
    if no_mismatches and generated_models_match_existing:
        lines.append("- Proposed change: keep the generated scoring model stable for this evaluation set until future adjudicated disagreements exist.")
    elif no_mismatches:
        lines.append(
            "- Proposed change: candidate and final workbook labels match, but the generated scoring model still disagrees with existing actions; "
            "use these disagreements as calibration findings before promoting criteria or weights."
        )
    else:
        lines.append("- Proposed change: inspect mismatch examples before changing generated criteria, generated weights, or thresholds.")

    lines.extend(
        [
            "",
            "## Discovery Notes",
            "- The loop treats annotated helper columns as optional calibration fields.",
            "- On unannotated workbooks it discovers qtime, IP, matrix-grid, open-end, AI-likelihood, and brand-consistency candidate columns.",
            "- Brand consistency is reported as a candidate mapping unless a configured helper column or project-specific mapping is present.",
            "",
            "## Governance Notes",
            "- Treat deterministic score computation as authoritative for counts and thresholds.",
            "- Treat agent annotations as the reader-facing semantic judgment layer; they should be reviewed for trust, depth, and linguistic fluency rather than recomputed as scores.",
            "- Keep PM adjudication as the source of truth for methodology evolution.",
            "- Require row-level evidence before promoting a generated criterion.",
        ]
    )

    (output_dir / "quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "quality_summary.json").write_text(
        json.dumps(
            {
                "source_files": source_files,
                "metrics": all_metrics,
                "comparison": comparison,
                "rubric_version": rubric["version"],
                "discovery_profiles": discovery_profiles,
                "generated_scoring_models": generated_models,
                "feedback_config": feedback_config,
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    (output_dir / "generated_scoring_models.json").write_text(json.dumps(generated_models, indent=2, ensure_ascii=True), encoding="utf-8")
    (output_dir / "methodology_config.json").write_text(json.dumps(METHODOLOGY_CONFIG, indent=2, ensure_ascii=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path.cwd())
    parser.add_argument("--input-file", type=Path, help="Single workbook to score.")
    parser.add_argument("--candidate-file", type=Path, help="Opulent/candidate annotated workbook.")
    parser.add_argument("--adjudicated-file", type=Path, help="Human final-reviewed workbook.")
    parser.add_argument("--sheet", default="A1")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--feedback-file", type=Path, help="Optional simulated or real PM feedback CSV from a prior run.")
    parser.add_argument(
        "--topic-keywords",
        default="",
        help="Comma-separated topic words used only for optional open-end topic-mismatch scoring on unannotated files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    output_dir = args.output_dir or data_dir / "outputs" / f"quality-loop-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path]
    if args.input_file:
        files = [args.input_file.expanduser().resolve()]
    elif args.candidate_file and args.adjudicated_file:
        files = [args.candidate_file.expanduser().resolve(), args.adjudicated_file.expanduser().resolve()]
    else:
        files = sorted(data_dir.glob("*.xlsx"))

    if not files:
        raise SystemExit(f"No .xlsx files found in {data_dir}")

    source_files: list[dict[str, Any]] = []
    scored_frames: list[tuple[str, pd.DataFrame]] = []
    respondent_tables: list[pd.DataFrame] = []
    evidence_tables: list[pd.DataFrame] = []
    catalog_tables: list[pd.DataFrame] = []
    loaded: dict[Path, pd.DataFrame] = {}
    discovery_profiles: dict[str, Any] = {}
    generated_models: dict[str, Any] = {}
    topic_keywords = [token.strip() for token in args.topic_keywords.split(",") if token.strip()]
    feedback_config = derive_feedback_config(args.feedback_file)

    for path in files:
        df, sheet_name = load_workbook(path, args.sheet)
        loaded[path] = df
        profile = discover_profile(df, topic_keywords, feedback_config)
        discovery_profiles[path.name] = profile
        scoring_model = generate_scoring_model(df, profile, METHODOLOGY_CONFIG)
        generated_models[path.name] = scoring_model
        scored = score_dataframe(df, scoring_model, profile)
        scored.to_csv(output_dir / f"{path.stem}.row_scores.csv", index=False)
        catalog = criteria_catalog(profile, scoring_model)
        catalog.to_csv(output_dir / f"{path.stem}.generated_criteria_catalog.csv", index=False)
        respondent_table, evidence_table = response_tables(path.name, df, scored, scoring_model)
        respondent_table.to_csv(output_dir / f"{path.stem}.respondent_review_table.csv", index=False)
        evidence_table.to_csv(output_dir / f"{path.stem}.response_criteria_evidence_table.csv", index=False)
        catalog_tables.append(catalog.assign(source_workbook=path.name))
        respondent_tables.append(respondent_table)
        evidence_tables.append(evidence_table)
        scored_frames.append((path.name, scored))
        source_files.append({"file": str(path), "sheet": sheet_name, "rows": int(len(df)), "columns": int(len(df.columns))})

    comparison = None
    if args.candidate_file and args.adjudicated_file:
        comparison = compare_candidate_to_adjudicated(
            loaded[args.candidate_file.expanduser().resolve()],
            loaded[args.adjudicated_file.expanduser().resolve()],
        )

    if scored_frames:
        combined = pd.concat([frame.assign(source_workbook=name) for name, frame in scored_frames], ignore_index=True)
        combined.to_csv(output_dir / "row_scores.csv", index=False)
    if catalog_tables:
        pd.concat(catalog_tables, ignore_index=True).to_csv(output_dir / "generated_criteria_catalog.csv", index=False)
    if respondent_tables:
        combined_respondents = pd.concat(respondent_tables, ignore_index=True)
        combined_respondents.to_csv(output_dir / "respondent_review_table.csv", index=False)
        write_review_markdown(output_dir, combined_respondents)
        write_agent_annotation_table(output_dir, combined_respondents)
    if evidence_tables:
        pd.concat(evidence_tables, ignore_index=True).to_csv(output_dir / "response_criteria_evidence_table.csv", index=False)

    (output_dir / "discovery_profiles.json").write_text(json.dumps(discovery_profiles, indent=2, ensure_ascii=True), encoding="utf-8")
    primary_model = next(iter(generated_models.values()))
    write_report(output_dir, source_files, scored_frames, comparison, primary_model, discovery_profiles, generated_models, feedback_config)
    print(output_dir)


if __name__ == "__main__":
    main()
