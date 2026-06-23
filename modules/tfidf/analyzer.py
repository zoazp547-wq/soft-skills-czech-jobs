"""TF-IDF analysis engine.

Computes a TF-IDF matrix from tokenized job descriptions, extracts
the top-N terms by mean TF-IDF score, counts document frequency,
classifies each term as soft skill / hard skill / noise, and detects
competencies using hybrid token-keyword + phrase-pattern matching.

Dual-mode competency detection
--------------------------------
Two named modes are supported:

``all_text``
    Matches token keywords against the full lemmatized token set and
    phrase patterns against the full description text.  No section
    filtering is applied.  This is the "naive" baseline — useful for
    showing how many matches are inflated by benefit/company sections.

``target_sections_only``
    Uses ``split_into_sections()`` from sections.py to parse the ad
    into labelled sections (requirements, responsibilities, benefits,
    company_pitch, other).  Only sections whose label appears in
    ``detection.target_section_labels`` (config) are searched.
    Token keywords require (a) presence in the lemmatized token set
    AND (b) at least one occurrence in the raw target-section text —
    this acts as a conservative position filter.  Phrase patterns are
    searched in target-section text only.
    Exclusion phrases always operate on the full text regardless of
    mode, to catch globally disqualifying context.

Both modes return the same dict structure:
    {"per_job": list[dict], "aggregate": dict}

The comparison between modes quantifies how much benefit/company-pitch
section noise inflates raw prevalence figures — a key methodological
point for the thesis.
"""

import logging
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from modules.tfidf.sections import split_into_sections

logger = logging.getLogger("[tfidf.analyzer]")


# ---------------------------------------------------------------------------
# TF-IDF matrix construction
# ---------------------------------------------------------------------------


def build_tfidf_matrix(
    documents: list[str], config: dict
) -> tuple[np.ndarray, list[str]]:
    """Fit a TfidfVectorizer on the tokenized documents.

    Args:
        documents: List of space-separated token strings (one per job).
        config: Parsed tfidf.yaml.

    Returns:
        (tfidf_matrix, feature_names) — the sparse matrix converted to dense
        and the corresponding vocabulary list.
    """
    tfidf_cfg = config.get("tfidf", {})

    max_features = tfidf_cfg.get("max_features", 0) or None
    min_df = tfidf_cfg.get("min_df", 2)
    max_df = tfidf_cfg.get("max_df", 0.90)
    ngram_min = tfidf_cfg.get("ngram_min", 1)
    ngram_max = tfidf_cfg.get("ngram_max", 1)

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=min_df,
        max_df=max_df,
        ngram_range=(ngram_min, ngram_max),
        token_pattern=r"(?u)\S+",
    )

    tfidf_matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out().tolist()

    logger.info(
        "TF-IDF matrix: %d documents x %d features (min_df=%s, max_df=%s, ngrams=(%d,%d))",
        tfidf_matrix.shape[0],
        tfidf_matrix.shape[1],
        min_df,
        max_df,
        ngram_min,
        ngram_max,
    )

    return tfidf_matrix, feature_names


# ---------------------------------------------------------------------------
# Top-term extraction and classification
# ---------------------------------------------------------------------------


def extract_top_terms(
    tfidf_matrix: np.ndarray,
    feature_names: list[str],
    config: dict,
) -> list[dict]:
    """Rank terms by mean TF-IDF score and return the top-N.

    Each entry contains: term, mean_tfidf, doc_frequency, category.
    """
    tfidf_cfg = config.get("tfidf", {})
    top_n = tfidf_cfg.get("top_n", 30)

    dense = tfidf_matrix.toarray()
    mean_scores = dense.mean(axis=0)
    doc_counts = (dense > 0).sum(axis=0)

    sorted_indices = mean_scores.argsort()[::-1][:top_n]

    soft_set, hard_set = _build_classification_sets(config)

    results = []
    for idx in sorted_indices:
        term = feature_names[idx]
        category = _classify_term(term, soft_set, hard_set)
        results.append({
            "term": term,
            "mean_tfidf": round(float(mean_scores[idx]), 6),
            "doc_frequency": int(doc_counts[idx]),
            "category": category,
        })

    soft_count = sum(1 for r in results if r["category"] == "soft")
    hard_count = sum(1 for r in results if r["category"] == "hard")
    noise_count = sum(1 for r in results if r["category"] == "noise")

    logger.info(
        "Top %d terms extracted — soft: %d, hard: %d, noise: %d",
        len(results),
        soft_count,
        hard_count,
        noise_count,
    )

    return results


