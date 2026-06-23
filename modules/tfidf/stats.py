"""Statistical significance testing for competency subgroup comparisons.

Implements a two-proportion z-test without external dependencies —
the normal CDF is computed via Python's built-in math.erfc so that
scipy is not required.

Typical usage from runner.py::

    from modules.tfidf.stats import compute_subgroup_significance

    sig = compute_subgroup_significance(rows, primary_mode_results, config)
    _write_json(sig, subgroup_significance_path)
"""

import logging
import math

logger = logging.getLogger("[tfidf.stats]")


# ---------------------------------------------------------------------------
# Low-level statistics
# ---------------------------------------------------------------------------


def two_proportion_ztest(
    count_a: int,
    n_a: int,
    count_b: int,
    n_b: int,
) -> tuple[float, float]:
    """Two-sample z-test for equality of two proportions.

    Uses the pooled proportion as the variance estimator under H₀:
    p_a = p_b.  The test is two-tailed.

    The p-value is computed from the complementary error function
    (math.erfc) so that no external libraries are needed:
        p = erfc(|z| / sqrt(2))   ≡   2 * (1 - Phi(|z|))

    Args:
        count_a: Number of detections (successes) in group A.
        n_a:     Total jobs in group A.
        count_b: Number of detections in group B.
        n_b:     Total jobs in group B.

    Returns:
        (z_statistic, p_value_two_tailed).
        Returns (0.0, 1.0) when the test cannot be computed
        (zero denominator or fully uniform proportions).
    """
    if n_a == 0 or n_b == 0:
        return 0.0, 1.0

    p_pool = (count_a + count_b) / (n_a + n_b)
    if p_pool in (0.0, 1.0):
        return 0.0, 1.0

    se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_a + 1.0 / n_b))
    if se == 0.0:
        return 0.0, 1.0

    z = (count_a / n_a - count_b / n_b) / se
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return round(z, 4), round(p_value, 4)


# ---------------------------------------------------------------------------
# Subgroup significance report
# ---------------------------------------------------------------------------


