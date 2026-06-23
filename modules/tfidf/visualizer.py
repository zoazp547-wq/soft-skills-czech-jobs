"""Visualization helpers for TF-IDF analysis results.

Generates horizontal bar charts for:
  - Top-N terms by mean TF-IDF score, coloured by skill category.
  - Competency prevalence across job listings, coloured by competency group.
  - Interactive HTML dashboard with clickable competency bars.
"""

import json
import logging
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger("[tfidf.visualizer]")

_CATEGORY_LABELS = {"soft": "Soft skill", "hard": "Hard skill", "noise": "Other"}


def plot_top_terms(top_terms: list[dict], output_path: str, config: dict) -> None:
    """Save a horizontal bar chart of top terms by mean TF-IDF score.

    Bars are coloured by category (soft / hard / noise).
    Figure height scales with the number of terms for readability.
    """
    viz_cfg = config.get("visualization", {})
    fig_w = viz_cfg.get("figure_width", 14)
    fig_h = max(viz_cfg.get("figure_height", 8), len(top_terms) * 0.35)
    color_map = {
        "soft": viz_cfg.get("color_soft", "#4CAF50"),
        "hard": viz_cfg.get("color_hard", "#2196F3"),
        "noise": viz_cfg.get("color_noise", "#9E9E9E"),
    }
    title = viz_cfg.get("title", "Top Terms by Mean TF-IDF Score")
    dpi = viz_cfg.get("dpi", 150)

    terms_reversed = list(reversed(top_terms))
    labels = [t["term"] for t in terms_reversed]
    scores = [t["mean_tfidf"] for t in terms_reversed]
    colors = [color_map.get(t["category"], "#9E9E9E") for t in terms_reversed]

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    bars = ax.barh(labels, scores, color=colors, edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Mean TF-IDF Score", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=10)

    for bar_item, score in zip(bars, scores):
        ax.text(
            bar_item.get_width() + max(scores) * 0.01,
            bar_item.get_y() + bar_item.get_height() / 2,
            f"{score:.4f}",
            va="center",
            fontsize=8,
            color="#333333",
        )

    # Build legend from categories actually present
    present_categories = sorted(set(t["category"] for t in top_terms))
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=color_map[cat])
        for cat in present_categories
    ]
    legend_labels = [_CATEGORY_LABELS.get(cat, cat) for cat in present_categories]
    ax.legend(legend_handles, legend_labels, loc="lower right", fontsize=10)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    logger.info("Chart saved: %s (%d x %d px @ %d dpi)", output_path, fig_w, fig_h, dpi)


_GROUP_COLOR_KEYS = {
    "Osobnostní": "color_osobnostni",
    "Interpersonální": "color_interpersonalni",
    "Kognitivní": "color_kognitivni",
    "Výkonové": "color_vykonove",
}

_GROUP_DEFAULTS = {
    "Osobnostní": "#FF9800",
    "Interpersonální": "#4CAF50",
    "Kognitivní": "#2196F3",
    "Výkonové": "#9C27B0",
}


def plot_competency_prevalence(
    aggregate: dict, output_path: str, config: dict
) -> None:
    """Save a horizontal bar chart of competency prevalence (% of jobs).

    Bars are coloured by competency group and annotated with
    absolute count and percentage.
    """
    viz_cfg = config.get("visualization", {})
    fig_w = viz_cfg.get("figure_width", 14)
    fig_h = viz_cfg.get("figure_height", 8)
    title = viz_cfg.get("competency_title", "Competency Prevalence in Job Listings")
    dpi = viz_cfg.get("dpi", 150)

    group_colors = {}
    for group, key in _GROUP_COLOR_KEYS.items():
        group_colors[group] = viz_cfg.get(key, _GROUP_DEFAULTS.get(group, "#9E9E9E"))

    sorted_comps = sorted(
        aggregate.items(),
        key=lambda item: item[1].get("prevalence_pct", 0),
    )

    labels = [v["label"] for _, v in sorted_comps]
    pcts = [v["prevalence_pct"] for _, v in sorted_comps]
    counts = [v["detected_count"] for _, v in sorted_comps]
    colors = [
        group_colors.get(v.get("group", ""), "#9E9E9E")
        for _, v in sorted_comps
    ]

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    bars = ax.barh(labels, pcts, color=colors, edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Prevalence (%)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(axis="y", labelsize=10)
    ax.tick_params(axis="x", labelsize=10)
    ax.set_xlim(0, 110)

    for bar_item, pct, count in zip(bars, pcts, counts):
        ax.text(
            bar_item.get_width() + 1.5,
            bar_item.get_y() + bar_item.get_height() / 2,
            f"{pct:.0f}% ({count})",
            va="center",
            fontsize=9,
            color="#333333",
        )

    present_groups = sorted(set(v.get("group", "") for _, v in sorted_comps))
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=group_colors.get(g, "#9E9E9E"))
        for g in present_groups
    ]
    ax.legend(legend_handles, present_groups, loc="lower right", fontsize=10)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    logger.info("Competency chart saved: %s", output_path)