def _build_classification_sets(config: dict) -> tuple[set[str], set[str]]:
    """Build soft/hard skill keyword sets.

    Soft skills are auto-generated from all competency token_keywords,
    supplemented by the manual fallback list in classification.soft_skills.
    Hard skills come solely from classification.hard_skills (manual list).
    If a keyword appears in both, hard_skills takes priority.
    """
    cls_cfg = config.get("classification", {})
    comp_defs = config.get("competencies", {})

    hard_set = {w.lower() for w in cls_cfg.get("hard_skills", [])}

    soft_set: set[str] = set()
    for comp_def in comp_defs.values():
        for kw in comp_def.get("token_keywords", []):
            kw_lower = kw.lower()
            if kw_lower not in hard_set:
                soft_set.add(kw_lower)

    for w in cls_cfg.get("soft_skills", []):
        w_lower = w.lower()
        if w_lower not in hard_set:
            soft_set.add(w_lower)

    return soft_set, hard_set


def _classify_term(term: str, soft_set: set[str], hard_set: set[str]) -> str:
    """Classify a single term (unigram or bigram) as 'soft', 'hard', or 'noise'."""
    lower = term.lower()
    if lower in soft_set:
        return "soft"
    if lower in hard_set:
        return "hard"
    parts = lower.split()
    if len(parts) > 1:
        has_hard = any(p in hard_set for p in parts)
        has_soft = any(p in soft_set for p in parts)
        if has_hard:
            return "hard"
        if has_soft:
            return "soft"
    return "noise"


# ---------------------------------------------------------------------------
# Subgroup TF-IDF analysis
# ---------------------------------------------------------------------------


def build_subgroup_tfidf(rows: list[dict], config: dict) -> dict:
    """Split rows by a location-like field and build separate TF-IDF per subgroup.

    Returns a dict keyed by subgroup name, each containing label, doc_count,
    and top_terms list. Returns empty dict if subgroups are disabled.
    """
    subgroup_cfg = config.get("subgroups", {})
    if not subgroup_cfg.get("enabled", False):
        return {}

    field = subgroup_cfg.get("field", "location")
    groups = subgroup_cfg.get("groups", {})
    token_field = config.get("input", {}).get("token_field", "description_tokens")

    subgroup_rows: dict[str, list[dict]] = {key: [] for key in groups}
    default_key = None
    match_keys: dict[str, str] = {}

    for key, grp in groups.items():
        match_val = grp.get("match", "")
        if match_val == "__default__":
            default_key = key
        else:
            match_keys[key] = match_val

    for row in rows:
        loc = row.get(field, "")
        assigned = False
        for key, match_val in match_keys.items():
            if match_val.lower() in loc.lower():
                subgroup_rows[key].append(row)
                assigned = True
                break
        if not assigned and default_key:
            subgroup_rows[default_key].append(row)

    results: dict = {}
    for key, sub_rows in subgroup_rows.items():
        documents = [
            r.get(token_field, "") for r in sub_rows if r.get(token_field, "").strip()
        ]
        if not documents:
            logger.warning("Subgroup '%s' has no documents — skipping", key)
            continue
        matrix, features = build_tfidf_matrix(documents, config)
        top_terms = extract_top_terms(matrix, features, config)
        results[key] = {
            "label": groups[key].get("label", key),
            "doc_count": len(sub_rows),
            "top_terms": top_terms,
        }

    logger.info(
        "Subgroup TF-IDF complete: %s",
        {v["label"]: v["doc_count"] for v in results.values()},
    )

    return results


