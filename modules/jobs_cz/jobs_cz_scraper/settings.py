"""Scrapy settings for the jobs_cz_scraper project.

These are the *default* settings. At runtime, runner.py overrides several of
them with values read from config/jobs_cz.yaml so that all configuration lives
in one place.  Overrides are applied via CrawlerProcess(settings={...}).
"""

BOT_NAME = "jobs_cz_scraper"
SPIDER_MODULES = ["jobs_cz_scraper.spiders"]
NEWSPIDER_MODULE = "jobs_cz_scraper.spiders"

# ---------------------------------------------------------------------------
# Defaults (overridden at runtime by runner.py from YAML config)
# ---------------------------------------------------------------------------

# CONFIGURABLE: User-Agent string
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# CONFIGURABLE: Obey robots.txt
ROBOTSTXT_OBEY = True

# CONFIGURABLE: Concurrent requests
CONCURRENT_REQUESTS = 4

# CONFIGURABLE: Download delay (seconds)
DOWNLOAD_DELAY = 1.5

# CONFIGURABLE: Download timeout (seconds)
DOWNLOAD_TIMEOUT = 30

# CONFIGURABLE: Retry count
RETRY_TIMES = 3

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

DOWNLOADER_MIDDLEWARES = {
    "jobs_cz_scraper.middlewares.RequestStatsMiddleware": 543,
}

# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

ITEM_PIPELINES = {
    "jobs_cz_scraper.pipelines.JsonExportPipeline": 300,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# CONFIGURABLE: Scrapy log level (overridden from settings.yaml at runtime)
LOG_LEVEL = "INFO"

# Disable the built-in log-to-file so we control logging ourselves
LOG_FILE = None
LOG_ENABLED = True

# ---------------------------------------------------------------------------
# Other
# ---------------------------------------------------------------------------

# Disable telnet console (not needed for scripted runs)
TELNETCONSOLE_ENABLED = False

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