def plot_subgroup_comparison(
    subgroup_results: dict, output_path: str, config: dict
) -> None:
    """Side-by-side horizontal bar charts of top terms for each subgroup.

    Creates one subplot column per subgroup, bars coloured by soft/hard/noise.
    """
    viz_cfg = config.get("visualization", {})
    dpi = viz_cfg.get("dpi", 150)
    color_map = {
        "soft": viz_cfg.get("color_soft", "#4CAF50"),
        "hard": viz_cfg.get("color_hard", "#2196F3"),
        "noise": viz_cfg.get("color_noise", "#9E9E9E"),
    }

    groups = list(subgroup_results.values())
    num_groups = len(groups)
    if num_groups == 0:
        logger.warning("No subgroup results to plot")
        return

    top_n_display = 25
    fig_w = 8 * num_groups
    fig_h = max(10, top_n_display * 0.38)

    fig, axes = plt.subplots(1, num_groups, figsize=(fig_w, fig_h), sharey=False)
    if num_groups == 1:
        axes = [axes]

    for ax, group_data in zip(axes, groups):
        terms = group_data["top_terms"][:top_n_display]
        terms_reversed = list(reversed(terms))
        labels = [t["term"] for t in terms_reversed]
        scores = [t["mean_tfidf"] for t in terms_reversed]
        colors = [color_map.get(t["category"], "#9E9E9E") for t in terms_reversed]

        ax.barh(labels, scores, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_title(
            f"{group_data['label']} ({group_data['doc_count']} docs)",
            fontsize=13,
            fontweight="bold",
            pad=10,
        )
        ax.set_xlabel("Mean TF-IDF", fontsize=10)
        ax.tick_params(axis="y", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    present_categories = sorted({
        t["category"]
        for g in groups for t in g["top_terms"][:top_n_display]
    })
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=color_map.get(cat, "#9E9E9E"))
        for cat in present_categories
    ]
    legend_labels = [_CATEGORY_LABELS.get(cat, cat) for cat in present_categories]
    fig.legend(legend_handles, legend_labels, loc="lower center", ncol=3, fontsize=10)

    fig.suptitle(
        "Subgroup Comparison — Top Terms by Mean TF-IDF",
        fontsize=15,
        fontweight="bold",
        y=1.01,
    )
    plt.tight_layout(rect=[0, 0.03, 1, 0.99])

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    logger.info("Subgroup comparison chart saved: %s", output_path)


_REGION_PREFIXES = [
    "Praha", "Brno", "Ostrava", "Plzeň", "Olomouc", "Liberec",
    "České Budějovice", "Hradec Králové", "Pardubice", "Zlín",
    "Karlovy Vary", "Jihlava", "Ústí nad Labem", "Opava",
]
_MIN_REGION_JOBS = 10


def _assign_region(location: str) -> str:
    """Map a raw location string to a major city/region."""
    loc = location.strip()
    for prefix in _REGION_PREFIXES:
        if loc.startswith(prefix) or loc == f"Hlavní město {prefix}":
            return prefix
    return loc


