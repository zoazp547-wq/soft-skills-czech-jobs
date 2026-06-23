import logging
from urllib.parse import urlparse

logger = logging.getLogger("[jobs_cz.middleware]")


class RequestStatsMiddleware:
    """Logs high-level statistics about every request/response cycle."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request):
        logger.debug("Sending request: %s %s", request.method, request.url)
        return None

    def process_response(self, request, response):
        parsed = urlparse(response.url)
        is_external = parsed.hostname not in (
            "www.jobs.cz",
            "jobs.cz",
            None,
        )

        if is_external:
            logger.info(
                "Response from external domain %s (status %d) for request %s",
                parsed.hostname,
                response.status,
                request.url,
            )
        elif response.status >= 400:
            logger.warning(
                "HTTP %d on %s", response.status, response.url
            )

        return response

    def process_exception(self, request, exception):
        logger.error(
            "Request exception for %s: %s — %s",
            request.url,
            type(exception).__name__,
            exception,
        )
        return None
