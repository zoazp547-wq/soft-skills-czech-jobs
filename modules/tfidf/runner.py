"""Runner for the TF-IDF analysis module.

Called by main.py with the parsed YAML config dicts. Reads the NLP-processed
JSON, computes TF-IDF, extracts top terms, classifies them, detects
competencies (dual-mode: all_text + target_sections_only), generates charts,
writes reports, produces framework_summary.json and subgroup_significance.json.
"""

import json
import logging
import os

from modules.tfidf.analyzer import (
    build_subgroup_tfidf,
    build_tfidf_matrix,
    detect_competencies_dual_mode,
    extract_top_terms,
)
from modules.tfidf.stats import compute_subgroup_significance
from modules.tfidf.visualizer import (
    generate_interactive_html,
    plot_competency_prevalence,
    plot_subgroup_comparison,
    plot_top_terms,
)

logger = logging.getLogger("[tfidf.runner]")


def run(global_config: dict, module_config: dict) -> None:
    """Execute the TF-IDF analysis pipeline.

    Args:
        global_config: Parsed contents of config/settings.yaml.
        module_config: Parsed contents of config/tfidf.yaml.
    """
    base_output_dir = global_config.get("output", {}).get("output_dir", "output")
    analysis_dir = module_config.get("output", {}).get("output_dir", "tfidf_analysis")
    output_dir = os.path.join(base_output_dir, analysis_dir)

    input_file = module_config.get("input", {}).get(
        "input_file", "jobs_cz_administrativa_nlp.json"
    )
    input_path = os.path.join(base_output_dir, input_file)

    report_file = module_config.get("output", {}).get(
        "report_file", "top_terms_report.json"
    )
    chart_file = module_config.get("output", {}).get(
        "chart_file", "top_terms_tfidf.png"
    )
    comp_report_file = module_config.get("output", {}).get(
        "competency_report_file", "competency_report.json"
    )
    comp_chart_file = module_config.get("output", {}).get(
        "competency_chart_file", "competency_prevalence.png"
    )
    interactive_file = module_config.get("output", {}).get(
        "interactive_file", "competency_dashboard.html"
    )
    subgroup_report_file = module_config.get("output", {}).get(
        "subgroup_report_file", "subgroup_comparison.json"
    )
    subgroup_chart_file = module_config.get("output", {}).get(
        "subgroup_chart_file", "subgroup_top_terms.png"
    )
    framework_summary_file = module_config.get("output", {}).get(
        "framework_summary_file", "framework_summary.json"
    )
    subgroup_significance_file = module_config.get("output", {}).get(
        "subgroup_significance_file", "subgroup_significance.json"
    )

    report_path = os.path.join(output_dir, report_file)
    chart_path = os.path.join(output_dir, chart_file)
    comp_report_path = os.path.join(output_dir, comp_report_file)
    comp_chart_path = os.path.join(output_dir, comp_chart_file)
    interactive_path = os.path.join(output_dir, interactive_file)
    subgroup_report_path = os.path.join(output_dir, subgroup_report_file)
    subgroup_chart_path = os.path.join(output_dir, subgroup_chart_file)
    framework_summary_path = os.path.join(output_dir, framework_summary_file)
    subgroup_significance_path = os.path.join(output_dir, subgroup_significance_file)

    # --- Load input ---
    rows = _read_json(input_path)
    if not rows:
        logger.warning("No rows loaded from %s — nothing to analyze", input_path)
        return

    token_field = module_config.get("input", {}).get("token_field", "description_tokens")
    documents = [row.get(token_field, "") for row in rows]
    non_empty = [d for d in documents if d.strip()]

    logger.info(
        "Loaded %d rows from %s (%d non-empty '%s' fields)",
        len(rows),
        input_path,
        len(non_empty),
        token_field,
    )

    if not non_empty:
        logger.warning("All documents are empty — nothing to analyze")
        return

    # --- Build TF-IDF matrix ---
    tfidf_matrix, feature_names = build_tfidf_matrix(non_empty, module_config)

    # --- Extract top terms with classification ---
    top_terms = extract_top_terms(tfidf_matrix, feature_names, module_config)

    # --- Write TF-IDF report ---
    _write_report(top_terms, report_path, len(rows), len(feature_names))

    # --- Generate TF-IDF chart ---
    plot_top_terms(top_terms, chart_path, module_config)

    # --- Dual-mode competency detection ---
    primary_mode = module_config.get("detection", {}).get(
        "primary_mode", "target_sections_only"
    )
    dual_results = detect_competencies_dual_mode(rows, module_config)
    primary_results = dual_results.get(primary_mode, dual_results["target_sections_only"])

    # --- Write extended competency report (both modes + delta) ---
    _write_competency_report_dual(
        dual_results, comp_report_path, len(rows), primary_mode
    )

    # --- Generate competency chart (uses primary mode) ---
    plot_competency_prevalence(
        primary_results["aggregate"], comp_chart_path, module_config
    )

    # --- Generate interactive HTML dashboard (uses primary mode) ---
    generate_interactive_html(
        primary_results, rows, interactive_path, module_config
    )

    # --- Subgroup TF-IDF analysis (e.g., Praha vs. Regiony) ---
    subgroup_results = build_subgroup_tfidf(rows, module_config)
    if subgroup_results:
        _write_json(subgroup_results, subgroup_report_path)
        logger.info("Subgroup report written: %s", subgroup_report_path)
        plot_subgroup_comparison(subgroup_results, subgroup_chart_path, module_config)

    # --- Framework summary (built from config) ---
    framework_summary = _build_framework_summary(module_config)
    _write_json(framework_summary, framework_summary_path)
    logger.info("Framework summary written: %s", framework_summary_path)

    # --- Subgroup statistical significance ---
    sig_results = compute_subgroup_significance(rows, primary_results, module_config)
    if sig_results:
        _write_json(sig_results, subgroup_significance_path)
        logger.info("Subgroup significance written: %s", subgroup_significance_path)
    else:
        logger.info("Subgroup significance skipped (disabled or insufficient groups)")

    logger.info(
        "TF-IDF analysis complete — reports: %s, %s | charts: %s, %s | "
        "dashboard: %s | framework: %s | significance: %s",
        report_path,
        comp_report_path,
        chart_path,
        comp_chart_path,
        interactive_path,
        framework_summary_path,
        subgroup_significance_path,
    )


