import logging
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy.exceptions import CloseSpider
from w3lib.html import remove_tags

from jobs_cz_scraper.items import JobItem

logger = logging.getLogger("[jobs_cz.spider]")


class JobsCzSpider(scrapy.Spider):
    name = "jobs_cz"

    def __init__(self, config=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if config is None:
            raise CloseSpider(
                "Spider requires a 'config' dict from jobs_cz.yaml. "
                "Launch via runner.py, not scrapy crawl."
            )

        self.config = config
        scraper_cfg = config["scraper"]
        self.selectors = config["selectors"]

        # CONFIGURABLE: base URL for the jobs.cz site
        self.base_url = scraper_cfg["base_url"]

        # CONFIGURABLE: category URL slug (e.g. "administrativa")
        self.category_slug = scraper_cfg["category_slug"]

        # CONFIGURABLE: human-readable category name for CSV output
        self.category_name = scraper_cfg["category_name"]

        # CONFIGURABLE: maximum items to scrape (0 = unlimited)
        self.max_items = scraper_cfg["max_items"]

        self.items_scraped = 0
        self.start_urls = [
            f"{self.base_url}/prace/{self.category_slug}/?page=1"
        ]

        logger.info(
            "Spider initialized: category=%s, max_items=%d, start_url=%s",
            self.category_slug,
            self.max_items,
            self.start_urls[0],
        )

    # ------------------------------------------------------------------
    # Listing page parsing
    # ------------------------------------------------------------------

    def parse(self, response):
        """Parse a listing page and follow each job card's detail link."""
        sel = self.selectors["listing"]
        cards = response.css(sel["card"])

        if not cards:
            logger.warning(
                "No job cards found on listing page %s — "
                "the page structure may have changed",
                response.url,
            )
            return

        logger.info(
            "Found %d job cards on %s", len(cards), response.url
        )

        for card in cards:
            if self._limit_reached():
                return

            try:
                item_meta = self._extract_card_data(card, response)
            except Exception:
                logger.exception(
                    "Failed to extract card data on %s", response.url
                )
                continue

            yield scrapy.Request(
                url=item_meta["url"],
                callback=self.parse_detail,
                cb_kwargs={"item_meta": item_meta},
                errback=self._handle_request_error,
            )

        yield from self._follow_next_page(response)

    def _extract_card_data(self, card, response):
        """Pull basic fields out of a single SearchResultCard element."""
        sel = self.selectors["listing"]
        title_link = card.css(sel["title_link"])

        job_id = title_link.attrib.get(sel["job_id_attr"], "").strip()
        title = title_link.css("::text").get("").strip()
        detail_href = title_link.attrib.get("href", "")
        detail_url = urljoin(response.url, detail_href)

        company = card.css(f"{sel['company']}::text").get("").strip()
        location_text = card.css(f"{sel['location']} ::text").getall()
        location = " ".join(t.strip() for t in location_text if t.strip())
        # Strip leading SVG-related whitespace/icon text
        location = location.replace("\n", " ").strip()

        return {
            "id": job_id,
            "title": title,
            "provider": company,
            "location": location,
            "url": detail_url,
            "category": self.category_name,
        }

    def _follow_next_page(self, response):
        """Find and follow the next-page link if the item limit is not yet met."""
        if self._limit_reached():
            return

        sel = self.selectors["listing"]
        next_link = response.css(sel["next_page"]).attrib.get("href")
        if next_link:
            next_url = urljoin(response.url, next_link)
            logger.info("Following next listing page: %s", next_url)
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                errback=self._handle_request_error,
            )
        else:
            logger.info("No more listing pages found after %s", response.url)

    # ------------------------------------------------------------------
    # Detail page parsing
    # ------------------------------------------------------------------

    def parse_detail(self, response, item_meta):
        """Parse a job detail page and yield a complete JobItem.

        If the page redirected to a company subdomain (JS-rendered widget),
        we cannot scrape the description; log a warning and yield partial data.
        """
        if self._limit_reached():
            return

        item = JobItem(
            id=item_meta["id"],
            title=item_meta["title"],
            provider=item_meta["provider"],
            location=item_meta["location"],
            url=item_meta["url"],
            category=item_meta["category"],
            description_html=None,
            description_text=None,
        )

        parsed_url = urlparse(response.url)
        is_jobs_cz_domain = parsed_url.hostname in (
            "www.jobs.cz",
            "jobs.cz",
        )

        if not is_jobs_cz_domain:
            logger.warning(
                "Detail page for job %s redirected to external domain %s "
                "(JS-rendered widget) — description will be empty",
                item_meta["id"],
                parsed_url.hostname,
            )
            self.items_scraped += 1
            yield item
            return

        try:
            self._fill_detail_fields(response, item)
        except Exception:
            logger.exception(
                "Failed to parse detail page for job %s at %s",
                item_meta["id"],
                response.url,
            )

        self.items_scraped += 1
        logger.debug(
            "Scraped item %d/%d: id=%s title=%s",
            self.items_scraped,
            self.max_items,
            item["id"],
            item["title"][:60],
        )
        yield item

    def _fill_detail_fields(self, response, item):
        """Extract description HTML/text from a server-rendered /fp/ detail page."""
        sel = self.selectors["detail"]

        desc_node = response.css(sel["description"])
        if desc_node:
            raw_html = desc_node.get()
            item["description_html"] = raw_html
            item["description_text"] = remove_tags(raw_html).strip()
        else:
            logger.warning(
                "Description container not found on %s — "
                "page structure may have changed",
                response.url,
            )

        detail_title = response.css(f"{sel['title']}::text").get()
        if detail_title and detail_title.strip():
            item["title"] = detail_title.strip()

        detail_location = response.css(f"{sel['location']}::text").get()
        if detail_location and detail_location.strip():
            item["location"] = detail_location.strip()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _limit_reached(self):
        if self.max_items > 0 and self.items_scraped >= self.max_items:
            logger.info(
                "Item limit reached (%d). Stopping spider.", self.max_items
            )
            raise CloseSpider(f"Reached max_items limit of {self.max_items}")
        return False

    def _handle_request_error(self, failure):
        logger.error(
            "Request failed: %s — %s",
            failure.request.url,
            failure.getErrorMessage(),
        )