def generate_interactive_html(
    comp_results: dict,
    rows: list[dict],
    output_path: str,
    config: dict,
) -> None:
    """Generate a self-contained interactive HTML dashboard.

    The dashboard has a clickable bar chart of competency prevalence with
    a location dropdown filter. Clicking a bar reveals the list of matching
    jobs with their indicators and description text.
    """
    viz_cfg = config.get("visualization", {})
    group_colors = {}
    for group, key in _GROUP_COLOR_KEYS.items():
        group_colors[group] = viz_cfg.get(key, _GROUP_DEFAULTS.get(group, "#9E9E9E"))

    aggregate = comp_results["aggregate"]
    per_job = comp_results["per_job"]
    text_field = config.get("input", {}).get("text_field", "description_text")
    token_field = config.get("input", {}).get("token_field", "description_tokens")

    row_lookup = {}
    region_counts: dict[str, int] = {}
    for row in rows:
        region = _assign_region(row.get("location", ""))
        row_lookup[row.get("id", "")] = {
            "title": row.get("title", ""),
            "provider": row.get("provider", ""),
            "location": row.get("location", ""),
            "region": region,
            "url": row.get("url", ""),
            "description": row.get(text_field, ""),
            "tokens": row.get(token_field, ""),
        }
        region_counts[region] = region_counts.get(region, 0) + 1

    significant_regions = {
        r for r, c in region_counts.items() if c >= _MIN_REGION_JOBS
    }
    for job_id in row_lookup:
        if row_lookup[job_id]["region"] not in significant_regions:
            row_lookup[job_id]["region"] = "Ostatní"
    region_counts_final: dict[str, int] = {}
    for data in row_lookup.values():
        r = data["region"]
        region_counts_final[r] = region_counts_final.get(r, 0) + 1

    sorted_regions = sorted(
        region_counts_final.items(), key=lambda x: -x[1]
    )
    region_list = [{"name": r, "count": c} for r, c in sorted_regions]

    sorted_comps = sorted(
        aggregate.items(),
        key=lambda item: -item[1].get("prevalence_pct", 0),
    )

    chart_data = {
        "labels": [v["label"] for _, v in sorted_comps],
        "keys": [k for k, _ in sorted_comps],
        "values": [v["prevalence_pct"] for _, v in sorted_comps],
        "counts": [v["detected_count"] for _, v in sorted_comps],
        "colors": [group_colors.get(v.get("group", ""), "#9E9E9E") for _, v in sorted_comps],
        "groups": [v.get("group", "") for _, v in sorted_comps],
    }

    all_jobs = []
    for job_profile in per_job:
        job_id = job_profile["id"]
        row_data = row_lookup.get(job_id, {})
        detected_comps = {}
        for comp_key in aggregate:
            comp_data = job_profile["competencies"].get(comp_key, {})
            if comp_data.get("detected"):
                detected_comps[comp_key] = comp_data.get("indicators", [])
        all_jobs.append({
            "id": job_id,
            "title": row_data.get("title", job_profile.get("title", "")),
            "provider": row_data.get("provider", ""),
            "location": row_data.get("location", ""),
            "region": row_data.get("region", "Ostatní"),
            "url": row_data.get("url", ""),
            "comps": detected_comps,
            "description": row_data.get("description", "")[:800],
            "tokens_snippet": " ".join(row_data.get("tokens", "").split()[:50]),
        })

    html = _build_html(
        chart_data, all_jobs, aggregate, len(rows), region_list
    )

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    logger.info("Interactive dashboard saved: %s", output_path)


