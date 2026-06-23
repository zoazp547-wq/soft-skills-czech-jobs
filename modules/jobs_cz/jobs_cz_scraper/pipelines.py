import json
import logging
import os

logger = logging.getLogger("[jobs_cz.pipeline]")

OUTPUT_FIELDS = [
    "id",
    "title",
    "provider",
    "location",
    "url",
    "description_html",
    "description_text",
    "category",
]


class JsonExportPipeline:
    """Writes each scraped JobItem to a JSON file, deduplicating by job ID.

    Output is a JSON array of objects, written incrementally and finalized
    on spider close.
    """

    def __init__(self, output_path):
        self.output_path = output_path
        self.seen_ids = set()
        self.items = []

    @classmethod
    def from_crawler(cls, crawler):
        # CONFIGURABLE: output file path is set via Scrapy custom settings
        output_path = crawler.settings.get("JOBSCZ_OUTPUT_PATH", "output/jobs.json")
        return cls(output_path)

    def open_spider(self):
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        logger.info("JSON export opened: %s", self.output_path)

    def close_spider(self):
        try:
            with open(self.output_path, "w", encoding="utf-8") as fh:
                json.dump(self.items, fh, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Failed to write JSON output: %s", self.output_path)

        logger.info(
            "JSON export closed: %s (%d unique items written)",
            self.output_path,
            len(self.seen_ids),
        )

    def process_item(self, item):
        job_id = item.get("id", "")
        if not job_id:
            logger.warning("Item missing 'id' field, skipping write: %s", dict(item))
            return item

        if job_id in self.seen_ids:
            logger.debug("Duplicate job id=%s, skipping write", job_id)
            return item

        self.seen_ids.add(job_id)

        row = {}
        for col in OUTPUT_FIELDS:
            value = item.get(col)
            row[col] = value if value is not None else ""

        self.items.append(row)

        return item
