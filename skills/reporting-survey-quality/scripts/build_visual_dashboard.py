#!/usr/bin/env python3
"""Build a visual survey-quality dashboard from run artifacts."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_series(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty or column not in df:
        return pd.Series(dtype=int)
    return df[column].fillna("missing").astype(str).value_counts()


def chart_records(series: pd.Series) -> list[dict[str, int | str]]:
    return [{"name": str(index), "value": int(value)} for index, value in series.items()]


def pct(value: int, total: int) -> str:
    return "0.0%" if total == 0 else f"{(value / total) * 100:.1f}%"


def int_value(value: object) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if pd.isna(numeric):
        return 0
    return int(numeric)


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value)


def plain_text(value: object) -> str:
    raw = " ".join(text(value).split())
    replacements = {
        "gas-station": "gas station",
        "convenience-store": "convenience store",
        "sub-four-minute": "under four minute",
        "near-complete": "almost complete",
        "review-only": "review only",
        "single-grid": "single grid",
        "single-signal": "single signal",
        "fielding controls": "fielding checks",
    }
    for old, new in replacements.items():
        raw = raw.replace(old, new)
    return raw


def plain_truncate(value: object, limit: int = 420) -> str:
    raw = plain_text(value)
    if len(raw) <= limit:
        return raw
    cut = raw[:limit].rsplit(" ", 1)[0].rstrip(" .,;:")
    return cut + "..."


def kpi(label: str, value: str, detail: str = "") -> str:
    return (
        "<div class='kpi'>"
        f"<div class='kpi-label'>{html.escape(label)}</div>"
        f"<div class='kpi-value'>{html.escape(value)}</div>"
        f"<div class='kpi-detail'>{html.escape(detail)}</div>"
        "</div>"
    )


def table_html(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
    if df.empty:
        return "<p>No rows available.</p>"
    available = [col for col in columns if col in df.columns]
    if not available:
        return "<p>No configured columns available.</p>"
    subset = df[available].head(limit).fillna("")
    header = "".join(f"<th>{html.escape(col)}</th>" for col in available)
    body = []
    for _, row in subset.iterrows():
        cells = "".join(f"<td>{html.escape(str(row[col]))}</td>" for col in available)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 12) -> list[str]:
    if df.empty:
        return ["No rows available."]
    available = [col for col in columns if col in df.columns]
    if not available:
        return ["No configured columns available."]
    subset = df[available].head(limit).fillna("")
    lines = ["| " + " | ".join(available) + " |", "| " + " | ".join(["---"] * len(available)) + " |"]
    for _, row in subset.iterrows():
        values = [plain_truncate(row[col], 520).replace("|", "\\|").replace("\n", " ") for col in available]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def artifact_links(run_dir: Path) -> list[tuple[str, str]]:
    files = [
        "agent_final_review_dashboard.html",
        "agent_final_visual_findings_report.md",
        "agent_review_judgment_table.csv",
        "agent_review_judgment_summary.md",
        "agent_verified_quality_brief.md",
        "agent_discard_set.csv",
        "agent_kept_review_synthesis.md",
        "agent_kept_review_synthesis_table.csv",
        "full_chain_analyst_readout.md",
        "full_chain_best_worst_examples.csv",
        "next_pass_signal_inventory.md",
        "next_pass_signal_inventory.csv",
        "next_pass_first_pass_config.json",
        "deep_semantic_review_sample.md",
        "deep_semantic_review_sample.csv",
        "demographic_summary.md",
        "demographic_summary.csv",
        "independent_full_response_audit.md",
        "independent_full_response_audit.csv",
        "deep_findings_analysis.md",
        "workflow_improvement_log.md",
        "respondent_review_table.csv",
        "response_criteria_evidence_table.csv",
        "agent_annotation_table.csv",
        "generated_criteria_catalog.csv",
        "quality_report.md",
        "pm_quality_brief.md",
    ]
    return [(name, str(run_dir / name)) for name in files if (run_dir / name).exists() or name.startswith("agent_final_")]


def citation_map(run_dir: Path) -> list[tuple[str, str, str]]:
    return [
        ("C1", "Respondent review table", str(run_dir / "respondent_review_table.csv")),
        ("C2", "Generated criteria catalog", str(run_dir / "generated_criteria_catalog.csv")),
        ("C3", "Discovery profile", str(run_dir / "discovery_profiles.json")),
        ("C4", "Criterion evidence table", str(run_dir / "response_criteria_evidence_table.csv")),
        ("C5", "Agent judgment table", str(run_dir / "agent_review_judgment_table.csv")),
        ("C6", "Kept review synthesis", str(run_dir / "agent_kept_review_synthesis_table.csv")),
        ("C11", "Next-pass signal inventory", str(run_dir / "next_pass_signal_inventory.csv")),
        ("C12", "Deep semantic review sample", str(run_dir / "deep_semantic_review_sample.md")),
        ("C13", "Demographic summary", str(run_dir / "demographic_summary.csv")),
        ("C7", "CBRE figures report format reference", "https://mktgdocs.cbre.com/2299/12439527-d1a2-46eb-b485-4fd377f0d618-223048296/European_Data_Centres_Figures_.pdf"),
        ("C8", "Plain writing skill", "https://github.com/shreyashankar/plain-writing-skill"),
        ("C9", "Recharts documentation", "https://recharts.org/"),
        ("C10", "Open design reference", "https://github.com/nexu-io/open-design"),
    ]


def citations_html(citations: list[tuple[str, str, str]]) -> str:
    rows = []
    for key, label, source in citations:
        escaped = html.escape(source)
        if source.startswith("http"):
            source_html = f"<a href='{escaped}'>{escaped}</a>"
        else:
            source_html = escaped
        rows.append(f"<tr><td>{html.escape(key)}</td><td>{html.escape(label)}</td><td>{source_html}</td></tr>")
    return "<table><thead><tr><th>Citation</th><th>Source</th><th>Location</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def discovery_summary(discovery: dict) -> dict[str, object]:
    if not discovery:
        return {}
    profile = next(iter(discovery.values())) if len(discovery) == 1 else discovery
    return {
        "qtime_columns": profile.get("qtime_columns", []),
        "fielding_timestamp_columns": profile.get("fielding_timestamp_columns", []),
        "fielding_timestamp_stats": profile.get("fielding_timestamp_stats", {}),
        "ip_columns": profile.get("ip_columns", []),
        "matrix_group_count": len(profile.get("matrix_groups", {})),
        "matrix_groups": list(profile.get("matrix_groups", {}).keys()),
        "open_end_columns": profile.get("open_end_columns", []),
        "brand_columns": profile.get("brand_consistency_candidate_columns", []),
        "ai_columns": profile.get("ai_likelihood_columns", []),
        "candidate_analyses": profile.get("candidate_analyses", []),
    }


def discovery_html(summary: dict[str, object]) -> str:
    if not summary:
        return "<p>No discovery profile was available.</p>"
    analyses = summary.get("candidate_analyses", [])
    rows = []
    for item in analyses:
        columns = item.get("candidate_columns", [])
        column_text = ", ".join(columns[:10])
        if len(columns) > 10:
            column_text += f", plus {len(columns) - 10} more"
        rows.append(
            "<tr>"
            f"<td>{html.escape(text(item.get('analysis_id')))}</td>"
            f"<td>{html.escape(text(item.get('status')))}</td>"
            f"<td>{html.escape(column_text or 'none')}</td>"
            f"<td>{html.escape(text(item.get('meaning')))}</td>"
            "<td>[C3]</td>"
            "</tr>"
        )
    return (
        "<div class='fact-grid'>"
        f"<div><strong>Duration fields</strong><span>{html.escape(', '.join(summary.get('qtime_columns', [])) or 'none')}</span></div>"
        f"<div><strong>Fielding timestamp fields</strong><span>{html.escape(', '.join(summary.get('fielding_timestamp_columns', [])) or 'none')}</span></div>"
        f"<div><strong>IP fields</strong><span>{html.escape(', '.join(summary.get('ip_columns', [])) or 'none')}</span></div>"
        f"<div><strong>Matrix groups</strong><span>{html.escape(str(summary.get('matrix_group_count', 0)))}</span></div>"
        f"<div><strong>Open-end fields</strong><span>{html.escape(', '.join(summary.get('open_end_columns', [])) or 'none')}</span></div>"
        f"<div><strong>Brand mapping candidates</strong><span>{html.escape(str(len(summary.get('brand_columns', []))))}</span></div>"
        f"<div><strong>AI helper fields</strong><span>{html.escape(', '.join(summary.get('ai_columns', [])) or 'none found')}</span></div>"
        "</div>"
        "<table><thead><tr><th>Analysis</th><th>Status</th><th>Candidate fields</th><th>Why it matters</th><th>Cite</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def criteria_shape(criteria: pd.DataFrame) -> pd.DataFrame:
    if criteria.empty:
        return pd.DataFrame()
    rows = []
    for _, row in criteria.iterrows():
        status = text(row.get("status"))
        support_rows = int_value(row.get("support_rows", 0))
        weight = int_value(row.get("generated_weight", 0))
        tags = text(row.get("tags"))
        role = "Discovery only"
        if status == "needs_mapping":
            role = "Do not score until a project mapping exists"
        elif weight > 0 and support_rows > 0:
            role = "Use to find review candidates"
        elif support_rows == 0:
            role = "Keep available for future runs"
        if any(token in tags for token in ["relevance", "open_end", "authenticity"]):
            role += "; agent must make final semantic call"
        rows.append(
            {
                "criterion_id": row.get("criterion_id", ""),
                "scoring_id": row.get("scoring_id", ""),
                "status": status,
                "tags": tags,
                "source_columns": plain_truncate(row.get("source_columns", ""), 180),
                "generated_weight": weight,
                "support_rows": support_rows,
                "support_rate": row.get("support_rate", ""),
                "decision_role": role,
                "rationale": plain_truncate(row.get("criterion_rationale", ""), 220),
                "citation": "[C2]",
            }
        )
    return pd.DataFrame(rows)


def response_analysis_table(evidence: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty or "criterion_id" not in evidence:
        return pd.DataFrame()
    rows = []
    grouped = evidence[evidence["criterion_id"].fillna("").astype(str).ne("none")].groupby("criterion_id", dropna=False)
    for criterion, group in grouped:
        decisions = group.get("second_pass_decision", pd.Series(dtype=str)).fillna("missing").astype(str).value_counts().to_dict()
        sample = group.iloc[0]
        rows.append(
            {
                "criterion_id": criterion,
                "rows": int(len(group)),
                "discard_candidates_before_agent": int(decisions.get("discard_candidate", 0)),
                "kept_with_recommendation": int(decisions.get("keep_with_recommendation", 0)),
                "sample_source": sample.get("source_column", ""),
                "sample_observed_value": plain_truncate(sample.get("observed_value", ""), 140),
                "how_to_read": "Candidate evidence only. The agent makes the final discard decision when text meaning or language quality is involved.",
                "citation": "[C4]",
            }
        )
    return pd.DataFrame(rows).sort_values(["rows", "criterion_id"], ascending=[False, True])


def observations(respondent: pd.DataFrame, judgments: pd.DataFrame, criteria: pd.DataFrame, kept_synthesis: pd.DataFrame) -> list[str]:
    notes: list[str] = []
    total = max(1, len(respondent))
    review_total = len(judgments)
    discard_total = int(judgments.get("agent_final_decision", pd.Series(dtype=str)).astype(str).eq("discard").sum()) if not judgments.empty else 0
    notes.append(f"The scoring pass sent {review_total} of {len(respondent)} rows to the agent for final review. That is {pct(review_total, total)} of all responses. The agent recommended {discard_total} rows for discard. [C1][C5]")
    if not criteria.empty and "support_rows" in criteria:
        open_topic = criteria[criteria["criterion_id"].astype(str).str.contains("open_end_relevance|open_end_topic|relevance", case=False, regex=True)]
        if not open_topic.empty:
            support = int(pd.to_numeric(open_topic["support_rows"], errors="coerce").fillna(0).max())
            notes.append(f"Topic mismatch was a broad discovery signal with as many as {support} supported rows, but it was not used as a final semantic decision. The agent kept rows when the raw language was still about the project topic or when the flagged field was only survey-experience feedback. [C2][C5]")
    if not kept_synthesis.empty:
        for _, row in kept_synthesis.iterrows():
            notes.append(f"{int(row['kept_review_rows'])} kept rows fell under '{row['theme']}'. The report turns those rows into survey design guidance instead of discard actions. [C6]")
    if not judgments.empty:
        supplier = judgments["supplier"].fillna("missing").astype(str).value_counts()
        if not supplier.empty:
            notes.append(f"{supplier.index[0]} had the largest number of agent-reviewed rows with {int(supplier.iloc[0])}. This is a routing observation, not proof that the supplier produced bad data. [C5]")
        themes = judgments["review_theme"].fillna("missing").astype(str).value_counts()
        if not themes.empty:
            notes.append(f"The largest semantic pattern was '{themes.index[0]}' with {int(themes.iloc[0])} reviewed rows. This shows that matrix design is a larger improvement opportunity than respondent removal in this run. [C5][C6]")
    notes.append("The report uses a research-style figure structure and source notes so reviewers can move from a chart to the row-level evidence. [C7][C9]")
    notes.append("The written explanations use plain language. Each decision states what the agent read, what it decided, and why the decision is defensible. [C8]")
    return notes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def date_trend(respondent: pd.DataFrame, judgments: pd.DataFrame) -> list[dict[str, int | str]]:
    if respondent.empty or "date" not in respondent:
        return []
    rows = respondent.copy()
    rows["_date"] = pd.to_datetime(rows["date"], errors="coerce").dt.strftime("%m/%d")
    rows["_date"] = rows["_date"].fillna("unknown")
    rows["_review"] = rows.get("computed_action", pd.Series(index=rows.index, dtype=str)).astype(str).ne("Keep").astype(int)
    rows["_discard"] = 0
    if not judgments.empty and {"respondent_key", "agent_final_decision"} <= set(judgments.columns):
        discard_keys = set(judgments.loc[judgments["agent_final_decision"].astype(str).eq("discard"), "respondent_key"].astype(str))
        rows["_discard"] = rows["respondent_key"].astype(str).isin(discard_keys).astype(int)
    grouped = rows.groupby("_date", sort=True).agg(total=("respondent_key", "size"), review=("_review", "sum"), discard=("_discard", "sum")).reset_index()
    return [
        {"name": str(row["_date"]), "total": int(row["total"]), "review": int(row["review"]), "discard": int(row["discard"])}
        for _, row in grouped.iterrows()
    ]


def stacked_supplier_records(judgments: pd.DataFrame) -> list[dict[str, int | str]]:
    if judgments.empty or "supplier" not in judgments:
        return []
    decisions = judgments.get("agent_final_decision", pd.Series(index=judgments.index, dtype=str)).fillna("missing").astype(str)
    temp = judgments.assign(_decision=decisions)
    grouped = temp.groupby(["supplier", "_decision"]).size().unstack(fill_value=0)
    grouped["total"] = grouped.sum(axis=1)
    grouped = grouped.sort_values("total", ascending=False).head(10)
    records = []
    for supplier, row in grouped.iterrows():
        records.append(
            {
                "name": str(supplier),
                "discard": int(row.get("discard", 0)),
                "keep_with_review_note": int(row.get("keep_with_review_note", 0)),
                "total": int(row.get("total", 0)),
            }
        )
    return records


def scatter_series(judgments: pd.DataFrame) -> list[dict[str, object]]:
    if judgments.empty:
        return []
    colors = {"discard": "#d87855", "keep_with_review_note": "#7fbfaf"}
    labels = {"discard": "Agent discard", "keep_with_review_note": "Kept after review"}
    series = []
    for decision, group in judgments.groupby(judgments.get("agent_final_decision", pd.Series(dtype=str)).fillna("missing").astype(str)):
        points = []
        for _, row in group.iterrows():
            try:
                qtime = float(row.get("qtime", 0))
            except (TypeError, ValueError):
                qtime = 0.0
            try:
                score = float(row.get("computed_score", 0))
            except (TypeError, ValueError):
                score = 0.0
            points.append(
                {
                    "x": round(qtime, 3),
                    "y": round(score, 3),
                    "z": 80 if decision == "discard" else 48,
                    "respondent": text(row.get("respondent_key")),
                    "supplier": text(row.get("supplier")),
                    "theme": text(row.get("review_theme")),
                }
            )
        series.append({"name": labels.get(decision, decision), "decision": decision, "color": colors.get(decision, "#354244"), "data": points})
    return series


def semantic_rows(judgments: pd.DataFrame) -> pd.DataFrame:
    if judgments.empty:
        return pd.DataFrame()
    columns = [
        "respondent_key",
        "agent_final_decision",
        "review_theme",
        "supplier",
        "qtime",
        "computed_score",
        "observed_evidence",
        "raw_open_end_text",
        "response_chain_field_count",
        "full_response_chain",
        "semantic_review_chain_field_count",
        "semantic_review_chain",
        "programmatic_discard_recommendation",
        "agent_verifier_mode",
        "verifier_counterevidence",
        "semantic_discard_basis",
        "semantic_pattern_findings",
        "agent_semantic_judgment",
        "agent_linguistic_fluency_assessment",
        "agent_trust_rationale",
        "agent_recommended_next_step",
    ]
    available = [col for col in columns if col in judgments.columns]
    return judgments[available].copy()


def semantic_card_html(row: pd.Series) -> str:
    decision = text(row.get("agent_final_decision"))
    cls = "discard" if decision == "discard" else "keep"
    title = f"{text(row.get('respondent_key'))} | {text(row.get('supplier'))}"
    return (
        f"<article class='memo {cls}'>"
        f"<h3>{html.escape(title)}</h3>"
        f"<div class='memo-meta'>{html.escape(decision)} | score {html.escape(text(row.get('computed_score')))} | qtime {html.escape(text(row.get('qtime')))}</div>"
        f"<p><strong>Theme.</strong> {html.escape(text(row.get('review_theme')))}</p>"
        f"<p><strong>Full chain fields.</strong> {html.escape(text(row.get('response_chain_field_count')))}</p>"
        f"<p><strong>Focused semantic fields.</strong> {html.escape(text(row.get('semantic_review_chain_field_count')))}</p>"
        f"<p><strong>Verifier counterevidence.</strong> {html.escape(plain_truncate(row.get('verifier_counterevidence'), 360))}</p>"
        f"<p><strong>Semantic discard basis.</strong> {html.escape(plain_truncate(row.get('semantic_discard_basis'), 360))}</p>"
        f"<p><strong>Focused response chain preview.</strong> {html.escape(plain_truncate(row.get('semantic_review_chain') or row.get('full_response_chain'), 520))}</p>"
        f"<p><strong>Semantic judgment.</strong> {html.escape(plain_truncate(row.get('agent_semantic_judgment'), 520))}</p>"
        f"<p><strong>Language quality.</strong> {html.escape(plain_truncate(row.get('agent_linguistic_fluency_assessment'), 360))}</p>"
        f"<p><strong>Trust basis.</strong> {html.escape(plain_truncate(row.get('agent_trust_rationale'), 420))}</p>"
        f"<p><strong>Next step.</strong> {html.escape(plain_truncate(row.get('agent_recommended_next_step'), 260))}</p>"
        "</article>"
    )


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    respondent = read_csv(run_dir / "respondent_review_table.csv")
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")
    discard = read_csv(run_dir / "agent_discard_set.csv")
    kept_synthesis = read_csv(run_dir / "agent_kept_review_synthesis_table.csv")
    next_pass_signals = read_csv(run_dir / "next_pass_signal_inventory.csv")
    criteria = read_csv(run_dir / "generated_criteria_catalog.csv")
    evidence = read_csv(run_dir / "response_criteria_evidence_table.csv")
    demographics = read_csv(run_dir / "demographic_summary.csv")
    discovery = read_json(run_dir / "discovery_profiles.json")

    total = int(len(respondent))
    review_total = int(len(judgments)) if not judgments.empty else int((respondent.get("computed_action", pd.Series(dtype=str)) != "Keep").sum())
    discard_total = int(len(discard))
    kept_review_total = max(0, review_total - discard_total)

    action_counts = count_series(respondent, "computed_action")
    disposition_counts = count_series(respondent, "second_pass_decision")
    agent_counts = count_series(judgments, "agent_final_decision")
    kept_theme_counts = kept_synthesis.set_index("theme")["kept_review_rows"] if not kept_synthesis.empty and "theme" in kept_synthesis else pd.Series(dtype=int)
    supplier_counts = count_series(judgments, "supplier").head(10)
    all_theme_counts = count_series(judgments, "review_theme")
    trend_records = date_trend(respondent, judgments)
    supplier_stack = stacked_supplier_records(judgments)
    clusters = scatter_series(judgments)
    semantic = semantic_rows(judgments)
    citations = citation_map(run_dir)
    discoveries = discovery_summary(discovery)
    criteria_expanded = criteria_shape(criteria)
    response_criteria = response_analysis_table(evidence)
    observation_notes = observations(respondent, judgments, criteria, kept_synthesis)

    chart_payload = {
        "actions": chart_records(action_counts),
        "dispositions": chart_records(disposition_counts),
        "agentDecisions": chart_records(agent_counts),
        "keptThemes": chart_records(kept_theme_counts),
        "allThemes": chart_records(all_theme_counts),
        "suppliers": chart_records(supplier_counts),
        "trend": trend_records,
        "supplierStack": supplier_stack,
        "clusters": clusters,
        "clusterFallback": [
            {"name": series["name"], "value": len(series["data"])}
            for series in clusters
        ],
    }

    top_finding = (
        f"The agent reviewed {review_total} rows and recommended {discard_total} for discard. "
        f"The remaining {kept_review_total} rows stayed in the data and became survey improvement signals. [C1][C5][C6]"
    )
    trend_note = "Review volume was low relative to the full data file. Use the trend chart to see whether review rows came from one fielding window or appeared across the whole run. [C1][C5]"
    cluster_note = "The cluster view plots review candidates by completion time and score. Discard rows should stand apart because they combine evidence, not because one score is high. [C5]"

    css = """
    :root{--ink:#263738;--forest:#003f2d;--mint:#7fbfaf;--aqua:#20d98b;--sand:#f5f7f5;--paper:#fff;--rule:#d7dfdc;--muted:#607074;--charcoal:#354244;--plum:#7a4f6d;--amber:#d8cf8c;--coral:#d87855}
    *{box-sizing:border-box}html{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}body{font-family:Inter,Arial,sans-serif;margin:0;background:var(--sand);color:var(--ink);letter-spacing:0;line-height:1.4}
    header{position:relative;background:var(--paper);padding:46px 64px 34px;border-bottom:1px solid var(--rule);overflow:hidden}
    header:before{content:"";position:absolute;left:0;top:0;bottom:0;width:18px;background:var(--aqua)}
    .eyebrow{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:18px}
    h1{font-family:Georgia,serif;color:var(--forest);font-weight:500;font-size:58px;line-height:1;margin:0;max-width:980px;text-wrap:balance}
    .deck{font-size:20px;line-height:1.45;color:var(--muted);max-width:1040px;margin:20px 0 0;text-wrap:pretty}
    main{padding:34px 64px 54px;max-width:1560px;margin:auto}.section-title{font-size:25px;font-weight:500;color:var(--ink);margin:44px 0 15px;clear:both;text-wrap:balance}
    .sub{color:var(--muted);font-size:12px;margin-top:16px}.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;margin:24px 0 12px}
    .kpi{background:var(--paper);border-top:3px solid var(--aqua);padding:20px 22px 24px;min-height:150px;min-width:0;overflow:hidden}
    .kpi-label{font-size:12px;text-transform:uppercase;color:var(--muted);font-weight:700}.kpi-value{font-family:Georgia,serif;color:var(--forest);font-size:50px;font-weight:500;margin:14px 0 8px;font-variant-numeric:tabular-nums}.kpi-detail{font-size:14px;line-height:1.35;color:var(--muted);text-wrap:pretty}
    .report-grid{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:24px;align-items:start;margin-bottom:24px}.wide-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:24px;margin-bottom:24px}.panel{background:var(--paper);border-top:1px solid var(--rule);padding:22px 24px;margin-bottom:0;min-width:0;overflow:hidden;display:flex;flex-direction:column}
    .panel.soft{background:#edf3f1;border:0}.panel h2{font-size:13px;line-height:1.3;margin:0 0 16px;font-weight:800;text-transform:uppercase;color:var(--charcoal)}
    .chart{height:330px;min-height:0;min-width:0;max-width:100%;overflow:hidden;position:relative;margin-bottom:14px}.chart.tall{height:430px}.chart.short{height:280px}.chart.fallback-rendered{height:auto;max-height:430px;overflow:auto;padding-right:8px;overscroll-behavior:contain}.chart svg{display:block;max-width:100%}.source{font-size:11px;color:var(--muted);margin-top:auto;padding-top:8px}.callout{background:var(--paper);border-left:6px solid var(--aqua);padding:18px 22px;margin:24px 0;font-size:16px;line-height:1.45;text-wrap:pretty}
    .narrative{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:12px}.text-box{background:#eaf1ef;padding:18px 20px;line-height:1.46;color:var(--charcoal)}
    .text-box strong{display:block;margin-bottom:8px;color:var(--forest)}.panel p{font-size:15px;line-height:1.45;color:var(--charcoal);margin:0 0 14px;text-wrap:pretty}
    .fact-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 20px}.fact-grid div{background:#f7faf9;border-top:1px solid var(--rule);padding:14px}.fact-grid strong{display:block;color:var(--forest);font-size:12px;text-transform:uppercase;margin-bottom:6px}.fact-grid span{font-size:13px;color:var(--charcoal);line-height:1.35}
    .observation-list{margin:0;padding-left:18px}.observation-list li{font-size:15px;line-height:1.5;margin:10px 0;color:var(--charcoal)}
    .memo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.memo{background:var(--paper);border-left:5px solid var(--mint);padding:18px 20px;border-top:1px solid var(--rule)}.memo.discard{border-left-color:var(--coral)}.memo h3{font-size:15px;margin:0 0 6px;color:var(--forest)}.memo-meta{font-size:12px;color:var(--muted);margin-bottom:12px}.memo p{font-size:13px;line-height:1.45;margin:8px 0}
    .fallback-row{display:grid;grid-template-columns:minmax(140px,240px) minmax(80px,1fr) 54px;gap:12px;align-items:center;margin:10px 0;min-width:0}.fallback-label{font-size:12px;line-height:1.25;color:var(--charcoal);min-width:0;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}.fallback-track{height:16px;background:#e7eeeb;min-width:0}.fallback-fill{height:100%;background:var(--mint)}.fallback-value{text-align:right;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.fallback-more{font-size:12px;color:var(--muted);margin-top:10px}
    table{width:100%;border-collapse:collapse;font-size:12px;line-height:1.35}th,td{border-bottom:1px solid #dfe7e4;padding:9px 8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{color:var(--muted);font-weight:800;text-transform:uppercase;font-size:10px;background:#f7faf9}
    .semantic-table td:nth-child(7),.semantic-table td:nth-child(8),.semantic-table td:nth-child(9){min-width:220px}.artifact td:first-child{font-weight:700}.footer{border-top:1px solid var(--rule);color:var(--muted);font-size:12px;margin-top:28px;padding-top:16px}
    @media(max-width:980px){header,main{padding-left:26px;padding-right:26px}h1{font-size:42px}.kpi-grid,.report-grid,.narrative,.memo-grid,.fact-grid{grid-template-columns:1fr}.chart{height:300px}.fallback-row{grid-template-columns:minmax(0,1fr);gap:6px}.fallback-value{text-align:left}}
    """
    chart_js = f"""
    window.__SURVEY_CHARTS__ = {json.dumps(chart_payload, ensure_ascii=True)};
    const colors = ['#7fbfaf','#354244','#20d98b','#d8cf8c','#d87855','#7a4f6d'];
    function escapeText(value) {{
      return String(value).replace(/[&<>"']/g, (char) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));
    }}
    function renderFallback(id, data, options = {{}}) {{
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.add('fallback-rendered');
      const rows = Array.isArray(data) ? data : [];
      const limit = options.limit || 12;
      const visibleRows = rows.slice(0, limit);
      const max = Math.max(1, ...rows.map((row) => row.value || row.total || row.review || row.discard || 0));
      const htmlRows = visibleRows.map((row) => {{
        const value = row.value || row.total || row.review || row.discard || 0;
        const width = Math.max(3, Math.round((value / max) * 100));
        return `<div class="fallback-row"><div class="fallback-label">${{escapeText(row.name)}}</div><div class="fallback-track"><div class="fallback-fill" style="width:${{width}}%"></div></div><div class="fallback-value">${{value}}</div></div>`;
      }}).join('');
      const more = rows.length > limit ? `<div class="fallback-more">Showing ${{limit}} of ${{rows.length}} rows. Open the source table for the full list.</div>` : '';
      el.innerHTML = htmlRows + more;
    }}
    function renderFallbacks() {{
      ['actions','dispositions','agentDecisions','keptThemes','allThemes','suppliers','trend','supplierStack'].forEach((key) => renderFallback('chart-' + key, window.__SURVEY_CHARTS__[key]));
      renderFallback('chart-clusters', window.__SURVEY_CHARTS__.clusterFallback);
    }}
    function renderCharts() {{
      const R = window.Recharts;
      if (!window.React || !window.ReactDOM || !R) {{
        renderFallbacks();
        return;
      }}
      const e = React.createElement;
      const tooltip = e(R.Tooltip, {{ wrapperStyle: {{ border: '1px solid #d7dfdc' }}, contentStyle: {{ borderRadius: 0, color: '#263738' }} }});
      function mount(id, chart) {{
        const el = document.getElementById(id);
        if (!el) return;
        ReactDOM.createRoot(el).render(e(R.ResponsiveContainer, {{ width: '100%', height: '100%' }}, chart));
      }}
      function BarPanel(id, data, layout='vertical') {{
        const chart = layout === 'vertical'
          ? e(R.BarChart, {{ data, margin: {{ top: 8, right: 18, left: 8, bottom: 18 }} }},
              e(R.CartesianGrid, {{ stroke: '#d7dfdc', vertical: false }}),
              e(R.XAxis, {{ dataKey: 'name', tick: {{ fill: '#607074', fontSize: 11 }}, interval: 0 }}),
              e(R.YAxis, {{ tick: {{ fill: '#607074', fontSize: 11 }}, allowDecimals: false }}),
              tooltip,
              e(R.Bar, {{ dataKey: 'value', fill: '#7fbfaf', label: {{ position: 'top', fill: '#263738', fontSize: 12 }} }}))
          : e(R.BarChart, {{ data, layout: 'vertical', margin: {{ top: 6, right: 28, left: 16, bottom: 6 }} }},
              e(R.CartesianGrid, {{ stroke: '#d7dfdc', horizontal: false }}),
              e(R.XAxis, {{ type: 'number', tick: {{ fill: '#607074', fontSize: 11 }}, allowDecimals: false }}),
              e(R.YAxis, {{ type: 'category', dataKey: 'name', width: 210, tick: {{ fill: '#607074', fontSize: 11 }} }}),
              tooltip,
              e(R.Bar, {{ dataKey: 'value', fill: '#7fbfaf', label: {{ position: 'right', fill: '#263738', fontSize: 12 }} }}));
        mount(id, chart);
      }}
      function DonutPanel(id, data) {{
        const chart = e(R.PieChart, null,
          e(R.Pie, {{ data, dataKey: 'value', nameKey: 'name', innerRadius: 68, outerRadius: 112, paddingAngle: 1, label: (p) => p.value }},
            data.map((_, i) => e(R.Cell, {{ key: i, fill: colors[i % colors.length] }}))),
          e(R.Legend, {{ verticalAlign: 'middle', align: 'right', layout: 'vertical', wrapperStyle: {{ fontSize: 12, color: '#263738' }} }}),
          tooltip);
        mount(id, chart);
      }}
      function TrendPanel(id, data) {{
        const chart = e(R.ComposedChart, {{ data, margin: {{ top: 8, right: 20, left: 0, bottom: 18 }} }},
          e(R.CartesianGrid, {{ stroke: '#d7dfdc', vertical: false }}),
          e(R.XAxis, {{ dataKey: 'name', tick: {{ fill: '#607074', fontSize: 11 }} }}),
          e(R.YAxis, {{ yAxisId: 'left', tick: {{ fill: '#607074', fontSize: 11 }}, allowDecimals: false }}),
          e(R.YAxis, {{ yAxisId: 'right', orientation: 'right', tick: {{ fill: '#607074', fontSize: 11 }}, allowDecimals: false }}),
          tooltip,
          e(R.Legend, {{ wrapperStyle: {{ fontSize: 12 }} }}),
          e(R.Bar, {{ yAxisId: 'left', dataKey: 'total', fill: '#d8cf8c', name: 'All responses' }}),
          e(R.Line, {{ yAxisId: 'right', type: 'monotone', dataKey: 'review', stroke: '#354244', strokeWidth: 2, dot: true, name: 'Review rows' }}),
          e(R.Line, {{ yAxisId: 'right', type: 'monotone', dataKey: 'discard', stroke: '#d87855', strokeWidth: 2, dot: true, name: 'Agent discards' }}));
        mount(id, chart);
      }}
      function StackedSupplierPanel(id, data) {{
        const chart = e(R.BarChart, {{ data, layout: 'vertical', margin: {{ top: 6, right: 28, left: 16, bottom: 6 }} }},
          e(R.CartesianGrid, {{ stroke: '#d7dfdc', horizontal: false }}),
          e(R.XAxis, {{ type: 'number', tick: {{ fill: '#607074', fontSize: 11 }}, allowDecimals: false }}),
          e(R.YAxis, {{ type: 'category', dataKey: 'name', width: 210, tick: {{ fill: '#607074', fontSize: 11 }} }}),
          tooltip,
          e(R.Legend, {{ wrapperStyle: {{ fontSize: 12 }} }}),
          e(R.Bar, {{ dataKey: 'keep_with_review_note', stackId: 'a', fill: '#7fbfaf', name: 'Kept after review' }}),
          e(R.Bar, {{ dataKey: 'discard', stackId: 'a', fill: '#d87855', name: 'Agent discard' }}));
        mount(id, chart);
      }}
      function ClusterPanel(id, series) {{
        const chart = e(R.ScatterChart, {{ margin: {{ top: 12, right: 22, bottom: 24, left: 4 }} }},
          e(R.CartesianGrid, {{ stroke: '#d7dfdc' }}),
          e(R.XAxis, {{ type: 'number', dataKey: 'x', name: 'qtime', tick: {{ fill: '#607074', fontSize: 11 }}, label: {{ value: 'Completion time in seconds', position: 'insideBottom', offset: -12, fill: '#607074', fontSize: 12 }} }}),
          e(R.YAxis, {{ type: 'number', dataKey: 'y', name: 'score', tick: {{ fill: '#607074', fontSize: 11 }}, allowDecimals: false, label: {{ value: 'Generated score', angle: -90, position: 'insideLeft', fill: '#607074', fontSize: 12 }} }}),
          e(R.ZAxis, {{ type: 'number', dataKey: 'z', range: [60, 150] }}),
          tooltip,
          e(R.Legend, {{ wrapperStyle: {{ fontSize: 12 }} }}),
          series.map((item) => e(R.Scatter, {{ key: item.name, name: item.name, data: item.data, fill: item.color }})));
        mount(id, chart);
      }}
      BarPanel('chart-actions', window.__SURVEY_CHARTS__.actions);
      BarPanel('chart-dispositions', window.__SURVEY_CHARTS__.dispositions);
      DonutPanel('chart-agentDecisions', window.__SURVEY_CHARTS__.agentDecisions);
      DonutPanel('chart-allThemes', window.__SURVEY_CHARTS__.allThemes);
      BarPanel('chart-keptThemes', window.__SURVEY_CHARTS__.keptThemes, 'horizontal');
      BarPanel('chart-suppliers', window.__SURVEY_CHARTS__.suppliers, 'horizontal');
      TrendPanel('chart-trend', window.__SURVEY_CHARTS__.trend);
      StackedSupplierPanel('chart-supplierStack', window.__SURVEY_CHARTS__.supplierStack);
      ClusterPanel('chart-clusters', window.__SURVEY_CHARTS__.clusters);
    }}
    window.addEventListener('load', renderCharts);
    """
    discard_cards = "".join(semantic_card_html(row) for _, row in semantic[semantic.get("agent_final_decision", pd.Series(dtype=str)).eq("discard")].iterrows())
    keep_cards = "".join(semantic_card_html(row) for _, row in semantic[semantic.get("agent_final_decision", pd.Series(dtype=str)).ne("discard")].head(6).iterrows())
    html_doc = [
        "<!doctype html><html><head><meta charset='utf-8'><title>Survey Quality Dashboard</title>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<style>{css}</style></head><body>",
        "<header><div class='eyebrow'>Figures | Survey Quality Intelligence | Agent-Verified Run</div>",
        "<h1>Survey Quality Review</h1>",
        "<p class='deck'>This report shows how the agent moved from candidate flags to final discard decisions. It also shows which kept rows should improve the survey design.</p>",
        f"<div class='sub'>Run directory: {html.escape(str(run_dir))}</div></header><main>",
        "<section class='kpi-grid'>",
        kpi("Total responses", str(total), "Rows in the respondent review table."),
        kpi("Review-tagged", str(review_total), f"{pct(review_total, total)} of responses."),
        kpi("Agent discards", str(discard_total), f"{pct(discard_total, total)} of responses."),
        kpi("Kept review rows", str(kept_review_total), "Rows kept with notes and design guidance."),
        "</section>",
        f"<div class='callout'>{html.escape(top_finding)}</div>",
        "<section class='narrative'>",
        "<div class='text-box'><strong>Decision rule</strong>Scoring finds rows to review. The agent makes the final discard decision after reading the evidence.</div>",
        "<div class='text-box'><strong>Semantic rule</strong>Keyword mismatch is not a final decision. The agent checks whether the answer is actually off topic or only worded differently.</div>",
        "<div class='text-box'><strong>Survey design rule</strong>Rows that survive review become recommendations for better questions and clearer fielding controls.</div>",
        "</section>",
        "<h2 class='section-title'>Decision funnel</h2><section class='report-grid'>",
        "<section class='panel'><h2>Figure 1: Scoring action counts</h2><div id='chart-actions' class='chart'></div><div class='source'>Source: Opulent scoring artifacts. [C1]</div></section>",
        "<section class='panel'><h2>Figure 2: Second pass disposition</h2><div id='chart-dispositions' class='chart'></div><div class='source'>Source: respondent review table. [C1]</div></section>",
        "</section><section class='report-grid'>",
        "<section class='panel soft'><h2>Figure 3: Agent review decisions</h2><div id='chart-agentDecisions' class='chart'></div><div class='source'>Source: agent judgment table. [C5]</div></section>",
        "<section class='panel soft'><h2>Figure 4: Review themes</h2><div id='chart-allThemes' class='chart'></div><div class='source'>Source: agent judgment table. [C5]</div></section>",
        "</section>",
        "<h2 class='section-title'>Trends and clusters</h2><section class='report-grid'>",
        f"<section class='panel'><h2>Figure 5: Fielding trend</h2><div id='chart-trend' class='chart'></div><p>{html.escape(trend_note)}</p><div class='source'>Source: respondent date field and final agent decisions. [C1][C5]</div></section>",
        f"<section class='panel'><h2>Figure 6: Review candidate cluster</h2><div id='chart-clusters' class='chart'></div><p>{html.escape(cluster_note)}</p><div class='source'>X axis is qtime. Y axis is generated score. Point color is final agent decision.</div></section>",
        "</section>",
        "<h2 class='section-title'>Supplier and improvement views</h2><section class='report-grid'>",
        "<section class='panel'><h2>Figure 7: Supplier review stack</h2><div id='chart-supplierStack' class='chart'></div><div class='source'>Supplier concentration is context. It is not proof of poor quality. [C5]</div></section>",
        "<section class='panel'><h2>Figure 8: Kept review themes</h2><div id='chart-keptThemes' class='chart'></div><div class='source'>Rows kept after review are used to improve questions and fielding controls. [C6]</div></section>",
        "</section><section class='wide-grid'>",
        "<section class='panel'><h2>Figure 9: Review rows by supplier</h2><div id='chart-suppliers' class='chart short'></div><div class='source'>Source: agent judgment table. [C5]</div></section>",
        "</section>",
        "<h2 class='section-title'>Discovery and scorer criteria</h2>",
        "<section class='panel'><h2>New discoveries from the raw export</h2>",
        discovery_html(discoveries),
        "</section>",
        "<section class='panel'><h2>Expanded scorer criteria shape</h2>",
        table_html(criteria_expanded, ["criterion_id", "status", "tags", "source_columns", "generated_weight", "support_rows", "support_rate", "decision_role", "rationale", "citation"], 40),
        "</section>",
        "<section class='panel'><h2>Response analysis criteria</h2>",
        table_html(response_criteria, ["criterion_id", "rows", "discard_candidates_before_agent", "kept_with_recommendation", "sample_source", "sample_observed_value", "how_to_read", "citation"], 40),
        "</section>",
        "<h2 class='section-title'>Dataset observations</h2>",
        "<section class='panel'><h2>Observed semantic and scoring patterns</h2><ul class='observation-list'>",
        "".join(f"<li>{html.escape(note)}</li>" for note in observation_notes),
        "</ul></section>",
        "<h2 class='section-title'>Agent semantic reasoning</h2>",
        "<section class='memo-grid'>",
        discard_cards or "<p>No discard rows were found.</p>",
        "</section>",
        "<section class='panel'><h2>All agent-reviewed rows</h2>",
        table_html(semantic, ["respondent_key", "agent_final_decision", "review_theme", "supplier", "qtime", "computed_score", "programmatic_discard_recommendation", "response_chain_field_count", "semantic_review_chain_field_count", "verifier_counterevidence", "semantic_discard_basis", "agent_semantic_judgment", "agent_trust_rationale", "agent_recommended_next_step"], 30).replace("<table>", "<table class='semantic-table'>"),
        "</section>",
        "<h2 class='section-title'>Kept rows that improve the survey</h2>",
        "<section class='memo-grid'>",
        keep_cards or "<p>No kept review rows were found.</p>",
        "</section>",
        "<section class='panel'><h2>Kept review synthesis</h2>",
        table_html(kept_synthesis, ["theme", "kept_review_rows", "why_kept", "survey_question_or_parameter_recommendation", "suggested_quality_parameter"], 10),
        "</section>",
        "<section class='panel'><h2>Next-pass signals</h2>",
        table_html(next_pass_signals, ["signal_id", "support_rows", "critical_signal", "first_pass_change", "evidence_needed", "escalation_rule"], 12),
        "<div class='source'>Source: next-pass signal inventory. [C11]</div>",
        "</section>",
        "<h2 class='section-title'>Demographic and aggregate insights</h2>",
        "<section class='panel'><h2>Demographic profile</h2>",
        table_html(demographics, ["field", "question_text", "nonempty_rows", "mean", "median", "top_values"], 20),
        "<div class='source'>Source: demographic summary from respondent data and Datamap labels. [C13]</div>",
        "</section>",
        "<section class='panel'><h2>Citations</h2>",
        citations_html(citations),
        "</section>",
        "<section class='panel'><h2>Artifact index</h2><table class='artifact'><thead><tr><th>Artifact</th><th>Path</th></tr></thead><tbody>",
        "".join(
            f"<tr><td>{html.escape(name)}</td><td>{html.escape(path)}</td></tr>"
            for name, path in artifact_links(run_dir)
        ),
        "</tbody></table></section>",
        "<div class='footer'>Generated from agent judgment artifacts. Final PM labels, when present, are validation data and not decision input.</div>",
        "<script src='https://unpkg.com/react@18/umd/react.production.min.js'></script>",
        "<script src='https://unpkg.com/react-dom@18/umd/react-dom.production.min.js'></script>",
        "<script src='https://unpkg.com/recharts/umd/Recharts.min.js'></script>",
        f"<script>{chart_js}</script>",
        "</main></body></html>",
    ]
    (run_dir / "agent_final_review_dashboard.html").write_text("\n".join(html_doc), encoding="utf-8")

    md = [
        "# Agent final visual findings report",
        "",
        f"Run directory: `{run_dir}`",
        "",
        "## Main finding",
        top_finding,
        "",
        "## KPI summary",
        f"- Total responses: {total}",
        f"- Review-tagged rows: {review_total} ({pct(review_total, total)})",
        f"- Agent discard rows: {discard_total} ({pct(discard_total, total)})",
        f"- Kept review rows used for survey improvements: {kept_review_total}",
        "",
        "## Figure guide",
        "- Figure 1 shows action counts from the scoring pass.",
        "- Figure 2 shows the second pass disposition before the agent made final discard decisions.",
        "- Figure 3 shows the final agent decisions.",
        "- Figure 4 shows the review themes.",
        "- Figure 5 shows review and discard volume by fielding date.",
        "- Figure 6 plots review candidates by completion time and generated score.",
        "- Figure 7 shows review outcomes by supplier.",
        "- Figure 8 shows kept review themes.",
        "- Figure 9 shows review rows by supplier.",
        "",
        "## Trend analysis",
        trend_note,
        "",
        "## Cluster analysis",
        cluster_note,
        "",
        "## New discoveries from the raw export",
        f"- Duration fields: {', '.join(discoveries.get('qtime_columns', [])) or 'none'} [C3]",
        f"- Fielding timestamp fields: {', '.join(discoveries.get('fielding_timestamp_columns', [])) or 'none'} [C3]",
        f"- IP fields: {', '.join(discoveries.get('ip_columns', [])) or 'none'} [C3]",
        f"- Matrix groups: {discoveries.get('matrix_group_count', 0)} [C3]",
        f"- Open-end fields: {', '.join(discoveries.get('open_end_columns', [])) or 'none'} [C3]",
        f"- Brand mapping candidates: {len(discoveries.get('brand_columns', []))} [C3]",
        f"- AI helper fields: {', '.join(discoveries.get('ai_columns', [])) or 'none found'} [C3]",
        "",
        "## Expanded scorer criteria shape",
        *markdown_table(criteria_expanded, ["criterion_id", "status", "tags", "source_columns", "generated_weight", "support_rows", "support_rate", "decision_role", "rationale", "citation"], 40),
        "",
        "## Response analysis criteria",
        *markdown_table(response_criteria, ["criterion_id", "rows", "discard_candidates_before_agent", "kept_with_recommendation", "sample_source", "sample_observed_value", "how_to_read", "citation"], 40),
        "",
        "## Dataset observations",
        *[f"- {note}" for note in observation_notes],
        "",
        "## Agent review decisions",
        *[f"- {idx}: {int(val)} ({pct(int(val), review_total)})" for idx, val in agent_counts.items()],
        "",
        "## Agent discard set",
        *markdown_table(discard, ["respondent_key", "agent_discard_rationale", "observed_evidence", "supplier", "qtime", "agent_semantic_judgment", "agent_trust_rationale"], 10),
        "",
        "## All semantic decisions",
        *markdown_table(semantic, ["respondent_key", "agent_final_decision", "review_theme", "supplier", "qtime", "computed_score", "programmatic_discard_recommendation", "response_chain_field_count", "semantic_review_chain_field_count", "verifier_counterevidence", "semantic_discard_basis", "agent_semantic_judgment", "agent_trust_rationale"], 30),
        "",
        "## Survey improvement synthesis",
        *markdown_table(kept_synthesis, ["theme", "kept_review_rows", "why_kept", "survey_question_or_parameter_recommendation", "suggested_quality_parameter"], 10),
        "",
        "## Next-pass signals",
        *markdown_table(next_pass_signals, ["signal_id", "support_rows", "critical_signal", "first_pass_change", "evidence_needed", "escalation_rule"], 12),
        "",
        "## Demographic and aggregate insights",
        *markdown_table(demographics, ["field", "question_text", "nonempty_rows", "mean", "median", "top_values"], 20),
        "",
        "## Final review rule",
        "Use scoring to find candidates. Use the agent to make the final semantic discard decision. Use kept review rows to improve the next survey. [C5][C6]",
        "",
        "## Citations",
        *[f"- [{key}] {label}: {source}" for key, label, source in citations],
        "",
        "## Artifact index",
        *[f"- `{name}`: `{path}`" for name, path in artifact_links(run_dir)],
    ]
    (run_dir / "agent_final_visual_findings_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(run_dir / "agent_final_review_dashboard.html")
    print(run_dir / "agent_final_visual_findings_report.md")


if __name__ == "__main__":
    main()