# ---------------------------------------------------------------------------
# Framework summary — introspects tfidf.yaml competency definitions
# ---------------------------------------------------------------------------


def _build_framework_summary(config: dict) -> dict:
    """Build a framework summary from the competency definitions in config.

    Produces counts of keywords, phrases, and exclusions per competency
    and per group, so thesis text can be verified against the actual
    implemented framework without manual counting.
    """
    comp_defs = config.get("competencies", {})
    detection_cfg = config.get("detection", {})

    groups: dict[str, dict] = {}
    competencies: dict[str, dict] = {}
    grand_token_keywords = 0
    grand_phrase_patterns = 0
    grand_exclusion_phrases = 0

    for comp_key, comp_def in comp_defs.items():
        token_kws = comp_def.get("token_keywords", [])
        phrases = comp_def.get("phrase_patterns", [])
        exclusions = comp_def.get("exclusion_phrases", [])
        group = comp_def.get("group", "Uncategorized")
        min_ind = comp_def.get("min_indicators", 1)

        competencies[comp_key] = {
            "label": comp_def.get("label", comp_key),
            "group": group,
            "token_keyword_count": len(token_kws),
            "phrase_pattern_count": len(phrases),
            "exclusion_phrase_count": len(exclusions),
            "min_indicators": min_ind,
            "token_keywords": token_kws,
            "phrase_patterns": phrases,
            "exclusion_phrases": exclusions,
        }

        grand_token_keywords += len(token_kws)
        grand_phrase_patterns += len(phrases)
        grand_exclusion_phrases += len(exclusions)

        if group not in groups:
            groups[group] = {"count": 0, "competency_keys": []}
        groups[group]["count"] += 1
        groups[group]["competency_keys"].append(comp_key)

    return {
        "total_competencies": len(comp_defs),
        "groups": groups,
        "competencies": competencies,
        "grand_totals": {
            "total_token_keywords": grand_token_keywords,
            "total_phrase_patterns": grand_phrase_patterns,
            "total_exclusion_phrases": grand_exclusion_phrases,
            "total_indicators": grand_token_keywords + grand_phrase_patterns,
        },
        "detection_settings": {
            "primary_mode": detection_cfg.get("primary_mode", "target_sections_only"),
            "target_section_labels": detection_cfg.get(
                "target_section_labels",
                ["requirements", "responsibilities", "other"],
            ),
            "significance_alpha": detection_cfg.get("significance_alpha", 0.05),
        },
    }