def _build_html(
    chart_data: dict,
    all_jobs: list[dict],
    aggregate: dict,
    total_jobs: int,
    region_list: list[dict],
) -> str:
    chart_json = json.dumps(chart_data, ensure_ascii=False)
    jobs_json = json.dumps(all_jobs, ensure_ascii=False)
    regions_json = json.dumps(region_list, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Competency Analysis Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    --bg: #f8f9fa;
    --card: #ffffff;
    --text: #212529;
    --muted: #6c757d;
    --border: #dee2e6;
    --accent: #0d6efd;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    padding: 2rem;
    text-align: center;
  }}
  .header h1 {{ font-size: 1.8rem; font-weight: 700; }}
  .header p {{ color: #adb5bd; margin-top: 0.5rem; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 1.5rem; }}
  .chart-section {{
    background: var(--card);
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }}
  .chart-section h2 {{ font-size: 1.2rem; margin-bottom: 0.5rem; color: var(--text); }}
  .chart-hint {{ font-size: 0.85rem; color: var(--muted); margin-bottom: 0.5rem; }}
  .location-filter {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 1rem;
    align-items: center;
  }}
  .location-filter > span {{ font-size: 0.9rem; font-weight: 600; margin-right: 0.3rem; }}
  .loc-chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.7rem;
    border: 1.5px solid var(--border);
    border-radius: 20px;
    font-size: 0.82rem;
    cursor: pointer;
    user-select: none;
    transition: all 0.15s;
    background: white;
  }}
  .loc-chip:hover {{ border-color: var(--accent); }}
  .loc-chip.active {{
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }}
  .loc-chip .loc-count {{
    font-size: 0.72rem;
    opacity: 0.7;
  }}
  .loc-actions {{
    display: inline-flex;
    gap: 0.3rem;
    margin-left: 0.5rem;
  }}
  .loc-actions button {{
    font-size: 0.78rem;
    padding: 0.2rem 0.5rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: white;
    cursor: pointer;
    color: var(--muted);
  }}
  .loc-actions button:hover {{ background: var(--bg); }}
  .location-badge {{
    font-size: 0.82rem;
    color: var(--muted);
    margin-top: 0.3rem;
  }}
  #chartContainer {{ position: relative; height: 520px; }}
  .detail-panel {{
    background: var(--card);
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    padding: 1.5rem;
    display: none;
  }}
  .detail-panel.active {{ display: block; }}
  .detail-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}
  .detail-header h2 {{ font-size: 1.2rem; }}
  .detail-count {{ color: var(--muted); font-size: 0.9rem; }}
  .close-btn {{
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.3rem 0.8rem;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--muted);
  }}
  .close-btn:hover {{ background: var(--bg); }}
  .search-box {{
    width: 100%;
    padding: 0.6rem 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }}
  .job-list {{ max-height: 70vh; overflow-y: auto; }}
  .job-card {{
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    transition: box-shadow 0.15s;
  }}
  .job-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .job-title {{
    font-weight: 600;
    font-size: 1rem;
    color: var(--accent);
    text-decoration: none;
  }}
  .job-title:hover {{ text-decoration: underline; }}
  .job-meta {{ font-size: 0.85rem; color: var(--muted); margin: 0.25rem 0; }}
  .indicators {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0.5rem 0;
  }}
  .indicator-tag {{
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 20px;
    font-weight: 500;
  }}
  .indicator-tag.token {{
    background: #e3f2fd;
    color: #1565c0;
    border: 1px solid #90caf9;
  }}
  .indicator-tag.phrase {{
    background: #f3e5f5;
    color: #7b1fa2;
    border: 1px solid #ce93d8;
  }}
  .desc-toggle {{
    font-size: 0.8rem;
    color: var(--accent);
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
    margin-top: 0.3rem;
  }}
  .desc-toggle:hover {{ text-decoration: underline; }}
  .desc-content {{
    display: none;
    margin-top: 0.5rem;
    padding: 0.75rem;
    background: #f8f9fa;
    border-radius: 6px;
    font-size: 0.85rem;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
    border-left: 3px solid var(--accent);
  }}
  .desc-content.open {{ display: block; }}
  .tokens-line {{
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 0.3rem;
    font-style: italic;
  }}
  .legend {{
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
    font-size: 0.85rem;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }}
  .legend-dot {{
    width: 12px;
    height: 12px;
    border-radius: 3px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Competency Analysis Dashboard</h1>
  <p><span id="headerCount">{total_jobs}</span> job listings analyzed &middot; 18 competencies detected</p>
</div>

<div class="container">
  <div class="chart-section">
    <h2>Competency Prevalence</h2>
    <div class="location-filter" id="locationFilter">
      <span>Locations:</span>
    </div>
    <div class="location-badge" id="locationBadge"></div>
    <p class="chart-hint">Click a bar to see matching job listings below. Chart auto-sorts by prevalence.</p>
    <div id="chartContainer">
      <canvas id="compChart"></canvas>
    </div>
    <div class="legend" id="legend"></div>
  </div>

  <div class="detail-panel" id="detailPanel">
    <div class="detail-header">
      <div>
        <h2 id="detailTitle">&mdash;</h2>
        <span class="detail-count" id="detailCount"></span>
      </div>
      <button class="close-btn" onclick="closePanel()">Close</button>
    </div>
    <input type="text" class="search-box" id="searchBox"
           placeholder="Filter by title, company, or indicator..."
           oninput="filterJobs()">
    <div class="job-list" id="jobList"></div>
  </div>
</div>

<script>
const BASE_CHART = {chart_json};
const ALL_JOBS   = {jobs_json};
const REGIONS    = {regions_json};
const COMP_KEYS  = BASE_CHART.keys;
const COMP_LABELS = BASE_CHART.labels;
const COMP_COLORS = BASE_CHART.colors;
const COMP_GROUPS = BASE_CHART.groups;
const TOTAL_JOBS = {total_jobs};

let selectedRegions = new Set(REGIONS.map(r => r.name));
let currentKey = null;
let currentSortOrder = [];
let currentFilteredJobs = [];

// Build location chip checkboxes
const filterEl = document.getElementById("locationFilter");
const actionsHtml = '<div class="loc-actions">' +
  '<button onclick="selectAll()">All</button>' +
  '<button onclick="selectNone()">None</button>' +
  '</div>';
REGIONS.forEach(r => {{
  const chip = document.createElement("span");
  chip.className = "loc-chip active";
  chip.dataset.region = r.name;
  chip.innerHTML = esc(r.name) + ' <span class="loc-count">(' + r.count + ')</span>';
  chip.onclick = () => toggleRegion(r.name, chip);
  filterEl.appendChild(chip);
}});
filterEl.insertAdjacentHTML("beforeend", actionsHtml);

function toggleRegion(name, chip) {{
  if (selectedRegions.has(name)) {{
    selectedRegions.delete(name);
    chip.classList.remove("active");
  }} else {{
    selectedRegions.add(name);
    chip.classList.add("active");
  }}
  onSelectionChange();
}}

function selectAll() {{
  selectedRegions = new Set(REGIONS.map(r => r.name));
  document.querySelectorAll(".loc-chip").forEach(c => c.classList.add("active"));
  onSelectionChange();
}}

function selectNone() {{
  selectedRegions.clear();
  document.querySelectorAll(".loc-chip").forEach(c => c.classList.remove("active"));
  onSelectionChange();
}}

function onSelectionChange() {{
  refreshChart();
  closePanel();
}}

// Build chart
const ctx = document.getElementById("compChart").getContext("2d");
const chart = new Chart(ctx, {{
  type: "bar",
  data: {{
    labels: [...COMP_LABELS],
    datasets: [{{
      data: [...BASE_CHART.values],
      backgroundColor: [...COMP_COLORS],
      borderWidth: 0,
      borderRadius: 4,
      barPercentage: 0.7,
    }}]
  }},
  options: {{
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    animation: {{ duration: 400 }},
    onClick: (e, elements) => {{
      if (elements.length > 0) {{
        const chartIdx = elements[0].index;
        const origIdx = currentSortOrder[chartIdx];
        showCompetency(origIdx);
      }}
    }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: (tooltipCtx) => {{
            const chartIdx = tooltipCtx.dataIndex;
            const origIdx = currentSortOrder[chartIdx];
            const val = tooltipCtx.dataset.data[chartIdx];
            const stats = computeStats();
            const count = stats.counts[origIdx];
            return val.toFixed(1) + "% (" + count + " jobs) — " + COMP_GROUPS[origIdx];
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        max: 100,
        title: {{ display: true, text: "Prevalence (%)", font: {{ size: 13 }} }},
        grid: {{ color: "#eee" }}
      }},
      y: {{
        ticks: {{ font: {{ size: 12 }} }},
        grid: {{ display: false }}
      }}
    }}
  }}
}});

// Build legend
const groups = [...new Set(COMP_GROUPS)];
const legendEl = document.getElementById("legend");
groups.forEach(g => {{
  const color = COMP_COLORS[COMP_GROUPS.indexOf(g)];
  legendEl.innerHTML += '<div class="legend-item"><div class="legend-dot" style="background:' + color + '"></div>' + g + '</div>';
}});

function getFilteredJobs() {{
  if (selectedRegions.size === REGIONS.length) return ALL_JOBS;
  return ALL_JOBS.filter(j => selectedRegions.has(j.region));
}}

function computeStats() {{
  const jobs = getFilteredJobs();
  const total = jobs.length;
  const counts = COMP_KEYS.map(key =>
    jobs.filter(j => j.comps && j.comps[key]).length
  );
  const pcts = counts.map(c => total > 0 ? Math.round(c / total * 1000) / 10 : 0);
  return {{ total, counts, pcts }};
}}

function refreshChart() {{
  const stats = computeStats();
  const indices = COMP_KEYS.map((_, i) => i);
  indices.sort((a, b) => stats.pcts[a] - stats.pcts[b]);
  currentSortOrder = indices;

  chart.data.labels = indices.map(i => COMP_LABELS[i]);
  chart.data.datasets[0].data = indices.map(i => stats.pcts[i]);
  chart.data.datasets[0].backgroundColor = indices.map(i => COMP_COLORS[i]);
  chart.update();

  document.getElementById("headerCount").textContent = stats.total;
  const badge = document.getElementById("locationBadge");
  if (selectedRegions.size === REGIONS.length) {{
    badge.textContent = "";
  }} else if (selectedRegions.size === 0) {{
    badge.textContent = "No locations selected";
  }} else {{
    const names = [...selectedRegions].join(", ");
    badge.textContent = stats.total + " jobs in: " + names;
  }}
}}

currentSortOrder = COMP_KEYS.map((_, i) => i);
refreshChart();

function showCompetency(origIdx) {{
  currentKey = COMP_KEYS[origIdx];
  const label = COMP_LABELS[origIdx];
  const jobs = getFilteredJobs().filter(j => j.comps && j.comps[currentKey]);
  currentFilteredJobs = jobs;
  const regionNote = selectedRegions.size < REGIONS.length
    ? " in " + [...selectedRegions].join(", ") : "";
  document.getElementById("detailTitle").textContent = label;
  document.getElementById("detailCount").textContent = jobs.length + " job listings detected" + regionNote;
  document.getElementById("searchBox").value = "";
  renderJobs(jobs);
  const panel = document.getElementById("detailPanel");
  panel.classList.add("active");
  panel.scrollIntoView({{ behavior: "smooth", block: "start" }});
}}

function closePanel() {{
  document.getElementById("detailPanel").classList.remove("active");
}}

function filterJobs() {{
  const q = document.getElementById("searchBox").value.toLowerCase();
  if (!q) {{ renderJobs(currentFilteredJobs); return; }}
  const filtered = currentFilteredJobs.filter(j =>
    j.title.toLowerCase().includes(q) ||
    j.provider.toLowerCase().includes(q) ||
    (j.comps[currentKey] || []).some(i => i.toLowerCase().includes(q)) ||
    j.description.toLowerCase().includes(q)
  );
  renderJobs(filtered);
}}

function renderJobs(jobs) {{
  const container = document.getElementById("jobList");
  if (jobs.length === 0) {{
    container.innerHTML = '<p style="color:#6c757d;padding:1rem;">No matching jobs found.</p>';
    return;
  }}
  container.innerHTML = jobs.map((j, i) => {{
    const indicators = j.comps[currentKey] || [];
    return '<div class="job-card">' +
      '<a class="job-title" href="' + esc(j.url) + '" target="_blank">' + esc(j.title) + '</a>' +
      '<div class="job-meta">' + esc(j.provider) + ' &middot; ' + esc(j.location) + ' &middot; ID: ' + j.id + '</div>' +
      '<div class="indicators">' +
        indicators.map(ind => {{
          const type = ind.startsWith("token:") ? "token" : "phrase";
          const lbl = ind.replace(/^(token|phrase):/, "");
          return '<span class="indicator-tag ' + type + '">' + (type === "token" ? "T" : "P") + ': ' + esc(lbl) + '</span>';
        }}).join("") +
      '</div>' +
      '<div class="tokens-line">Tokens: ' + esc(j.tokens_snippet) + '...</div>' +
      '<button class="desc-toggle" onclick="toggleDesc(' + i + ')">Show description</button>' +
      '<div class="desc-content" id="desc-' + i + '">' + esc(j.description) + '</div>' +
    '</div>';
  }}).join("");
}}

function toggleDesc(i) {{
  const el = document.getElementById("desc-" + i);
  el.classList.toggle("open");
  const btn = el.previousElementSibling;
  btn.textContent = el.classList.contains("open") ? "Hide description" : "Show description";
}}

function esc(s) {{
  if (!s) return "";
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}}
</script>
</body>
</html>"""
