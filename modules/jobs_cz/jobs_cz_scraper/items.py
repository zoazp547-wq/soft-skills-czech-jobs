import scrapy


class JobItem(scrapy.Item):
    """Represents a single job listing scraped from jobs.cz.

    Fields correspond to the final CSV output columns.
    """

    # Unique identifier from data-jobad-id attribute
    id = scrapy.Field()

    # Job posting title
    title = scrapy.Field()

    # Company / agency that posted the job
    provider = scrapy.Field()

    # Geographic location of the job
    location = scrapy.Field()

    # Full URL to the job detail page
    url = scrapy.Field()

    # Rich HTML content of the job description (from detail page)
    description_html = scrapy.Field()

    # Plain-text version of the job description (HTML tags stripped)
    description_text = scrapy.Field()

    # Search category that this job was found under (e.g. "Administrativa")
    category = scrapy.Field()
