"""
core/exceptions.py
──────────────────────────────────────────────────────────────────────────────
Custom application exceptions representing domain-specific errors.
"""

class AppException(Exception):
    """Base custom exception for the application."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

class DomainNotFoundError(AppException):
    """Raised when an expected domain entity is not found (e.g., 404 mappings)."""
    pass

class DataProcessingError(AppException):
    """Raised when critical data validation or processing fails."""
    pass