# ---------------------------------------------------------------------------
# Dual-mode competency detection
# ---------------------------------------------------------------------------


def detect_competencies_dual_mode(rows: list[dict], config: dict) -> dict:
    """Run competency detection in both all_text and target_sections_only modes.

    Both modes share a single pass over rows for efficiency — sections are
    parsed once per job rather than twice.

    Args:
        rows:   Full job rows (need both token_field and text_field).
        config: Parsed tfidf.yaml with competencies, detection, sections.

    Returns:
        {
            "all_text":              {"per_job": [...], "aggregate": {...}},
            "target_sections_only":  {"per_job": [...], "aggregate": {...}},
        }
    """
    comp_defs = config.get("competencies", {})
    token_field = config.get("input", {}).get("token_field", "description_tokens")
    text_field = config.get("input", {}).get("text_field", "description_text")
    target_labels: set[str] = set(
        config.get("detection", {}).get(
            "target_section_labels", ["requirements", "responsibilities", "other"]
        )
    )

    if not comp_defs:
        logger.warning("No competencies defined in config — skipping detection")
        empty: dict = {"per_job": [], "aggregate": {}}
        return {"all_text": empty, "target_sections_only": empty}

    # Initialise per-mode aggregate accumulators
    modes = ("all_text", "target_sections_only")
    aggregate: dict[str, dict] = {
        mode: {ck: {"detected_count": 0, "total_indicators": 0} for ck in comp_defs}
        for mode in modes
    }
    per_job: dict[str, list] = {mode: [] for mode in modes}

    for row in rows:
        token_set = set(row.get(token_field, "").split())
        full_text = row.get(text_field, "")
        text_lower = full_text.lower()

        # Parse sections once per job — used only by target_sections_only mode
        sections = split_into_sections(full_text, config)
        target_text_lower = _build_target_text(sections, target_labels)

        job_profiles: dict[str, dict] = {
            mode: {
                "id": row.get("id", ""),
                "title": row.get("title", ""),
                "competencies": {},
            }
            for mode in modes
        }

        for ck, comp_def in comp_defs.items():
            all_matched = _match_all_text(comp_def, token_set, text_lower)
            sec_matched = _match_target_sections(
                comp_def, token_set, target_text_lower, text_lower
            )

            for mode, matched in (("all_text", all_matched), ("target_sections_only", sec_matched)):
                min_req = comp_def.get("min_indicators", 1)
                detected = len(matched) >= min_req
                job_profiles[mode]["competencies"][ck] = {
                    "detected": detected,
                    "indicator_count": len(matched),
                    "indicators": matched,
                }
                if detected:
                    aggregate[mode][ck]["detected_count"] += 1
                aggregate[mode][ck]["total_indicators"] += len(matched)

        for mode in modes:
            per_job[mode].append(job_profiles[mode])

    # Finalise aggregate stats (add label, group, prevalence_pct)
    total_jobs = len(rows)
    for mode in modes:
        for ck, comp_def in comp_defs.items():
            agg = aggregate[mode][ck]
            agg["label"] = comp_def.get("label", ck)
            agg["group"] = comp_def.get("group", "")
            agg["prevalence_pct"] = (
                round(agg["detected_count"] / total_jobs * 100, 1)
                if total_jobs else 0
            )

    for mode in modes:
        logger.info(
            "Competency detection [%s] for %d jobs: %s",
            mode,
            total_jobs,
            {v["label"]: v["detected_count"] for v in aggregate[mode].values()},
        )

    return {
        mode: {"per_job": per_job[mode], "aggregate": aggregate[mode]}
        for mode in modes
    }


def detect_competencies(rows: list[dict], config: dict) -> dict:
    """Run competency detection using the configured primary mode.

    Backward-compatible wrapper around detect_competencies_dual_mode.
    Returns the single-mode result dict ``{"per_job": [...], "aggregate": {...}}``
    for whichever mode is set as ``detection.primary_mode`` in the config
    (default: ``target_sections_only``).
    """
    primary = config.get("detection", {}).get("primary_mode", "target_sections_only")
    dual = detect_competencies_dual_mode(rows, config)
    return dual.get(primary, dual["target_sections_only"])


