"""Runner for the NLP module.

Called by main.py with the parsed YAML config dicts. Reads the cleaned JSON,
applies the NLP processing pipeline, and writes the result to a new JSON.
"""

import json
import logging
import os

from modules.nlp.processor import process_rows

logger = logging.getLogger("[nlp.runner]")


def run(global_config: dict, module_config: dict) -> None:
    """Execute the NLP processing pipeline.

    Args:
        global_config: Parsed contents of config/settings.yaml.
        module_config: Parsed contents of config/nlp.yaml.
    """
    output_dir = global_config.get("output", {}).get("output_dir", "output")
    input_file = module_config.get("input", {}).get(
        "input_file", "jobs_cz_administrativa_clean.json"
    )
    output_file = module_config.get("output", {}).get(
        "output_file", "jobs_cz_administrativa_nlp.json"
    )

    input_path = os.path.join(output_dir, input_file)
    output_path = os.path.join(output_dir, output_file)

    # --- Load input JSON ---
    rows = _read_json(input_path)
    if not rows:
        logger.warning("No rows loaded from %s — nothing to process", input_path)
        return

    logger.info("Loaded %d rows from %s", len(rows), input_path)

    # --- Run NLP pipeline ---
    rows = process_rows(rows, module_config)

    # --- Write output JSON ---
    _write_json(rows, output_path)
    logger.info("NLP processing complete — %d rows written to %s", len(rows), output_path)


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
    """Write processed rows to a JSON file."""
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
