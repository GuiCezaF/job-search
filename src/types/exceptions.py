class AppError(Exception):
    """Base exception for the application."""
    pass

class ConfigError(AppError):
    """Raised when there is a configuration error."""
    pass

class ScannerError(AppError):
    """Raised when a scanner fails."""
    pass

class LoginError(ScannerError):
    """Raised when LinkedIn login fails."""
    pass

class SearchError(ScannerError):
    """Raised when LinkedIn search fails."""
    pass

class ReportingError(AppError):
    """Raised when reporting fails."""
    pass
