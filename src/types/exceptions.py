class AppError(Exception):
    """Base exception for application-level failures."""


class ConfigError(AppError):
    """Invalid, missing, or unreadable configuration."""


class ScannerError(AppError):
    """Generic failure during automated data collection (scraping)."""


class LoginError(ScannerError):
    """LinkedIn authentication did not complete successfully."""


class SearchError(ScannerError):
    """Job search or listing parse failed (optional use by scrapers)."""


class ReportingError(AppError):
    """Persistence or external notification failed."""
