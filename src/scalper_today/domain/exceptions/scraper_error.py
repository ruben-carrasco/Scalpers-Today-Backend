from .external_service_error import ExternalServiceError


class ScraperError(ExternalServiceError):
    def __init__(self, message: str = "Failed to fetch data"):
        super().__init__(service="scraper", message=message)
        self.code = "SCRAPER_ERROR"
