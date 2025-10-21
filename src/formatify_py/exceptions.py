"""Custom exceptions for the formatify package."""

from typing import Optional


class FormatifyError(Exception):
    """Base exception class for formatify errors."""

    pass


class TimestampParsingError(FormatifyError):
    """Raised when timestamp parsing fails."""

    def __init__(
        self, timestamp: str, format_string: str, message: Optional[str] = None
    ):
        self.timestamp = timestamp
        self.format_string = format_string
        if message is None:
            message = (
                f"Failed to parse timestamp '{timestamp}' with format '{format_string}'"
            )
        super().__init__(message)


class InconsistentFormatError(FormatifyError):
    """Raised when timestamps have inconsistent component counts."""

    def __init__(self, component_counts: set, message: Optional[str] = None):
        self.component_counts = component_counts
        if message is None:
            message = f"Inconsistent component counts detected: {component_counts}"
        super().__init__(message)


class UnsupportedFormatError(FormatifyError):
    """Raised when an unsupported timestamp format is encountered."""

    def __init__(self, timestamp: str, message: Optional[str] = None):
        self.timestamp = timestamp
        if message is None:
            message = f"Unsupported timestamp format: '{timestamp}'"
        super().__init__(message)


class InsufficientDataError(FormatifyError):
    """Raised when insufficient data is provided for analysis."""

    def __init__(
        self,
        data_count: int,
        minimum_required: int = 1,
        message: Optional[str] = None,
    ):
        self.data_count = data_count
        self.minimum_required = minimum_required
        if message is None:
            message = (
                f"Insufficient data: got {data_count}, need at least {minimum_required}"
            )
        super().__init__(message)
