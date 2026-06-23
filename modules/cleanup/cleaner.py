"""Data cleanup pipeline for scraped job listings.

Each public function represents one cleanup stage. They accept a list of
row dicts (from csv.DictReader) and the parsed cleanup.yaml config, then
return a filtered/transformed copy of the list.

The stages are designed to be called sequentially by runner.py.
"""

import html
import logging
import re

logger = logging.getLogger("[cleanup.cleaner]")

# ---------------------------------------------------------------------------
# Stage 1 — Filter rows missing critical fields
# ---------------------------------------------------------------------------


def filter_required_fields(rows: list[dict], config: dict) -> list[dict]:
    """Remove rows where any required field is empty or missing."""
    required = config.get("filtering", {}).get("required_fields", [])
    if not required:
        return rows

    before = len(rows)
    kept = []
    for row in rows:
        missing = [f for f in required if not row.get(f, "").strip()]
        if missing:
            logger.debug(
                "Dropping row id=%s — missing required fields: %s",
                row.get("id", "?"),
                missing,
            )
        else:
            kept.append(row)

    logger.info(
        "Required-fields filter: %d -> %d rows (%d removed)",
        before,
        len(kept),
        before - len(kept),
    )
    return kept


# ---------------------------------------------------------------------------
# Stage 2 — Filter short / empty descriptions
# ---------------------------------------------------------------------------


def filter_short_descriptions(rows: list[dict], config: dict) -> list[dict]:
    """Remove rows whose description_text is missing or shorter than the
    configured minimum length."""
    min_len = config.get("filtering", {}).get("min_description_length", 50)

    before = len(rows)
    kept = []
    for row in rows:
        desc = row.get("description_text", "") or ""
        if len(desc.strip()) < min_len:
            logger.debug(
                "Dropping row id=%s — description too short (%d < %d chars)",
                row.get("id", "?"),
                len(desc.strip()),
                min_len,
            )
        else:
            kept.append(row)

    logger.info(
        "Short-description filter (min %d chars): %d -> %d rows (%d removed)",
        min_len,
        before,
        len(kept),
        before - len(kept),
    )
    return kept


# ---------------------------------------------------------------------------
# Stage 3 — Deduplication
# ---------------------------------------------------------------------------


def deduplicate(rows: list[dict], config: dict) -> list[dict]:
    """Remove duplicate rows.

    First pass: exact match on primary_key (e.g. "id").
    Second pass: exact match on all secondary_keys together (e.g. title+provider).
    The first occurrence is always kept.
    """
    dedup_cfg = config.get("deduplication", {})
    primary_key = dedup_cfg.get("primary_key", "id")
    secondary_keys = dedup_cfg.get("secondary_keys", [])

    before = len(rows)

    seen_primary = set()
    after_primary = []
    for row in rows:
        val = row.get(primary_key, "").strip()
        if val and val in seen_primary:
            logger.debug("Dedup (primary=%s): dropping duplicate '%s'", primary_key, val)
            continue
        if val:
            seen_primary.add(val)
        after_primary.append(row)

    primary_removed = before - len(after_primary)

    seen_secondary = set()
    after_secondary = []
    for row in after_primary:
        composite = tuple(row.get(k, "").strip().lower() for k in secondary_keys)
        if all(composite) and composite in seen_secondary:
            logger.debug(
                "Dedup (secondary=%s): dropping duplicate %s",
                secondary_keys,
                composite,
            )
            continue
        if all(composite):
            seen_secondary.add(composite)
        after_secondary.append(row)

    secondary_removed = len(after_primary) - len(after_secondary)
    logger.info(
        "Deduplication: %d -> %d rows (primary: %d, secondary: %d removed)",
        before,
        len(after_secondary),
        primary_removed,
        secondary_removed,
    )
    return after_secondary


# ---------------------------------------------------------------------------
# Stage 4 — Text cleanup (description_text)
# ---------------------------------------------------------------------------

# Regex that matches boundaries where HTML block elements were stripped,
# producing runs of text that should be on separate lines.
# Looks for a lowercase/punctuation char immediately followed by an uppercase
# char — a sign that two sections were concatenated.
_SECTION_BOUNDARY = re.compile(
    r"([a-záčďéěíňóřšťúůýž.!?:;)\]])([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])"
)


def clean_description_text(rows: list[dict], config: dict) -> list[dict]:
    """Apply text-level fixes to the description_text field."""
    text_cfg = config.get("text_cleanup", {})
    fix_nbsp = text_cfg.get("fix_nbsp", True)
    collapse_ws = text_cfg.get("collapse_whitespace", True)
    decode_entities = text_cfg.get("decode_html_entities", True)
    add_separators = text_cfg.get("add_section_separators", True)

    for row in rows:
        desc = row.get("description_text")
        if not desc:
            continue

        if fix_nbsp:
            desc = desc.replace("\xa0", " ")

        if decode_entities:
            desc = html.unescape(desc)

        if add_separators:
            desc = _SECTION_BOUNDARY.sub(r"\1\n\2", desc)

        if collapse_ws:
            lines = desc.split("\n")
            lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
            desc = "\n".join(line for line in lines if line)

        row["description_text"] = desc.strip()

    logger.info("Text cleanup applied to %d rows", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Stage 5 — Privacy: redact personal information
# ---------------------------------------------------------------------------

# Czech and international phone patterns:
#   +420 123 456 789, +420123456789, 00420 123 456 789,
#   123 456 789, 123456789, 732 123 456
_PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\+\d{1,3}[\s-]?)?"
    r"(?:00\d{1,3}[\s-]?)?"
    r"\d{3}[\s-]?\d{3}[\s-]?\d{3}"
    r"(?!\d)"
)

