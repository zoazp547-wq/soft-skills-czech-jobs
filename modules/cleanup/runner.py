"""Runner for the cleanup module.

Called by main.py with the parsed YAML config dicts. Reads the raw scraped
JSON, applies each cleanup stage in order, and writes the cleaned JSON.
"""

import json
import logging
import os

from modules.cleanup.cleaner import (
    clean_description_text,
    deduplicate,
    filter_required_fields,
    filter_short_descriptions,
    normalize_fields,
    redact_personal_info,
    select_columns,
)

logger = logging.getLogger("[cleanup.runner]")


def run(global_config: dict, module_config: dict) -> None:
    """Execute the full cleanup pipeline.

    Args:
        global_config: Parsed contents of config/settings.yaml.
        module_config: Parsed contents of config/cleanup.yaml.
    """
    output_dir = global_config.get("output", {}).get("output_dir", "output")
    input_file = module_config.get("input", {}).get(
        "input_file", "jobs_cz_administrativa.json"
    )
    output_file = module_config.get("output", {}).get(
        "output_file", "jobs_cz_administrativa_clean.json"
    )

    input_path = os.path.join(output_dir, input_file)
    output_path = os.path.join(output_dir, output_file)

    # --- Load input JSON ---
    rows = _read_json(input_path)
    if not rows:
        logger.warning("No rows loaded from %s — nothing to clean", input_path)
        return

    logger.info("Loaded %d rows from %s", len(rows), input_path)

    # --- Run cleanup stages in order ---
    rows = filter_required_fields(rows, module_config)
    rows = filter_short_descriptions(rows, module_config)
    rows = deduplicate(rows, module_config)
    rows = clean_description_text(rows, module_config)
    rows = redact_personal_info(rows, module_config)
    rows = normalize_fields(rows, module_config)
    rows = select_columns(rows, module_config)

    # --- Write output JSON ---
    _write_json(rows, output_path)
    logger.info("Cleanup complete — %d rows written to %s", len(rows), output_path)


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


def _write_json(rows: list[dict], path: str) -> None:
    """Write the cleaned rows to a JSON file."""
    if not rows:
        logger.warning("No rows to write — skipping JSON output")
        return

    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to write output JSON: %s", path)
