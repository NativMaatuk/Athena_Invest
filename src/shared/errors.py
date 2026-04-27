class AthenaError(Exception):
    """Base application error."""


class ValidationError(AthenaError):
    """Raised when user input is invalid."""


class ExternalServiceError(AthenaError):
    """Raised when a dependent external service fails."""


class RequestTimeoutError(ExternalServiceError):
    """Raised when an external request times out."""
