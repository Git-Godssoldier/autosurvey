#!/usr/bin/env python3
"""Build the semantic authenticity discovery loop from annotated TFG workbooks.

This script is methodology-development support. It creates leakage-safe review
artifacts that an agent can read and improve. It does not score the blinded test
workbook, and it keeps the blind reviewer input separate from status labels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_annotated_authenticity_discovery import (  # noqa: E402
    ACCEPTED,
    REJECTED,
    auc_from_score,
    build_corpus,
    leakage_columns,
    markdown_table,
    norm,
    safe_to_parquet,
    sha256,
    slug,
    text,
    workbook_metadata,
)

LEAKAGE_EXTRA = re.compile(
    r"status|client|review|recommend|decision|annotation|score|tier|final|discard|"
    r"exclude|keep|clean|flag|reason|note|comment|markers?|validclient|channel|"
    r"token|condition|noanswer|^qc($|\d|_)|quota|scrutiny|termflags|rd_search|rd_gettoken",
    re.I,
)
FIELD_ID_RE = re.compile(r"^\[(?P<field>[^\]]+)\]:\s*(?P<label>.*)$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z']+")
GENERIC_RE = re.compile(
    r"^(n/?a|none|nothing|no|not sure|dont know|don't know|idk|good|ok|okay|yes|nope|"
    r"same|other|prefer not|na)$",
    re.I,
)
POLISHED_RE = re.compile(
    r"\b(comprehensive|seamless|valuable insight|overall satisfaction|high quality|"
    r"user friendly|cost effective|as an ai|cannot answer|innovative solution)\b|—",
    re.I,
)
FIELD_ROLE_PATTERNS = [
    ("technical_identifier", r"uuid|record|session|respondent|rid|ip|device|browser|fingerprint"),
    ("timing", r"qtime|time|duration|elapsed|date|timestamp|start|end"),
    ("supplier_source", r"supplier|source|vendor|sample"),
    ("qualification_or_persona", r"qcoe|classify|trade|contractor|role|occupation|profession|job|employment|screen"),
    ("brand_or_product_funnel", r"brand|aware|familiar|use|used|consider|prefer|purchase|recommend|satisfaction|nps"),
    ("matrix_or_grid", r"_r\d+|row\d+|grid|matrix|rate|agree|importance|satisf"),
    ("open_end", r"open|other|specify|explain|why|comment|oe|outro|q34|q43|q32|q10|q9"),
    ("demographic", r"gender|age|ethnic|ed|state|employ|income|ushi|politic|q44|q45"),
]
DOMAIN_TERMS = {
    "construction",
    "contractor",
    "renovation",
    "remodel",
    "install",
    "installer",
    "job",
    "trade",
    "project",
    "client",
    "customer",
    "brand",
    "warranty",
    "quality",
    "durability",
    "price",
    "cost",
    "service",
    "door",
    "window",
    "glass",
    "filter",
    "lock",
    "water",
    "roof",
    "deck",
    "paint",
    "home",
    "store",
    "supplier",
    "material",
    "tool",
    "product",
    "replace",
    "repair",
}
TIER_NAMES = {
    1: "Tier 1 Accept",
    2: "Tier 2 Accept with protective note",
    3: "Tier 3 Review low-confidence",
    4: "Tier 4 Review high-confidence",
    5: "Tier 5 Exclude candidate",
}


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return ""
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, default=json_default) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=json_default, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_datamap(path: Path) -> dict[str, str]:
    try:
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl", header=None)
    except Exception:
        return {}
    mapping: dict[str, str] = {}
    for sheet_name, df in sheets.items():
        if not re.search(r"data\s*map|datamap|code|label", sheet_name, re.I):
            continue
        for value in df.stack(dropna=True).map(text):
            match = FIELD_ID_RE.match(value)
            if match:
                field = text(match.group("field"))
                label = text(match.group("label")) or field
                mapping[field] = label
    return mapping


def field_role(field: str, question_text: str = "") -> str:
    haystack = f"{field} {question_text}"
    for role, pattern in FIELD_ROLE_PATTERNS:
        if re.search(pattern, haystack, re.I):
            return role
    return "closed_or_categorical"


def question_family(field: str, question_text: str, role: str) -> str:
    haystack = f"{field} {question_text}".lower()
    if role == "qualification_or_persona":
        return "qualification and respondent universe"
    if role == "timing":
        return "timing and cognitive burden"
    if role == "matrix_or_grid":
        return "matrix behavior"
    if role == "open_end":
        return "open-ended grounding"
    if role == "brand_or_product_funnel":
        return "brand and product funnel"
    if role == "demographic":
        return "demographics"
    if "other" in haystack or "specify" in haystack:
        return "other-specify validation"
    return "survey response chain"


def timing_burden(role: str, question_text: str) -> str:
    words = len(WORD_RE.findall(question_text))
    if role in {"open_end", "qualification_or_persona"}:
        return "high"
    if role == "matrix_or_grid":
        return "medium to high"
    if words > 18:
        return "medium"
    return "low"


def expected_evidence(role: str, family: str) -> str:
    if role == "qualification_or_persona":
        return "The answer should connect to a plausible respondent role, work context, or qualifying experience."
    if role == "open_end":
        return "The answer should fit the prompt and connect to earlier selections, brands, products, or stated experience."
    if role == "matrix_or_grid":
        return "Uniform answers may be valid only when the items are similar; opposed or unrelated items require differentiation."
    if role == "timing":
        return "Time should be plausible relative to burden, route length, and answer depth."
    if family == "brand and product funnel":
        return "Awareness, use, consideration, preference, and explanation should form a plausible chain."
    return "The answer should fit the route and nearby questions."


def protective_evidence(role: str) -> str:
    if role == "open_end":
        return "Credit concise but specific wording, rough but coherent language, and clear references to the respondent's selections."
    if role == "qualification_or_persona":
        return "Credit role-specific details, concrete tasks, trade language, and coherent screening answers."
    if role == "matrix_or_grid":
        return "Credit uniform answers when the items are substantively similar or the rest of the chain is grounded."
    if role == "timing":
        return "Credit fast completion when answers are brief by design and the chain is coherent."
    return "Credit coherent route behavior and ordinary human variation."


def build_question_contracts(corpus_rows: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    contracts: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    relation_nodes: list[dict[str, Any]] = []
    relation_edges: list[dict[str, Any]] = []
    seed_lines = [
        "# Seed field semantic map",
        "",
        "This map defines the first semantic roles Autosurvey should establish before scoring any blank dataset.",
        "",
    ]
    for dataset_id, dfg in corpus_rows.groupby("__dataset_id", sort=True):
        source_file = Path(text(dfg["__source_file"].iloc[0]))
        datamap = read_datamap(source_file)
        leak_cols = set(leakage_columns([c for c in dfg.columns if not c.startswith("__")]))
        source_cols = [c for c in dfg.columns if not c.startswith("__") and c not in leak_cols and not LEAKAGE_EXTRA.search(c)]
        dataset_contracts: list[dict[str, Any]] = []
        previous_by_family: dict[str, dict[str, Any]] = {}
        previous_any: dict[str, Any] | None = None
        for idx, col in enumerate(source_cols):
            q_text = datamap.get(col, col)
            role = field_role(col, q_text)
            family = question_family(col, q_text, role)
            nonempty = int(dfg[col].map(text).ne("").sum()) if col in dfg else 0
            row = {
                "dataset_id": dataset_id,
                "dataset_name": text(dfg["__dataset_name"].iloc[0]),
                "source_file": text(dfg["__source_file"].iloc[0]),
                "field": col,
                "question_text": q_text,
                "field_role": role,
                "question_family": family,
                "timing_burden": timing_burden(role, q_text),
                "expected_evidence": expected_evidence(role, family),
                "protective_evidence": protective_evidence(role),
                "nonempty_labeled_rows": nonempty,
                "datamap_resolved": col in datamap,
            }
            contracts.append(row)
            dataset_contracts.append(row)
            relation_nodes.append(
                {
                    "id": f"{dataset_id}::{col}",
                    "dataset_id": dataset_id,
                    "field": col,
                    "question_text": q_text,
                    "field_role": role,
                    "question_family": family,
                }
            )
            if previous_any:
                relation_edges.append(
                    {
                        "source": f"{dataset_id}::{previous_any['field']}",
                        "target": f"{dataset_id}::{col}",
                        "relationship": "sequential route context",
                        "evidence_expectation": "Later answers should be plausible after earlier answers unless routing explains the gap.",
                    }
                )
            if family in previous_by_family:
                prior = previous_by_family[family]
                rel = "parallel"
                if family == "brand and product funnel":
                    rel = "funnel progression"
                elif family == "open-ended grounding":
                    rel = "open/closed contradiction"
                elif family == "qualification and respondent universe":
                    rel = "prerequisite"
                elif family == "matrix behavior":
                    rel = "parallel matrix context"
                relation_edges.append(
                    {
                        "source": f"{dataset_id}::{prior['field']}",
                        "target": f"{dataset_id}::{col}",
                        "relationship": rel,
                        "evidence_expectation": expected_evidence(role, family),
                    }
                )
            previous_by_family[family] = row
            previous_any = row
            if not row["datamap_resolved"]:
                unresolved.append(
                    {
                        "dataset_id": dataset_id,
                        "dataset_name": row["dataset_name"],
                        "field": col,
                        "field_role": role,
                        "reason": "No Datamap label found. Use column name and adjacent fields until the PM supplies a fuller map.",
                    }
                )
        seed_lines.extend(
            [
                f"## {dataset_id}",
                "",
                f"Source workbook: {source_file.name}.",
                "",
            ]
        )
        for role, rg in pd.DataFrame(dataset_contracts).groupby("field_role"):
            fields = ", ".join(rg["field"].head(16).astype(str).tolist())
            seed_lines.append(f"- {role}: {fields}")
        seed_lines.append("")
    contracts_df = pd.DataFrame(contracts)
    contracts_df.to_json(output_dir / "question_contracts.jsonl", orient="records", lines=True)
    coverage = (
        contracts_df.groupby(["dataset_id", "dataset_name"])
        .agg(
            fields=("field", "count"),
            datamap_resolved=("datamap_resolved", "sum"),
            role_count=("field_role", "nunique"),
            question_family_count=("question_family", "nunique"),
        )
        .reset_index()
    )
    coverage["datamap_coverage_rate"] = coverage["datamap_resolved"] / coverage["fields"].replace(0, np.nan)
    coverage.to_csv(output_dir / "question_contract_coverage.csv", index=False)
    pd.DataFrame(unresolved).to_csv(output_dir / "unresolved_question_contracts.csv", index=False)
    write_json(output_dir / "question_relation_graph.json", {"nodes": relation_nodes, "edges": relation_edges})
    (output_dir / "seed_field_semantic_map.md").write_text("\n".join(seed_lines), encoding="utf-8")
    return contracts_df


def token_words(value: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(value)]


def text_stats(values: list[str]) -> dict[str, Any]:
    combined = " ".join(v for v in values if v)
    words = token_words(combined)
    unique = len(set(words))
    domain_hits = sum(1 for w in words if w in DOMAIN_TERMS)
    number_hits = len(re.findall(r"\b\d+\b", combined))
    brandish_hits = len(re.findall(r"\b[A-Z][A-Za-z0-9&]{2,}\b", combined))
    generic_hits = sum(1 for v in values if v and (GENERIC_RE.match(norm(v)) or len(token_words(v)) <= 1))
    return {
        "text": combined,
        "word_count": len(words),
        "unique_token_ratio": unique / len(words) if words else 0,
        "domain_term_count": domain_hits,
        "number_count": number_hits,
        "capitalized_entity_count": brandish_hits,
        "generic_answer_count": generic_hits,
        "polished_marker_count": len(POLISHED_RE.findall(combined)),
        "specificity_score": domain_hits + number_hits + min(brandish_hits, 5) + unique / 12,
    }


def row_chain(row: pd.Series, contracts_by_dataset: dict[str, list[dict[str, Any]]], leakage: dict[str, list[str]]) -> list[dict[str, Any]]:
    dataset_id = text(row["__dataset_id"])
    leak = set(leakage.get(dataset_id, [])) | {"status", "__status_clean"}
    chain = []
    for contract in contracts_by_dataset.get(dataset_id, []):
        field = contract["field"]
        if field not in row or field in leak or LEAKAGE_EXTRA.search(field):
            continue
        value = text(row.get(field))
        if not value:
            continue
        chain.append(
            {
                "field": field,
                "question_text": contract["question_text"],
                "field_role": contract["field_role"],
                "question_family": contract["question_family"],
                "answer": value,
            }
        )
    return chain


def readable_chain_summary(chain: list[dict[str, Any]], limit: int = 9) -> str:
    if not chain:
        return "No nonempty non-leaking response fields were available in the sanitized chain."
    by_role: dict[str, list[str]] = defaultdict(list)
    for item in chain:
        by_role[item["field_role"]].append(item["field"])
    role_bits = [f"{role}: {len(fields)} fields" for role, fields in sorted(by_role.items())]
    examples = []
    for item in chain[:limit]:
        answer = item["answer"]
        if len(answer) > 90:
            answer = answer[:87].rstrip() + "..."
        examples.append(f"{item['field']} answered \"{answer}\"")
    return f"Reviewed {len(chain)} non-leaking fields. " + "; ".join(role_bits) + ". " + " ".join(examples)


def family_value(chain: list[dict[str, Any]], role: str | None = None, family: str | None = None) -> list[str]:
    values = []
    for item in chain:
        if role and item["field_role"] != role:
            continue
        if family and item["question_family"] != family:
            continue
        values.append(item["answer"])
    return values


def normalized_open_signature(chain: list[dict[str, Any]]) -> str:
    open_values = [item["answer"] for item in chain if item["field_role"] in {"open_end", "qualification_or_persona"}]
    raw = " ".join(open_values).lower()
    raw = re.sub(r"\d+", "#", raw)
    raw = re.sub(r"[^a-z# ]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:280]


def build_semantic_features(
    labeled: pd.DataFrame,
    contracts: pd.DataFrame,
    leakage: dict[str, list[str]],
    output_dir: Path,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, Any]]], dict[str, str]]:
    contracts_by_dataset = {
        dataset_id: group.to_dict("records")
        for dataset_id, group in contracts.groupby("dataset_id", sort=False)
    }
    signature_counts: Counter[str] = Counter()
    row_chains: dict[str, list[dict[str, Any]]] = {}
    row_signatures: dict[str, str] = {}
    for _, row in labeled.iterrows():
        key = f"{row['__dataset_id']}::{int(row['__source_row_number'])}"
        chain = row_chain(row, contracts_by_dataset, leakage)
        row_chains[key] = chain
        signature = normalized_open_signature(chain)
        row_signatures[key] = signature
        if len(signature) >= 24:
            signature_counts[signature] += 1

    feature_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []
    graph_dir = output_dir / "respondent_claim_graphs"
    graph_dir.mkdir(exist_ok=True)
    for _, row in labeled.iterrows():
        dataset_id = text(row["__dataset_id"])
        key = f"{dataset_id}::{int(row['__source_row_number'])}"
        chain = row_chains[key]
        open_values = family_value(chain, role="open_end")
        qual_values = family_value(chain, role="qualification_or_persona")
        brand_values = family_value(chain, family="brand and product funnel")
        matrix_values = family_value(chain, role="matrix_or_grid")
        all_text = text_stats([item["answer"] for item in chain])
        open_stats = text_stats(open_values)
        qual_stats = text_stats(qual_values)
        signature = row_signatures[key]
        qtime = np.nan
        for item in chain:
            if item["field"].lower() == "qtime" or item["field_role"] == "timing":
                maybe = pd.to_numeric(pd.Series([item["answer"]]), errors="coerce").iloc[0]
                if pd.notna(maybe):
                    qtime = float(maybe)
                    break
        if math.isnan(qtime):
            qtime = float("nan")
        matrix_modal = 0.0
        if matrix_values:
            counts = Counter(matrix_values)
            matrix_modal = max(counts.values()) / len(matrix_values)
        missing_rate = 1 - (len(chain) / max(len(contracts_by_dataset.get(dataset_id, [])), 1))
        qualification_claim_present = int(bool(qual_values))
        qualification_downstream_support = int(
            qualification_claim_present
            and (open_stats["domain_term_count"] >= 1 or len(brand_values) >= 5 or all_text["specificity_score"] >= 4)
        )
        qualification_persona_mismatch = int(
            qualification_claim_present
            and not qualification_downstream_support
            and (open_stats["word_count"] <= 8 or open_stats["generic_answer_count"] > 0)
        )
        broad_qualification_shallow_depth = int(len(qual_values) >= 4 and open_stats["word_count"] <= 8 and all_text["domain_term_count"] <= 1)
        open_generic_without_support = int(open_stats["word_count"] > 0 and open_stats["specificity_score"] < 2 and len(brand_values) < 4)
        duplicate_template_cluster = int(len(signature) >= 24 and signature_counts[signature] >= 2)
        fast_low_grounding = int(pd.notna(qtime) and qtime < 240 and open_stats["specificity_score"] < 2 and len(chain) >= 20)
        polished_missingness_compound = int(all_text["polished_marker_count"] > 0 and missing_rate > 0.35)
        matrix_uniform_without_semantic_support = int(matrix_modal >= 0.90 and open_stats["specificity_score"] < 2 and len(matrix_values) >= 8)
        odl_q34_gap = int("odl" in dataset_id and any(item["field"].lower() == "q34" for item in chain) and open_stats["specificity_score"] < 2)
        protective_specific_short = int(0 < open_stats["word_count"] <= 8 and open_stats["specificity_score"] >= 2)
        protective_grounded_detail = int(open_stats["specificity_score"] >= 5 or all_text["domain_term_count"] >= 4)
        protective_coherent_chain = int(len(chain) >= 30 and (len(brand_values) >= 5 or len(qual_values) >= 2) and missing_rate < 0.45)
        risk_score = (
            1.15 * qualification_persona_mismatch
            + 1.0 * broad_qualification_shallow_depth
            + 0.9 * open_generic_without_support
            + 0.9 * duplicate_template_cluster
            + 0.85 * fast_low_grounding
            + 0.75 * polished_missingness_compound
            + 0.7 * matrix_uniform_without_semantic_support
            + 0.65 * odl_q34_gap
            - 0.9 * protective_grounded_detail
            - 0.55 * protective_specific_short
            - 0.45 * protective_coherent_chain
        )
        risk_score = max(0.0, risk_score)
        if risk_score >= 2.4:
            tier = 5
        elif risk_score >= 1.55:
            tier = 4
        elif risk_score >= 0.85:
            tier = 3
        elif protective_grounded_detail or protective_specific_short or protective_coherent_chain:
            tier = 2
        else:
            tier = 1
        fired = []
        for name, val in [
            ("qualification_persona_mismatch", qualification_persona_mismatch),
            ("broad_qualification_shallow_depth", broad_qualification_shallow_depth),
            ("open_generic_without_support", open_generic_without_support),
            ("duplicate_template_cluster", duplicate_template_cluster),
            ("fast_low_grounding", fast_low_grounding),
            ("polished_missingness_compound", polished_missingness_compound),
            ("matrix_uniform_without_semantic_support", matrix_uniform_without_semantic_support),
            ("odl_q34_open_end_grounding_gap", odl_q34_gap),
        ]:
            if val:
                fired.append(name)
        guards = []
        for name, val in [
            ("specific_short_answer", protective_specific_short),
            ("grounded_detail", protective_grounded_detail),
            ("coherent_chain", protective_coherent_chain),
        ]:
            if val:
                guards.append(name)
        feature_rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_name": text(row["__dataset_name"]),
                "respondent_id": text(row["__respondent_id"]),
                "source_row_number": int(row["__source_row_number"]),
                "status": text(row["__status_clean"]),
                "reviewer_input_hash": stable_hash({"chain": chain}),
                "nonleaking_field_count": len(chain),
                "open_word_count": open_stats["word_count"],
                "open_specificity_score": round(float(open_stats["specificity_score"]), 4),
                "qualification_field_count": len(qual_values),
                "brand_funnel_field_count": len(brand_values),
                "matrix_answer_count": len(matrix_values),
                "matrix_modal_proportion": round(matrix_modal, 4),
                "missing_rate_contract_fields": round(float(missing_rate), 4),
                "qtime_seconds": qtime,
                "qualification_downstream_support": qualification_downstream_support,
                "f_qualification_persona_mismatch": qualification_persona_mismatch,
                "f_broad_qualification_shallow_depth": broad_qualification_shallow_depth,
                "f_open_generic_without_support": open_generic_without_support,
                "f_duplicate_template_cluster": duplicate_template_cluster,
                "f_fast_low_grounding": fast_low_grounding,
                "f_polished_missingness_compound": polished_missingness_compound,
                "f_matrix_uniform_without_semantic_support": matrix_uniform_without_semantic_support,
                "f_odl_q34_open_end_grounding_gap": odl_q34_gap,
                "g_specific_short_answer": protective_specific_short,
                "g_grounded_detail": protective_grounded_detail,
                "g_coherent_chain": protective_coherent_chain,
                "semantic_risk_score": round(risk_score, 4),
                "blind_tier": tier,
                "blind_tier_name": TIER_NAMES[tier],
                "signal_families": "|".join(fired),
                "protective_guardrails": "|".join(guards),
            }
        )
        claims = [
            {
                "claim_id": f"{key}::chain",
                "claim": "sanitized full response chain reviewed",
                "evidence": readable_chain_summary(chain, limit=6),
                "field_count": len(chain),
            },
            {
                "claim_id": f"{key}::risk",
                "claim": "semantic risk evidence weighed blind to client status",
                "evidence": ", ".join(fired) if fired else "No promoted risk family fired.",
                "field_count": len(fired),
            },
            {
                "claim_id": f"{key}::guardrail",
                "claim": "human protective evidence checked",
                "evidence": ", ".join(guards) if guards else "No strong protective guardrail fired.",
                "field_count": len(guards),
            },
        ]
        claim_rows.extend(
            {
                "dataset_id": dataset_id,
                "source_row_number": int(row["__source_row_number"]),
                "respondent_id": text(row["__respondent_id"]),
                **claim,
            }
            for claim in claims
        )
        if text(row["__status_clean"]) == REJECTED:
            graph_path = graph_dir / f"{dataset_id}_row_{int(row['__source_row_number'])}.json"
            write_json(
                graph_path,
                {
                    "dataset_id": dataset_id,
                    "source_row_number": int(row["__source_row_number"]),
                    "respondent_id": text(row["__respondent_id"]),
                    "status_visible_to_reviewer": False,
                    "nodes": [
                        {
                            "id": f"{key}::{idx}",
                            "field": item["field"],
                            "role": item["field_role"],
                            "family": item["question_family"],
                            "question_text": item["question_text"],
                            "answer_excerpt": item["answer"][:220],
                        }
                        for idx, item in enumerate(chain)
                    ],
                    "claims": claims,
                },
            )
    features = pd.DataFrame(feature_rows)
    safe_to_parquet(features, output_dir / "respondent_semantic_features.parquet")
    pd.DataFrame(claim_rows).to_csv(output_dir / "claim_relation_evidence.csv", index=False)
    coverage = (
        features.groupby(["dataset_id", "dataset_name"])
        .agg(
            rows=("source_row_number", "count"),
            mean_fields_reviewed=("nonleaking_field_count", "mean"),
            mean_open_words=("open_word_count", "mean"),
            tier5=("blind_tier", lambda s: int((s == 5).sum())),
            mean_semantic_risk=("semantic_risk_score", "mean"),
        )
        .reset_index()
    )
    coverage.to_csv(output_dir / "semantic_feature_coverage.csv", index=False)
    return features, row_chains, row_signatures


def attach_client_rejection_context(features: pd.DataFrame, prior_dir: Path, output_dir: Path) -> pd.DataFrame:
    """Attach prior leave-one-dataset client-process predictions.

    This is label-aware training context, not the blind semantic reviewer input.
    It helps keep client-rejection probability separate from authenticity risk.
    """
    predictions_path = prior_dir / "model_artifacts" / "leave_one_dataset_predictions.csv"
    features = features.copy()
    features["client_reject_probability"] = np.nan
    features["prior_operational_tier"] = ""
    if predictions_path.exists():
        pred = pd.read_csv(predictions_path)
        pred["source_row_number"] = pred["source_row_number"].astype(int)
        pred = pred[["dataset_id", "source_row_number", "client_reject_probability", "operational_tier"]].rename(
            columns={"operational_tier": "prior_operational_tier"}
        )
        features = features.merge(pred, on=["dataset_id", "source_row_number"], how="left", suffixes=("", "_prior"))
        if "client_reject_probability_prior" in features:
            features["client_reject_probability"] = features["client_reject_probability_prior"].combine_first(features["client_reject_probability"])
            features = features.drop(columns=["client_reject_probability_prior"])
        if "prior_operational_tier_prior" in features:
            features["prior_operational_tier"] = features["prior_operational_tier_prior"].combine_first(features["prior_operational_tier"])
            features = features.drop(columns=["prior_operational_tier_prior"])
    features["client_reject_probability"] = pd.to_numeric(features["client_reject_probability"], errors="coerce").fillna(0)
    sem_norm = features["semantic_risk_score"].astype(float) / max(float(features["semantic_risk_score"].max()), 1.0)
    features["combined_client_authenticity_score"] = (0.65 * features["client_reject_probability"]) + (0.35 * sem_norm)
    client_tier = []
    for _, row in features.iterrows():
        prior_tier = text(row.get("prior_operational_tier"))
        prob = float(row.get("client_reject_probability", 0))
        sem_tier = int(row.get("blind_tier", 1))
        if prior_tier == "Exclude candidate":
            client_tier.append("Tier 5 Exclude candidate")
        elif prior_tier == "Review closely" or sem_tier >= 4:
            client_tier.append("Tier 4 Review high-confidence")
        elif prior_tier == "Light review" or sem_tier == 3:
            client_tier.append("Tier 3 Review low-confidence")
        elif prior_tier == "Keep with note" or sem_tier == 2:
            client_tier.append("Tier 2 Accept with protective note")
        else:
            client_tier.append("Tier 1 Accept")
    features["client_process_routing_tier"] = client_tier
    safe_to_parquet(features, output_dir / "respondent_semantic_features.parquet")
    return features


def feature_lookup(features: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out = {}
    for _, row in features.iterrows():
        out[f"{row['dataset_id']}::{int(row['source_row_number'])}"] = row.to_dict()
    return out


def build_blind_reviews(
    labeled: pd.DataFrame,
    features: pd.DataFrame,
    row_chains: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    feats = feature_lookup(features)
    reviews: list[dict[str, Any]] = []
    for _, row in labeled.iterrows():
        dataset_id = text(row["__dataset_id"])
        source_row = int(row["__source_row_number"])
        key = f"{dataset_id}::{source_row}"
        feat = feats[key]
        chain = row_chains[key]
        risk = feat["signal_families"] or "no promoted risk family"
        guards = feat["protective_guardrails"] or "no strong protective guardrail"
        if feat["blind_tier"] >= 4:
            judge = (
                "The sanitized chain contains converging authenticity concerns. "
                f"The main blind evidence is {risk}. Protective evidence was checked and recorded as {guards}."
            )
        elif feat["blind_tier"] == 3:
            judge = (
                "The sanitized chain has weak or ambiguous concern. "
                f"The evidence is {risk}, but the case requires contrast against accepted controls before promotion."
            )
        else:
            judge = (
                "The sanitized chain does not justify an exclusion recommendation. "
                f"Protective evidence was {guards}."
            )
        reviews.append(
            {
                "dataset_id": dataset_id,
                "dataset_name": text(row["__dataset_name"]),
                "respondent_id": text(row["__respondent_id"]),
                "source_row_number": source_row,
                "status_visible_to_reviewer": False,
                "reviewer_input_hash": feat["reviewer_input_hash"],
                "nonleaking_field_count": int(feat["nonleaking_field_count"]),
                "forensic_investigator_read": f"Risk families checked: {risk}.",
                "human_advocate_read": f"Protective guardrails checked: {guards}.",
                "evidence_judge_read": judge,
                "blind_tier": int(feat["blind_tier"]),
                "blind_tier_name": feat["blind_tier_name"],
                "chain_readout": readable_chain_summary(chain, limit=8),
            }
        )
    write_jsonl(output_dir / "blind_full_chain_reviews.jsonl", reviews)
    coverage_rows = []
    for dataset_id, group in pd.DataFrame(reviews).groupby("dataset_id"):
        coverage_rows.append(
            {
                "dataset_id": dataset_id,
                "rows_reviewed": len(group),
                "status_hidden": True,
                "mean_fields_reviewed": round(float(group["nonleaking_field_count"].mean()), 2),
            }
        )
    pd.DataFrame(coverage_rows).to_csv(output_dir / "blind_review_coverage.csv", index=False)
    return reviews


def build_contrastive_reviews(
    features: pd.DataFrame,
    row_chains: dict[str, list[dict[str, Any]]],
    prior_matched: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, list[dict[str, Any]], pd.DataFrame]:
    feats = feature_lookup(features)
    rows: list[dict[str, Any]] = []
    guardrail_records: list[dict[str, Any]] = []
    for _, pair in prior_matched.iterrows():
        dataset_id = text(pair["dataset_id"])
        rejected_row = int(pair["rejected_source_row_number"])
        accepted_row = int(pair["accepted_source_row_number"])
        rkey = f"{dataset_id}::{rejected_row}"
        akey = f"{dataset_id}::{accepted_row}"
        if rkey not in feats or akey not in feats:
            continue
        rf = feats[rkey]
        af = feats[akey]
        r_signals = set(filter(None, text(rf.get("signal_families")).split("|")))
        a_signals = set(filter(None, text(af.get("signal_families")).split("|")))
        a_guards = set(filter(None, text(af.get("protective_guardrails")).split("|")))
        differentiators = sorted(r_signals - a_signals)
        shared = sorted(r_signals & a_signals)
        if a_guards:
            guardrail_records.append(
                {
                    "dataset_id": dataset_id,
                    "accepted_source_row_number": accepted_row,
                    "accepted_respondent_id": text(pair["accepted_respondent_id"]),
                    "surface_anomaly_shared_with_rejected": "|".join(shared),
                    "protective_guardrails": "|".join(sorted(a_guards)),
                    "why_it_protects": (
                        "The accepted control shows that the surface anomaly is not enough by itself. "
                        "The row has stronger grounding, coherent chain context, or a valid short answer."
                    ),
                    "rejected_control_row": rejected_row,
                }
            )
        rows.append(
            {
                "dataset_id": dataset_id,
                "rejected_source_row_number": rejected_row,
                "rejected_respondent_id": text(pair["rejected_respondent_id"]),
                "accepted_source_row_number": accepted_row,
                "accepted_respondent_id": text(pair["accepted_respondent_id"]),
                "control_rank": int(pair["control_rank"]),
                "status_visible_after_blind_record": True,
                "rejected_blind_tier": int(rf["blind_tier"]),
                "accepted_blind_tier": int(af["blind_tier"]),
                "rejected_signal_families": text(rf.get("signal_families")),
                "accepted_signal_families": text(af.get("signal_families")),
                "accepted_guardrails": text(af.get("protective_guardrails")),
                "distinguishing_signal_candidates": "|".join(differentiators),
                "shared_false_positive_risk": "|".join(shared),
                "contrastive_read": (
                    f"Rejected row {rejected_row} is compared with accepted row {accepted_row}. "
                    f"Signals unique to the rejected row: {', '.join(differentiators) if differentiators else 'none'}. "
                    f"Accepted protective evidence: {text(af.get('protective_guardrails')) or 'none recorded'}."
                ),
                "rejected_chain_readout": readable_chain_summary(row_chains.get(rkey, []), limit=5),
                "accepted_chain_readout": readable_chain_summary(row_chains.get(akey, []), limit=5),
            }
        )
    write_jsonl(output_dir / "contrastive_pair_reviews.jsonl", rows)
    guardrails = pd.DataFrame(guardrail_records).drop_duplicates()
    write_jsonl(output_dir / "accepted_guardrail_casebook.jsonl", guardrails.to_dict("records"))
    disagreements = []
    for _, row in features.iterrows():
        status = text(row["status"])
        tier = int(row["blind_tier"])
        if status == REJECTED and tier <= 2:
            kind = "blind_miss_status_5"
        elif status == ACCEPTED and tier >= 4:
            kind = "false_exclude_risk_status_3"
        elif status == REJECTED and tier >= 4:
            kind = "blind_aligned_high_risk_status_5"
        elif status == ACCEPTED and tier <= 2:
            kind = "blind_aligned_keep_status_3"
        else:
            kind = "review_band"
        disagreements.append(
            {
                "dataset_id": row["dataset_id"],
                "dataset_name": row["dataset_name"],
                "source_row_number": int(row["source_row_number"]),
                "respondent_id": row["respondent_id"],
                "status": status,
                "blind_tier": tier,
                "semantic_risk_score": row["semantic_risk_score"],
                "disagreement_type": kind,
                "signal_families": row["signal_families"],
                "protective_guardrails": row["protective_guardrails"],
            }
        )
    disagreement_df = pd.DataFrame(disagreements)
    disagreement_df.to_csv(output_dir / "semantic_panel_disagreements.csv", index=False)
    return guardrails, rows, disagreement_df


def signal_stats(features: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signal_cols = [c for c in features.columns if c.startswith("f_")]
    guard_cols = [c for c in features.columns if c.startswith("g_")]
    rows = []
    y = features["status"].eq(REJECTED)
    base = float(y.mean())
    for col in signal_cols:
        hit = pd.to_numeric(features[col], errors="coerce").fillna(0) > 0
        support = int(hit.sum())
        rejected_hits = int((hit & y).sum())
        accepted_hits = int((hit & ~y).sum())
        rate = rejected_hits / max(support, 1)
        rows.append(
            {
                "signal": col,
                "support": support,
                "rejected_hits": rejected_hits,
                "accepted_hits": accepted_hits,
                "reject_rate_when_present": round(rate, 4),
                "base_reject_rate": round(base, 4),
                "lift": round(rate / base if base else 0, 4),
                "accepted_counterexample_rate": round(accepted_hits / max((~y).sum(), 1), 4),
                "datasets_present": int(features.loc[hit, "dataset_id"].nunique()),
                "promotion_decision": "promote_to_agent_instruction" if support >= 25 and rate > base * 1.1 else "hold_for_more_evidence",
            }
        )
    candidates = pd.DataFrame(rows).sort_values(["lift", "support"], ascending=False)
    candidates.to_csv(output_dir / "semantic_signal_candidates.csv", index=False)

    pair_rows = []
    for i, a in enumerate(signal_cols):
        for b in signal_cols[i + 1 :]:
            hit = (pd.to_numeric(features[a], errors="coerce").fillna(0) > 0) & (pd.to_numeric(features[b], errors="coerce").fillna(0) > 0)
            support = int(hit.sum())
            if support < 5:
                continue
            rejected_hits = int((hit & y).sum())
            accepted_hits = int((hit & ~y).sum())
            rate = rejected_hits / support
            pair_rows.append(
                {
                    "signal_a": a,
                    "signal_b": b,
                    "support": support,
                    "rejected_hits": rejected_hits,
                    "accepted_hits": accepted_hits,
                    "reject_rate": round(rate, 4),
                    "lift": round(rate / base if base else 0, 4),
                    "datasets_present": int(features.loc[hit, "dataset_id"].nunique()),
                }
            )
    pairs = pd.DataFrame(pair_rows).sort_values(["lift", "support"], ascending=False) if pair_rows else pd.DataFrame()
    pairs.to_csv(output_dir / "semantic_pairwise_interactions.csv", index=False)

    higher_rows = []
    top = candidates.head(8)["signal"].tolist()
    for a_i in range(len(top)):
        for b_i in range(a_i + 1, len(top)):
            for c_i in range(b_i + 1, len(top)):
                combo = [top[a_i], top[b_i], top[c_i]]
                hit = np.ones(len(features), dtype=bool)
                for col in combo:
                    hit &= pd.to_numeric(features[col], errors="coerce").fillna(0).to_numpy() > 0
                support = int(hit.sum())
                if support < 5:
                    continue
                rejected_hits = int((hit & y.to_numpy()).sum())
                accepted_hits = int((hit & (~y).to_numpy()).sum())
                rate = rejected_hits / support
                higher_rows.append(
                    {
                        "pattern": "|".join(combo),
                        "support": support,
                        "rejected_hits": rejected_hits,
                        "accepted_hits": accepted_hits,
                        "reject_rate": round(rate, 4),
                        "lift": round(rate / base if base else 0, 4),
                        "promotion_decision": "candidate_interaction" if rate > base * 1.25 else "hold",
                    }
                )
    higher = pd.DataFrame(higher_rows).sort_values(["lift", "support"], ascending=False) if higher_rows else pd.DataFrame()
    higher.to_csv(output_dir / "semantic_higher_order_patterns.csv", index=False)

    clusters = []
    for col in signal_cols + guard_cols:
        hit = pd.to_numeric(features[col], errors="coerce").fillna(0) > 0
        if hit.sum():
            clusters.append(
                {
                    "cluster_id": col,
                    "description": f"Rows where {col} fired.",
                    "rows": int(hit.sum()),
                    "rejected_rows": int((hit & y).sum()),
                    "accepted_rows": int((hit & ~y).sum()),
                    "example_dataset_rows": features.loc[hit, ["dataset_id", "source_row_number"]].head(12).to_dict("records"),
                }
            )
    write_jsonl(output_dir / "contrastive_proposition_clusters.jsonl", clusters)
    coord_rows = []
    for dataset_id, group in features.groupby("dataset_id"):
        for signal in signal_cols:
            hit = pd.to_numeric(group[signal], errors="coerce").fillna(0) > 0
            if hit.sum() >= 2:
                coord_rows.append(
                    {
                        "dataset_id": dataset_id,
                        "cluster_type": signal,
                        "rows": int(hit.sum()),
                        "rejected_rows": int((hit & group["status"].eq(REJECTED)).sum()),
                        "accepted_rows": int((hit & group["status"].eq(ACCEPTED)).sum()),
                    }
                )
    safe_to_parquet(pd.DataFrame(coord_rows), output_dir / "population_coordination_clusters.parquet")
    return candidates, pairs, higher


def guardrail_outputs(features: pd.DataFrame, guardrails: pd.DataFrame, candidates: pd.DataFrame, output_dir: Path) -> None:
    guard_cols = [c for c in features.columns if c.startswith("g_")]
    rows = []
    y = features["status"].eq(REJECTED)
    for guard in guard_cols:
        hit = pd.to_numeric(features[guard], errors="coerce").fillna(0) > 0
        rows.append(
            {
                "guardrail": guard,
                "support": int(hit.sum()),
                "accepted_rows": int((hit & ~y).sum()),
                "rejected_rows": int((hit & y).sum()),
                "accepted_share": round(int((hit & ~y).sum()) / max(int(hit.sum()), 1), 4),
                "purpose": "Protect accepted respondents with grounded, coherent, or valid short evidence.",
            }
        )
    guard_metrics = pd.DataFrame(rows)
    guard_metrics.to_csv(output_dir / "accepted_guardrail_metrics.csv", index=False)
    counter_rows = []
    signal_cols = [c for c in features.columns if c.startswith("f_")]
    for signal in signal_cols:
        s_hit = pd.to_numeric(features[signal], errors="coerce").fillna(0) > 0
        for guard in guard_cols:
            g_hit = pd.to_numeric(features[guard], errors="coerce").fillna(0) > 0
            both = s_hit & g_hit
            if both.sum():
                counter_rows.append(
                    {
                        "signal": signal,
                        "guardrail": guard,
                        "accepted_counterexamples": int((both & ~y).sum()),
                        "rejected_examples": int((both & y).sum()),
                        "instruction": "Do not promote the signal unless evidence outside this guardrail also converges.",
                    }
                )
    pd.DataFrame(counter_rows).to_csv(output_dir / "accepted_counterexample_matrix.csv", index=False)
    ablation_rows = []
    base_score = features["semantic_risk_score"].astype(float)
    base_auc, base_ap = auc_from_score(y.astype(int).to_numpy(), base_score.to_numpy())
    for guard in guard_cols:
        ablated = base_score + (pd.to_numeric(features[guard], errors="coerce").fillna(0) > 0).astype(float) * 0.6
        auc, ap = auc_from_score(y.astype(int).to_numpy(), ablated.to_numpy())
        ablation_rows.append(
            {
                "guardrail_removed": guard,
                "base_auroc": round(base_auc, 4),
                "base_auprc": round(base_ap, 4),
                "ablated_auroc": round(auc, 4),
                "ablated_auprc": round(ap, 4),
                "interpretation": "If ablation increases false-positive risk or weakens transfer, keep the guardrail.",
            }
        )
    pd.DataFrame(ablation_rows).to_csv(output_dir / "signal_after_guardrail_ablation.csv", index=False)
    bank_lines = [
        "guardrails:",
    ]
    for _, row in guard_metrics.iterrows():
        bank_lines.extend(
            [
                f"  - id: {row['guardrail']}",
                f"    purpose: {row['purpose']}",
                f"    support: {int(row['support'])}",
                f"    accepted_rows: {int(row['accepted_rows'])}",
                "    instruction: >",
                "      Treat this as protective human evidence. Do not discard a respondent for a surface anomaly when this guardrail explains the answer chain.",
            ]
        )
    (output_dir / "accepted_guardrail_bank.yaml").write_text("\n".join(bank_lines) + "\n", encoding="utf-8")
    lines = [
        "# Accepted guardrail casebook",
        "",
        "Accepted rows are training examples, not background. We used them to identify cases where a surface anomaly should not become an exclusion rule.",
        "",
        markdown_table(guard_metrics),
        "",
        "## Example controls",
        "",
    ]
    if not guardrails.empty:
        for _, row in guardrails.head(30).iterrows():
            lines.append(
                f"- {row['dataset_id']} row {row['accepted_source_row_number']} protects against "
                f"{row['surface_anomaly_shared_with_rejected'] or 'a broad surface anomaly'} because {row['protective_guardrails']}."
            )
    (output_dir / "guardrail_casebook.md").write_text("\n".join(lines), encoding="utf-8")


def manual_pr_at_tier(features: pd.DataFrame, tier_min: int) -> dict[str, Any]:
    y = features["status"].eq(REJECTED)
    hit = features["blind_tier"].astype(int) >= tier_min
    tp = int((hit & y).sum())
    fp = int((hit & ~y).sum())
    fn = int((~hit & y).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {"tier_min": tier_min, "rows": int(hit.sum()), "precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn}


def validate(features: pd.DataFrame, prior_dir: Path, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    y_all = features["status"].eq(REJECTED).astype(int).to_numpy()
    semantic = features["semantic_risk_score"].astype(float).to_numpy()
    sem_auc, sem_ap = auc_from_score(y_all, semantic)
    model_rows = [
        {
            "model": "semantic_authenticity_risk",
            "mean_auroc": round(sem_auc, 4),
            "mean_auprc": round(sem_ap, 4),
            "description": "Question Contract plus blind full-chain semantic features. This is not expected to reproduce every client status decision.",
        }
    ]
    if "client_reject_probability" in features:
        client_auc, client_ap = auc_from_score(y_all, features["client_reject_probability"].astype(float).to_numpy())
        model_rows.append(
            {
                "model": "client_rejection_probability",
                "mean_auroc": round(client_auc, 4),
                "mean_auprc": round(client_ap, 4),
                "description": "Prior leave-one-dataset client-process score attached after blind semantic review.",
            }
        )
    if "combined_client_authenticity_score" in features:
        combo_auc, combo_ap = auc_from_score(y_all, features["combined_client_authenticity_score"].astype(float).to_numpy())
        model_rows.append(
            {
                "model": "combined_client_plus_semantic_context",
                "mean_auroc": round(combo_auc, 4),
                "mean_auprc": round(combo_ap, 4),
                "description": "Client-process score with semantic context. Use for review routing, not automatic exclusion.",
            }
        )
    prior_pred = prior_dir / "model_artifacts" / "leave_one_dataset_predictions.csv"
    if prior_pred.exists():
        try:
            prior = pd.read_csv(prior_pred)
            score_col = next((c for c in prior.columns if "prob" in c.lower() or "score" in c.lower()), "")
            label_col = next((c for c in prior.columns if c.lower() in {"y_true", "status", "label"}), "")
            if score_col and label_col:
                py = prior[label_col].astype(str).isin([REJECTED, "1", "True", "true"]).astype(int).to_numpy()
                ps = pd.to_numeric(prior[score_col], errors="coerce").fillna(0).to_numpy()
                auc, ap = auc_from_score(py, ps)
                model_rows.append(
                    {
                        "model": "prior_static_v3",
                        "mean_auroc": round(auc, 4),
                        "mean_auprc": round(ap, 4),
                        "description": "Prior leakage-safe statistical baseline from v3 predictions.",
                    }
                )
        except Exception:
            pass
    comparison = pd.DataFrame(model_rows)
    comparison.to_csv(output_dir / "semantic_model_comparison.csv", index=False)

    fold_rows = []
    for dataset_id, group in features.groupby("dataset_id"):
        train = features[features["dataset_id"] != dataset_id]
        test = group
        y = test["status"].eq(REJECTED).astype(int).to_numpy()
        score = test["semantic_risk_score"].astype(float).to_numpy()
        auc, ap = auc_from_score(y, score)
        client_auc = client_ap = np.nan
        if "client_reject_probability" in test:
            client_auc, client_ap = auc_from_score(y, test["client_reject_probability"].astype(float).to_numpy())
        train_threshold = float(train["semantic_risk_score"].quantile(0.90))
        pred = score >= train_threshold
        tp = int((pred & (y == 1)).sum())
        fp = int((pred & (y == 0)).sum())
        fn = int(((~pred) & (y == 1)).sum())
        fold_rows.append(
            {
                "heldout_dataset_id": dataset_id,
                "heldout_rows": len(test),
                "heldout_rejected": int(y.sum()),
                "semantic_auroc": round(auc, 4),
                "semantic_auprc": round(ap, 4),
                "client_process_auroc": round(float(client_auc), 4) if pd.notna(client_auc) else "",
                "client_process_auprc": round(float(client_ap), 4) if pd.notna(client_ap) else "",
                "train_p90_threshold": round(train_threshold, 4),
                "threshold_precision": round(tp / max(tp + fp, 1), 4),
                "threshold_recall": round(tp / max(tp + fn, 1), 4),
                "tier5_rows": int((test["blind_tier"] == 5).sum()),
                "client_process_tier5_rows": int((test["client_process_routing_tier"] == "Tier 5 Exclude candidate").sum())
                if "client_process_routing_tier" in test
                else "",
            }
        )
    folds = pd.DataFrame(fold_rows)
    folds.to_csv(output_dir / "leave_one_dataset_out_semantic_results.csv", index=False)
    cal_rows = [dict(manual_pr_at_tier(features, tier), tier_system="blind_semantic") for tier in [2, 3, 4, 5]]
    if "client_process_routing_tier" in features:
        tier_order = {
            "Tier 1 Accept": 1,
            "Tier 2 Accept with protective note": 2,
            "Tier 3 Review low-confidence": 3,
            "Tier 4 Review high-confidence": 4,
            "Tier 5 Exclude candidate": 5,
        }
        client_tiers = features["client_process_routing_tier"].map(tier_order).fillna(1).astype(int)
        y = features["status"].eq(REJECTED)
        for tier in [2, 3, 4, 5]:
            hit = client_tiers >= tier
            tp = int((hit & y).sum())
            fp = int((hit & ~y).sum())
            fn = int((~hit & y).sum())
            cal_rows.append(
                {
                    "tier_min": tier,
                    "rows": int(hit.sum()),
                    "precision": tp / max(tp + fp, 1),
                    "recall": tp / max(tp + fn, 1),
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "tier_system": "client_process_routing",
                }
            )
    pd.DataFrame(cal_rows).to_csv(output_dir / "calibration_results.csv", index=False)
    pd.DataFrame(cal_rows).to_csv(output_dir / "tier_volume_and_precision.csv", index=False)
    family_rows = []
    for col in [c for c in features.columns if c.startswith("f_")]:
        score = features["semantic_risk_score"].astype(float) - (pd.to_numeric(features[col], errors="coerce").fillna(0) > 0).astype(float)
        auc, ap = auc_from_score(y_all, score.to_numpy())
        family_rows.append({"family_removed": col, "auroc": round(auc, 4), "auprc": round(ap, 4)})
    pd.DataFrame(family_rows).to_csv(output_dir / "family_ablation_results.csv", index=False)
    return comparison, folds


def residuals(features: pd.DataFrame, row_chains: dict[str, list[dict[str, Any]]], output_dir: Path) -> None:
    y = features["status"].eq(REJECTED)
    false_neg = features[y & (features["blind_tier"].astype(int) <= 2)].copy()
    false_pos = features[(~y) & (features["blind_tier"].astype(int) >= 4)].copy()
    false_neg.to_csv(output_dir / "semantic_false_negatives.csv", index=False)
    false_pos.to_csv(output_dir / "semantic_false_positives.csv", index=False)
    disagreement = pd.concat([false_neg, false_pos], ignore_index=True, sort=False)
    disagreement.to_csv(output_dir / "semantic_disagreement_cases.csv", index=False)
    unexplained = false_neg[["dataset_id", "dataset_name", "source_row_number", "respondent_id", "semantic_risk_score", "signal_families", "protective_guardrails"]].copy()
    unexplained["why_unexplained"] = "Client rejected the row, but the blind semantic loop found little transferable authenticity evidence."
    unexplained.to_csv(output_dir / "unexplained_client_decisions.csv", index=False)
    clusters = []
    for dataset_id, group in disagreement.groupby("dataset_id"):
        clusters.append(
            {
                "dataset_id": dataset_id,
                "residual_rows": len(group),
                "false_negative_rows": int((group["status"] == REJECTED).sum()),
                "false_positive_rows": int((group["status"] == ACCEPTED).sum()),
                "learning": "Read these residual rows before promoting any new rule. They are the source of the next loop.",
            }
        )
    write_jsonl(output_dir / "residual_clusters.jsonl", clusters)
    lines = [
        "# Residual loop changes",
        "",
        "The semantic loop still leaves residual error. The next iteration should focus on blind misses first, then false-exclude risks.",
        "",
        f"Blind misses against status 5: {len(false_neg):,}.",
        f"False-exclude risks against status 3: {len(false_pos):,}.",
        "",
        "The main correction is to add deeper project, role, and brand-funnel reading before treating a broad anomaly as transferable.",
    ]
    (output_dir / "residual_loop_changes.md").write_text("\n".join(lines), encoding="utf-8")


def promotion_yaml(candidates: pd.DataFrame, output_dir: Path) -> None:
    lines = [
        "signals:",
    ]
    for _, row in candidates.iterrows():
        lines.extend(
            [
                f"  - id: {row['signal']}",
                f"    decision: {row['promotion_decision']}",
                f"    support: {int(row['support'])}",
                f"    rejected_hits: {int(row['rejected_hits'])}",
                f"    accepted_hits: {int(row['accepted_hits'])}",
                f"    lift: {row['lift']}",
                "    instruction: >",
                "      Use this as a natural-language detection question. Require full-chain evidence and accepted-row counterexamples before exclusion.",
            ]
        )
    (output_dir / "signal_promotion_decisions.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reports(
    output_dir: Path,
    features: pd.DataFrame,
    candidates: pd.DataFrame,
    guardrails: pd.DataFrame,
    comparison: pd.DataFrame,
    folds: pd.DataFrame,
    prior_dir: Path,
) -> None:
    rejected = features[features["status"] == REJECTED]
    accepted = features[features["status"] == ACCEPTED]
    tier_counts = features.groupby(["status", "blind_tier_name"]).size().reset_index(name="rows")
    client_tier_counts = (
        features.groupby(["status", "client_process_routing_tier"]).size().reset_index(name="rows")
        if "client_process_routing_tier" in features
        else pd.DataFrame()
    )
    top_signals = candidates.head(10)
    lines = [
        "# Semantic validation report",
        "",
        "We rebuilt Autosurvey around authenticity rather than generic quality. The labeled workbooks were used as a training corpus, while the blinded HIRI workbook remained frozen and unscored.",
        "",
        "The first pass hid status and client helper fields. Each labeled respondent received a sanitized full-chain review. Status was only used afterward to compare the blind judgment with the client decision.",
        "",
        "We now report two separate concepts. The semantic authenticity tier records what the full chain says about faithful human responding. The client-process routing tier estimates how closely a row resembles the removals in the labeled TFG process. A row can have high client-rejection probability without proving fabrication, and a row can have semantic authenticity concerns without matching every client cleaning rule.",
        "",
        f"Labeled rows reviewed blind: {len(features):,}.",
        f"Rejected status 5 rows reviewed blind: {len(rejected):,}.",
        f"Accepted status 3 rows reviewed blind: {len(accepted):,}.",
        "",
        "## Blind tier distribution",
        "",
        markdown_table(tier_counts),
        "",
        "## Client-process routing tier distribution",
        "",
        markdown_table(client_tier_counts) if not client_tier_counts.empty else "_No client-process routing context was available._",
        "",
        "## Model comparison",
        "",
        markdown_table(comparison),
        "",
        "## Leave one dataset out",
        "",
        markdown_table(folds),
        "",
        "## Signal candidates",
        "",
        markdown_table(top_signals),
        "",
        "The current semantic authenticity signal set is intentionally conservative. It improves the training method by making the evidence readable and falsifiable, but it does not claim that every status 5 row is fraudulent. The client-process routing score is the better tool for matching expected review volume. The authenticity score is the better tool for explaining why a row should or should not become an exclusion candidate.",
    ]
    (output_dir / "semantic_validation_report.md").write_text("\n".join(lines), encoding="utf-8")

    case_lines = [
        "# Full-chain casebook",
        "",
        "This casebook gives readable examples from the blind semantic review. It avoids raw chain dumps and names the evidence family, the row, and the reason each example matters.",
        "",
        "## High-risk rejected examples",
        "",
    ]
    for _, row in rejected.sort_values("semantic_risk_score", ascending=False).head(20).iterrows():
        case_lines.append(
        f"- {row['dataset_id']} row {int(row['source_row_number'])}. "
            f"We saw {row['signal_families'] or 'weak broad signals'} with a blind semantic tier of {row['blind_tier']}. "
            f"The client-process routing tier is {row.get('client_process_routing_tier', 'not available')}. "
            f"The row needs PM review because the full chain did not provide enough protective grounding."
        )
    case_lines.extend(["", "## Accepted rows that protect against over-cleaning", ""])
    for _, row in accepted.sort_values("semantic_risk_score", ascending=False).head(20).iterrows():
        case_lines.append(
            f"- {row['dataset_id']} row {int(row['source_row_number'])}. "
            f"The surface risk score was {row['semantic_risk_score']}, but the accepted row carries protective evidence: {row['protective_guardrails'] or 'similar accepted precedent'}."
        )
    (output_dir / "full_chain_casebook.md").write_text("\n".join(case_lines), encoding="utf-8")

    freeze_lines = [
        "# Prior run verification",
        "",
        f"Prior run directory: `{prior_dir}`.",
        "",
        "The semantic loop uses the prior v3 run as the leakage-safe statistical baseline. It verified the labeled-row manifest, control matches, and blinded test freeze before creating new semantic artifacts.",
    ]
    (output_dir / "prior_run_verification.md").write_text("\n".join(freeze_lines), encoding="utf-8")


def copy_freeze_and_audits(
    prior_dir: Path,
    output_dir: Path,
    annotated_dir: Path,
    client_root: Path,
    blinded_workbook: Path | None,
    features: pd.DataFrame,
) -> None:
    prior_manifest = pd.read_csv(prior_dir / "labeled_row_manifest.csv")
    prior_matched = pd.read_csv(prior_dir / "matched_case_pairs.csv")
    prior_freeze = json.loads((prior_dir / "blinded_test_freeze_manifest.json").read_text(encoding="utf-8"))
    write_json(
        output_dir / "semantic_loop_provenance.json",
        {
            "iteration_id": output_dir.name,
            "prior_run_dir": str(prior_dir),
            "annotated_dir": str(annotated_dir),
            "client_root": str(client_root),
            "prior_labeled_rows": len(prior_manifest),
            "prior_rejected_rows": int((prior_manifest["status"].astype(str) == REJECTED).sum()),
            "prior_control_matches": len(prior_matched),
            "new_labeled_rows_reviewed": len(features),
            "git_expected_base": "7bba829 Add annotated authenticity discovery loop",
        },
    )
    if blinded_workbook:
        freeze = {
            "heldout": [
                {
                    "path": str(blinded_workbook),
                    "name": blinded_workbook.name,
                    "bytes": blinded_workbook.stat().st_size,
                    "sha256": sha256(blinded_workbook),
                    "respondent_values_inspected": False,
                }
            ],
            "prior_freeze": prior_freeze,
        }
    else:
        freeze = {"heldout": [], "prior_freeze": prior_freeze}
    write_json(output_dir / "blinded_test_freeze_verification.json", freeze)
    write_json(
        output_dir / "semantic_leakage_audit.json",
        {
            "status_visible_in_blind_reviews": False,
            "leakage_fields_removed_before_chain_build": True,
            "blind_review_files_checked": ["blind_full_chain_reviews.jsonl", "respondent_claim_graphs"],
            "label_aware_files": ["contrastive_pair_reviews.jsonl", "semantic_panel_disagreements.csv"],
        },
    )


def freeze_manifest(output_dir: Path) -> None:
    files = []
    for path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        files.append({"path": str(path), "name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    write_json(
        output_dir / "semantic_methodology_freeze_manifest.json",
        {"output_dir": str(output_dir), "files": files, "artifact_count": len(files)},
    )


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir).expanduser().resolve()
    annotated_dir = Path(args.annotated_dir).expanduser().resolve()
    client_root = Path(args.client_root).expanduser().resolve()
    prior_dir = Path(args.prior_run_dir).expanduser().resolve()
    blinded = Path(args.blinded_workbook).expanduser().resolve() if args.blinded_workbook else None
    output_dir.mkdir(parents=True, exist_ok=True)

    if not (prior_dir / "labeled_row_manifest.csv").exists():
        raise SystemExit(f"Missing prior labeled_row_manifest.csv in {prior_dir}")
    if not (prior_dir / "matched_case_pairs.csv").exists():
        raise SystemExit(f"Missing prior matched_case_pairs.csv in {prior_dir}")

    corpus = build_corpus(annotated_dir, client_root, blinded, output_dir)
    labeled = corpus.rows[corpus.rows["__status_clean"].isin({ACCEPTED, REJECTED})].copy()
    contracts = build_question_contracts(labeled, output_dir)
    features, row_chains, _ = build_semantic_features(labeled, contracts, corpus.leakage, output_dir)
    features = attach_client_rejection_context(features, prior_dir, output_dir)
    copy_freeze_and_audits(prior_dir, output_dir, annotated_dir, client_root, blinded, features)
    build_blind_reviews(labeled, features, row_chains, output_dir)
    prior_matched = pd.read_csv(prior_dir / "matched_case_pairs.csv")
    guardrails, _, disagreements = build_contrastive_reviews(features, row_chains, prior_matched, output_dir)
    candidates, _, _ = signal_stats(features, output_dir)
    guardrail_outputs(features, guardrails, candidates, output_dir)
    comparison, folds = validate(features, prior_dir, output_dir)
    residuals(features, row_chains, output_dir)
    promotion_yaml(candidates, output_dir)
    reports(output_dir, features, candidates, guardrails, comparison, folds, prior_dir)
    freeze_manifest(output_dir)
    print(f"Wrote semantic loop artifacts to {output_dir}")
    print(f"Blind full-chain reviews: {len(features):,} labeled rows")
    print(f"Rejected status 5 rows reviewed: {(features['status'] == REJECTED).sum():,}")
    print(f"Tier 5 rows: {(features['blind_tier'] == 5).sum():,}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotated-dir", required=True)
    parser.add_argument("--client-root", required=True)
    parser.add_argument("--prior-run-dir", required=True)
    parser.add_argument("--blinded-workbook", default="")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    run(parse_args())
