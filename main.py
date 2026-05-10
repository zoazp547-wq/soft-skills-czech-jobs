#!/usr/bin/env python3
"""Main entry point for the webscrape-personal project.

Loads global and per-module YAML configuration, sets up logging,
and dispatches to the appropriate module runner.

Usage:
    python main.py                    # Run all enabled modules
    python main.py --module jobs_cz   # Run only the jobs_cz module
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import yaml

# ---------------------------------------------------------------------------
# Project root (directory containing this file)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# CONFIGURABLE: Paths to configuration files (relative to project root)
# ---------------------------------------------------------------------------
GLOBAL_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "settings.yaml")
MODULE_CONFIGS = {
    # CONFIGURABLE: Add new modules here as {name: config_path}
    "jobs_cz": os.path.join(PROJECT_ROOT, "config", "jobs_cz.yaml"),
    "cleanup": os.path.join(PROJECT_ROOT, "config", "cleanup.yaml"),
    "nlp": os.path.join(PROJECT_ROOT, "config", "nlp.yaml"),
    "tfidf": os.path.join(PROJECT_ROOT, "config", "tfidf.yaml"),
}


def load_yaml(path: str) -> dict:
    """Load and parse a YAML file, returning an empty dict on failure."""
    logger = logging.getLogger("[main]")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if data is None:
                logger.warning("YAML file is empty: %s", path)
                return {}
            return data
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", path)
        sys.exit(1)
    except yaml.YAMLError as exc:
        logger.error("Failed to parse YAML file %s: %s", path, exc)
        sys.exit(1)


def setup_logging(global_config: dict, module_name: str) -> None:
    """Configure the Python logging module from global settings."""
    log_cfg = global_config.get("logging", {})

    # CONFIGURABLE: Log level (DEBUG, INFO, WARNING, ERROR)
    level_name = log_cfg.get("level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # CONFIGURABLE: Log format string
    log_format = log_cfg.get(
        "format", "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )

    # CONFIGURABLE: Log directory
    log_dir = os.path.join(PROJECT_ROOT, log_cfg.get("log_dir", "logs"))
    os.makedirs(log_dir, exist_ok=True)

    # CONFIGURABLE: Log file name pattern
    file_pattern = log_cfg.get("file_pattern", "{module}_{timestamp}.log")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = file_pattern.format(module=module_name, timestamp=timestamp)
    log_filepath = os.path.join(log_dir, log_filename)

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filepath, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers,
    )

    logging.getLogger("[main]").info(
        "Logging initialized — level=%s, file=%s", level_name, log_filepath
    )


def run_module(module_name: str, global_config: dict) -> None:
    """Load module config and dispatch to the module's runner."""
    logger = logging.getLogger("[main]")

    config_path = MODULE_CONFIGS.get(module_name)
    if config_path is None:
        logger.error(
            "Unknown module '%s'. Available modules: %s",
            module_name,
            ", ".join(MODULE_CONFIGS.keys()),
        )
        sys.exit(1)

    module_config = load_yaml(config_path)
    logger.info("Loaded config for module '%s' from %s", module_name, config_path)

    if module_name == "jobs_cz":
        from modules.jobs_cz.runner import run as run_jobs_cz

        run_jobs_cz(global_config, module_config)
    elif module_name == "cleanup":
        from modules.cleanup.runner import run as run_cleanup

        run_cleanup(global_config, module_config)
    elif module_name == "nlp":
        from modules.nlp.runner import run as run_nlp

        run_nlp(global_config, module_config)
    elif module_name == "tfidf":
        from modules.tfidf.runner import run as run_tfidf

        run_tfidf(global_config, module_config)
    else:
        logger.error("Module '%s' has no runner implementation yet", module_name)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Webscrape-personal: modular web scraping toolkit"
    )
    parser.add_argument(
        "--module",
        type=str,
        default=None,
        help="Run a specific module (e.g. 'jobs_cz'). Omit to run all.",
    )
    args = parser.parse_args()

    global_config = load_yaml(GLOBAL_CONFIG_PATH)

    modules_to_run = (
        [args.module] if args.module else list(MODULE_CONFIGS.keys())
    )

    for module_name in modules_to_run:
        setup_logging(global_config, module_name)
        logger = logging.getLogger("[main]")
        logger.info("=" * 60)
        logger.info("Starting module: %s", module_name)
        logger.info("=" * 60)

        try:
            run_module(module_name, global_config)
        except SystemExit:
            raise
        except Exception:
            logger.exception("Module '%s' failed with an unhandled exception", module_name)

        logger.info("Module '%s' completed", module_name)


if __name__ == "__main__":
    main()