def compute_subgroup_significance(
    rows: list[dict],
    mode_results: dict,
    config: dict,
) -> dict:
    """Compare competency prevalence between two location-based subgroups.

    Runs a two-proportion z-test for every detected competency and attaches
    a plain-language interpretation label suitable for direct use in a
    thesis.

    Subgroup membership is determined by the same config-driven logic used
    in build_subgroup_tfidf (match_val.lower() in location.lower(); anything
    unmatched falls into the __default__ group).

    Args:
        rows:         Original job rows (must contain the subgroup location
                      field, typically "location").
        mode_results: Per-job and aggregate results from a single detection
                      mode — expects keys "per_job" and "aggregate".
        config:       Parsed tfidf.yaml.  Uses ``subgroups``,
                      ``competencies``, and ``detection.significance_alpha``.

    Returns:
        Dict with ``metadata``, ``summary``, and ``competencies`` keys.
        Returns an empty dict if subgroups are disabled in config.
    """
    subgroup_cfg = config.get("subgroups", {})
    if not subgroup_cfg.get("enabled", False):
        logger.info("Subgroup significance skipped — subgroups disabled in config")
        return {}

    field = subgroup_cfg.get("field", "location")
    groups: dict = subgroup_cfg.get("groups", {})
    if len(groups) < 2:
        logger.warning("Subgroup significance requires ≥2 groups — skipping")
        return {}

    alpha = config.get("detection", {}).get("significance_alpha", 0.05)

    # ------------------------------------------------------------------ #
    # Separate explicit-match group from the default (catch-all) group    #
    # ------------------------------------------------------------------ #
    match_keys: dict[str, str] = {}
    default_key: str | None = None
    for key, grp in groups.items():
        mv = grp.get("match", "")
        if mv == "__default__":
            default_key = key
        else:
            match_keys[key] = mv

    def _assign_group(location: str) -> str | None:
        for key, mv in match_keys.items():
            if mv.lower() in location.lower():
                return key
        return default_key

    # Map job id → subgroup key
    id_to_group: dict[str, str] = {}
    for row in rows:
        gk = _assign_group(row.get(field, ""))
        if gk:
            id_to_group[str(row.get("id", ""))] = gk

    # Subgroup sizes
    total_by_group: dict[str, int] = {k: 0 for k in groups}
    for gk in id_to_group.values():
        total_by_group[gk] += 1

    # Build fast per-job lookup: job_id → competency detections
    per_job: list[dict] = mode_results.get("per_job", [])
    job_comps: dict[str, dict] = {
        str(p.get("id", "")): p.get("competencies", {})
        for p in per_job
    }

    # Count detections per competency per subgroup
    all_comp_keys = set(mode_results.get("aggregate", {}).keys())
    comp_counts: dict[str, dict[str, int]] = {
        ck: {k: 0 for k in groups} for ck in all_comp_keys
    }
    for job_id, gk in id_to_group.items():
        comps = job_comps.get(job_id, {})
        for ck, cd in comps.items():
            if ck in comp_counts and cd.get("detected"):
                comp_counts[ck][gk] += 1

    # Identify the two groups for the z-test
    group1_key = next(iter(match_keys)) if match_keys else list(groups)[0]
    group2_key = default_key if default_key else list(groups)[1]

    n1 = int(total_by_group.get(group1_key, 0))
    n2 = int(total_by_group.get(group2_key, 0))
    g1_label = groups[group1_key]["label"]
    g2_label = groups[group2_key]["label"]

    comp_defs: dict = config.get("competencies", {})
    comp_results: dict = {}

    for ck in sorted(all_comp_keys):
        counts = comp_counts.get(ck, {})
        k1 = int(counts.get(group1_key, 0))
        k2 = int(counts.get(group2_key, 0))
        p1 = k1 / n1 if n1 else 0.0
        p2 = k2 / n2 if n2 else 0.0

        z_stat, p_val = two_proportion_ztest(k1, n1, k2, n2)

        if p_val < alpha:
            interpretation = "significant_difference"
        elif p_val == 1.0 and z_stat == 0.0:
            interpretation = "exploratory_only"
        else:
            interpretation = "no_statistically_significant_difference"

        comp_def = comp_defs.get(ck, {})
        comp_results[ck] = {
            "label": comp_def.get("label", ck),
            "group": comp_def.get("group", ""),
            g1_label: {
                "count": k1,
                "total": n1,
                "prevalence_pct": round(p1 * 100, 1),
            },
            g2_label: {
                "count": k2,
                "total": n2,
                "prevalence_pct": round(p2 * 100, 1),
            },
            "delta_pct": round((p1 - p2) * 100, 1),
            "z_statistic": float(z_stat),
            "p_value": float(p_val),
            "test": "two_proportion_z_test",
            "interpretation": interpretation,
        }

    # Sort by absolute delta for easy thesis reading
    sig_keys = sorted(
        [k for k, v in comp_results.items() if v["interpretation"] == "significant_difference"],
        key=lambda k: -abs(comp_results[k]["delta_pct"]),
    )
    non_sig_keys = [
        k for k, v in comp_results.items()
        if v["interpretation"] == "no_statistically_significant_difference"
    ]
    expl_keys = [
        k for k, v in comp_results.items()
        if v["interpretation"] == "exploratory_only"
    ]

    n_total = len(comp_results)
    n_sig = len(sig_keys)

    logger.info(
        "Subgroup significance (%s n=%d vs %s n=%d): "
        "%d/%d competencies significant at alpha=%.2f",
        g1_label, n1, g2_label, n2, n_sig, n_total, alpha,
    )

    return {
        "metadata": {
            "subgroup_a": {"key": group1_key, "label": g1_label, "n": n1},
            "subgroup_b": {"key": group2_key, "label": g2_label, "n": n2},
            "test": "two_proportion_z_test",
            "significance_threshold": alpha,
            "detection_mode": config.get("detection", {}).get(
                "primary_mode", "target_sections_only"
            ),
        },
        "summary": {
            "competencies_tested": n_total,
            "significant_differences": n_sig,
            "not_significant": len(non_sig_keys),
            "exploratory_only": len(expl_keys),
            "significant_competency_keys": sig_keys,
            "significant_competency_labels": [
                comp_defs.get(k, {}).get("label", k) for k in sig_keys
            ],
            "thesis_note": (
                f"Two-proportion z-test comparing {g1_label} (n={n1}) vs "
                f"{g2_label} (n={n2}) at α={alpha}. "
                f"{n_sig}/{n_total} competencies show a statistically "
                f"significant regional difference in prevalence."
            ),
        },
        "competencies": comp_results,
    }