_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Matches "Kontakt:" / "Contact:" / "Kontaktní osoba:" followed by a name
_CONTACT_NAME_PATTERN = re.compile(
    r"((?:Kontakt(?:ní osoba)?|Contact)\s*:\s*)"
    r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+){1,2})",
    re.IGNORECASE,
)


def redact_personal_info(rows: list[dict], config: dict) -> list[dict]:
    """Replace phone numbers, emails, and contact names with a placeholder."""
    priv_cfg = config.get("privacy", {})
    placeholder = priv_cfg.get("redaction_placeholder", "[REDACTED]")
    do_phones = priv_cfg.get("redact_phone_numbers", True)
    do_emails = priv_cfg.get("redact_emails", True)
    do_names = priv_cfg.get("redact_contact_names", True)

    phone_count = 0
    email_count = 0
    name_count = 0

    for row in rows:
        desc = row.get("description_text")
        if not desc:
            continue

        if do_emails:
            desc, n = _EMAIL_PATTERN.subn(placeholder, desc)
            email_count += n

        if do_phones:
            desc, n = _PHONE_PATTERN.subn(placeholder, desc)
            phone_count += n

        if do_names:
            desc, n = _CONTACT_NAME_PATTERN.subn(
                rf"\1{placeholder}", desc
            )
            name_count += n

        row["description_text"] = desc

    logger.info(
        "Privacy redaction: %d phones, %d emails, %d contact names redacted",
        phone_count,
        email_count,
        name_count,
    )
    return rows


# ---------------------------------------------------------------------------
# Stage 6 — Field normalization
# ---------------------------------------------------------------------------

# Common Czech legal suffixes and their canonical forms
_LEGAL_SUFFIX_MAP = {
    r"s\.\s*r\.\s*o\.": "s.r.o.",
    r"a\.\s*s\.": "a.s.",
    r"v\.\s*o\.\s*s\.": "v.o.s.",
    r"k\.\s*s\.": "k.s.",
    r"spol\.\s*s\s*r\.\s*o\.": "spol. s r.o.",
    r"z\.\s*s\.": "z.s.",
    r"z\.\s*ú\.": "z.ú.",
    r"o\.\s*p\.\s*s\.": "o.p.s.",
    r"s\.\s*p\.": "s.p.",
    r"SE": "SE",
}

# Pattern: "Street Name 123/4, City" or "Street Name 123, City – District"
# We try to extract the part after the last comma as the city.
_STREET_PREFIX = re.compile(
    r"^[A-Za-záčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ\s./]+\d+[a-zA-Z]?(?:/\d+[a-zA-Z]?)?\s*,\s*"
)


def normalize_fields(rows: list[dict], config: dict) -> list[dict]:
    """Trim whitespace, normalize provider suffixes, normalize locations,
    and validate URLs."""
    norm_cfg = config.get("normalization", {})
    do_trim = norm_cfg.get("trim_whitespace", True)
    do_provider = norm_cfg.get("normalize_provider_suffixes", True)
    do_location = norm_cfg.get("normalize_location", True)
    do_url = norm_cfg.get("validate_urls", True)

    url_warnings = 0

    for row in rows:
        if do_trim:
            for key in row:
                if isinstance(row[key], str):
                    row[key] = row[key].strip()

        if do_provider and row.get("provider"):
            row["provider"] = _normalize_provider(row["provider"])

        if do_location and row.get("location"):
            row["location"] = _normalize_location(row["location"])

        if do_url:
            url = row.get("url", "")
            if url and not url.startswith("https://"):
                logger.warning("Invalid URL for id=%s: %s", row.get("id", "?"), url)
                url_warnings += 1

    if url_warnings:
        logger.info("URL validation: %d warnings", url_warnings)
    logger.info("Field normalization applied to %d rows", len(rows))
    return rows


def _normalize_provider(provider: str) -> str:
    """Canonicalize legal entity suffixes in provider names."""
    result = provider.strip()
    for pattern, canonical in _LEGAL_SUFFIX_MAP.items():
        result = re.sub(pattern, canonical, result)
    # Collapse extra spaces
    result = re.sub(r"\s{2,}", " ", result).strip()
    # Remove trailing comma left over from suffix normalization
    result = result.rstrip(",").strip()
    return result


def _normalize_location(location: str) -> str:
    """Try to extract the city/district from a full address string.

    Examples:
        "Křižíkova 1884, Čelákovice"  ->  "Čelákovice"
        "5. května 1640/65, Praha – Nusle"  ->  "Praha – Nusle"
        "Praha 5 - Nové Butovice"  ->  "Praha 5 - Nové Butovice"  (unchanged)
        "Brno"  ->  "Brno"  (unchanged)
    """
    location = location.strip()
    # If there's a street + number + comma pattern, take what's after the comma
    match = _STREET_PREFIX.search(location)
    if match:
        city_part = location[match.end():].strip()
        if city_part:
            return city_part

    return location


# ---------------------------------------------------------------------------
# Stage 7 — Select output columns (drop description_html, etc.)
# ---------------------------------------------------------------------------


def select_columns(rows: list[dict], config: dict) -> list[dict]:
    """Keep only the columns listed in config -> output -> columns."""
    columns = config.get("output", {}).get("columns", [])
    if not columns:
        return rows

    result = []
    for row in rows:
        result.append({col: row.get(col, "") for col in columns})

    dropped = set(rows[0].keys()) - set(columns) if rows else set()
    if dropped:
        logger.info("Dropped columns: %s", sorted(dropped))
    return result
