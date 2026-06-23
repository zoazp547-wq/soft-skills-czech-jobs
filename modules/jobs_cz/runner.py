"""Runner for the jobs.cz Scrapy spider.

Called by main.py with the parsed YAML config dicts. Translates config
values into Scrapy settings and starts the CrawlerProcess.
"""

import logging
import os
import sys

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

logger = logging.getLogger("[jobs_cz.runner]")

# Ensure the Scrapy project package is importable
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)


def run(global_config: dict, module_config: dict) -> None:
    """Start the jobs.cz scraper.

    Args:
        global_config: Parsed contents of config/settings.yaml.
        module_config: Parsed contents of config/jobs_cz.yaml.
    """
    logger.info("Preparing jobs.cz Scrapy crawler")

    output_dir = global_config.get("output", {}).get("output_dir", "output")
    output_file = module_config["scraper"]["output_file"]
    output_path = os.path.join(output_dir, output_file)

    network_cfg = module_config.get("network", {})

    settings = get_project_settings()
    settings.setmodule("jobs_cz_scraper.settings")

    runtime_overrides = {
        # CONFIGURABLE: Network tuning from jobs_cz.yaml -> network section
        "USER_AGENT": network_cfg.get(
            "user_agent", settings.get("USER_AGENT")
        ),
        "DOWNLOAD_DELAY": network_cfg.get(
            "request_delay", settings.getfloat("DOWNLOAD_DELAY")
        ),
        "CONCURRENT_REQUESTS": network_cfg.get(
            "concurrent_requests", settings.getint("CONCURRENT_REQUESTS")
        ),
        "DOWNLOAD_TIMEOUT": network_cfg.get(
            "timeout", settings.getint("DOWNLOAD_TIMEOUT")
        ),
        "RETRY_TIMES": network_cfg.get(
            "retry_times", settings.getint("RETRY_TIMES")
        ),
        "ROBOTSTXT_OBEY": network_cfg.get(
            "obey_robotstxt", settings.getbool("ROBOTSTXT_OBEY")
        ),
        # CONFIGURABLE: Log level from global settings.yaml
        "LOG_LEVEL": global_config.get("logging", {}).get("level", "INFO"),
        # Pipeline receives the output path through a custom setting key
        "JOBSCZ_OUTPUT_PATH": output_path,
    }

    for key, value in runtime_overrides.items():
        settings.set(key, value, priority="cmdline")

    logger.info(
        "Scrapy settings applied — delay=%.1fs, concurrency=%d, output=%s",
        settings.getfloat("DOWNLOAD_DELAY"),
        settings.getint("CONCURRENT_REQUESTS"),
        output_path,
    )

    process = CrawlerProcess(settings)
    process.crawl(
        "jobs_cz",
        config=module_config,
    )
    process.start()

    logger.info("Crawler process finished")
