"""Section-aware parsing for job advertisement text.

Splits raw job ad text into labeled sections (requirements, responsibilities,
benefits, company_pitch, other) using configurable regex header patterns
loaded from tfidf.yaml.
"""

import logging
import re

logger = logging.getLogger("[tfidf.sections]")


def split_into_sections(text: str, config: dict) -> list[dict]:
    """Split job ad text into labeled sections.

    Detects section boundaries by matching configurable header patterns from
    config['sections']['header_patterns'].  Each returned section dict contains:

        label  — logical section name ('requirements', 'responsibilities',
                  'benefits', 'company_pitch', or 'other')
        header — matched header text, stripped of surrounding whitespace
        text   — section body (everything after the header line until the
                  next detected header)
        start  — char offset of the section start (including header) in the
                  original document
        end    — char offset of the section end in the original document

    If no headers are detected the function returns a single 'other' section
    that spans the entire text, so callers always receive at least one entry.

    Args:
        text:   Raw (cleaned) job ad text.
        config: Parsed tfidf.yaml, expected to contain sections.header_patterns.

    Returns:
        Non-empty list of section dicts, sorted by document position.
    """
    if not text:
        return [_make_section("other", "", "", 0, 0)]

    patterns_by_label: dict[str, list[str]] = (
        config.get("sections", {}).get("header_patterns", {})
    )
    if not patterns_by_label:
        return [_make_section("other", "", text, 0, len(text))]

    # Compile each pattern and tag it with its section label
    compiled: list[tuple[re.Pattern, str]] = []
    for label, raw_list in patterns_by_label.items():
        for raw in raw_list:
            try:
                compiled.append(
                    (re.compile(raw, re.IGNORECASE | re.MULTILINE), label)
                )
            except re.error as exc:
                logger.warning(
                    "Skipping invalid section pattern for '%s': %s — %s",
                    label, raw, exc,
                )

    # Find all header matches across the full text
    raw_matches: list[tuple[int, int, str, str]] = []
    for pattern, label in compiled:
        for m in pattern.finditer(text):
            raw_matches.append((m.start(), m.end(), label, m.group().strip()))

    if not raw_matches:
        return [_make_section("other", "", text, 0, len(text))]

    # Sort by position; resolve overlapping header matches by keeping the first
    raw_matches.sort(key=lambda x: x[0])
    matches: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, label, header in raw_matches:
        if start >= last_end:
            matches.append((start, end, label, header))
            last_end = end

    sections: list[dict] = []

    # Text before the first header becomes an 'other' section
    if matches[0][0] > 0:
        sections.append(
            _make_section("other", "", text[: matches[0][0]], 0, matches[0][0])
        )

    # Build one section per detected header
    for i, (start, header_end, label, header) in enumerate(matches):
        body_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        sections.append(
            _make_section(label, header, text[header_end:body_end], start, body_end)
        )

    logger.debug("Sections detected: %s", [s["label"] for s in sections])
    return sections


def _make_section(
    label: str, header: str, text: str, start: int, end: int
) -> dict:
    """Return a section dict with a consistent structure."""
    return {
        "label": label,
        "header": header,
        "text": text,
        "start": start,
        "end": end,
    }
