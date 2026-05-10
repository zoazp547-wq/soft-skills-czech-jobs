"""Build Příloha G: corpus segmentation table.

Reads the (private) clean JSON, classifies each ad into role category and
location bucket using the title-keyword rules described in section 3.4.1,
and writes a non-confidential CSV with one row per ad:

    id ; title ; role_category ; location_bucket ; char_length ; token_count

This output contains NO ad descriptions and NO employer names — only the
publicly factual fields needed to demonstrate corpus segmentation. The
employer name is intentionally dropped; the ad title (role label) is kept
because it is the unit on which the segmentation is performed and the
opponent must be able to verify the rule.

Usage:
    python scripts/build_priloha_g.py \
        --clean output/jobs_cz_administrativa_clean.json \
        --nlp   output/jobs_cz_administrativa_nlp.json \
        --out   priloha_g_segmentace_korpusu.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Role keyword rules — must match section 3.4.1 of the thesis
# ---------------------------------------------------------------------------

UCETNI_KEYWORDS = {
    "účetní", "ucetni", "účetnictví", "ucetnictvi",
    "mzdový", "mzdovy", "mzdová", "mzdova",
    "daňový", "danovy", "daňová", "danova",
    "bookkeeper", "accountant", "accounting", "controller",
}

ASISTENT_KEYWORDS = {
    "asistent", "asistentka",
    "sekretář", "sekretar", "sekretářka", "sekretarka",
    "office", "recepční", "recepcni",
    "administrátor", "administrator",
    "koordinátor", "koordinator",
    "referent", "referentka",
}

# Excluded asistent variants (also from 3.4.1)
ASISTENT_EXCLUSIONS = {
    "asistent prodeje", "obchodní asistent", "obchodni asistent",
    "zdravotní", "zdravotni", "laboratorní", "laboratorni",
    "projektový asistent", "projektovy asistent",
    "pedagogický", "pedagogicky",
    "asistent v gastronomii", "gastronomi",
}

# Manager exclusions for účetní (kap. 3.4.1)
UCETNI_EXCLUSIONS = {"manažer", "manazer", "manager"}


def classify_role(title: str) -> str:
    """Return 'ucetni', 'asistent', or 'ostatni'."""
    t = title.lower()

    # Účetní first (more specific)
    if any(kw in t for kw in UCETNI_KEYWORDS):
        if not any(ex in t for ex in UCETNI_EXCLUSIONS):
            return "ucetni"

    # Asistent
    if any(kw in t for kw in ASISTENT_KEYWORDS):
        if not any(ex in t for ex in ASISTENT_EXCLUSIONS):
            return "asistent"

    return "ostatni"


def classify_location(location: str) -> str:
    """Return 'Praha' or 'Regiony' (3.3.2 split)."""
    return "Praha" if "praha" in (location or "").lower() else "Regiony"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", required=True, type=Path,
                        help="Path to *_clean.json")
    parser.add_argument("--nlp", required=True, type=Path,
                        help="Path to *_nlp.json (for token counts)")
    parser.add_argument("--out", default=Path("priloha_g_segmentace_korpusu.csv"),
                        type=Path)
    args = parser.parse_args()

    clean = json.loads(args.clean.read_text(encoding="utf-8"))
    nlp = json.loads(args.nlp.read_text(encoding="utf-8"))
    nlp_by_id = {ad["id"]: ad for ad in nlp}

    rows = []
    counts = {"ucetni": 0, "asistent": 0, "ostatni": 0}
    loc_counts = {"Praha": 0, "Regiony": 0}

    for ad in clean:
        ad_id = ad["id"]
        title = ad.get("title", "")
        location = ad.get("location", "")
        desc = ad.get("description_text", "") or ""

        nlp_ad = nlp_by_id.get(ad_id, {})
        token_str = nlp_ad.get("description_tokens", "") or ""
        token_count = len(token_str.split()) if token_str else 0

        role = classify_role(title)
        loc_bucket = classify_location(location)

        counts[role] += 1
        loc_counts[loc_bucket] += 1

        rows.append({
            "id": ad_id,
            "title": title,
            "role_category": role,
            "location_bucket": loc_bucket,
            "char_length": len(desc),
            "token_count": token_count,
        })

    rows.sort(key=lambda r: (r["role_category"], r["location_bucket"], r["id"]))

    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    # Summary to stderr (not piped into CSV)
    print(f"Total ads: {len(rows)}", file=sys.stderr)
    print(f"By role: {counts}", file=sys.stderr)
    print(f"By location: {loc_counts}", file=sys.stderr)
    print(f"Written: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