# ---------------------------------------------------------------------------
# Internal helpers — section-aware text extraction
# ---------------------------------------------------------------------------


def _build_target_text(sections: list[dict], target_labels: set[str]) -> str:
    """Concatenate text from sections whose label is in target_labels.

    When split_into_sections finds no headers it returns a single 'other'
    section containing the full text.  Since 'other' is in target_labels by
    default, this means unsectioned ads are searched in full — the function
    degrades gracefully without a separate fallback branch.
    """
    parts = [s["text"] for s in sections if s["label"] in target_labels]
    return "\n".join(parts).lower() if parts else ""


# ---------------------------------------------------------------------------
# Internal helpers — matching strategies per mode
# ---------------------------------------------------------------------------


def _match_all_text(
    comp_def: dict,
    token_set: set[str],
    text_lower: str,
) -> list[str]:
    """Match a competency against the full document with no section filtering.

    Token keywords are checked against the lemmatized token set (exact match
    after lower-casing).  Phrase patterns are substring-searched in the full
    lowercased description text.  This is the baseline "all_text" mode.

    Exclusion phrases are applied against the full text.

    Returns:
        List of fired indicator strings, e.g. ["token:komunikace",
        "phrase:komunikační dovednosti"].
    """
    matched: list[str] = []

    for keyword in comp_def.get("token_keywords", []):
        if keyword.lower() in token_set:
            matched.append(f"token:{keyword}")

    for phrase in comp_def.get("phrase_patterns", []):
        if phrase.lower() in text_lower:
            matched.append(f"phrase:{phrase}")

    matched = _apply_exclusions(matched, comp_def, text_lower)
    return matched


def _match_target_sections(
    comp_def: dict,
    token_set: set[str],
    target_text_lower: str,
    full_text_lower: str,
) -> list[str]:
    """Match a competency against target-section text only.

    Token keywords require TWO conditions to fire:
      1. The lemmatized keyword is present in the full-document token set
         (ensures lemmatisation handles morphological variation).
      2. The keyword appears as a word-boundary substring in the raw
         target-section text (position filter — excludes benefit/pitch
         section occurrences).

    Phrase patterns are substring-searched in target-section text only.
    Exclusion phrases still check the full text (global disqualifiers).

    Design note: because lemmatized tokens and raw surface forms differ
    (e.g. token "komunikace" vs. raw "komunikaci"), condition 2 is
    intentionally conservative and may miss some inflected occurrences.
    This trade-off is documented as part of the section-aware methodology.

    Returns:
        List of fired indicator strings.
    """
    matched: list[str] = []

    for keyword in comp_def.get("token_keywords", []):
        kw = keyword.lower()
        # Condition 1: lemmatized token present in full document
        if kw not in token_set:
            continue
        # Condition 2: keyword surface form appears in target section text
        if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", target_text_lower):
            matched.append(f"token:{keyword}")

    for phrase in comp_def.get("phrase_patterns", []):
        if phrase.lower() in target_text_lower:
            matched.append(f"phrase:{phrase}")

    matched = _apply_exclusions(matched, comp_def, full_text_lower)
    return matched


def _apply_exclusions(
    matched: list[str],
    comp_def: dict,
    full_text_lower: str,
) -> list[str]:
    """Remove token indicators that are invalidated by exclusion phrases.

    Exclusion phrases operate on the FULL text regardless of detection mode —
    they represent globally disqualifying contexts (e.g. "vedení účetnictví"
    for the vedení_lidi competency).

    Only token-level indicators are removed; phrase indicators survive
    exclusion checks (phrase matches already carry stronger signal).
    """
    exclusion_phrases = [p.lower() for p in comp_def.get("exclusion_phrases", [])]
    if not exclusion_phrases or not matched:
        return matched

    for exc in exclusion_phrases:
        if exc in full_text_lower:
            matched = [
                m for m in matched
                if not (m.startswith("token:") and m.split(":", 1)[1].lower() in exc)
            ]
    return matched