# ---------------------------------------------------------------------------
# Dual-mode competency report
# ---------------------------------------------------------------------------


def _write_competency_report_dual(
    dual_results: dict,
    path: str,
    total_documents: int,
    primary_mode: str,
) -> None:
    """Write the competency detection report with both detection modes.

    Top-level ``aggregate`` and ``per_job`` keys point to the primary mode
    for backward compatibility.  The ``dual_mode`` block adds both modes'
    aggregates, per-mode rankings, and a delta comparison.
    """
    primary = dual_results.get(primary_mode, dual_results["target_sections_only"])
    all_text = dual_results["all_text"]
    target_only = dual_results["target_sections_only"]

    all_agg = all_text["aggregate"]
    tgt_agg = target_only["aggregate"]

    # Per-mode ranked lists (descending by prevalence)
    def _ranked(agg: dict) -> list[dict]:
        items = sorted(
            agg.items(),
            key=lambda kv: -kv[1].get("prevalence_pct", 0),
        )
        return [
            {
                "rank": i + 1,
                "key": key,
                "label": val.get("label", key),
                "group": val.get("group", ""),
                "prevalence_pct": val.get("prevalence_pct", 0),
                "detected_count": val.get("detected_count", 0),
            }
            for i, (key, val) in enumerate(items)
        ]

    all_text_rankings = _ranked(all_agg)
    target_rankings = _ranked(tgt_agg)

    # Delta between modes
    delta: dict[str, dict] = {}
    for comp_key in all_agg:
        at = all_agg[comp_key]
        ts = tgt_agg.get(comp_key, {})
        at_pct = at.get("prevalence_pct", 0)
        ts_pct = ts.get("prevalence_pct", 0)
        delta[comp_key] = {
            "label": at.get("label", comp_key),
            "group": at.get("group", ""),
            "all_text_prevalence_pct": at_pct,
            "target_sections_prevalence_pct": ts_pct,
            "delta_pct": round(at_pct - ts_pct, 1),
            "all_text_count": at.get("detected_count", 0),
            "target_sections_count": ts.get("detected_count", 0),
        }

    report = {
        "summary": {
            "total_documents": total_documents,
            "competencies_analyzed": len(primary.get("aggregate", {})),
            "primary_mode": primary_mode,
            "detection_modes": ["all_text", "target_sections_only"],
        },
        "aggregate": primary["aggregate"],
        "per_job": primary["per_job"],
        "dual_mode": {
            "all_text": {
                "aggregate": all_agg,
                "rankings": all_text_rankings,
            },
            "target_sections_only": {
                "aggregate": tgt_agg,
                "rankings": target_rankings,
            },
            "delta": delta,
        },
    }

    _write_json(report, path)
    logger.info("Competency report (dual-mode) written: %s", path)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_json(path: str) -> list[dict]:
    """Read a JSON array file and return a list of row dicts."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if not isinstance(data, list):
                logger.error("Expected JSON array in %s, got %s", path, type(data).__name__)
                return []
            return data
    except FileNotFoundError:
        logger.error("Input JSON not found: %s", path)
        return []
    except json.JSONDecodeError as exc:
        logger.error("Malformed JSON in %s: %s", path, exc)
        return []
    except Exception:
        logger.exception("Failed to read input JSON: %s", path)
        return []


def _write_report(
    top_terms: list[dict],
    path: str,
    total_documents: int,
    vocabulary_size: int,
) -> None:
    """Write the TF-IDF top terms report as a JSON file."""
    report = {
        "summary": {
            "total_documents": total_documents,
            "vocabulary_size": vocabulary_size,
            "top_n": len(top_terms),
            "soft_count": sum(1 for t in top_terms if t["category"] == "soft"),
            "hard_count": sum(1 for t in top_terms if t["category"] == "hard"),
            "noise_count": sum(1 for t in top_terms if t["category"] == "noise"),
        },
        "top_terms": top_terms,
    }

    _write_json(report, path)
    logger.info("TF-IDF report written: %s", path)


def _write_json(data: dict, path: str) -> None:
    """Write a dict to a JSON file with proper encoding."""
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to write JSON: %s", path)
